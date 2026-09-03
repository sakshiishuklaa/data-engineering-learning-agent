"""CRUD operations for structured learner memory.

The service deliberately accepts a SQLAlchemy session from its caller.  This keeps
transactions explicit and makes the memory usable from an API, a UI, or tests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Learner, LearnerSkill, LearningProgress, Project, Skill


def _apply_updates(instance: Any, updates: dict[str, Any], allowed_fields: set[str]) -> None:
    unknown_fields = set(updates) - allowed_fields
    if unknown_fields:
        raise ValueError(f"Unsupported update fields: {', '.join(sorted(unknown_fields))}")
    for field, value in updates.items():
        setattr(instance, field, value)


def create_learner(session: Session, name: str, experience_years: float = 0, **profile: Any) -> Learner:
    """Create and persist a learner profile."""
    learner = Learner(name=name, experience_years=experience_years, **profile)
    session.add(learner)
    session.commit()
    session.refresh(learner)
    return learner


def get_learner(session: Session, learner_id: int) -> Learner | None:
    return session.get(Learner, learner_id)


def list_learners(session: Session) -> list[Learner]:
    return list(session.scalars(select(Learner).order_by(Learner.id)))


def update_learner(session: Session, learner_id: int, **updates: Any) -> Learner | None:
    learner = get_learner(session, learner_id)
    if learner is None:
        return None
    _apply_updates(
        learner,
        updates,
        {
            "name",
            "experience_years",
            "current_role",
            "target_role",
            "target_company_type",
            "target_timeline",
            "study_hours_per_week",
            "preferred_cloud",
        },
    )
    session.commit()
    session.refresh(learner)
    return learner


def delete_learner(session: Session, learner_id: int) -> bool:
    learner = get_learner(session, learner_id)
    if learner is None:
        return False
    session.delete(learner)
    session.commit()
    return True


def create_skill(session: Session, name: str, category: str) -> Skill:
    """Create a canonical skill."""
    skill = Skill(name=name, category=category)
    session.add(skill)
    session.commit()
    session.refresh(skill)
    return skill


def get_skill(session: Session, skill_id: int) -> Skill | None:
    return session.get(Skill, skill_id)


def list_skills(session: Session, category: str | None = None) -> list[Skill]:
    statement = select(Skill).order_by(Skill.name)
    if category is not None:
        statement = statement.where(Skill.category == category)
    return list(session.scalars(statement))


def update_skill(session: Session, skill_id: int, **updates: Any) -> Skill | None:
    skill = get_skill(session, skill_id)
    if skill is None:
        return None
    _apply_updates(skill, updates, {"name", "category"})
    session.commit()
    session.refresh(skill)
    return skill


def delete_skill(session: Session, skill_id: int) -> bool:
    skill = get_skill(session, skill_id)
    if skill is None:
        return False
    session.delete(skill)
    session.commit()
    return True


def add_skill_to_learner(
    session: Session,
    learner_id: int,
    skill_id: int,
    proficiency_score: float = 0,
    target_score: float = 100,
    last_assessed_at: datetime | None = None,
) -> LearnerSkill:
    """Record a learner's current and target score for a skill."""
    if get_learner(session, learner_id) is None:
        raise ValueError(f"Learner {learner_id} does not exist")
    if get_skill(session, skill_id) is None:
        raise ValueError(f"Skill {skill_id} does not exist")
    learner_skill = LearnerSkill(
        learner_id=learner_id,
        skill_id=skill_id,
        proficiency_score=proficiency_score,
        target_score=target_score,
        last_assessed_at=last_assessed_at or datetime.now().astimezone(),
    )
    session.add(learner_skill)
    session.commit()
    session.refresh(learner_skill)
    return learner_skill


def get_learner_skill(session: Session, learner_id: int, skill_id: int) -> LearnerSkill | None:
    return session.get(LearnerSkill, (learner_id, skill_id))


