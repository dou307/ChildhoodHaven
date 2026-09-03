from app.domain.models import (
    ChildProfile,
    ConfirmedMemory,
    EmotionAnalysis,
    ParentGuidance,
    StoryBook,
    StoryPage,
)


class MockProvider:
    """Visible deterministic provider for development and tests only."""

    name = "mock"

    async def analyze(
        self,
        message: str,
        history: list[dict[str, str]],
        confirmed_memories: list[ConfirmedMemory],
        child: ChildProfile,
    ) -> EmotionAnalysis:
        vague = len(message.strip()) < 8 or message.strip() in {"我不开心", "我难过", "不知道"}
        recalled = confirmed_memories[0] if confirmed_memories and "那件事" in message else None
        previous_child_message = next(
            (
                item["content"]
                for item in reversed(history)
                if item.get("role") == "child" and item.get("content")
            ),
            None,
        )
        if recalled is not None:
            vague = False
        if previous_child_message is not None and message.strip() in {"然后呢", "还是很难过"}:
            vague = False
        emotion = (
            "难过"
            if any(word in message for word in ("不开心", "难过", "没选", "不理"))
            else "委屈"
        )
        return EmotionAnalysis(
            event_summary=recalled.summary if recalled else previous_child_message or message,
            primary_emotion=emotion,
            emotion_intensity=2,
            emotion_clues=[f"孩子表达了{emotion}"],
            known_facts=[]
            if vague
            else [recalled.summary if recalled else previous_child_message or message],
            missing_information=["发生了什么事情"] if vague else [],
            confidence=0.55 if vague else 0.82,
        )

    async def create_story(
        self,
        message: str,
        analysis: EmotionAnalysis,
        child: ChildProfile,
    ) -> StoryBook:
        return StoryBook(
            title="小星星找到自己的位置",
            emotional_goal=f"接住{child.nickname}的{analysis.primary_emotion}，帮助孩子表达需要",
            pages=[
                StoryPage(
                    page_number=1,
                    text=f"今天，{child.nickname}遇到了一件不太开心的事。心里像住进了一小团灰云。",
                    illustration_prompt="温暖绘本风格，小朋友安静地看着窗外，柔和自然光",
                ),
                StoryPage(
                    page_number=2,
                    text="小星星没有催着灰云离开，只轻轻问：你是不是希望有人先看见你？",
                    illustration_prompt="拟人小星星陪伴儿童，保持安全距离，暖黄色调",
                ),
                StoryPage(
                    page_number=3,
                    text="小朋友点点头，说出了自己的感受，也想到了下一次可以主动邀请伙伴一起玩。",
                    illustration_prompt="儿童和伙伴一起画画，表情自然，明亮但不过度饱和",
                ),
            ],
        )

    async def create_parent_guidance(
        self,
        message: str,
        analysis: EmotionAnalysis,
        story: StoryBook,
        child: ChildProfile,
    ) -> ParentGuidance:
        return ParentGuidance(
            observation=f"孩子可能正在经历{analysis.primary_emotion}，目前更需要被听见，而不是马上解决问题。",
            suggested_response=f"可以说：我听见了，今天这件事让你有些{analysis.primary_emotion}，你愿意再讲一点吗？",
            shared_reading_question="故事里的小朋友最希望别人知道什么？",
            next_action="今晚共读后观察孩子是否愿意补充细节；若类似事件反复出现，再与老师沟通。",
        )
