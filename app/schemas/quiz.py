"""Schemas for Module 8 quiz generation and answer evaluation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

QuizTopic = Literal[
    "Python",
    "SQL",
    "ETL",
    "Spark",
    "Cloud",
    "Data Warehousing",
    "Orchestration",
    "System Design",
]
QuizDifficulty = Literal["Beginner", "Intermediate", "Advanced"]


class QuizQuestion(BaseModel):
    """One durable quiz question with its evaluation rubric."""

    question: str = Field(min_length=1)
    topic: QuizTopic
    difficulty: QuizDifficulty
    expected_concepts: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def expected_concepts_must_be_specific(self) -> "QuizQuestion":
        if any(not concept.strip() for concept in self.expected_concepts):
            raise ValueError("Expected concepts must not be blank.")
        if len({concept.strip().lower() for concept in self.expected_concepts}) != len(self.expected_concepts):
            raise ValueError("Expected concepts must be unique.")
        return self


class Quiz(BaseModel):
    """A topic-and-difficulty quiz."""

    topic: QuizTopic
    difficulty: QuizDifficulty
    questions: tuple[QuizQuestion, ...] = Field(min_length=1)


class AnswerEvaluation(BaseModel):
    """Structured evaluation for a learner answer."""

    score: float = Field(ge=0, le=10)
    correct_points: tuple[str, ...] = ()
    missing_points: tuple[str, ...] = ()
    mistakes: tuple[str, ...] = ()
    improved_answer: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)


class QuizAnswerResult(BaseModel):
    """Evaluation result plus conservative skill-memory update metadata."""

    evaluation: AnswerEvaluation
    observations_count: int = Field(ge=1)
    skill_updated: bool
    previous_proficiency_score: float
    new_proficiency_score: float
    recommended_action: str = Field(min_length=1)
