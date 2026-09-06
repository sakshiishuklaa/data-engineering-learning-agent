"""Adaptive daily and weekly learning planner for roadmap phases."""

from __future__ import annotations

from app.schemas.planner import (
    DailyPlan,
    LearningPlannerInput,
    LearningPlan,
    PlanActivityType,
    WeeklyPlanItem,
)
from app.schemas.roadmap import RoadmapPhase

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def generate_learning_plan(planner_input: LearningPlannerInput) -> LearningPlan:
    """Generate a weekly table and daily activity buckets from a roadmap."""
    completed_topics = _normalized_set(planner_input.completed_topics)
    weak_topics = _normalized_set(planner_input.weak_topics)
    revision_required_topics = _normalized_set(planner_input.revision_required_topics)
    incomplete_topics = _normalized_set(planner_input.incomplete_tasks)
    phase_lookup = {phase.phase: phase for phase in planner_input.personalized_roadmap.phases}
    eligible_phases = tuple(
        phase for phase in planner_input.personalized_roadmap.phases if phase.phase >= planner_input.current_phase
    )

    topic_phase = {
        _normalize_topic(topic): phase
        for phase in planner_input.personalized_roadmap.phases
        for topic in phase.topics
    }
    prerequisite_topics = _required_prerequisites(
        phase_lookup=phase_lookup,
        current_phase=planner_input.current_phase,
        completed_topics=completed_topics,
        revision_required_topics=revision_required_topics,
        incomplete_topics=incomplete_topics,
    )

    scheduled_topics: list[str] = []
    for topic in planner_input.incomplete_tasks:
        normalized_topic = _normalize_topic(topic)
        if normalized_topic in completed_topics and normalized_topic not in revision_required_topics:
            continue
        phase = topic_phase.get(normalized_topic)
        if phase is None:
            continue
        scheduled_topics.extend(_topic_with_needed_prerequisites(topic, phase, completed_topics, scheduled_topics))

    for topic in prerequisite_topics:
        if _normalize_topic(topic) not in completed_topics or _normalize_topic(topic) in revision_required_topics:
            _append_unique(scheduled_topics, topic)

    for phase in eligible_phases:
        for topic in phase.topics:
            normalized_topic = _normalize_topic(topic)
            if normalized_topic in completed_topics and normalized_topic not in revision_required_topics:
                continue
            scheduled_topics.extend(_topic_with_needed_prerequisites(topic, phase, completed_topics, scheduled_topics))

    scheduled_topics = _unique_in_order(scheduled_topics)
    weekly_plan = _build_weekly_plan(planner_input, scheduled_topics, weak_topics, incomplete_topics)
    return LearningPlan(
        weekly_plan=tuple(weekly_plan),
        daily_plan=_build_daily_plan(weekly_plan),
        allocation=planner_input.allocation,
        rescheduled_topics=tuple(
            topic
            for topic in scheduled_topics
            if _normalize_topic(topic) in incomplete_topics
        ),
        preserved_prerequisites=tuple(_unique_in_order(prerequisite_topics)),
    )


def _required_prerequisites(
    *,
    phase_lookup: dict[int, RoadmapPhase],
    current_phase: int,
    completed_topics: set[str],
    revision_required_topics: set[str],
    incomplete_topics: set[str],
) -> list[str]:
    prerequisites: list[str] = []
    for phase_number in range(1, current_phase + 1):
        phase = phase_lookup.get(phase_number)
        if phase is None:
            continue
        for prerequisite in phase.prerequisites:
            normalized_prerequisite = _normalize_topic(prerequisite)
            if normalized_prerequisite in completed_topics and normalized_prerequisite not in revision_required_topics:
                continue
            if normalized_prerequisite in incomplete_topics or phase_number == current_phase:
                _append_unique(prerequisites, prerequisite)
    return prerequisites


