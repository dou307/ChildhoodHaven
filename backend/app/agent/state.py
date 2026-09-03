import operator
from typing import Annotated, TypedDict

from app.domain.models import (
    AgentAction,
    ChildProfile,
    ConfirmedMemory,
    EmotionAnalysis,
    MemoryCandidate,
    ParentGuidance,
    SafetyResult,
    StoryBook,
    ToolTraceItem,
    TurnResponse,
)


class AgentState(TypedDict, total=False):
    conversation_id: str
    turn_id: str | None
    child: ChildProfile
    latest_message: str
    messages: Annotated[list[dict[str, str]], operator.add]
    confirmed_memories: list[ConfirmedMemory]
    safety: SafetyResult
    analysis: EmotionAnalysis | None
    action: AgentAction
    story: StoryBook | None
    parent_guidance: ParentGuidance | None
    memory_candidate: MemoryCandidate | None
    child_message: str
    trace: list[ToolTraceItem]
    response: TurnResponse | None
