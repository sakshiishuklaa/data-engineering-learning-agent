"""Tests for Module 8 quiz and answer evaluation engine."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models import QuizAttempt
from app.schemas.quiz import AnswerEvaluation, QuizDifficulty, QuizQuestion, QuizTopic
from app.services.learner_memory_service import add_skill_to_learner, create_learner, create_skill, get_learner_skill
from app.services.quiz_service import (
    QUESTION_BANK,
    evaluate_learner_answer,
    get_quiz,
    list_quiz_questions,
    submit_quiz_answer,
)


class MockQuizLLMClient:
    """Simple structured-output fake for answer evaluation tests."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.prompts: list[str] = []
        self.response_model: type[AnswerEvaluation] | None = None

    def evaluate_answer(self, *, prompt: str, response_model: type[AnswerEvaluation]) -> Any:
        self.prompts.append(prompt)
        self.response_model = response_model
        if not self.responses:
            raise AssertionError("No mocked LLM responses left")
        return self.responses.pop(0)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    database_session = session_factory()
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _evaluation(score: float) -> dict[str, Any]:
    return {
        "score": score,
        "correct_points": ["Identified the main concept."],
        "missing_points": ["Add an implementation detail."],
        "mistakes": [],
        "improved_answer": "A stronger answer names the concept and explains how it is applied in a pipeline.",
        "recommended_action": "Practice one similar question and compare against the expected concepts.",
    }


def test_question_bank_covers_required_topics_and_difficulties() -> None:
    expected_topics: set[QuizTopic] = {
        "Python",
        "SQL",
        "ETL",
        "Spark",
        "Cloud",
        "Data Warehousing",
        "Orchestration",
        "System Design",
    }
    expected_difficulties: set[QuizDifficulty] = {"Beginner", "Intermediate", "Advanced"}

    assert len(QUESTION_BANK) == len(expected_topics) * len(expected_difficulties)
    assert {(question.topic, question.difficulty) for question in QUESTION_BANK} == {
        (topic, difficulty) for topic in expected_topics for difficulty in expected_difficulties
    }
    assert all(question.question and question.expected_concepts for question in QUESTION_BANK)


def test_get_quiz_returns_topic_and_difficulty_questions() -> None:
    quiz = get_quiz("Spark", "Intermediate")

    assert quiz.topic == "Spark"
    assert quiz.difficulty == "Intermediate"
    assert len(quiz.questions) == 1
    assert quiz.questions[0].topic == "Spark"
    assert quiz.questions[0].difficulty == "Intermediate"
    assert list_quiz_questions(topic="Spark") != ()


def test_evaluates_answer_through_mock_llm_client() -> None:
    question = QuizQuestion(
        topic="SQL",
        difficulty="Intermediate",
        question="How would you find customers with more than three orders?",
        expected_concepts=("GROUP BY", "HAVING"),
    )
    client = MockQuizLLMClient([_evaluation(8)])

    result = evaluate_learner_answer(question, "Group orders by customer and use HAVING count(*) > 3.", client)

    assert result.score == 8
    assert result.correct_points == ("Identified the main concept.",)
    assert client.response_model is AnswerEvaluation
    assert "structured JSON only" in client.prompts[0]
    assert "Expected concepts" in client.prompts[0]


def test_submit_quiz_answer_records_attempt_without_single_question_score_increase(session: Session) -> None:
    learner = create_learner(session, name="Asha Patel")
    skill = create_skill(session, name="SQL", category="Databases")
    add_skill_to_learner(session, learner.id, skill.id, proficiency_score=40, target_score=80)
    client = MockQuizLLMClient([_evaluation(9)])
    question = get_quiz("SQL", "Beginner").questions[0]

    result = submit_quiz_answer(
        session,
        learner_id=learner.id,
        skill_id=skill.id,
        question=question,
        learner_answer="WHERE filters rows before aggregation; GROUP BY groups rows for aggregate results.",
        llm_client=client,
    )

    learner_skill = get_learner_skill(session, learner.id, skill.id)
    attempts = list(session.scalars(select(QuizAttempt)))
    assert result.skill_updated is False
    assert result.observations_count == 1
    assert result.new_proficiency_score == 40
    assert learner_skill is not None
    assert learner_skill.proficiency_score == 40
    assert len(attempts) == 1
    assert attempts[0].score == 9
    assert attempts[0].recommended_action == result.recommended_action


def test_skill_score_updates_conservatively_after_multiple_observations(session: Session) -> None:
    learner = create_learner(session, name="Asha Patel")
    skill = create_skill(session, name="PySpark", category="Distributed processing")
    add_skill_to_learner(session, learner.id, skill.id, proficiency_score=40, target_score=80)
    client = MockQuizLLMClient([_evaluation(9), _evaluation(8), _evaluation(10)])
    question = get_quiz("Spark", "Beginner").questions[0]

    first = submit_quiz_answer(
        session,
        learner_id=learner.id,
        skill_id=skill.id,
        question=question,
        learner_answer="Spark partitions data so executors can work in parallel.",
        llm_client=client,
    )
    second = submit_quiz_answer(
        session,
        learner_id=learner.id,
        skill_id=skill.id,
        question=question,
        learner_answer="Partitions allow distributed parallel work over big datasets.",
        llm_client=client,
    )
    third = submit_quiz_answer(
        session,
        learner_id=learner.id,
        skill_id=skill.id,
        question=question,
        learner_answer="Spark divides data into partitions processed across executors.",
        llm_client=client,
    )

    learner_skill = get_learner_skill(session, learner.id, skill.id)
    assert first.skill_updated is False
    assert second.skill_updated is False
    assert third.skill_updated is True
    assert third.observations_count == 3
    assert third.previous_proficiency_score == 40
    assert third.new_proficiency_score == 44
    assert learner_skill is not None
    assert learner_skill.proficiency_score == 44


def test_submit_rejects_question_skill_mismatch(session: Session) -> None:
    learner = create_learner(session, name="Asha Patel")
    skill = create_skill(session, name="Python", category="Programming")
    add_skill_to_learner(session, learner.id, skill.id, proficiency_score=40, target_score=80)

    with pytest.raises(ValueError, match="maps to skill SQL"):
        submit_quiz_answer(
            session,
            learner_id=learner.id,
            skill_id=skill.id,
            question=get_quiz("SQL", "Beginner").questions[0],
            learner_answer="WHERE filters rows.",
            llm_client=MockQuizLLMClient([_evaluation(5)]),
        )
