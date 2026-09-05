"""Tests for learner onboarding validation and persistence."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.services.onboarding_service import get_existing_onboarding_profile, save_onboarding_profile, validate_onboarding_profile


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    database_session = sessionmaker(bind=engine, class_=Session)()
    Base.metadata.create_all(engine)
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def profile_data() -> dict[str, object]:
    return {
        "current_role": "Data Analyst", "experience_years": 2, "education": "Bachelor's degree",
        "python_level": "Intermediate", "sql_level": "Intermediate", "database_experience": "Beginner",
        "cloud_experience": "No experience", "git_github_level": "Beginner", "linux_level": "Beginner",
        "etl_elt_level": "No experience", "data_warehousing_level": "No experience",
        "spark_pyspark_level": "No experience", "airflow_orchestration_level": "No experience",
        "docker_level": "No experience", "existing_projects": "Sales dashboard",
        "target_role": "Data Engineer", "target_company_type": "Product company", "preferred_cloud": "AWS",
        "study_hours_per_week": 8, "target_timeline": "6 months", "learning_preference": "Hands-on projects",
    }


def test_validation_rejects_missing_required_text_and_invalid_hours(profile_data: dict[str, object]) -> None:
    profile_data["current_role"] = " "
    profile_data["study_hours_per_week"] = 0
    with pytest.raises(ValueError, match="Current role is required"):
        validate_onboarding_profile(profile_data)


def test_save_persists_all_onboarding_answers(session: Session, profile_data: dict[str, object]) -> None:
    saved = save_onboarding_profile(session, profile_data)
    persisted = get_existing_onboarding_profile(session)
    assert persisted is not None
    assert persisted.learner_id == saved.learner_id
    assert persisted.education == "Bachelor's degree"
    assert persisted.spark_pyspark_level == "No experience"
    assert persisted.existing_projects == "Sales dashboard"
    assert persisted.learner.current_role == "Data Analyst"


def test_save_updates_existing_profile_instead_of_creating_another(session: Session, profile_data: dict[str, object]) -> None:
    first = save_onboarding_profile(session, profile_data)
    profile_data["target_role"] = "Analytics Engineer"
    profile_data["study_hours_per_week"] = 12
    updated = save_onboarding_profile(session, profile_data)
    assert updated.learner_id == first.learner_id
    assert session.query(type(updated)).count() == 1
    assert updated.target_role == "Analytics Engineer"
    assert updated.learner.study_hours_per_week == 12
