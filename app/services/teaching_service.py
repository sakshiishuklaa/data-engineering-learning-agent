"""Deterministic mentor-mode teaching engine for Module 7."""

from __future__ import annotations

import re

from app.schemas.planner import LearningPlan
from app.schemas.roadmap import PersonalizedRoadmap
from app.schemas.teaching import (
    QuizQuestion,
    TeachingCommand,
    TeachingFlow,
    TeachingRequest,
    TeachingResponse,
    TeachingSession,
)
from app.services.skill_gap_service import canonical_skill_name

BEGINNER_FOUNDATIONS = {"python", "sql", "git", "linux"}


TOPIC_ALIASES = {
    "git": "Git",
    "join": "Joins",
    "joins": "Joins",
    "linux": "Linux",
    "partition": "Partitioning",
    "partitioning": "Partitioning",
    "partitions": "Partitioning",
    "python": "Python",
    "spark": "PySpark",
    "apache spark": "PySpark",
    "sql": "SQL",
}


TOPIC_CONTENT = {
    "PySpark": {
        "concept": "Spark uses a driver to coordinate distributed work across executors.",
        "simple": {
            "beginner": "Think of Spark as a way to split a large data job into smaller chunks that run in parallel.",
            "intermediate": "Spark builds a logical plan for DataFrame operations, optimizes it, then executes stages across partitions.",
            "advanced": "Focus on execution plans, shuffles, partition sizing, and where transformations force stage boundaries.",
        },
        "example": "A data engineering team can read daily raw events, clean columns, and write curated parquet datasets.",
        "code": (
            "from pyspark.sql import functions as F\n\n"
            "events = spark.read.json('s3://lake/raw/events/date=2026-09-05/')\n"
            "clean = events.select('user_id', 'event_name', F.to_timestamp('event_time').alias('event_ts'))\n"
            "clean.write.mode('overwrite').partitionBy('event_name').parquet('s3://lake/curated/events/')"
        ),
        "exercise": "Create a PySpark job that reads a CSV, filters invalid rows, adds a load_date column, and writes parquet.",
        "quiz": ("Why does Spark split data into partitions?", "To process large datasets in parallel across executors."),
    },
    "Partitioning": {
        "concept": "Partitioning controls how data is split for storage and parallel processing.",
        "simple": {
            "beginner": "A partition is one slice of data. Good partitioning helps Spark skip irrelevant slices and run work in parallel.",
            "intermediate": "Partition choices affect file pruning, task count, shuffle volume, and small-file pressure.",
            "advanced": "Balance partition cardinality, skew, file size, and downstream query predicates instead of partitioning every column.",
        },
        "example": "An events table partitioned by event_date lets a daily pipeline read only one date instead of scanning years of data.",
        "code": (
            "events.repartition('event_date') \\\n"
            "    .write.mode('append') \\\n"
            "    .partitionBy('event_date') \\\n"
            "    .parquet('s3://lake/events/')"
        ),
        "exercise": "Given an events dataset, choose a partition key and explain how it changes reads, writes, and file counts.",
        "quiz": ("Why can a high-cardinality partition key be risky?", "It can create too many tiny directories and files."),
    },
    "Joins": {
        "concept": "A join combines rows from two datasets using matching keys.",
        "simple": {
            "beginner": "Use joins when one table has facts and another table has details you need to attach.",
            "intermediate": "Join strategy depends on data size, key uniqueness, null behavior, and whether Spark must shuffle both sides.",
            "advanced": "Tune joins by checking cardinality, skew, broadcast eligibility, and the physical plan chosen by Spark.",
        },
        "example": "Join order events to users so each event has the user's country and acquisition channel.",
        "code": (
            "orders = spark.table('silver.orders')\n"
            "users = spark.table('silver.users')\n\n"
            "orders_with_users = orders.join(users, on='user_id', how='left')"
        ),
        "exercise": "Build a left join between orders and users, then count rows before and after to check for duplicated keys.",
        "quiz": ("What does a left join preserve?", "All rows from the left dataset, plus matching columns from the right dataset."),
    },
    "Data Modeling": {
        "concept": "Data modeling defines table shape, grain, keys, and relationships.",
        "simple": {
            "beginner": "It is the blueprint for turning raw data into tables people can query reliably.",
            "intermediate": "Strong models make grain explicit and separate facts, dimensions, and derived metrics.",
            "advanced": "Model decisions should account for query patterns, slowly changing dimensions, lineage, and ownership.",
        },
        "example": "A product analytics model may use one fact table for events and dimensions for users, accounts, and dates.",
        "code": (
            "SELECT user_id, DATE(event_ts) AS event_date, COUNT(*) AS event_count\n"
            "FROM silver.events\n"
            "GROUP BY user_id, DATE(event_ts);"
        ),
        "exercise": "Define the grain, primary key, and dimensions for a daily active users mart.",
        "quiz": ("What does table grain mean?", "The exact business event or entity represented by one row."),
    },
}


