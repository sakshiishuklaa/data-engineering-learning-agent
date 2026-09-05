"""Tests for Module 5 personalized roadmap generation."""

from __future__ import annotations

from typing import Any

from app.schemas.assessment import AssessmentResult
from app.schemas.roadmap import PersonalizedRoadmap, RoadmapGenerationInput
from app.schemas.skill_gap import LearnerProfileInput, SkillGapAnalysisResult, SkillGapNode
from app.services.roadmap_service import generate_personalized_roadmap, validate_roadmap


class MockRoadmapLLMClient:
    """Simple structured-output fake for roadmap generation tests."""

    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.prompt = ""
        self.response_model: type[PersonalizedRoadmap] | None = None

    def generate_roadmap(self, *, prompt: str, response_model: type[PersonalizedRoadmap]) -> Any:
        self.prompt = prompt
        self.response_model = response_model
        if self.error is not None:
            raise self.error
        return self.response


def _node(
    skill: str,
    current_score: float,
    target_score: float,
    priority: str,
    prerequisites: tuple[str, ...] = (),
) -> SkillGapNode:
    return SkillGapNode(
        skill=skill,
        category="Data engineering",
        current_score=current_score,
        target_score=target_score,
        gap=round(max(target_score - current_score, 0), 1),
        priority=priority,
        status="met" if current_score >= target_score else "in_progress",
        prerequisites=prerequisites,
        unlocks=(),
        estimated_hours=24,
        ready_to_learn=True,
    )


def _generation_input() -> RoadmapGenerationInput:
    gap_analysis = SkillGapAnalysisResult(
        target_role="Data Engineer",
        timeline_weeks=8,
        study_hours_per_week=6,
        total_capacity_hours=48,
        required_gap_hours=72,
        capacity_status="tight",
        nodes=(
            _node("Python", 7, 7, "Low"),
            _node("SQL", 8, 7.5, "Low"),
            _node("PySpark", 1, 7, "Critical", ("Python",)),
            _node("Data Modeling", 1, 6.5, "High", ("SQL",)),
            _node("Data Warehousing", 1, 6.5, "High", ("Data Modeling",)),
            _node("Git", 5, 6, "Low"),
        ),
        edges=(),
        critical_gaps=("PySpark",),
        ready_to_learn=("PySpark", "Data Modeling", "Git"),
        blocked_skills=("Data Warehousing",),
    )
    return RoadmapGenerationInput(
        learner_profile=LearnerProfileInput(current_role="Data Analyst", experience_years=2),
        skill_assessment=(
            AssessmentResult(
                skill="PySpark",
                current_score=1,
                target_score=7,
                gap=6,
                level="Beginner",
                priority="Critical",
                confidence="High",
                evidence_sources=("Quiz",),
            ),
        ),
        skill_gap_analysis=gap_analysis,
        target_role="Data Engineer",
        target_timeline="8 weeks",
        weekly_study_hours=6,
    )


