"""Structured roadmap generation inputs and validated LLM output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.assessment import AssessmentResult
from app.schemas.skill_gap import LearnerProfileInput, SkillGapAnalysisResult

LearningPriority = Literal["MUST_LEARN", "GOOD_TO_LEARN", "OPTIONAL"]


class RoadmapGenerationInput(BaseModel):
    """Inputs required to ask an LLM for a personalized learning roadmap."""

    learner_profile: LearnerProfileInput
    skill_assessment: tuple[AssessmentResult, ...]
    skill_gap_analysis: SkillGapAnalysisResult
    target_role: str
    target_timeline: str
    weekly_study_hours: float = Field(gt=0, le=168)


class RoadmapPhase(BaseModel):
    """One focused learning phase in the generated roadmap."""

    phase: int = Field(ge=1)
    goal: str = Field(min_length=1)
    topics: tuple[str, ...] = Field(min_length=1, max_length=4)
    prerequisites: tuple[str, ...] = ()
    priority: LearningPriority
    estimated_duration_weeks: int = Field(ge=1)
    hands_on_exercises: tuple[str, ...] = Field(min_length=1)
    mini_project: str = Field(min_length=1)
    interview_questions: tuple[str, ...] = Field(min_length=1)
    completion_criteria: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def topics_must_be_unique(self) -> "RoadmapPhase":
        normalized_topics = {topic.strip().lower() for topic in self.topics}
        if len(normalized_topics) != len(self.topics):
            raise ValueError("Roadmap phase topics must be unique.")
        if any(not topic.strip() for topic in self.topics):
            raise ValueError("Roadmap phase topics must not be blank.")
        return self


class PersonalizedRoadmap(BaseModel):
    """Structured roadmap returned by the LLM after Pydantic parsing."""

    target_role: str
    timeline_weeks: int = Field(ge=1)
    study_hours_per_week: float = Field(gt=0, le=168)
    total_estimated_weeks: int = Field(ge=1)
    phases: tuple[RoadmapPhase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def phases_must_be_sequential_and_fit_summary(self) -> "PersonalizedRoadmap":
        expected_phase_numbers = tuple(range(1, len(self.phases) + 1))
        actual_phase_numbers = tuple(phase.phase for phase in self.phases)
        if actual_phase_numbers != expected_phase_numbers:
            raise ValueError("Roadmap phases must be sequential starting at 1.")
        duration_total = sum(phase.estimated_duration_weeks for phase in self.phases)
        if self.total_estimated_weeks != duration_total:
            raise ValueError("Roadmap total_estimated_weeks must equal the sum of phase durations.")
        return self


class RoadmapGenerationResult(BaseModel):
    """Service result that can fail gracefully without exposing free-form LLM text."""

    success: bool
    roadmap: PersonalizedRoadmap | None = None
    error: str | None = None
    validation_errors: tuple[str, ...] = ()
