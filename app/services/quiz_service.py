"""Quiz generation, answer evaluation, and conservative skill updates."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import QuizAttempt
from app.schemas.quiz import AnswerEvaluation, Quiz, QuizAnswerResult, QuizDifficulty, QuizQuestion, QuizTopic
from app.services.learner_memory_service import get_learner, get_learner_skill, get_skill

MIN_OBSERVATIONS_FOR_SKILL_UPDATE = 3
RECENT_OBSERVATIONS_FOR_AVERAGE = 5
MAX_PROFICIENCY_INCREASE = 4.0
MAX_PROFICIENCY_DECREASE = 6.0

TOPIC_TO_SKILL = {
    "Python": "Python",
    "SQL": "SQL",
    "ETL": "ETL/ELT",
    "Spark": "PySpark",
    "Cloud": "Cloud",
    "Data Warehousing": "Data Warehousing",
    "Orchestration": "Orchestration",
    "System Design": "System Design",
}


class QuizEvaluationLLMClient(Protocol):
    """Boundary for a structured-output answer evaluator."""

    def evaluate_answer(self, *, prompt: str, response_model: type[AnswerEvaluation]) -> Any:
        """Return data that can be parsed as ``AnswerEvaluation``."""


QUESTION_BANK: tuple[QuizQuestion, ...] = (
    QuizQuestion(
        topic="Python",
        difficulty="Beginner",
        question="How would you read a CSV file and keep only rows where status is 'active' in Python?",
        expected_concepts=("CSV/dataframe reading", "row filtering", "basic syntax"),
    ),
    QuizQuestion(
        topic="Python",
        difficulty="Intermediate",
        question="Explain how you would process a large file in Python without loading the entire file into memory.",
        expected_concepts=("iteration or streaming", "memory efficiency", "chunked processing"),
    ),
    QuizQuestion(
        topic="Python",
        difficulty="Advanced",
        question="How would you design a reusable Python data validation component for multiple pipeline stages?",
        expected_concepts=("separation of concerns", "schema or rule validation", "testability", "clear error reporting"),
    ),
    QuizQuestion(
        topic="SQL",
        difficulty="Beginner",
        question="What is the difference between WHERE and GROUP BY in a SQL query?",
        expected_concepts=("row filtering", "aggregation grouping", "query order awareness"),
    ),
    QuizQuestion(
        topic="SQL",
        difficulty="Intermediate",
        question="How would you find customers who placed more than three orders in the last 30 days?",
        expected_concepts=("JOIN or orders table filtering", "date filtering", "GROUP BY", "HAVING"),
    ),
    QuizQuestion(
        topic="SQL",
        difficulty="Advanced",
        question="How would you debug a slow analytical SQL query over a large fact table?",
        expected_concepts=("query plan", "partition pruning", "indexes or clustering", "join and aggregation strategy"),
    ),
    QuizQuestion(
        topic="ETL",
        difficulty="Beginner",
        question="What do extract, transform, and load mean in a data pipeline?",
        expected_concepts=("source extraction", "data transformation", "target loading"),
    ),
    QuizQuestion(
        topic="ETL",
        difficulty="Intermediate",
        question="How would you make an ETL job safe to rerun after a failure?",
        expected_concepts=("idempotency", "checkpoints or state", "deduplication", "retry behavior"),
    ),
    QuizQuestion(
        topic="ETL",
        difficulty="Advanced",
        question="How would you design an incremental ETL pipeline that handles late-arriving data?",
        expected_concepts=("watermarks", "incremental extraction", "merge/upsert strategy", "backfill window"),
    ),
    QuizQuestion(
        topic="Spark",
        difficulty="Beginner",
        question="Why does Spark split data into partitions?",
        expected_concepts=("parallel processing", "distributed executors", "large dataset handling"),
    ),
    QuizQuestion(
        topic="Spark",
        difficulty="Intermediate",
        question="What causes a shuffle in Spark, and why can it be expensive?",
        expected_concepts=("data movement across partitions", "wide transformations", "network/disk cost", "join or groupBy examples"),
    ),
    QuizQuestion(
        topic="Spark",
        difficulty="Advanced",
        question="How would you investigate and fix a skewed Spark join?",
        expected_concepts=("detect skew", "physical plan or metrics", "salting or broadcast join", "partition tuning"),
    ),
    QuizQuestion(
        topic="Cloud",
        difficulty="Beginner",
        question="What is the difference between object storage and a database in cloud data systems?",
        expected_concepts=("object storage files/blobs", "database structured querying", "different access patterns"),
    ),
    QuizQuestion(
        topic="Cloud",
        difficulty="Intermediate",
        question="How would you securely let a pipeline write files to cloud object storage?",
        expected_concepts=("least privilege IAM", "service identity", "bucket/path permissions", "secret avoidance"),
    ),
    QuizQuestion(
        topic="Cloud",
        difficulty="Advanced",
        question="How would you design a cloud data platform for reliability across ingestion, storage, and compute?",
        expected_concepts=("fault tolerance", "scalable storage and compute", "monitoring/alerting", "security boundaries"),
    ),
    QuizQuestion(
        topic="Data Warehousing",
        difficulty="Beginner",
        question="Why are data warehouses commonly used for analytics instead of operational application databases?",
        expected_concepts=("analytics workload optimization", "historical/curated data", "separation from operational systems"),
    ),
    QuizQuestion(
        topic="Data Warehousing",
        difficulty="Intermediate",
        question="Explain staging, dimension, fact, and mart layers in a warehouse.",
        expected_concepts=("staging raw-ish data", "dimensions", "facts and grain", "business-facing marts"),
    ),
    QuizQuestion(
        topic="Data Warehousing",
        difficulty="Advanced",
        question="How would you model changing customer attributes in a warehouse?",
        expected_concepts=("slowly changing dimensions", "history preservation", "effective dates or versioning", "business requirements"),
    ),
    QuizQuestion(
        topic="Orchestration",
        difficulty="Beginner",
        question="What problem does a workflow orchestrator solve in data engineering?",
        expected_concepts=("task scheduling", "dependencies", "retries or monitoring"),
    ),
    QuizQuestion(
        topic="Orchestration",
        difficulty="Intermediate",
        question="How would you design a DAG for daily raw-to-curated data processing?",
        expected_concepts=("task dependencies", "extract/load/transform steps", "failure handling", "scheduling"),
    ),
    QuizQuestion(
        topic="Orchestration",
        difficulty="Advanced",
        question="How would you prevent a DAG backfill from overwhelming downstream systems?",
        expected_concepts=("concurrency limits", "rate limiting", "partitioned backfill", "downstream capacity awareness"),
    ),
    QuizQuestion(
        topic="System Design",
        difficulty="Beginner",
        question="What are the main components of a simple batch data platform?",
        expected_concepts=("ingestion", "storage", "processing", "serving or analytics"),
    ),
    QuizQuestion(
        topic="System Design",
        difficulty="Intermediate",
        question="Design a pipeline that ingests events and makes daily metrics available to analysts.",
        expected_concepts=("event ingestion", "batch or streaming processing", "data quality checks", "warehouse or mart output"),
    ),
    QuizQuestion(
        topic="System Design",
        difficulty="Advanced",
        question="How would you design a data platform that supports both real-time alerts and historical analytics?",
        expected_concepts=("stream processing", "batch/historical storage", "serving paths", "consistency and latency tradeoffs"),
    ),
)


def list_quiz_questions(topic: QuizTopic | None = None, difficulty: QuizDifficulty | None = None) -> tuple[QuizQuestion, ...]:
    """Return quiz questions, optionally filtered by topic and difficulty."""
    return tuple(
        question
        for question in QUESTION_BANK
        if (topic is None or question.topic == topic) and (difficulty is None or question.difficulty == difficulty)
    )


def get_quiz(topic: QuizTopic, difficulty: QuizDifficulty) -> Quiz:
    """Create the quiz for a requested topic and difficulty from the question bank."""
    questions = list_quiz_questions(topic=topic, difficulty=difficulty)
    if not questions:
        raise ValueError(f"No quiz exists for {topic} at {difficulty} difficulty.")
    return Quiz(topic=topic, difficulty=difficulty, questions=questions)


def evaluate_learner_answer(
    question: QuizQuestion,
    learner_answer: str,
    llm_client: QuizEvaluationLLMClient,
) -> AnswerEvaluation:
    """Evaluate an answer through a structured LLM boundary."""
    if not learner_answer.strip():
        raise ValueError("Learner answer is required.")
    prompt = build_answer_evaluation_prompt(question, learner_answer)
    raw_evaluation = llm_client.evaluate_answer(prompt=prompt, response_model=AnswerEvaluation)
    return raw_evaluation if isinstance(raw_evaluation, AnswerEvaluation) else AnswerEvaluation.model_validate(raw_evaluation)


def build_answer_evaluation_prompt(question: QuizQuestion, learner_answer: str) -> str:
    """Create a constrained prompt for a structured-output evaluator."""
    return (
        "Evaluate this learner answer as structured JSON only. "
        "Use the supplied response_model/Pydantic schema. Return score / 10, correct_points, missing_points, "
        "mistakes, improved_answer, and recommended_action. Award credit for concepts that are present even "
        "if wording differs. Be specific and constructive.\n"
        f"Topic: {question.topic}\n"
        f"Difficulty: {question.difficulty}\n"
        f"Question: {question.question}\n"
        f"Expected concepts: {question.expected_concepts}\n"
        f"Learner answer: {learner_answer}\n"
        f"Evaluation JSON schema: {AnswerEvaluation.model_json_schema()}"
    )


def submit_quiz_answer(
    session: Session,
    *,
    learner_id: int,
    skill_id: int,
    question: QuizQuestion,
    learner_answer: str,
    llm_client: QuizEvaluationLLMClient,
) -> QuizAnswerResult:
    """Evaluate, persist, and use an answer as conservative skill evidence."""
    if get_learner(session, learner_id) is None:
        raise ValueError(f"Learner {learner_id} does not exist")
    skill = get_skill(session, skill_id)
    if skill is None:
        raise ValueError(f"Skill {skill_id} does not exist")
    expected_skill = TOPIC_TO_SKILL[question.topic]
    if skill.name != expected_skill:
        raise ValueError(f"Question topic {question.topic} maps to skill {expected_skill}, not {skill.name}.")
    learner_skill = get_learner_skill(session, learner_id, skill_id)
    if learner_skill is None:
        raise ValueError(f"Learner {learner_id} does not track skill {skill_id}")

    evaluation = evaluate_learner_answer(question, learner_answer, llm_client)
    previous_score = learner_skill.proficiency_score
    attempt = QuizAttempt(
        learner_id=learner_id,
        skill_id=skill_id,
        topic=question.topic,
        difficulty=question.difficulty,
        question=question.question,
        learner_answer=learner_answer,
        score=evaluation.score,
        correct_points=list(evaluation.correct_points),
        missing_points=list(evaluation.missing_points),
        mistakes=list(evaluation.mistakes),
        improved_answer=evaluation.improved_answer,
        recommended_action=evaluation.recommended_action,
    )
    session.add(attempt)
    session.flush()

    new_score, observations_count, skill_updated = _conservative_skill_score(
        session=session,
        learner_id=learner_id,
        skill_id=skill_id,
        current_score=previous_score,
    )
    learner_skill.last_assessed_at = datetime.now().astimezone()
    if skill_updated:
        learner_skill.proficiency_score = new_score
    session.commit()
    session.refresh(learner_skill)

    return QuizAnswerResult(
        evaluation=evaluation,
        observations_count=observations_count,
        skill_updated=skill_updated,
        previous_proficiency_score=previous_score,
        new_proficiency_score=learner_skill.proficiency_score,
        recommended_action=evaluation.recommended_action,
    )


def _conservative_skill_score(
    *,
    session: Session,
    learner_id: int,
    skill_id: int,
    current_score: float,
) -> tuple[float, int, bool]:
    attempts = list(
        session.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.learner_id == learner_id, QuizAttempt.skill_id == skill_id)
            .order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc())
        )
    )
    observations_count = len(attempts)
    if observations_count < MIN_OBSERVATIONS_FOR_SKILL_UPDATE:
        return current_score, observations_count, False

    recent_attempts = attempts[:RECENT_OBSERVATIONS_FOR_AVERAGE]
    quiz_average_on_memory_scale = (sum(attempt.score for attempt in recent_attempts) / len(recent_attempts)) * 10
    raw_delta = quiz_average_on_memory_scale - current_score
    if raw_delta > 0:
        bounded_delta = min(raw_delta * 0.25, MAX_PROFICIENCY_INCREASE)
    else:
        bounded_delta = max(raw_delta * 0.35, -MAX_PROFICIENCY_DECREASE)
    return round(min(max(current_score + bounded_delta, 0), 100), 1), observations_count, abs(bounded_delta) > 0
