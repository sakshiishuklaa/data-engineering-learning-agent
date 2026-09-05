"""Skill dependency graph and gap analysis for target data roles."""

from __future__ import annotations

import re

from app.schemas.skill_gap import (
    LearnerSkillInput,
    SkillGapAnalysisInput,
    SkillGapAnalysisResult,
    SkillGapEdge,
    SkillGapNode,
)

PREREQUISITE_READY_SCORE = 5.0

SKILL_CATEGORIES = {
    "Python": "Programming",
    "PySpark": "Distributed processing",
    "Spark Optimization": "Distributed processing",
    "SQL": "Databases",
    "Data Modeling": "Analytics engineering",
    "Data Warehousing": "Analytics engineering",
    "Linux": "Developer workflow",
    "Git": "Developer workflow",
    "Docker": "DevOps",
    "CI/CD": "DevOps",
    "ETL/ELT": "Data pipelines",
    "Orchestration": "Data pipelines",
}

SKILL_ALIASES = {
    "apache spark": "PySpark",
    "airflow": "Orchestration",
    "airflow/orchestration": "Orchestration",
    "ci cd": "CI/CD",
    "cicd": "CI/CD",
    "data warehouse": "Data Warehousing",
    "data warehousing": "Data Warehousing",
    "etl": "ETL/ELT",
    "etl elt": "ETL/ELT",
    "etl/elt": "ETL/ELT",
    "git/github": "Git",
    "github": "Git",
    "pyspark": "PySpark",
    "spark": "PySpark",
    "spark/pyspark": "PySpark",
}

ROLE_REQUIREMENTS = {
    "data engineer": {
        "Python": 7.0,
        "PySpark": 7.0,
        "Spark Optimization": 6.5,
        "SQL": 7.5,
        "Data Modeling": 6.5,
        "Data Warehousing": 6.5,
        "Linux": 6.0,
        "Git": 6.0,
        "Docker": 6.0,
        "CI/CD": 5.5,
        "ETL/ELT": 7.0,
        "Orchestration": 6.5,
    },
    "analytics engineer": {
        "Python": 5.5,
        "SQL": 8.0,
        "Data Modeling": 7.5,
        "Data Warehousing": 7.0,
        "Git": 6.5,
        "ETL/ELT": 6.0,
        "Orchestration": 5.5,
    },
}

DEPENDENCIES = {
    "PySpark": ("Python",),
    "Spark Optimization": ("PySpark",),
    "Data Modeling": ("SQL",),
    "Data Warehousing": ("Data Modeling",),
    "Docker": ("Linux", "Git"),
    "CI/CD": ("Docker",),
    "Orchestration": ("ETL/ELT",),
}

HOURS_PER_GAP_POINT = {
    "Programming": 8.0,
    "Distributed processing": 10.0,
    "Databases": 7.0,
    "Analytics engineering": 8.0,
    "Developer workflow": 5.0,
    "DevOps": 7.0,
    "Data pipelines": 8.0,
}


def canonical_skill_name(skill: str) -> str:
    """Normalize caller-provided skill labels to graph node names."""
    cleaned = re.sub(r"\s+", " ", skill.strip())
    lookup = cleaned.lower().replace("&", "and")
    lookup = re.sub(r"[^a-z0-9/]+", " ", lookup).strip()
    return SKILL_ALIASES.get(lookup, cleaned)


def parse_timeline_weeks(target_timeline: str) -> int:
    """Convert common timeline text into whole weeks."""
    timeline = target_timeline.strip().lower()
    if not timeline:
        raise ValueError("Target timeline is required.")
    match = re.search(r"(\d+(?:\.\d+)?)", timeline)
    if match is None:
        raise ValueError("Target timeline must include a number, such as '6 months' or '12 weeks'.")
    amount = float(match.group(1))
    if amount <= 0:
        raise ValueError("Target timeline must be greater than zero.")
    if "week" in timeline or re.search(r"\bwks?\b", timeline):
        weeks = amount
    elif "year" in timeline or "yr" in timeline:
        weeks = amount * 52
    elif "day" in timeline:
        weeks = amount / 7
    else:
        weeks = amount * 4
    return max(round(weeks), 1)


