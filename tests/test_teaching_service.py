"""Tests for Module 7 mentor and learning mode."""

from __future__ import annotations

from app.schemas.planner import LearningPlan, WeeklyPlanItem
from app.schemas.roadmap import PersonalizedRoadmap
from app.schemas.teaching import TeachingRequest, TeachingSession
from app.services.teaching_service import extract_topic, handle_teaching_command, parse_teaching_command


def _roadmap() -> PersonalizedRoadmap:
    return PersonalizedRoadmap.model_validate(
        {
            "target_role": "Data Engineer",
            "timeline_weeks": 6,
            "study_hours_per_week": 8,
            "total_estimated_weeks": 6,
            "phases": [
                {
                    "phase": 1,
                    "goal": "Build foundations.",
                    "topics": ["Python", "SQL", "PySpark"],
                    "prerequisites": [],
                    "priority": "MUST_LEARN",
                    "estimated_duration_weeks": 3,
                    "hands_on_exercises": ["Create Python and SQL pipeline basics."],
                    "mini_project": "Load source data into parquet.",
                    "interview_questions": ["How does a batch pipeline work?"],
                    "completion_criteria": ["Can run a small pipeline."],
                },
                {
                    "phase": 2,
                    "goal": "Improve Spark performance.",
                    "topics": ["Partitioning", "Joins"],
                    "prerequisites": ["PySpark"],
                    "priority": "MUST_LEARN",
                    "estimated_duration_weeks": 3,
                    "hands_on_exercises": ["Tune partitions and joins."],
                    "mini_project": "Optimize a Spark job.",
                    "interview_questions": ["What causes a shuffle?"],
                    "completion_criteria": ["Can explain the physical plan."],
                },
            ],
        }
    )


def _learning_plan() -> LearningPlan:
    weak_item = WeeklyPlanItem(
        day="Monday",
        topic="Joins",
        activity="Revision",
        duration=1,
        expected_outcome="Refresh weak points and prerequisites connected to Joins.",
    )
    next_item = WeeklyPlanItem(
        day="Monday",
        topic="Partitioning",
        activity="Learn",
        duration=1,
        expected_outcome="Understand the core concepts and vocabulary for Partitioning.",
    )
    return LearningPlan(weekly_plan=(weak_item, next_item), daily_plan={}, allocation={})


def test_parses_required_learning_commands_and_topics() -> None:
    assert parse_teaching_command("Teach me Spark") == "teach"
    assert extract_topic("Teach me Spark", "teach") == "PySpark"
    assert parse_teaching_command("Explain partitioning") == "explain"
    assert extract_topic("Explain partitioning", "explain") == "Partitioning"
    assert parse_teaching_command("Give me today's task") == "todays_task"
    assert parse_teaching_command("I don't understand joins") == "explain"
    assert extract_topic("I don't understand joins", "explain") == "Joins"
    assert parse_teaching_command("next topic") == "next_topic"


def test_teach_spark_returns_complete_teaching_flow_and_updates_session_topic() -> None:
    response = handle_teaching_command(
        TeachingRequest(
            message="Teach me Spark",
            session=TeachingSession(session_id="s1", learner_level="beginner", completed_topics=("Python",)),
            roadmap=_roadmap(),
        )
    )

    assert response.command == "teach"
    assert response.topic == "PySpark"
    assert response.session.current_topic == "PySpark"
    assert response.session.turn_count == 1
    assert response.flow.concept
    assert response.flow.simple_explanation
    assert response.flow.data_engineering_example
    assert "spark.read" in response.flow.code_example
    assert response.flow.hands_on_exercise
    assert response.flow.quiz[0].question
    assert response.flow.evaluation
    assert response.flow.next_step


def test_next_topic_prioritizes_weak_areas_before_future_roadmap_topics() -> None:
    response = handle_teaching_command(
        TeachingRequest(
            message="next topic",
            session=TeachingSession(
                session_id="s2",
                learner_level="intermediate",
                current_phase=2,
                completed_topics=("Python", "SQL", "PySpark"),
                weak_areas=("Joins",),
            ),
            roadmap=_roadmap(),
        )
    )

    assert response.command == "next_topic"
    assert response.topic == "Joins"
    assert "weak area" in response.flow.evaluation


def test_next_topic_skips_mastered_beginner_topics_in_current_phase() -> None:
    response = handle_teaching_command(
        TeachingRequest(
            message="next topic",
            session=TeachingSession(
                session_id="s3",
                learner_level="beginner",
                current_phase=1,
                completed_topics=("Python", "SQL"),
            ),
            roadmap=_roadmap(),
        )
    )

    assert response.topic == "PySpark"
    assert response.avoided_topics == ("Python", "SQL")


def test_explicit_mastered_beginner_topic_uses_advanced_context_instead_of_repeating_basics() -> None:
    response = handle_teaching_command(
        TeachingRequest(
            message="explain SQL",
            session=TeachingSession(
                session_id="s4",
                learner_level="beginner",
                completed_topics=("SQL",),
            ),
        )
    )

    assert response.topic == "SQL"
    assert "already have the beginner foundation" in response.flow.simple_explanation
    assert "production failure modes" in response.flow.evaluation


def test_todays_task_selects_unmastered_weak_plan_topic() -> None:
    response = handle_teaching_command(
        TeachingRequest(
            message="Give me today's task",
            session=TeachingSession(
                session_id="s5",
                learner_level="intermediate",
                completed_topics=("Partitioning",),
                weak_areas=("Joins",),
            ),
            learning_plan=_learning_plan(),
        )
    )

    assert response.command == "todays_task"
    assert response.topic == "Joins"
    assert response.session.current_topic == "Joins"
