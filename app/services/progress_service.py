"""Learner progress aggregation for the Module 9 dashboard."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Learner, LearnerSkill, LearningProgress, Project, QuizAttempt
from app.schemas.progress import (
    NextRecommendation,
    PhaseProgressSummary,
    ProgressDashboard,
    ProjectProgressSummary,
    QuizPerformanceSummary,
    SkillProgressSummary,
    TopicProgressSummary,
)
from app.schemas.roadmap import PersonalizedRoadmap, RoadmapPhase

RECENT_QUIZ_LIMIT = 5
WEAK_SKILL_LIMIT = 5


def get_progress_dashboard(
    session: Session,
    learner_id: int,
    roadmap: PersonalizedRoadmap | None = None,
    *,
    today: date | None = None,
) -> ProgressDashboard:
    """Build a dashboard snapshot from persisted learner state and optional roadmap context."""
    learner = session.scalar(
        select(Learner)
        .where(Learner.id == learner_id)
        .options(selectinload(Learner.skills).selectinload(LearnerSkill.skill))
    )
    if learner is None:
        raise ValueError(f"Learner {learner_id} does not exist")

    progress_records = list(
        session.scalars(
            select(LearningProgress)
            .where(LearningProgress.learner_id == learner_id)
            .order_by(LearningProgress.last_activity_at.desc(), LearningProgress.topic)
        )
    )
    projects = list(
        session.scalars(
            select(Project).where(Project.learner_id == learner_id).order_by(Project.project_name)
        )
    )
    recent_quizzes = list(
        session.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.learner_id == learner_id)
            .order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc())
            .limit(RECENT_QUIZ_LIMIT)
        )
    )
    all_quizzes = list(
        session.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.learner_id == learner_id)
            .order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc())
        )
    )

    topics = tuple(_topic_summary(record) for record in progress_records)
    topic_by_name = {topic.topic: topic for topic in topics}
    phases = calculate_phase_completion(roadmap.phases if roadmap else (), topic_by_name)
    completed_topics = tuple(topic for topic in topics if _is_completed(topic))
    upcoming_tasks = tuple(topic for topic in topics if not _is_completed(topic))[:5]
    skills = tuple(sorted((_skill_summary(item) for item in learner.skills), key=lambda item: item.improvement_needed, reverse=True))
    weak_areas = tuple(skill for skill in skills if skill.improvement_needed > 0)[:WEAK_SKILL_LIMIT]
    project_summaries = tuple(_project_summary(project) for project in projects)
    quiz_summaries = tuple(_quiz_summary(attempt) for attempt in recent_quizzes)

    roadmap_completion = _roadmap_completion(phases, topics)
    topic_completion = _average([topic.completion_percentage for topic in topics])
    skill_improvement = _average([skill.progress_to_target_percentage for skill in skills])
    project_progress = _average([project.completion_percentage for project in project_summaries])
    quiz_average = _average([attempt.score for attempt in all_quizzes]) if all_quizzes else None
    current_phase = _current_phase(phases)
    streak = calculate_study_streak(progress_records, all_quizzes, today=today)

    overall_progress = calculate_overall_progress(
        roadmap_completion=roadmap_completion,
        topic_completion=topic_completion,
        skill_improvement=skill_improvement,
        project_progress=project_progress,
        quiz_average_score=quiz_average,
    )

    return ProgressDashboard(
        learner_id=learner.id,
        learner_name=learner.name,
        overall_progress_percentage=overall_progress,
        roadmap_completion_percentage=roadmap_completion,
        topic_completion_percentage=topic_completion,
        skill_improvement_percentage=skill_improvement,
        project_progress_percentage=project_progress,
        quiz_average_score=quiz_average,
        study_streak_days=streak,
        current_phase=current_phase,
        phases=phases,
        skills=skills,
        completed_topics=completed_topics,
        upcoming_tasks=upcoming_tasks,
        weak_areas=weak_areas,
        projects=project_summaries,
        recent_quiz_performance=quiz_summaries,
        next_recommendation=recommend_next_action(
            upcoming_tasks=upcoming_tasks,
            weak_areas=weak_areas,
            projects=project_summaries,
            recent_quizzes=quiz_summaries,
            current_phase=current_phase,
        ),
    )


def calculate_phase_completion(
    phases: tuple[RoadmapPhase, ...],
    topic_by_name: dict[str, TopicProgressSummary],
) -> tuple[PhaseProgressSummary, ...]:
    """Calculate completion percentages for roadmap phases."""
    summaries: list[PhaseProgressSummary] = []
    for phase in phases:
        percentages = [
            topic_by_name.get(topic).completion_percentage if topic in topic_by_name else 0.0
            for topic in phase.topics
        ]
        completion = _average(percentages)
        completed_count = sum(1 for percentage in percentages if percentage >= 100)
        status = "completed" if completion >= 100 else "in_progress" if completion > 0 else "not_started"
        summaries.append(
            PhaseProgressSummary(
                phase=phase.phase,
                goal=phase.goal,
                completion_percentage=completion,
                completed_topics=completed_count,
                total_topics=len(phase.topics),
                status=status,
                topics=phase.topics,
            )
        )
    return tuple(summaries)


def calculate_overall_progress(
    *,
    roadmap_completion: float,
    topic_completion: float,
    skill_improvement: float,
    project_progress: float,
    quiz_average_score: float | None,
) -> float:
    """Blend the available progress dimensions into one dashboard percentage."""
    weighted_values = [
        (roadmap_completion, 0.30),
        (topic_completion, 0.25),
        (skill_improvement, 0.25),
        (project_progress, 0.10),
    ]
    if quiz_average_score is not None:
        weighted_values.append((quiz_average_score * 10, 0.10))

    total_weight = sum(weight for _, weight in weighted_values)
    if total_weight == 0:
        return 0.0
    return round(sum(value * weight for value, weight in weighted_values) / total_weight, 1)


def calculate_study_streak(
    progress_records: list[LearningProgress],
    quiz_attempts: list[QuizAttempt],
    *,
    today: date | None = None,
) -> int:
    """Count consecutive activity days from today or the most recent prior activity day."""
    activity_dates = {
        _as_local_date(record.last_activity_at)
        for record in progress_records
        if record.last_activity_at is not None
    }
    activity_dates.update(
        _as_local_date(attempt.created_at)
        for attempt in quiz_attempts
        if attempt.created_at is not None
    )
    if not activity_dates:
        return 0

    anchor = today or datetime.now().astimezone().date()
    if anchor not in activity_dates:
        yesterday = anchor - timedelta(days=1)
        if yesterday in activity_dates:
            anchor = yesterday
        else:
            return 0

    streak = 0
    cursor = anchor
    while cursor in activity_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def recommend_next_action(
    *,
    upcoming_tasks: tuple[TopicProgressSummary, ...],
    weak_areas: tuple[SkillProgressSummary, ...],
    projects: tuple[ProjectProgressSummary, ...],
    recent_quizzes: tuple[QuizPerformanceSummary, ...],
    current_phase: PhaseProgressSummary | None,
) -> NextRecommendation:
    """Choose the next action from learner state instead of a fixed task list."""
    low_quiz = next((quiz for quiz in recent_quizzes if quiz.score < 7), None)
    if low_quiz is not None:
        return NextRecommendation(
            title=f"Review {low_quiz.topic} quiz feedback",
            rationale=f"Your recent {low_quiz.difficulty} quiz score was {low_quiz.score}/10.",
            action_type="quiz_review",
            topic=low_quiz.topic,
        )

    active_task = next((task for task in upcoming_tasks if task.status == "in_progress"), None)
    if active_task is not None:
        return NextRecommendation(
            title=f"Continue {active_task.topic}",
            rationale=f"This topic is already {active_task.completion_percentage}% complete.",
            action_type="topic",
            topic=active_task.topic,
        )

    weak_area = weak_areas[0] if weak_areas else None
    phase_topics = set(current_phase.topics) if current_phase is not None else set()
    if weak_area is not None:
        matching_task = next((task for task in upcoming_tasks if task.topic == weak_area.skill), None)
        if matching_task is not None or not phase_topics or weak_area.skill in phase_topics:
            return NextRecommendation(
                title=f"Practice {weak_area.skill}",
                rationale=f"It has the largest target gap at {weak_area.improvement_needed} points.",
                action_type="skill_practice",
                topic=weak_area.skill,
            )

    next_topic = upcoming_tasks[0] if upcoming_tasks else None
    if next_topic is not None:
        return NextRecommendation(
            title=f"Start {next_topic.topic}",
            rationale="It is the next incomplete topic in your tracked learning progress.",
            action_type="topic",
            topic=next_topic.topic,
        )

    active_project = next((project for project in projects if project.completion_percentage < 100), None)
    if active_project is not None:
        return NextRecommendation(
            title=f"Move project forward: {active_project.project_name}",
            rationale=f"The project is currently marked {active_project.status}.",
            action_type="project",
        )

    return NextRecommendation(
        title="Add your next learning activity",
        rationale="No incomplete topics, weak areas, quiz gaps, or active projects are currently tracked.",
        action_type="complete_profile",
    )


def _topic_summary(record: LearningProgress) -> TopicProgressSummary:
    return TopicProgressSummary(
        topic=record.topic,
        status=record.status,
        completion_percentage=_clamp_percentage(record.completion_percentage),
        score=record.score,
        last_activity_at=record.last_activity_at,
    )


def _skill_summary(learner_skill: object) -> SkillProgressSummary:
    target_score = float(learner_skill.target_score)
    current_score = float(learner_skill.proficiency_score)
    return SkillProgressSummary(
        skill=learner_skill.skill.name,
        category=learner_skill.skill.category,
        current_score=current_score,
        target_score=target_score,
        improvement_needed=round(max(target_score - current_score, 0), 1),
        progress_to_target_percentage=_progress_to_target(current_score, target_score),
        last_assessed_at=learner_skill.last_assessed_at,
    )


def _project_summary(project: Project) -> ProjectProgressSummary:
    return ProjectProgressSummary(
        project_name=project.project_name,
        description=project.description,
        status=project.status,
        completion_percentage=_project_completion(project.status),
        technologies=tuple(project.technologies),
    )


def _quiz_summary(attempt: QuizAttempt) -> QuizPerformanceSummary:
    return QuizPerformanceSummary(
        topic=attempt.topic,
        difficulty=attempt.difficulty,
        score=attempt.score,
        created_at=attempt.created_at,
        recommended_action=attempt.recommended_action,
    )


def _current_phase(phases: tuple[PhaseProgressSummary, ...]) -> PhaseProgressSummary | None:
    return next((phase for phase in phases if phase.status != "completed"), phases[-1] if phases else None)


def _roadmap_completion(
    phases: tuple[PhaseProgressSummary, ...],
    topics: tuple[TopicProgressSummary, ...],
) -> float:
    if phases:
        return _average([phase.completion_percentage for phase in phases])
    return _average([topic.completion_percentage for topic in topics])


def _is_completed(topic: TopicProgressSummary) -> bool:
    return topic.status == "completed" or topic.completion_percentage >= 100


def _progress_to_target(current_score: float, target_score: float) -> float:
    if target_score <= 0:
        return 100.0
    return _clamp_percentage((current_score / target_score) * 100)


def _project_completion(status: str) -> float:
    normalized_status = status.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized_status in {"completed", "complete", "done"}:
        return 100.0
    if normalized_status in {"in_progress", "active", "building"}:
        return 50.0
    if normalized_status in {"blocked", "paused"}:
        return 25.0
    return 0.0


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _clamp_percentage(value: float) -> float:
    return round(min(max(float(value), 0.0), 100.0), 1)


def _as_local_date(value: datetime) -> date:
    if value.tzinfo is None:
        return value.date()
    return value.astimezone().date()