def _valid_roadmap_dict() -> dict[str, Any]:
    return {
        "target_role": "Data Engineer",
        "timeline_weeks": 8,
        "study_hours_per_week": 6,
        "total_estimated_weeks": 8,
        "phases": [
            {
                "phase": 1,
                "goal": "Build Spark foundations without repeating known Python.",
                "topics": ["PySpark"],
                "prerequisites": ["Python"],
                "priority": "MUST_LEARN",
                "estimated_duration_weeks": 3,
                "hands_on_exercises": ["Read partitioned files and run DataFrame transformations."],
                "mini_project": "Create a local PySpark batch job for CSV to parquet conversion.",
                "interview_questions": ["How does Spark distribute DataFrame work?"],
                "completion_criteria": ["Can write and explain a tested PySpark transformation."],
            },
            {
                "phase": 2,
                "goal": "Model analytics-ready data.",
                "topics": ["Data Modeling"],
                "prerequisites": ["SQL"],
                "priority": "MUST_LEARN",
                "estimated_duration_weeks": 2,
                "hands_on_exercises": ["Design facts and dimensions from event data."],
                "mini_project": "Build a star schema for product usage analytics.",
                "interview_questions": ["When would you denormalize analytics data?"],
                "completion_criteria": ["Can justify grain, keys, and table relationships."],
            },
            {
                "phase": 3,
                "goal": "Load modeled data into warehouse-style layers.",
                "topics": ["Data Warehousing"],
                "prerequisites": ["Data Modeling"],
                "priority": "MUST_LEARN",
                "estimated_duration_weeks": 2,
                "hands_on_exercises": ["Create staging, intermediate, and mart tables."],
                "mini_project": "Extend the model into a warehouse-style reporting layer.",
                "interview_questions": ["How do staging and mart layers differ?"],
                "completion_criteria": ["Can explain warehouse layers and load order."],
            },
            {
                "phase": 4,
                "goal": "Round out workflow basics.",
                "topics": ["Git"],
                "prerequisites": [],
                "priority": "OPTIONAL",
                "estimated_duration_weeks": 1,
                "hands_on_exercises": ["Use branches and pull-request style reviews."],
                "mini_project": "Version the previous projects with clean commits.",
                "interview_questions": ["How would you resolve a merge conflict?"],
                "completion_criteria": ["Can branch, commit, and review changes confidently."],
            },
        ],
    }


def test_generates_structured_roadmap_through_mock_llm_client() -> None:
    generation_input = _generation_input()
    client = MockRoadmapLLMClient(response=_valid_roadmap_dict())

    result = generate_personalized_roadmap(generation_input, client)

    assert result.success is True
    assert result.roadmap is not None
    assert client.response_model is PersonalizedRoadmap
    assert "structured JSON only" in client.prompt
    assert "Known skills to skip as topics" in client.prompt
    assert all("SQL" not in phase.topics for phase in result.roadmap.phases)


def test_rejects_roadmap_that_violates_known_topic_or_prerequisite_rules() -> None:
    generation_input = _generation_input()
    invalid_roadmap = _valid_roadmap_dict()
    invalid_roadmap["phases"][0]["topics"] = ["Data Warehousing", "SQL"]
    invalid_roadmap["phases"][0]["prerequisites"] = ["Data Modeling"]

    result = generate_personalized_roadmap(generation_input, MockRoadmapLLMClient(response=invalid_roadmap))

    assert result.success is False
    assert result.roadmap is None
    assert result.error == "Generated roadmap failed validation."
    assert any("already-known topic: SQL" in error for error in result.validation_errors)
    assert any("before prerequisites: Data Modeling" in error for error in result.validation_errors)


def test_validation_rejects_timeline_overrun_and_missing_must_learn_skills() -> None:
    generation_input = _generation_input()
    invalid_roadmap = PersonalizedRoadmap.model_validate(_valid_roadmap_dict() | {"timeline_weeks": 8})
    longer_roadmap = invalid_roadmap.model_copy(update={"total_estimated_weeks": 9})
    missing_required_roadmap = invalid_roadmap.model_copy(
        update={"phases": tuple(phase for phase in invalid_roadmap.phases if "PySpark" not in phase.topics)}
    )

    errors = validate_roadmap(longer_roadmap, generation_input)
    missing_errors = validate_roadmap(missing_required_roadmap, generation_input)

    assert "Roadmap exceeds the requested target timeline." in errors
    assert any("Roadmap omits MUST_LEARN skills" in error and "PySpark" in error for error in missing_errors)


def test_llm_failure_returns_graceful_error_without_raw_output() -> None:
    result = generate_personalized_roadmap(
        _generation_input(),
        MockRoadmapLLMClient(error=RuntimeError("API key missing")),
    )

    assert result.success is False
    assert result.roadmap is None
    assert result.error == "Roadmap generation failed. Please retry later."
    assert result.validation_errors == ()


def test_unparseable_llm_response_returns_graceful_error() -> None:
    result = generate_personalized_roadmap(
        _generation_input(),
        MockRoadmapLLMClient(response={"freeform": "learn spark then stuff"}),
    )

    assert result.success is False
    assert result.roadmap is None
    assert result.error == "Roadmap generation failed. Please retry later."
