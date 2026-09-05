"""Tests for Module 4 skill gap dependency analysis."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.skill_gap import LearnerProfileInput, LearnerSkillInput, SkillGapAnalysisInput
from app.services.skill_gap_service import analyze_skill_gaps, canonical_skill_name, parse_timeline_weeks


def _analysis_input(skills: list[LearnerSkillInput], timeline: str = "6 months", hours: float = 8) -> SkillGapAnalysisInput:
    return SkillGapAnalysisInput(
        learner_profile=LearnerProfileInput(current_role="Data Analyst", experience_years=2),
        learner_skills=skills,
        target_role="Data Engineer",
        target_timeline=timeline,
        study_hours_per_week=hours,
    )


def test_dependency_graph_contains_requested_learning_chains() -> None:
    result = analyze_skill_gaps(_analysis_input([
        LearnerSkillInput(skill="Python", current_score=6),
        LearnerSkillInput(skill="SQL", current_score=7),
        LearnerSkillInput(skill="Linux", current_score=5),
        LearnerSkillInput(skill="Git", current_score=5),
        LearnerSkillInput(skill="ETL", current_score=4),
    ]))

    edges = {(edge.prerequisite, edge.unlocks) for edge in result.edges}
    assert ("Python", "PySpark") in edges
    assert ("PySpark", "Spark Optimization") in edges
    assert ("SQL", "Data Modeling") in edges
    assert ("Data Modeling", "Data Warehousing") in edges
    assert ("Linux", "Docker") in edges
    assert ("Git", "Docker") in edges
    assert ("Docker", "CI/CD") in edges
    assert ("ETL/ELT", "Orchestration") in edges


def test_graph_marks_skills_blocked_until_prerequisites_are_ready() -> None:
    result = analyze_skill_gaps(_analysis_input([
        LearnerSkillInput(skill="Python", current_score=3),
        LearnerSkillInput(skill="SQL", current_score=6),
        LearnerSkillInput(skill="Linux", current_score=5),
        LearnerSkillInput(skill="Git", current_score=5),
    ]))
    nodes = {node.skill: node for node in result.nodes}

    assert nodes["PySpark"].ready_to_learn is False
    assert "PySpark" in result.blocked_skills
    assert nodes["Data Modeling"].ready_to_learn is True
    assert "Data Modeling" in result.ready_to_learn


def test_capacity_uses_timeline_and_study_hours_without_generating_roadmap() -> None:
    result = analyze_skill_gaps(_analysis_input([
        LearnerSkillInput(skill="Python", current_score=7),
        LearnerSkillInput(skill="SQL", current_score=7.5),
        LearnerSkillInput(skill="Linux", current_score=6),
        LearnerSkillInput(skill="Git", current_score=6),
        LearnerSkillInput(skill="ETL/ELT", current_score=7),
        LearnerSkillInput(skill="PySpark", current_score=7),
        LearnerSkillInput(skill="Data Modeling", current_score=6.5),
        LearnerSkillInput(skill="Data Warehousing", current_score=6.5),
        LearnerSkillInput(skill="Docker", current_score=6),
        LearnerSkillInput(skill="CI/CD", current_score=0),
        LearnerSkillInput(skill="Spark Optimization", current_score=0),
        LearnerSkillInput(skill="Orchestration", current_score=0),
    ], timeline="10 weeks", hours=4))

    assert result.timeline_weeks == 10
    assert result.total_capacity_hours == 40
    assert result.required_gap_hours == 155.5
    assert result.capacity_status == "at_risk"
    assert not hasattr(result, "roadmap")


def test_skill_aliases_and_duplicate_detection_are_normalized() -> None:
    assert canonical_skill_name("Spark/PySpark") == "PySpark"
    with pytest.raises(ValueError, match="Duplicate learner skill supplied: PySpark"):
        analyze_skill_gaps(_analysis_input([
            LearnerSkillInput(skill="PySpark", current_score=4),
            LearnerSkillInput(skill="Apache Spark", current_score=5),
        ]))


def test_timeline_parser_accepts_common_units_and_rejects_missing_numbers() -> None:
    assert parse_timeline_weeks("3 months") == 12
    assert parse_timeline_weeks("12 wks") == 12
    assert parse_timeline_weeks("1 year") == 52
    assert parse_timeline_weeks("21 days") == 3
    with pytest.raises(ValueError, match="must include a number"):
        parse_timeline_weeks("soon")


def test_study_hours_must_be_feasible() -> None:
    with pytest.raises(ValidationError):
        _analysis_input([], hours=0)
