"""Tests for Module 6 adaptive daily and weekly learning planner."""

from __future__ import annotations

import pytest

from app.schemas.planner import LearningPlannerInput, PlannerAllocation
from app.schemas.roadmap import PersonalizedRoadmap
from app.services.planner_service import generate_learning_plan


def _roadmap() -> PersonalizedRoadmap:
    return PersonalizedRoadmap.model_validate(
        {
            "target_role": "Data Engineer",
            "timeline_weeks": 6,
            "study_hours_per_week": 10,
            "total_estimated_weeks": 6,
            "phases": [
                {
                    "phase": 1,
                    "goal": "Build Spark foundations.",
                    "topics": ["PySpark"],
                    "prerequisites": ["Python"],
                    "priority": "MUST_LEARN",
                    "estimated_duration_weeks": 2,
                    "hands_on_exercises": ["Transform local files with DataFrames."],
                    "mini_project": "Build a CSV to parquet PySpark job.",
                    "interview_questions": ["How does Spark distribute work?"],
                    "completion_criteria": ["Can explain a DataFrame transformation."],
                },
                {
                    "phase": 2,
                    "goal": "Model analytics data.",
                    "topics": ["Data Modeling"],
                    "prerequisites": ["SQL"],
                    "priority": "MUST_LEARN",
                    "estimated_duration_weeks": 2,
                    "hands_on_exercises": ["Design fact and dimension tables."],
                    "mini_project": "Create a product analytics star schema.",
                    "interview_questions": ["What is table grain?"],
                    "completion_criteria": ["Can justify keys, grain, and relationships."],
                },
                {
                    "phase": 3,
                    "goal": "Create warehouse layers.",
                    "topics": ["Data Warehousing"],
                    "prerequisites": ["Data Modeling"],
                    "priority": "MUST_LEARN",
                    "estimated_duration_weeks": 2,
                    "hands_on_exercises": ["Build staging and mart tables."],
                    "mini_project": "Extend the model into reporting layers.",
                    "interview_questions": ["How do staging and marts differ?"],
                    "completion_criteria": ["Can describe warehouse load order."],
                },
            ],
        }
    )


def test_generates_weekly_and_daily_plan_with_default_allocation() -> None:
    plan = generate_learning_plan(
        LearningPlannerInput(
            personalized_roadmap=_roadmap(),
            available_study_hours=10,
            completed_topics=("Python",),
            current_phase=1,
            weak_topics=("PySpark",),
        )
    )

    assert len(plan.weekly_plan) == 35
    assert plan.allocation.theory == 0.30
    assert plan.allocation.hands_on == 0.50
    assert plan.allocation.interview_practice == 0.20
    assert {item.activity for item in plan.weekly_plan} == {
        "Learn",
        "Practice",
        "Hands-on",
        "Revision",
        "Interview practice",
    }
    assert plan.daily_plan.learn
    assert plan.daily_plan.practice
    assert plan.daily_plan.hands_on
    assert plan.daily_plan.revision
    assert plan.daily_plan.interview_practice
    assert all(item.topic != "Python" for item in plan.weekly_plan)


def test_custom_allocation_changes_generated_durations() -> None:
    plan = generate_learning_plan(
        LearningPlannerInput(
            personalized_roadmap=_roadmap(),
            available_study_hours=10,
            completed_topics=("Python",),
            allocation=PlannerAllocation(theory=0.2, hands_on=0.6, interview_practice=0.2),
        )
    )

    monday = [item for item in plan.weekly_plan if item.day == "Monday"]

    assert next(item.duration for item in monday if item.activity == "Learn") == 0.21
    assert next(item.duration for item in monday if item.activity == "Hands-on") == 0.86
    assert next(item.duration for item in monday if item.activity == "Revision") == 0.07
    assert next(item.duration for item in monday if item.activity == "Practice") == 0.14
    assert next(item.duration for item in monday if item.activity == "Interview practice") == 0.14


def test_completed_topics_are_skipped_unless_revision_is_required() -> None:
    without_revision = generate_learning_plan(
        LearningPlannerInput(
            personalized_roadmap=_roadmap(),
            available_study_hours=8,
            completed_topics=("Python", "PySpark"),
            current_phase=1,
        )
    )
    with_revision = generate_learning_plan(
        LearningPlannerInput(
            personalized_roadmap=_roadmap(),
            available_study_hours=8,
            completed_topics=("Python", "PySpark"),
            current_phase=1,
            revision_required_topics=("PySpark",),
        )
    )

    assert all(item.topic != "PySpark" for item in without_revision.weekly_plan)
    assert any(item.topic == "PySpark" for item in with_revision.weekly_plan)


def test_falling_behind_reschedules_incomplete_tasks_and_preserves_prerequisites() -> None:
    plan = generate_learning_plan(
        LearningPlannerInput(
            personalized_roadmap=_roadmap(),
            available_study_hours=10,
            completed_topics=("Python",),
            current_phase=2,
            incomplete_tasks=("PySpark",),
        )
    )

    scheduled_topics = [item.topic for item in plan.weekly_plan]

    assert plan.rescheduled_topics == ("PySpark",)
    assert "SQL" in plan.preserved_prerequisites
    assert scheduled_topics.index("PySpark") < scheduled_topics.index("Data Modeling")
    assert "Data Warehousing" in scheduled_topics


def test_rejects_allocation_that_does_not_sum_to_one() -> None:
    with pytest.raises(ValueError, match="Planner allocation must sum to 1.0"):
        PlannerAllocation(theory=0.4, hands_on=0.4, interview_practice=0.3)
