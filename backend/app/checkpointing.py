from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

_DOMAIN_TYPES = (
    "AgentAction",
    "RiskLevel",
    "MemoryCategory",
    "ChildProfile",
    "EmotionAnalysis",
    "StoryPage",
    "StoryBook",
    "ParentGuidance",
    "SafetyResult",
    "ToolTraceItem",
    "MemoryCandidate",
    "ConfirmedMemory",
    "TurnResponse",
)


def create_checkpoint_serializer() -> JsonPlusSerializer:
    allowed = [("app.domain.models", type_name) for type_name in _DOMAIN_TYPES]
    return JsonPlusSerializer(allowed_msgpack_modules=allowed)
