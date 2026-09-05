"""Validated inputs and graph results for the skill gap analysis engine."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GapPriority = Literal["Critical", "High", "Medium", "Low"]
GapStatus = Literal["met", "in_progress", "not_started"]
CapacityStatus = Literal["manageable", "tight", "at_risk"]


class LearnerProfileInput(BaseModel):
    """Career context supplied by onboarding or another caller."""

    current_role: str | None = None
    experience_years: float | None = Field(default=None, ge=0)
    target_company_type: str | None = None
    preferred_cloud: str | None = None
    learning_preference: str | None = None


class LearnerSkillInput(BaseModel):
    """The learner's current score for one skill on a 0--10 scale."""

    skill: str
    current_score: float = Field(ge=0, le=10)


class SkillGapAnalysisInput(BaseModel):
    """Inputs required for Module 4 skill dependency analysis."""

    learner_profile: LearnerProfileInput
    learner_skills: list[LearnerSkillInput]
    target_role: str
    target_timeline: str
    study_hours_per_week: float = Field(gt=0, le=168)


class SkillGapNode(BaseModel):
    """One skill in the target-role dependency graph."""

    skill: str
    category: str
    current_score: float = Field(ge=0, le=10)
    target_score: float = Field(ge=0, le=10)
    gap: float = Field(ge=0, le=10)
    priority: GapPriority
    status: GapStatus
    prerequisites: tuple[str, ...]
    unlocks: tuple[str, ...]
    estimated_hours: float = Field(ge=0)
    ready_to_learn: bool


class SkillGapEdge(BaseModel):
    """A prerequisite relationship in the graph."""

    prerequisite: str
    unlocks: str


class SkillGapAnalysisResult(BaseModel):
    """Explainable dependency graph without roadmap generation."""

    target_role: str
    timeline_weeks: int
    study_hours_per_week: float
    total_capacity_hours: float
    required_gap_hours: float
    capacity_status: CapacityStatus
    nodes: tuple[SkillGapNode, ...]
    edges: tuple[SkillGapEdge, ...]
    critical_gaps: tuple[str, ...]
    ready_to_learn: tuple[str, ...]
    blocked_skills: tuple[str, ...]
