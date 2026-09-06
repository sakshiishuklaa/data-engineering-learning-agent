"""Dashboard schemas for learner progress tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ProgressStatus = Literal["not_started", "in_progress", "completed"]
RecommendationType = Literal["topic", "quiz_review", "skill_practice", "project", "complete_profile"]


class TopicProgressSummary(BaseModel):
    """Progress for one tracked learning topic."""

    topic: str
    status: str
    completion_percentage: float = Field(ge=0, le=100)
    score: float | None = None
    last_activity_at: datetime


class PhaseProgressSummary(BaseModel):
    """Aggregated completion for one roadmap phase."""

    phase: int
    goal: str
    completion_percentage: float = Field(ge=0, le=100)
    completed_topics: int = Field(ge=0)
    total_topics: int = Field(ge=0)
    status: ProgressStatus
    topics: tuple[str, ...]


class SkillProgressSummary(BaseModel):
    """Current learner skill state for dashboard display."""

    skill: str
    category: str
    current_score: float = Field(ge=0)
    target_score: float = Field(ge=0)
    improvement_needed: float = Field(ge=0)
    progress_to_target_percentage: float = Field(ge=0, le=100)
    last_assessed_at: datetime | None = None


class ProjectProgressSummary(BaseModel):
    """Portfolio project state for dashboard display."""

    project_name: str
    description: str | None = None
    status: str
    completion_percentage: float = Field(ge=0, le=100)
    technologies: tuple[str, ...]


class QuizPerformanceSummary(BaseModel):
    """Recent quiz attempt evidence."""

    topic: str
    difficulty: str
    score: float = Field(ge=0, le=10)
    created_at: datetime
    recommended_action: str


class NextRecommendation(BaseModel):
    """Learner-state-derived next action for the dashboard."""

    title: str
    rationale: str
    action_type: RecommendationType
    topic: str | None = None


class ProgressDashboard(BaseModel):
    """Complete snapshot for the learner progress dashboard."""

    learner_id: int
    learner_name: str
    overall_progress_percentage: float = Field(ge=0, le=100)
    roadmap_completion_percentage: float = Field(ge=0, le=100)
    topic_completion_percentage: float = Field(ge=0, le=100)
    skill_improvement_percentage: float = Field(ge=0, le=100)
    project_progress_percentage: float = Field(ge=0, le=100)
    quiz_average_score: float | None = Field(default=None, ge=0, le=10)
    study_streak_days: int = Field(ge=0)
    current_phase: PhaseProgressSummary | None = None
    phases: tuple[PhaseProgressSummary, ...]
    skills: tuple[SkillProgressSummary, ...]
    completed_topics: tuple[TopicProgressSummary, ...]
    upcoming_tasks: tuple[TopicProgressSummary, ...]
    weak_areas: tuple[SkillProgressSummary, ...]
    projects: tuple[ProjectProgressSummary, ...]
    recent_quiz_performance: tuple[QuizPerformanceSummary, ...]
    next_recommendation: NextRecommendation
