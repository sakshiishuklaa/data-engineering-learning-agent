"""Validated inputs and outputs for adaptive learning plan generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.roadmap import PersonalizedRoadmap

PlanActivityType = Literal["Learn", "Practice", "Hands-on", "Revision", "Interview practice"]


class PlannerAllocation(BaseModel):
    """Configurable study-time allocation across learning modes."""

    theory: float = Field(default=0.30, ge=0, le=1)
    hands_on: float = Field(default=0.50, ge=0, le=1)
    interview_practice: float = Field(default=0.20, ge=0, le=1)

    @model_validator(mode="after")
    def allocation_must_sum_to_one(self) -> "PlannerAllocation":
        total = self.theory + self.hands_on + self.interview_practice
        if abs(total - 1.0) > 0.001:
            raise ValueError("Planner allocation must sum to 1.0.")
        return self


class LearningPlannerInput(BaseModel):
    """Inputs required to build a daily and weekly learning plan."""

    personalized_roadmap: PersonalizedRoadmap
    available_study_hours: float = Field(gt=0, le=168)
    completed_topics: tuple[str, ...] = ()
    current_phase: int = Field(default=1, ge=1)
    weak_topics: tuple[str, ...] = ()
    allocation: PlannerAllocation = Field(default_factory=PlannerAllocation)
    incomplete_tasks: tuple[str, ...] = ()
    revision_required_topics: tuple[str, ...] = ()
    days_per_week: int = Field(default=7, ge=1, le=7)


class WeeklyPlanItem(BaseModel):
    """One row in the weekly learning plan."""

    day: str
    topic: str
    activity: str
    duration: float = Field(gt=0)
    expected_outcome: str


class DailyPlan(BaseModel):
    """Daily study blocks using the Module 6 required sections."""

    learn: tuple[WeeklyPlanItem, ...] = ()
    practice: tuple[WeeklyPlanItem, ...] = ()
    hands_on: tuple[WeeklyPlanItem, ...] = ()
    revision: tuple[WeeklyPlanItem, ...] = ()
    interview_practice: tuple[WeeklyPlanItem, ...] = ()


class LearningPlan(BaseModel):
    """Generated adaptive daily and weekly planner output."""

    weekly_plan: tuple[WeeklyPlanItem, ...]
    daily_plan: DailyPlan
    allocation: PlannerAllocation
    rescheduled_topics: tuple[str, ...] = ()
    preserved_prerequisites: tuple[str, ...] = ()
