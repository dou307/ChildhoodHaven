from typing import Protocol

from app.domain.models import (
    ChildProfile,
    ConfirmedMemory,
    EmotionAnalysis,
    ParentGuidance,
    StoryBook,
)


class ModelProvider(Protocol):
    name: str

    async def analyze(
        self,
        message: str,
        history: list[dict[str, str]],
        confirmed_memories: list[ConfirmedMemory],
        child: ChildProfile,
    ) -> EmotionAnalysis: ...

    async def create_story(
        self,
        message: str,
        analysis: EmotionAnalysis,
        child: ChildProfile,
    ) -> StoryBook: ...

    async def create_parent_guidance(
        self,
        message: str,
        analysis: EmotionAnalysis,
        story: StoryBook,
        child: ChildProfile,
    ) -> ParentGuidance: ...
