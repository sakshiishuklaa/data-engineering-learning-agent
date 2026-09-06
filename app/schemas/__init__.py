"""Request and response schemas."""

from app.schemas.assessment import AssessmentResult, SkillAssessmentInput
from app.schemas.skill_gap import (
    LearnerProfileInput,
    LearnerSkillInput,
    SkillGapAnalysisInput,
    SkillGapAnalysisResult,
    SkillGapEdge,
    SkillGapNode,
)
from app.schemas.roadmap import (
    PersonalizedRoadmap,
    RoadmapGenerationInput,
    RoadmapGenerationResult,
    RoadmapPhase,
)
from app.schemas.planner import (
    DailyPlan,
    LearningPlan,
    LearningPlannerInput,
    PlannerAllocation,
    WeeklyPlanItem,
)
from app.schemas.teaching import (
    LearnerSkillLevel,
    QuizQuestion,
    TeachingCommand,
    TeachingFlow,
    TeachingRequest,
    TeachingResponse,
    TeachingSession,
)

__all__ = [
    "AssessmentResult",
    "SkillAssessmentInput",
    "LearnerProfileInput",
    "LearnerSkillInput",
    "SkillGapAnalysisInput",
    "SkillGapAnalysisResult",
    "SkillGapEdge",
    "SkillGapNode",
    "PersonalizedRoadmap",
    "RoadmapGenerationInput",
    "RoadmapGenerationResult",
    "RoadmapPhase",
    "DailyPlan",
    "LearningPlan",
    "LearningPlannerInput",
    "PlannerAllocation",
    "WeeklyPlanItem",
    "LearnerSkillLevel",
    "QuizQuestion",
    "TeachingCommand",
    "TeachingFlow",
    "TeachingRequest",
    "TeachingResponse",
    "TeachingSession",
]