def _topic_with_needed_prerequisites(
    topic: str,
    phase: RoadmapPhase,
    completed_topics: set[str],
    already_scheduled: list[str],
) -> list[str]:
    topics: list[str] = []
    for prerequisite in phase.prerequisites:
        normalized_prerequisite = _normalize_topic(prerequisite)
        if normalized_prerequisite not in completed_topics and normalized_prerequisite not in _normalized_set(already_scheduled):
            topics.append(prerequisite)
    topics.append(topic)
    return topics


def _build_weekly_plan(
    planner_input: LearningPlannerInput,
    topics: list[str],
    weak_topics: set[str],
    incomplete_topics: set[str],
) -> list[WeeklyPlanItem]:
    if not topics:
        topics = ["Revision"]

    daily_hours = round(planner_input.available_study_hours / planner_input.days_per_week, 2)
    blocks = (
        ("Learn", round(daily_hours * planner_input.allocation.theory * 0.75, 2)),
        ("Practice", round(daily_hours * planner_input.allocation.interview_practice * 0.5, 2)),
        ("Hands-on", round(daily_hours * planner_input.allocation.hands_on, 2)),
        ("Revision", round(daily_hours * planner_input.allocation.theory * 0.25, 2)),
        ("Interview practice", round(daily_hours * planner_input.allocation.interview_practice * 0.5, 2)),
    )
    positive_blocks = tuple((activity, duration or 0.25) for activity, duration in blocks if duration > 0)
    plan: list[WeeklyPlanItem] = []
    topic_index = 0

    for day_index in range(planner_input.days_per_week):
        day = DAY_NAMES[day_index]
        focus_topic = topics[min(topic_index, len(topics) - 1)]
        for activity, duration in positive_blocks:
            if activity == "Revision":
                topic = _revision_topic(topics, focus_topic, weak_topics, day_index)
            else:
                topic = focus_topic
            plan.append(
                WeeklyPlanItem(
                    day=day,
                    topic=topic,
                    activity=activity,
                    duration=duration,
                    expected_outcome=_expected_outcome(activity, topic, _normalize_topic(topic) in incomplete_topics),
                )
            )
        if day_index % 2 == 1 and topic_index < len(topics) - 1:
            topic_index += 1

    return plan


def _build_daily_plan(weekly_plan: list[WeeklyPlanItem]) -> DailyPlan:
    def items_for(activity: PlanActivityType) -> tuple[WeeklyPlanItem, ...]:
        return tuple(item for item in weekly_plan if item.activity.startswith(activity))

    return DailyPlan(
        learn=items_for("Learn"),
        practice=items_for("Practice"),
        hands_on=items_for("Hands-on"),
        revision=items_for("Revision"),
        interview_practice=items_for("Interview practice"),
    )


def _revision_topic(topics: list[str], focus_topic: str, weak_topics: set[str], day_index: int) -> str:
    weak_topic_labels = [topic for topic in topics if _normalize_topic(topic) in weak_topics]
    if weak_topic_labels:
        return weak_topic_labels[day_index % len(weak_topic_labels)]
    return focus_topic


def _expected_outcome(activity: str, topic: str, is_incomplete: bool) -> str:
    outcomes = {
        "Learn": f"Understand the core concepts and vocabulary for {topic}.",
        "Practice": f"Solve focused exercises that reinforce {topic}.",
        "Hands-on": f"Produce a working artifact or notebook using {topic}.",
        "Revision": f"Refresh weak points and prerequisites connected to {topic}.",
        "Interview practice": f"Answer and explain interview prompts about {topic}.",
    }
    if is_incomplete:
        return f"Rescheduled: {outcomes[activity]}"
    return outcomes[activity]


def _append_unique(items: list[str], item: str) -> None:
    if _normalize_topic(item) not in _normalized_set(items):
        items.append(item)


def _unique_in_order(items: list[str]) -> list[str]:
    unique: list[str] = []
    for item in items:
        _append_unique(unique, item)
    return unique


def _normalized_set(topics: tuple[str, ...] | list[str]) -> set[str]:
    return {_normalize_topic(topic) for topic in topics}


def _normalize_topic(topic: str) -> str:
    return " ".join(topic.strip().lower().split())
