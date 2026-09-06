"""Tests for Module 9 learner progress dashboard calculations."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models import QuizAttempt
from app.schemas.progress import SkillProgressSummary, TopicProgressSummary
from app.schemas.roadmap import PersonalizedRoadmap, RoadmapPhase
from app.services.learner_memory_service import (
    add_skill_to_learner,
    create_learner,
    create_learning_progress,
    create_project,
    create_skill,
    update_learning_progress,
)
from app.services.progress_service import (
    calculate_overall_progress,
    calculate_phase_completion,
    calculate_study_streak,
    get_progress_dashboard,
    recommend_next_action,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    database_session = session_factory()
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _roadmap() -> PersonalizedRoadmap:
    return PersonalizedRoadmap(
        target_role="Data Engineer",
        timeline_weeks=6,
        study_hours_per_week=8,
        total_estimated_weeks=6,
        phases=(
            RoadmapPhase(
                phase=1,
                goal="Build SQL foundations",
                topics=("SQL", "Data Modeling"),
                priority="MUST_LEARN",
                estimated_duration_weeks=3,
                hands_on_exercises=("Write joins and aggregations.",),
                mini_project="Model an orders dataset.",
                interview_questions=("Explain GROUP BY.",),
                completion_criteria=("Complete SQL and modeling tasks.",),
            ),
            RoadmapPhase(
                phase=2,
                goal="Build pipeline foundations",
                topics=("ETL/ELT",),
                priority="GOOD_TO_LEARN",
                estimated_duration_weeks=3,
                hands_on_exercises=("Create a batch pipeline.",),
                mini_project="Load cleaned data into a warehouse.",
                interview_questions=("Explain idempotency.",),
                completion_criteria=("Complete the pipeline project.",),
            ),
        ),
    )


def _topic(topic: str, percentage: float, status: str = "in_progress") -> TopicProgressSummary:
    return TopicProgressSummary(
        topic=topic,
        status=status,
        completion_percentage=percentage,
        last_activity_at=datetime(2026, 9, 7, 9, 0),
    )


def _skill(skill: str, current: float, target: float) -> SkillProgressSummary:
    return SkillProgressSummary(
        skill=skill,
        category="Test",
        current_score=current,
        target_score=target,
        improvement_needed=max(target - current, 0),
        progress_to_target_percentage=round((current / target) * 100, 1),
    )


def test_calculates_phase_completion_from_topic_state() -> None:
    topic_by_name = {
        "SQL": _topic("SQL", 100, "completed"),
        "Data Modeling": _topic("Data Modeling", 50),
    }

    phases = calculate_phase_completion(_roadmap().phases, topic_by_name)

    assert phases[0].completion_percentage == 75
    assert phases[0].completed_topics == 1
    assert phases[0].status == "in_progress"
    assert phases[1].completion_percentage == 0
    assert phases[1].status == "not_started"


def test_overall_progress_blends_available_dimensions() -> None:
    progress = calculate_overall_progress(
        roadmap_completion=50,
        topic_completion=60,
        skill_improvement=70,
        project_progress=40,
        quiz_average_score=8,
    )

    assert progress == 59.5


def test_study_streak_uses_progress_and_quiz_activity(session: Session) -> None:
    learner = create_learner(session, name="Asha Patel")
    skill = create_skill(session, name="SQL", category="Databases")
    progress = create_learning_progress(session, learner.id, "SQL", status="in_progress", completion_percentage=20)
    today = datetime(2026, 9, 7, 9, 0)
    update_learning_progress(session, learner.id, progress.topic, last_activity_at=today - timedelta(days=2))
    session.add(
        QuizAttempt(
            learner_id=learner.id,
            skill_id=skill.id,
            topic="SQL",
            difficulty="Beginner",
            question="Question",
            learner_answer="Answer",
            score=8,
            correct_points=[],
            missing_points=[],
            mistakes=[],
            improved_answer="Improved",
            recommended_action="Keep practicing.",
            created_at=today - timedelta(days=1),
        )
    )
    session.commit()

    assert calculate_study_streak(list(learner.progress_records), list(learner.quiz_attempts), today=today.date()) == 2


def test_dashboard_aggregates_learner_state_and_recommends_quiz_review(session: Session) -> None:
    learner = create_learner(session, name="Asha Patel")
    sql = create_skill(session, name="SQL", category="Databases")
    etl = create_skill(session, name="ETL/ELT", category="Data pipelines")
    add_skill_to_learner(session, learner.id, sql.id, proficiency_score=40, target_score=80)
    add_skill_to_learner(session, learner.id, etl.id, proficiency_score=55, target_score=75)
    create_learning_progress(session, learner.id, "SQL", status="completed", completion_percentage=100, score=90)
    create_learning_progress(session, learner.id, "Data Modeling", status="in_progress", completion_percentage=50)
    create_project(session, learner.id, "Orders Warehouse", status="in_progress", technologies=["SQL", "dbt"])
    session.add(
        QuizAttempt(
            learner_id=learner.id,
            skill_id=sql.id,
            topic="SQL",
            difficulty="Intermediate",
            question="Question",
            learner_answer="Answer",
            score=6,
            correct_points=[],
            missing_points=["HAVING"],
            mistakes=[],
            improved_answer="Improved",
            recommended_action="Review aggregate filters.",
        )
    )
    session.commit()

    dashboard = get_progress_dashboard(session, learner.id, _roadmap(), today=datetime.now().date())

    assert dashboard.learner_name == "Asha Patel"
    assert dashboard.current_phase is not None
    assert dashboard.current_phase.phase == 1
    assert dashboard.roadmap_completion_percentage == 37.5
    assert dashboard.topic_completion_percentage == 75
    assert dashboard.project_progress_percentage == 50
    assert dashboard.quiz_average_score == 6
    assert dashboard.completed_topics[0].topic == "SQL"
    assert dashboard.upcoming_tasks[0].topic == "Data Modeling"
    assert dashboard.weak_areas[0].skill == "SQL"
    assert dashboard.next_recommendation.action_type == "quiz_review"
    assert dashboard.next_recommendation.topic == "SQL"


def test_recommendation_uses_active_task_when_no_low_quiz() -> None:
    recommendation = recommend_next_action(
        upcoming_tasks=(_topic("Data Modeling", 40),),
        weak_areas=(_skill("SQL", 70, 80),),
        projects=(),
        recent_quizzes=(),
        current_phase=None,
    )

    assert recommendation.action_type == "topic"
    assert recommendation.topic == "Data Modeling"
