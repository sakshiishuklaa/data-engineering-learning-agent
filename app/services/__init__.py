"""Application service layer."""

from app.services.learner_memory_service import (
    add_skill_to_learner,
    create_learner,
    create_learning_progress,
    create_project,
    create_skill,
    update_learner,
    update_learner_skill_score,
    update_learning_progress,
    update_project,
)
from app.services.skill_gap_service import analyze_skill_gaps
from app.services.roadmap_service import generate_personalized_roadmap, validate_roadmap
from app.services.planner_service import generate_learning_plan
from app.services.teaching_service import (
    build_teaching_flow,
    extract_topic,
    handle_teaching_command,
    parse_teaching_command,
)
from app.services.quiz_service import (
    evaluate_learner_answer,
    get_quiz,
    list_quiz_questions,
    submit_quiz_answer,
)
from app.services.progress_service import (
    calculate_overall_progress,
    calculate_phase_completion,
    calculate_study_streak,
    get_progress_dashboard,
    recommend_next_action,
)

__all__ = [
    "create_learner",
    "update_learner",
    "create_skill",
    "add_skill_to_learner",
    "update_learner_skill_score",
    "create_learning_progress",
    "update_learning_progress",
    "create_project",
    "update_project",
    "analyze_skill_gaps",
    "generate_personalized_roadmap",
    "validate_roadmap",
    "generate_learning_plan",
    "build_teaching_flow",
    "extract_topic",
    "handle_teaching_command",
    "parse_teaching_command",
    "evaluate_learner_answer",
    "get_quiz",
    "list_quiz_questions",
    "submit_quiz_answer",
    "calculate_overall_progress",
    "calculate_phase_completion",
    "calculate_study_streak",
    "get_progress_dashboard",
    "recommend_next_action",
]
