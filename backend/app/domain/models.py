from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AgentAction(StrEnum):
    ASK_CHILD = "ask_child"
    CREATE_STORY = "create_story"
    ESCALATE_GUARDIAN = "escalate_guardian"


class RiskLevel(StrEnum):
    NONE = "none"
    WATCH = "watch"
    URGENT = "urgent"


class MemoryCategory(StrEnum):
    SOCIAL_EVENT = "social_event"
    EMOTIONAL_PATTERN = "emotional_pattern"
    PREFERENCE = "preference"
    ROUTINE = "routine"


class ChildProfile(BaseModel):
    child_id: str = Field(min_length=1, max_length=64)
    nickname: str = Field(min_length=1, max_length=20)
    age: int = Field(ge=3, le=12)


class TurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    child: ChildProfile
    turn_id: str | None = Field(default=None, min_length=1, max_length=64)


class EmotionAnalysis(BaseModel):
    event_summary: str
    primary_emotion: str
    emotion_intensity: int = Field(ge=0, le=3)
    emotion_clues: list[str] = Field(default_factory=list)
    known_facts: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class StoryPage(BaseModel):
    page_number: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=300)
    illustration_prompt: str = Field(min_length=1, max_length=300)


class StoryBook(BaseModel):
    title: str = Field(min_length=1, max_length=40)
    emotional_goal: str = Field(min_length=1, max_length=100)
    pages: list[StoryPage] = Field(min_length=3, max_length=5)


class ParentGuidance(BaseModel):
    observation: str
    suggested_response: str
    shared_reading_question: str
    next_action: str
    disclaimer: str = "本建议仅用于日常情绪陪伴，不构成心理或医学诊断。"


class SafetyResult(BaseModel):
    risk_level: RiskLevel
    matched_signals: list[str] = Field(default_factory=list)
    reason: str


class ToolTraceItem(BaseModel):
    step: int
    node: str
    summary: str


class MemoryCandidate(BaseModel):
    summary: str = Field(min_length=1, max_length=200)
    category: MemoryCategory
    reason: str = Field(min_length=1, max_length=200)
    requires_guardian_confirmation: bool = True


class ConfirmMemoryRequest(BaseModel):
    candidate: MemoryCandidate
    guardian_confirmed: bool


class ConfirmedMemory(BaseModel):
    memory_id: str
    child_id: str
    summary: str
    category: MemoryCategory
    created_at: datetime


class TurnResponse(BaseModel):
    conversation_id: str
    action: AgentAction
    child_message: str
    safety: SafetyResult
    analysis: EmotionAnalysis | None = None
    story: StoryBook | None = None
    parent_guidance: ParentGuidance | None = None
    memory_candidate: MemoryCandidate | None = None
    tool_trace: list[ToolTraceItem]
    model_provider: str
