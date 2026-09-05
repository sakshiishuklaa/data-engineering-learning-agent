"""Structured persistence models for learner memory."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Learner(Base):
    """A learner's durable profile and career goals."""

    __tablename__ = "learners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    experience_years: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    current_role: Mapped[str | None] = mapped_column(String(255))
    target_role: Mapped[str | None] = mapped_column(String(255))
    target_company_type: Mapped[str | None] = mapped_column(String(255))
    target_timeline: Mapped[str | None] = mapped_column(String(255))
    study_hours_per_week: Mapped[float | None] = mapped_column(Float)
    preferred_cloud: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    skills: Mapped[list[LearnerSkill]] = relationship(back_populates="learner", cascade="all, delete-orphan")
    progress_records: Mapped[list[LearningProgress]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )
    projects: Mapped[list[Project]] = relationship(back_populates="learner", cascade="all, delete-orphan")
    onboarding_profile: Mapped[OnboardingProfile | None] = relationship(
        back_populates="learner", cascade="all, delete-orphan", uselist=False
    )


class OnboardingProfile(Base):
    """The learner information collected during Module 2 onboarding."""

    __tablename__ = "onboarding_profiles"

    learner_id: Mapped[int] = mapped_column(ForeignKey("learners.id", ondelete="CASCADE"), primary_key=True)
    current_role: Mapped[str] = mapped_column(String(255), nullable=False)
    experience_years: Mapped[float] = mapped_column(Float, nullable=False)
    education: Mapped[str] = mapped_column(String(255), nullable=False)
    python_level: Mapped[str] = mapped_column(String(50), nullable=False)
    sql_level: Mapped[str] = mapped_column(String(50), nullable=False)
    database_experience: Mapped[str] = mapped_column(String(50), nullable=False)
    cloud_experience: Mapped[str] = mapped_column(String(50), nullable=False)
    git_github_level: Mapped[str] = mapped_column(String(50), nullable=False)
    linux_level: Mapped[str] = mapped_column(String(50), nullable=False)
    etl_elt_level: Mapped[str] = mapped_column(String(50), nullable=False)
    data_warehousing_level: Mapped[str] = mapped_column(String(50), nullable=False)
    spark_pyspark_level: Mapped[str] = mapped_column(String(50), nullable=False)
    airflow_orchestration_level: Mapped[str] = mapped_column(String(50), nullable=False)
    docker_level: Mapped[str] = mapped_column(String(50), nullable=False)
    existing_projects: Mapped[str | None] = mapped_column(Text)
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    target_company_type: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_cloud: Mapped[str] = mapped_column(String(100), nullable=False)
    study_hours_per_week: Mapped[float] = mapped_column(Float, nullable=False)
    target_timeline: Mapped[str] = mapped_column(String(255), nullable=False)
    learning_preference: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    learner: Mapped[Learner] = relationship(back_populates="onboarding_profile")


class Skill(Base):
    """A canonical skill that can be assessed for any learner."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    learners: Mapped[list[LearnerSkill]] = relationship(back_populates="skill", cascade="all, delete-orphan")


class LearnerSkill(Base):
    """A learner-specific assessment for a canonical skill."""

    __tablename__ = "learner_skills"

    learner_id: Mapped[int] = mapped_column(ForeignKey("learners.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    proficiency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    target_score: Mapped[float] = mapped_column(Float, nullable=False, default=100)
    last_assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    learner: Mapped[Learner] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship(back_populates="learners")


class LearningProgress(Base):
    """Current progress for one learner and learning topic."""

    __tablename__ = "learning_progress"

    learner_id: Mapped[int] = mapped_column(ForeignKey("learners.id", ondelete="CASCADE"), primary_key=True)
    topic: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="not_started", index=True)
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    score: Mapped[float | None] = mapped_column(Float)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    learner: Mapped[Learner] = relationship(back_populates="progress_records")


class Project(Base):
    """A portfolio project owned by a learner."""

    __tablename__ = "projects"

    learner_id: Mapped[int] = mapped_column(ForeignKey("learners.id", ondelete="CASCADE"), primary_key=True)
    project_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planned", index=True)
    technologies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    learner: Mapped[Learner] = relationship(back_populates="projects")