def handle_teaching_command(request: TeachingRequest) -> TeachingResponse:
    """Parse a learner message and return the next mentor-mode response."""
    command = parse_teaching_command(request.message)
    explicit_topic = extract_topic(request.message, command)
    avoided_topics: tuple[str, ...] = ()

    if command == "todays_task":
        topic = _topic_from_learning_plan(request.learning_plan, request.session) or _select_next_topic(request.session, request.roadmap)
        rationale = "Selected from the current learning plan and learner session."
    elif command == "next_topic":
        topic, avoided_topics = _next_unmastered_topic(request.session, request.roadmap)
        rationale = "Selected the next unmastered roadmap topic for the current phase."
    elif explicit_topic:
        topic = explicit_topic
        rationale = "Used the topic requested by the learner."
    else:
        topic = request.session.current_topic or _select_next_topic(request.session, request.roadmap)
        rationale = "Continued the active teaching session topic."

    flow = build_teaching_flow(
        topic=topic,
        command=command,
        learner_level=request.session.learner_level,
        mastered_topics=request.session.mastered_topics,
        weak_areas=request.session.weak_areas,
    )
    updated_session = request.session.model_copy(
        update={
            "current_topic": topic,
            "current_step": "practice" if command == "practice" else "teaching_flow",
            "turn_count": request.session.turn_count + 1,
        }
    )
    return TeachingResponse(
        command=command,
        topic=topic,
        flow=flow,
        session=updated_session,
        avoided_topics=avoided_topics,
        rationale=rationale,
    )


def parse_teaching_command(message: str) -> TeachingCommand:
    """Map learner language to one of the supported mentor commands."""
    normalized = _normalize(message)
    if "today" in normalized and "task" in normalized:
        return "todays_task"
    if normalized.startswith("next topic") or normalized in {"next", "next lesson"}:
        return "next_topic"
    if normalized.startswith("practice") or "give me practice" in normalized:
        return "practice"
    if normalized.startswith("teach") or "teach me" in normalized:
        return "teach"
    if normalized.startswith("explain") or "i dont understand" in normalized or "i do not understand" in normalized:
        return "explain"
    return "explain"


