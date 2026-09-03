"""Tests for durable, structured learner memory."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models import Learner
from app.services.learner_memory_service import (
    add_skill_to_learner,
    create_learner,
    create_learning_progress,
    create_skill,
    get_learning_progress,
    get_learner_skill,
    update_learner,
    update_learner_skill_score,
    update_learning_progress,
)


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


def test_creating_learner_persists_a_complete_profile(session: Session) -> None:
    learner = create_learner(
        session,
        name="Asha Patel",
        experience_years=2.5,
        current_role="Data Analyst",
        target_role="Data Engineer",
        target_company_type="Product company",
        target_timeline="6 months",
        study_hours_per_week=10,
        preferred_cloud="AWS",
    )

    persisted = session.get(Learner, learner.id)
    assert persisted is not None
    assert persisted.name == "Asha Patel"
    assert persisted.target_role == "Data Engineer"
    assert persisted.preferred_cloud == "AWS"
    assert persisted.created_at is not None
    assert persisted.updated_at is not None


def test_updating_learner_changes_only_requested_profile_fields(session: Session) -> None:
    learner = create_learner(session, name="Asha Patel", current_role="Analyst", preferred_cloud="AWS")

    updated = update_learner(
        session,
        learner.id,
        current_role="Senior Data Analyst",
        target_role="Analytics Engineer",
        preferred_cloud="GCP",
    )

    assert updated is not None
    assert updated.name == "Asha Patel"
    assert updated.current_role == "Senior Data Analyst"
    assert updated.target_role == "Analytics Engineer"
    assert updated.preferred_cloud == "GCP"


def test_adding_skills_links_a_learner_to_a_canonical_skill(session: Session) -> None:
    learner = create_learner(session, name="Asha Patel")
    skill = create_skill(session, name="SQL", category="Databases")

    learner_skill = add_skill_to_learner(
        session,
        learner.id,
        skill.id,
        proficiency_score=45,
        target_score=85,
    )

    assert learner_skill.learner_id == learner.id
    assert learner_skill.skill_id == skill.id
    assert learner_skill.proficiency_score == 45
    assert learner_skill.target_score == 85
    assert learner_skill.last_assessed_at is not None


def test_updating_skill_score_records_the_latest_assessment(session: Session) -> None:
    learner = create_learner(session, name="Asha Patel")
    skill = create_skill(session, name="Apache Spark", category="Processing")
    add_skill_to_learner(session, learner.id, skill.id, proficiency_score=30, target_score=80)

    updated = update_learner_skill_score(session, learner.id, skill.id, proficiency_score=60)

    persisted = get_learner_skill(session, learner.id, skill.id)
    assert updated is not None
    assert persisted is not None
    assert persisted.proficiency_score == 60
    assert persisted.target_score == 80
    assert persisted.last_assessed_at is not None


def test_tracking_progress_preserves_topic_status_and_score(session: Session) -> None:
    learner = create_learner(session, name="Asha Patel")
    progress = create_learning_progress(
        session,
        learner.id,
        topic="Data Modeling",
        status="in_progress",
        completion_percentage=25,
        score=72,
    )

    updated = update_learning_progress(
        session,
        learner.id,
        progress.topic,
        completion_percentage=75,
        status="completed",
        score=92,
    )

    persisted = get_learning_progress(session, learner.id, "Data Modeling")
    assert updated is not None
    assert persisted is not None
    assert persisted.status == "completed"
    assert persisted.completion_percentage == 75
    assert persisted.score == 92
    assert persisted.last_activity_at is not None
