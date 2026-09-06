"""Schemas for Module 7 mentor and learning mode."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.planner import LearningPlan
from app.schemas.roadmap import PersonalizedRoadmap

LearnerSkillLevel = Literal["beginner", "intermediate", "advanced"]
TeachingCommand = Literal["teach", "explain", "practice", "todays_task", "next_topic"]


class TeachingSession(BaseModel):
    """Conversation state for the current mentor-mode session."""

    session_id: str
    learner_level: LearnerSkillLevel = "beginner"
    current_topic: str | None = None
    current_step: str | None = None
    current_phase: int = Field(default=1, ge=1)
    completed_topics: tuple[str, ...] = ()
    mastered_topics: tuple[str, ...] = ()
    weak_areas: tuple[str, ...] = ()
    turn_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def completed_topics_count_as_mastered(self) -> "TeachingSession":
        mastered = list(self.mastered_topics)
        normalized_mastered = {_normalize_topic(topic) for topic in mastered}
        for topic in self.completed_topics:
            if _normalize_topic(topic) not in normalized_mastered:
                mastered.append(topic)
                normalized_mastered.add(_normalize_topic(topic))
        self.mastered_topics = tuple(mastered)
        return self


class TeachingRequest(BaseModel):
    """Inputs for one learner message in mentor mode."""

    message: str = Field(min_length=1)
    session: TeachingSession
    roadmap: PersonalizedRoadmap | None = None
    learning_plan: LearningPlan | None = None


class QuizQuestion(BaseModel):
    """A short formative quiz prompt."""

    question: str
    expected_answer: str


class TeachingFlow(BaseModel):
    """The complete mentor teaching flow for one topic."""

    concept: str
    simple_explanation: str
    data_engineering_example: str
    code_example: str
    hands_on_exercise: str
    quiz: tuple[QuizQuestion, ...] = Field(min_length=1)
    evaluation: str
    next_step: str


class TeachingResponse(BaseModel):
    """Mentor-mode output plus updated session state."""

    command: TeachingCommand
    topic: str
    flow: TeachingFlow
    session: TeachingSession
    avoided_topics: tuple[str, ...] = ()
    rationale: str


def _normalize_topic(topic: str) -> str:
    return " ".join(topic.strip().lower().split())