def list_learner_skills(session: Session, learner_id: int) -> list[LearnerSkill]:
    return list(
        session.scalars(
            select(LearnerSkill).where(LearnerSkill.learner_id == learner_id).order_by(LearnerSkill.skill_id)
        )
    )


def update_learner_skill_score(
    session: Session,
    learner_id: int,
    skill_id: int,
    proficiency_score: float,
    target_score: float | None = None,
    assessed_at: datetime | None = None,
) -> LearnerSkill | None:
    learner_skill = get_learner_skill(session, learner_id, skill_id)
    if learner_skill is None:
        return None
    learner_skill.proficiency_score = proficiency_score
    if target_score is not None:
        learner_skill.target_score = target_score
    learner_skill.last_assessed_at = assessed_at or datetime.now().astimezone()
    session.commit()
    session.refresh(learner_skill)
    return learner_skill


def remove_skill_from_learner(session: Session, learner_id: int, skill_id: int) -> bool:
    learner_skill = get_learner_skill(session, learner_id, skill_id)
    if learner_skill is None:
        return False
    session.delete(learner_skill)
    session.commit()
    return True


def create_learning_progress(
    session: Session,
    learner_id: int,
    topic: str,
    status: str = "not_started",
    completion_percentage: float = 0,
    score: float | None = None,
) -> LearningProgress:
    """Start tracking a topic for a learner."""
    if get_learner(session, learner_id) is None:
        raise ValueError(f"Learner {learner_id} does not exist")
    progress = LearningProgress(
        learner_id=learner_id,
        topic=topic,
        status=status,
        completion_percentage=completion_percentage,
        score=score,
    )
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress


def get_learning_progress(session: Session, learner_id: int, topic: str) -> LearningProgress | None:
    return session.get(LearningProgress, (learner_id, topic))


def list_learning_progress(session: Session, learner_id: int, status: str | None = None) -> list[LearningProgress]:
    statement = select(LearningProgress).where(LearningProgress.learner_id == learner_id).order_by(LearningProgress.topic)
    if status is not None:
        statement = statement.where(LearningProgress.status == status)
    return list(session.scalars(statement))


def update_learning_progress(session: Session, learner_id: int, topic: str, **updates: Any) -> LearningProgress | None:
    progress = get_learning_progress(session, learner_id, topic)
    if progress is None:
        return None
    _apply_updates(progress, updates, {"status", "completion_percentage", "score", "last_activity_at"})
    if "last_activity_at" not in updates:
        progress.last_activity_at = datetime.now().astimezone()
    session.commit()
    session.refresh(progress)
    return progress


def delete_learning_progress(session: Session, learner_id: int, topic: str) -> bool:
    progress = get_learning_progress(session, learner_id, topic)
    if progress is None:
        return False
    session.delete(progress)
    session.commit()
    return True


def create_project(
    session: Session,
    learner_id: int,
    project_name: str,
    description: str | None = None,
    status: str = "planned",
    technologies: list[str] | None = None,
) -> Project:
    if get_learner(session, learner_id) is None:
        raise ValueError(f"Learner {learner_id} does not exist")
    project = Project(
        learner_id=learner_id,
        project_name=project_name,
        description=description,
        status=status,
        technologies=technologies or [],
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def get_project(session: Session, learner_id: int, project_name: str) -> Project | None:
    return session.get(Project, (learner_id, project_name))


def list_projects(session: Session, learner_id: int, status: str | None = None) -> list[Project]:
    statement = select(Project).where(Project.learner_id == learner_id).order_by(Project.project_name)
    if status is not None:
        statement = statement.where(Project.status == status)
    return list(session.scalars(statement))


def update_project(session: Session, learner_id: int, project_name: str, **updates: Any) -> Project | None:
    project = get_project(session, learner_id, project_name)
    if project is None:
        return None
    _apply_updates(project, updates, {"description", "status", "technologies"})
    session.commit()
    session.refresh(project)
    return project


def delete_project(session: Session, learner_id: int, project_name: str) -> bool:
    project = get_project(session, learner_id, project_name)
    if project is None:
        return False
    session.delete(project)
    session.commit()
    return True
