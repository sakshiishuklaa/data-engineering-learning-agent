"""LLM-powered personalized roadmap generation with validation gates."""

from __future__ import annotations

from typing import Any, Protocol

from app.schemas.roadmap import (
    LearningPriority,
    PersonalizedRoadmap,
    RoadmapGenerationInput,
    RoadmapGenerationResult,
)


class RoadmapLLMClient(Protocol):
    """Boundary for a structured-output LLM adapter."""

    def generate_roadmap(self, *, prompt: str, response_model: type[PersonalizedRoadmap]) -> Any:
        """Return data that can be parsed as ``PersonalizedRoadmap``."""


PRIORITY_BY_GAP_PRIORITY: dict[str, LearningPriority] = {
    "Critical": "MUST_LEARN",
    "High": "MUST_LEARN",
    "Medium": "GOOD_TO_LEARN",
    "Low": "OPTIONAL",
}


def generate_personalized_roadmap(
    generation_input: RoadmapGenerationInput,
    llm_client: RoadmapLLMClient,
) -> RoadmapGenerationResult:
    """Generate a roadmap through a structured LLM boundary and validate it."""
    prompt = build_roadmap_prompt(generation_input)
    try:
        raw_roadmap = llm_client.generate_roadmap(prompt=prompt, response_model=PersonalizedRoadmap)
        roadmap = raw_roadmap if isinstance(raw_roadmap, PersonalizedRoadmap) else PersonalizedRoadmap.model_validate(raw_roadmap)
    except Exception:
        return RoadmapGenerationResult(success=False, error="Roadmap generation failed. Please retry later.")

    validation_errors = validate_roadmap(roadmap, generation_input)
    if validation_errors:
        return RoadmapGenerationResult(
            success=False,
            error="Generated roadmap failed validation.",
            validation_errors=tuple(validation_errors),
        )
    return RoadmapGenerationResult(success=True, roadmap=roadmap)


def build_roadmap_prompt(generation_input: RoadmapGenerationInput) -> str:
    """Create a constrained prompt for a structured-output LLM adapter."""
    skill_gaps = [
        {
            "skill": node.skill,
            "gap": node.gap,
            "priority": PRIORITY_BY_GAP_PRIORITY[node.priority],
            "prerequisites": node.prerequisites,
            "estimated_hours": node.estimated_hours,
            "ready_to_learn": node.ready_to_learn,
        }
        for node in generation_input.skill_gap_analysis.nodes
        if node.gap > 0
    ]
    known_skills = [
        node.skill
        for node in generation_input.skill_gap_analysis.nodes
        if node.gap == 0 or node.current_score >= node.target_score
    ]
    return (
        "Generate a personalized data-engineering learning roadmap as structured JSON only. "
        "Use the supplied response_model/Pydantic schema. Do not include prose outside the JSON. "
        "Rules: do not teach everything simultaneously; respect prerequisites; skip known topics; "
        "prioritize MUST_LEARN skills; keep the plan realistic for the target timeline and weekly hours; "
        "include hands-on exercises, progressively harder mini projects, interview questions, and completion criteria; "
        "clearly mark each phase priority as MUST_LEARN, GOOD_TO_LEARN, or OPTIONAL.\n"
        f"Target role: {generation_input.target_role}\n"
        f"Target timeline: {generation_input.target_timeline} "
        f"({generation_input.skill_gap_analysis.timeline_weeks} weeks)\n"
        f"Weekly study hours: {generation_input.weekly_study_hours}\n"
        f"Learner profile: {generation_input.learner_profile.model_dump_json()}\n"
        f"Known skills to skip as topics: {known_skills}\n"
        f"Skill gaps to plan: {skill_gaps}\n"
        f"Roadmap JSON schema: {PersonalizedRoadmap.model_json_schema()}"
    )


def validate_roadmap(roadmap: PersonalizedRoadmap, generation_input: RoadmapGenerationInput) -> list[str]:
    """Check generated roadmap against dependency, priority, and capacity rules."""
    errors: list[str] = []
    gap_nodes = {node.skill: node for node in generation_input.skill_gap_analysis.nodes}
    priority_by_skill = {skill: PRIORITY_BY_GAP_PRIORITY[node.priority] for skill, node in gap_nodes.items() if node.gap > 0}
    allowed_topics = set(priority_by_skill)
    known_topics = {skill for skill, node in gap_nodes.items() if node.gap == 0 or node.current_score >= node.target_score}
    planned_topics: list[str] = []
    completed_topics = set(known_topics)

    if roadmap.timeline_weeks != generation_input.skill_gap_analysis.timeline_weeks:
        errors.append("Roadmap timeline_weeks must match the skill gap analysis timeline.")
    if roadmap.study_hours_per_week != generation_input.weekly_study_hours:
        errors.append("Roadmap study_hours_per_week must match the requested weekly study hours.")
    if roadmap.total_estimated_weeks > generation_input.skill_gap_analysis.timeline_weeks:
        errors.append("Roadmap exceeds the requested target timeline.")

    for phase in roadmap.phases:
        if len(phase.topics) > 4:
            errors.append(f"Phase {phase.phase} teaches too many topics simultaneously.")
        for topic in phase.topics:
            if topic in known_topics:
                errors.append(f"Phase {phase.phase} includes already-known topic: {topic}.")
            if topic not in allowed_topics:
                errors.append(f"Phase {phase.phase} includes unsupported topic: {topic}.")
                continue
            planned_topics.append(topic)
            if phase.priority != priority_by_skill[topic]:
                errors.append(f"Phase {phase.phase} marks {topic} as {phase.priority}, expected {priority_by_skill[topic]}.")
            missing_prerequisites = [
                prerequisite
                for prerequisite in gap_nodes[topic].prerequisites
                if prerequisite not in completed_topics
            ]
            if missing_prerequisites:
                errors.append(
                    f"Phase {phase.phase} teaches {topic} before prerequisites: {', '.join(missing_prerequisites)}."
                )
        completed_topics.update(topic for topic in phase.topics if topic in allowed_topics)

    planned_topic_set = set(planned_topics)
    missing_must_learn = {
        skill for skill, priority in priority_by_skill.items() if priority == "MUST_LEARN" and skill not in planned_topic_set
    }
    if missing_must_learn:
        errors.append(f"Roadmap omits MUST_LEARN skills: {', '.join(sorted(missing_must_learn))}.")

    must_learn_phase_numbers = [
        phase.phase for phase in roadmap.phases for topic in phase.topics if priority_by_skill.get(topic) == "MUST_LEARN"
    ]
    optional_phase_numbers = [
        phase.phase for phase in roadmap.phases for topic in phase.topics if priority_by_skill.get(topic) == "OPTIONAL"
    ]
    if must_learn_phase_numbers and optional_phase_numbers and min(optional_phase_numbers) < max(must_learn_phase_numbers):
        errors.append("OPTIONAL topics appear before all MUST_LEARN topics are scheduled.")

    return errors