def analyze_skill_gaps(analysis_input: SkillGapAnalysisInput) -> SkillGapAnalysisResult:
    """Build a target-role skill dependency graph and calculate current gaps."""
    target_scores = _target_scores_for_role(analysis_input.target_role)
    current_scores = _current_scores_by_skill(analysis_input.learner_skills)
    edges = tuple(
        SkillGapEdge(prerequisite=prerequisite, unlocks=skill)
        for skill, prerequisites in DEPENDENCIES.items()
        if skill in target_scores
        for prerequisite in prerequisites
        if prerequisite in target_scores
    )
    unlocks_by_skill = {skill: tuple(edge.unlocks for edge in edges if edge.prerequisite == skill) for skill in target_scores}
    nodes = tuple(
        _build_node(skill, target_score, current_scores.get(skill, 0.0), unlocks_by_skill.get(skill, ()), current_scores)
        for skill, target_score in target_scores.items()
    )
    required_gap_hours = round(sum(node.estimated_hours for node in nodes), 1)
    timeline_weeks = parse_timeline_weeks(analysis_input.target_timeline)
    total_capacity_hours = round(timeline_weeks * analysis_input.study_hours_per_week, 1)
    return SkillGapAnalysisResult(
        target_role=analysis_input.target_role.strip(),
        timeline_weeks=timeline_weeks,
        study_hours_per_week=analysis_input.study_hours_per_week,
        total_capacity_hours=total_capacity_hours,
        required_gap_hours=required_gap_hours,
        capacity_status=_capacity_status(required_gap_hours, total_capacity_hours),
        nodes=tuple(sorted(nodes, key=_node_sort_key)),
        edges=edges,
        critical_gaps=tuple(node.skill for node in nodes if node.priority == "Critical"),
        ready_to_learn=tuple(node.skill for node in nodes if node.ready_to_learn and node.gap > 0),
        blocked_skills=tuple(node.skill for node in nodes if not node.ready_to_learn and node.gap > 0),
    )


def _target_scores_for_role(target_role: str) -> dict[str, float]:
    normalized_role = target_role.strip().lower()
    if not normalized_role:
        raise ValueError("Target role is required.")
    for role, scores in ROLE_REQUIREMENTS.items():
        if role in normalized_role:
            return dict(scores)
    return dict(ROLE_REQUIREMENTS["data engineer"])


def _current_scores_by_skill(learner_skills: list[LearnerSkillInput]) -> dict[str, float]:
    current_scores: dict[str, float] = {}
    for learner_skill in learner_skills:
        skill = canonical_skill_name(learner_skill.skill)
        if skill in current_scores:
            raise ValueError(f"Duplicate learner skill supplied: {skill}")
        current_scores[skill] = learner_skill.current_score
    return current_scores


def _build_node(
    skill: str,
    target_score: float,
    current_score: float,
    unlocks: tuple[str, ...],
    current_scores: dict[str, float],
) -> SkillGapNode:
    prerequisites = tuple(item for item in DEPENDENCIES.get(skill, ()) if item in SKILL_CATEGORIES)
    gap = round(max(target_score - current_score, 0), 1)
    category = SKILL_CATEGORIES[skill]
    return SkillGapNode(
        skill=skill,
        category=category,
        current_score=current_score,
        target_score=target_score,
        gap=gap,
        priority=_priority(gap),
        status=_status(current_score, target_score),
        prerequisites=prerequisites,
        unlocks=unlocks,
        estimated_hours=round(gap * HOURS_PER_GAP_POINT[category], 1),
        ready_to_learn=all(current_scores.get(prerequisite, 0.0) >= PREREQUISITE_READY_SCORE for prerequisite in prerequisites),
    )


def _status(current_score: float, target_score: float) -> str:
    if current_score >= target_score:
        return "met"
    if current_score > 0:
        return "in_progress"
    return "not_started"


def _priority(gap: float) -> str:
    if gap >= 6:
        return "Critical"
    if gap >= 4:
        return "High"
    if gap >= 2:
        return "Medium"
    return "Low"


def _capacity_status(required_hours: float, capacity_hours: float) -> str:
    if required_hours <= capacity_hours:
        return "manageable"
    if required_hours <= capacity_hours * 1.25:
        return "tight"
    return "at_risk"


def _node_sort_key(node: SkillGapNode) -> tuple[int, int, str]:
    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    return (priority_order[node.priority], len(node.prerequisites), node.skill)
