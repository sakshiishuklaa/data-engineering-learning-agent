"""Tests for evidence-weighted skill assessment."""

from __future__ import annotations

import pytest

from app.schemas.assessment import SkillAssessmentInput
from app.services.assessment_service import DATA_ENGINEERING_SKILLS, DIAGNOSTIC_QUESTIONS, assess_skill, assess_skills, level_for_score


def test_assessment_uses_objective_evidence_not_just_self_report() -> None:
    result = assess_skill(SkillAssessmentInput(skill="Python", self_reported_score=9, target_score=10,
                                                diagnostic_score=4, quiz_score=5, project_evidence_score=6))
    assert result.current_score == 5.7
    assert result.level == "Intermediate"
    assert result.gap == 4.3
    assert result.priority == "High"
    assert result.confidence == "High"
    assert result.evidence_sources == ("Self report", "Diagnostic", "Quiz", "Project evidence")


@pytest.mark.parametrize(("score", "expected"), [(1, "Beginner"), (3, "Beginner"), (4, "Intermediate"), (6, "Intermediate"), (7, "Advanced"), (8, "Advanced"), (9, "Expert"), (10, "Expert")])
def test_level_boundaries(score: int, expected: str) -> None:
    assert level_for_score(score) == expected


def test_self_report_only_result_is_marked_low_confidence() -> None:
    result = assess_skill(SkillAssessmentInput(skill="SQL", self_reported_score=6, target_score=7))
    assert result.current_score == 6
    assert result.confidence == "Low"
    assert result.priority == "Low"


def test_batch_requires_every_canonical_skill_once() -> None:
    assessments = [SkillAssessmentInput(skill=skill, self_reported_score=3, target_score=7) for skill in DATA_ENGINEERING_SKILLS]
    assert len(assess_skills(assessments)) == len(DATA_ENGINEERING_SKILLS)
    with pytest.raises(ValueError, match="Missing skills"):
        assess_skills(assessments[:-1])


def test_each_canonical_skill_has_an_optional_diagnostic_question() -> None:
    assert set(DIAGNOSTIC_QUESTIONS) == set(DATA_ENGINEERING_SKILLS)