def extract_topic(message: str, command: TeachingCommand) -> str | None:
    """Pull the requested topic from common learning-mode utterances."""
    normalized = _normalize(message)
    if command in {"todays_task", "next_topic"}:
        return None

    patterns = (
        r"teach me (?P<topic>.+)",
        r"teach (?P<topic>.+)",
        r"explain (?P<topic>.+)",
        r"practice (?P<topic>.+)",
        r"i dont understand (?P<topic>.+)",
        r"i do not understand (?P<topic>.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return _canonical_topic(match.group("topic"))
    return None


def build_teaching_flow(
    *,
    topic: str,
    command: TeachingCommand,
    learner_level: str,
    mastered_topics: tuple[str, ...] = (),
    weak_areas: tuple[str, ...] = (),
) -> TeachingFlow:
    """Create the concept-to-next-step teaching flow for a topic."""
    canonical_topic = _canonical_topic(topic)
    content = TOPIC_CONTENT.get(canonical_topic, _generic_content(canonical_topic))
    effective_level = learner_level if learner_level in {"beginner", "intermediate", "advanced"} else "beginner"
    normalized_topic = _normalize(canonical_topic)
    mastered = normalized_topic in _normalized_set(mastered_topics)
    weak = normalized_topic in _normalized_set(weak_areas)

    simple_explanation = content["simple"][effective_level]
    if mastered and normalized_topic in BEGINNER_FOUNDATIONS:
        simple_explanation = (
            f"You already have the beginner foundation for {canonical_topic}, so we will use it as a tool "
            "inside data-engineering work instead of reteaching definitions."
        )
    if command == "practice":
        simple_explanation = f"Quick practice mode: apply {canonical_topic} first, then use the quiz to check the idea."

    evaluation = _evaluation(canonical_topic, mastered, weak, effective_level)
    return TeachingFlow(
        concept=content["concept"],
        simple_explanation=simple_explanation,
        data_engineering_example=content["example"],
        code_example=content["code"],
        hands_on_exercise=content["exercise"],
        quiz=(QuizQuestion(question=content["quiz"][0], expected_answer=content["quiz"][1]),),
        evaluation=evaluation,
        next_step=_next_step(canonical_topic, command, mastered, weak),
    )


def _next_unmastered_topic(session: TeachingSession, roadmap: PersonalizedRoadmap | None) -> tuple[str, tuple[str, ...]]:
    mastered = _normalized_set(session.mastered_topics)
    weak_topic = _first_unmastered(session.weak_areas, mastered)
    if weak_topic is not None:
        return weak_topic, ()

    avoided: list[str] = []
    for topic in _roadmap_topics(roadmap, session.current_phase):
        if _normalize(topic) in mastered:
            avoided.append(topic)
            continue
        return topic, tuple(avoided)
    return session.current_topic or "PySpark", tuple(avoided)


def _select_next_topic(session: TeachingSession, roadmap: PersonalizedRoadmap | None) -> str:
    topic, _ = _next_unmastered_topic(session, roadmap)
    return topic


def _topic_from_learning_plan(learning_plan: LearningPlan | None, session: TeachingSession) -> str | None:
    if learning_plan is None:
        return None
    mastered = _normalized_set(session.mastered_topics)
    weak = _normalized_set(session.weak_areas)
    for item in learning_plan.weekly_plan:
        if _normalize(item.topic) in weak and _normalize(item.topic) not in mastered:
            return item.topic
    for item in learning_plan.weekly_plan:
        if _normalize(item.topic) not in mastered:
            return item.topic
    return None


def _roadmap_topics(roadmap: PersonalizedRoadmap | None, current_phase: int) -> tuple[str, ...]:
    if roadmap is None:
        return ("PySpark", "Data Modeling", "Data Warehousing", "Orchestration")
    current_and_future_phases = sorted(
        (phase for phase in roadmap.phases if phase.phase >= current_phase),
        key=lambda phase: phase.phase,
    )
    return tuple(topic for phase in current_and_future_phases for topic in phase.topics)


def _first_unmastered(topics: tuple[str, ...], mastered: set[str]) -> str | None:
    for topic in topics:
        if _normalize(topic) not in mastered:
            return topic
    return None


def _evaluation(topic: str, mastered: bool, weak: bool, learner_level: str) -> str:
    if weak:
        return f"{topic} is marked as a weak area, so the answer should include both the definition and a pipeline example."
    if mastered:
        return f"{topic} is already mastered; evaluate by asking for trade-offs and production failure modes."
    if learner_level == "beginner":
        return f"Ready to move on when the learner can explain {topic} in plain language and complete the exercise."
    return f"Ready to move on when the learner can apply {topic}, explain trade-offs, and debug one realistic issue."


def _next_step(topic: str, command: TeachingCommand, mastered: bool, weak: bool) -> str:
    if command == "practice":
        return f"Review the exercise result, then ask for a harder {topic} scenario."
    if weak:
        return f"Do one more guided practice round on {topic} before moving to the next roadmap topic."
    if mastered:
        return "Move to the next unmastered topic in the current roadmap phase."
    return f"Attempt the hands-on exercise, answer the quiz, then mark {topic} complete if the answer is solid."


def _generic_content(topic: str) -> dict[str, object]:
    return {
        "concept": f"{topic} is a data-engineering concept that should be understood through a real pipeline.",
        "simple": {
            "beginner": f"Start with what {topic} does, why it exists, and where it appears in a data workflow.",
            "intermediate": f"Connect {topic} to pipeline design choices, data quality, cost, and maintainability.",
            "advanced": f"Reason about {topic} through scale limits, operational trade-offs, and failure modes.",
        },
        "example": f"Use {topic} while moving raw source data into a reliable analytics-ready layer.",
        "code": "# Sketch the smallest working example for this topic in SQL or Python, then run it on sample data.",
        "exercise": f"Build a tiny example that uses {topic}, then explain the input, output, and one edge case.",
        "quiz": (f"What problem does {topic} solve in a data pipeline?", "It makes pipeline behavior clearer, safer, or more scalable."),
    }


def _canonical_topic(topic: str) -> str:
    cleaned = topic.strip().strip(".?!")
    normalized = _normalize(cleaned)
    if normalized in TOPIC_ALIASES:
        return TOPIC_ALIASES[normalized]
    canonical_skill = canonical_skill_name(cleaned)
    return canonical_skill[:1].upper() + canonical_skill[1:] if canonical_skill else "PySpark"


def _normalized_set(topics: tuple[str, ...]) -> set[str]:
    return {_normalize(topic) for topic in topics}


def _normalize(value: str) -> str:
    value = value.strip().lower().replace("'", "")
    return re.sub(r"\s+", " ", value)
