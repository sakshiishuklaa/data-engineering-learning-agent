"""Validated inputs and results for the skill assessment engine."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

SkillLevel = Literal["Beginner", "Intermediate", "Advanced", "Expert"]
Priority = Literal["Critical", "High", "Medium", "Low"]
Confidence = Literal["Low", "Medium", "High"]


class SkillAssessmentInput(BaseModel):
    """Evidence supplied for one data-engineering skill."""

    skill: str
    self_reported_score: float = Field(ge=1, le=10)
    target_score: float = Field(ge=1, le=10)
    diagnostic_score: float | None = Field(default=None, ge=0, le=10)
    quiz_score: float | None = Field(default=None, ge=0, le=10)
    project_evidence_score: float | None = Field(default=None, ge=0, le=10)

    @model_validator(mode="after")
    def target_must_not_be_lower_than_current_claim(self) -> "SkillAssessmentInput":
        if self.target_score < self.self_reported_score:
            raise ValueError("Target score must be at least the self-reported score.")
        return self


class AssessmentResult(BaseModel):
    """Calculated, explainable assessment result for one skill."""

    skill: str
    current_score: float = Field(ge=1, le=10)
    target_score: float = Field(ge=1, le=10)
    gap: float = Field(ge=0, le=9)
    level: SkillLevel
    priority: Priority
    confidence: Confidence
    evidence_sources: tuple[str, ...]
