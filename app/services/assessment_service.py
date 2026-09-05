"""Evidence-weighted data-engineering skill assessment."""

from __future__ import annotations

from app.schemas.assessment import AssessmentResult, SkillAssessmentInput

DATA_ENGINEERING_SKILLS = (
    "Python", "SQL", "Databases", "Data Modeling", "ETL/ELT", "Data Warehousing",
    "Linux", "Git", "Cloud", "Object Storage", "Spark/PySpark", "Orchestration",
    "Streaming", "Data Quality", "Docker", "CI/CD", "Monitoring", "System Design",
)
EVIDENCE_WEIGHTS = {"self_report": 0.20, "diagnostic": 0.30, "quiz": 0.35, "project": 0.15}

# One lightweight, opt-in check per skill for the first assessment pass. The
# engine accepts a diagnostic score so a future richer quiz UI can reuse it.
DIAGNOSTIC_QUESTIONS = {
    "Python": ("Which collection is mutable?", ("tuple", "list", "string"), "list"),
    "SQL": ("Which clause groups aggregate results?", ("GROUP BY", "ORDER BY", "WHERE"), "GROUP BY"),
    "Databases": ("What does an index primarily improve?", ("Query lookup speed", "Disk encryption", "Row size"), "Query lookup speed"),
    "Data Modeling": ("A fact table usually stores:", ("Measurable events", "Only user names", "API secrets"), "Measurable events"),
    "ETL/ELT": ("In ELT, transformation happens:", ("After loading", "Before extraction", "Only in a browser"), "After loading"),
    "Data Warehousing": ("A warehouse is optimized mainly for:", ("Analytics", "Mobile rendering", "Source control"), "Analytics"),
    "Linux": ("Which command lists files?", ("ls", "cd", "pwd"), "ls"),
    "Git": ("Which command records staged changes?", ("git commit", "git clone", "git fetch"), "git commit"),
    "Cloud": ("Which cloud property allows capacity to scale?", ("Elasticity", "Normalization", "Denormalization"), "Elasticity"),
    "Object Storage": ("Object storage organizes data as:", ("Objects in buckets", "Rows in tables", "Blocks in RAM"), "Objects in buckets"),
    "Spark/PySpark": ("Spark is designed for:", ("Distributed processing", "Only spreadsheet macros", "DNS resolution"), "Distributed processing"),
    "Orchestration": ("A DAG represents:", ("Task dependencies", "A database backup", "A container image"), "Task dependencies"),
    "Streaming": ("Streaming data is processed:", ("Continuously as events arrive", "Only yearly", "Only after manual export"), "Continuously as events arrive"),
    "Data Quality": ("A uniqueness check detects:", ("Unexpected duplicates", "Slow CPU", "Expired certificates"), "Unexpected duplicates"),
    "Docker": ("A Docker image is:", ("A runnable package template", "A running process", "A Git branch"), "A runnable package template"),
    "CI/CD": ("Continuous integration emphasizes:", ("Frequent validated merges", "Manual server access", "Monthly backups"), "Frequent validated merges"),
    "Monitoring": ("An alert should be based on:", ("A meaningful threshold", "A random schedule", "A file name"), "A meaningful threshold"),
    "System Design": ("A load balancer primarily:", ("Distributes traffic", "Stores objects", "Compiles Python"), "Distributes traffic"),
}


def level_for_score(score: float) -> str:
    """Map a 1--10 score to the learner-facing proficiency bands."""
    if score <= 3:
        return "Beginner"
    if score <= 6:
        return "Intermediate"
    if score <= 8:
        return "Advanced"
    return "Expert"


def _confidence(evidence_count: int) -> str:
    return "Low" if evidence_count <= 1 else "Medium" if evidence_count == 2 else "High"


def _priority(gap: float, confidence: str) -> str:
    if gap >= 6:
        return "Critical"
    if gap >= 4:
        return "High"
    if gap >= 2:
        return "Medium"
    return "Low" if confidence == "Low" else "Medium"


def assess_skill(assessment: SkillAssessmentInput) -> AssessmentResult:
    """Combine self-report, diagnostics, quizzes, and project evidence.

    Present evidence is normalized by configured weight. Self-report counts for
    just 20% when objective evidence is supplied. A self-report-only result is
    retained as a clearly low-confidence provisional result, not validation.
    """
    if assessment.skill not in DATA_ENGINEERING_SKILLS:
        raise ValueError(f"Unsupported skill: {assessment.skill}")
    evidence: list[tuple[str, float, float]] = [("Self report", assessment.self_reported_score, EVIDENCE_WEIGHTS["self_report"])]
    if assessment.diagnostic_score is not None:
        evidence.append(("Diagnostic", assessment.diagnostic_score, EVIDENCE_WEIGHTS["diagnostic"]))
    if assessment.quiz_score is not None:
        evidence.append(("Quiz", assessment.quiz_score, EVIDENCE_WEIGHTS["quiz"]))
    if assessment.project_evidence_score is not None:
        evidence.append(("Project evidence", assessment.project_evidence_score, EVIDENCE_WEIGHTS["project"]))
    total_weight = sum(weight for _, _, weight in evidence)
    current_score = round(sum(score * weight for _, score, weight in evidence) / total_weight, 1)
    gap = round(max(assessment.target_score - current_score, 0), 1)
    confidence = _confidence(len(evidence))
    return AssessmentResult(skill=assessment.skill, current_score=current_score, target_score=assessment.target_score,
                            gap=gap, level=level_for_score(current_score), priority=_priority(gap, confidence),
                            confidence=confidence, evidence_sources=tuple(name for name, _, _ in evidence))


def assess_skills(assessments: list[SkillAssessmentInput]) -> list[AssessmentResult]:
    """Assess every canonical skill once and return priority-sorted results."""
    supplied = {assessment.skill for assessment in assessments}
    missing = set(DATA_ENGINEERING_SKILLS) - supplied
    duplicates = len(supplied) != len(assessments)
    if missing or duplicates:
        details = [f"Missing skills: {', '.join(sorted(missing))}"] if missing else []
        if duplicates:
            details.append("Each skill may be assessed only once.")
        raise ValueError(" ".join(details))
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    return sorted((assess_skill(item) for item in assessments), key=lambda item: (order[item.priority], -item.gap, item.skill))
