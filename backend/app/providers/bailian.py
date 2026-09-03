import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.domain.models import (
    ChildProfile,
    ConfirmedMemory,
    EmotionAnalysis,
    ParentGuidance,
    StoryBook,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class BailianProvider:
    name = "bailian"

    def __init__(self, api_key: str, base_url: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    async def _structured_call(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_model: type[ModelT],
    ) -> ModelT:
        schema = json.dumps(output_model.model_json_schema(), ensure_ascii=False)
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt}\n只输出符合以下 JSON Schema 的 JSON，"
                        f"不要输出 Markdown：\n{schema}"
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        return output_model.model_validate_json(content)

    async def analyze(
        self,
        message: str,
        history: list[dict[str, str]],
        confirmed_memories: list[ConfirmedMemory],
        child: ChildProfile,
    ) -> EmotionAnalysis:
        return await self._structured_call(
            system_prompt=(
                "你是儿童情绪陪伴 Agent 的理解模块。只做日常情绪理解，不做心理或医学诊断。"
                "区分孩子明确说出的事实与推测；信息不足时填写 missing_information。"
            ),
            user_prompt=json.dumps(
                {
                    "child": child.model_dump(),
                    "message": message,
                    "recent_history": history[-6:],
                    "guardian_confirmed_memories": [
                        item.model_dump(mode="json") for item in confirmed_memories[:5]
                    ],
                },
                ensure_ascii=False,
            ),
            output_model=EmotionAnalysis,
        )

    async def create_story(
        self,
        message: str,
        analysis: EmotionAnalysis,
        child: ChildProfile,
    ) -> StoryBook:
        return await self._structured_call(
            system_prompt=(
                "你是儿童绘本工具。生成 3 页适合亲子共读的短故事，每页不超过 80 个汉字。"
                "故事要承认情绪、避免说教，不虚构孩子未提供的敏感事实，不承诺一定解决。"
            ),
            user_prompt=json.dumps(
                {
                    "child": child.model_dump(),
                    "message": message,
                    "analysis": analysis.model_dump(),
                },
                ensure_ascii=False,
            ),
            output_model=StoryBook,
        )

    async def create_parent_guidance(
        self,
        message: str,
        analysis: EmotionAnalysis,
        story: StoryBook,
        child: ChildProfile,
    ) -> ParentGuidance:
        return await self._structured_call(
            system_prompt=(
                "你是家长陪伴建议工具。提供具体、温和、可执行的回应，不做诊断，不给出惩罚建议。"
                "明确区分观察和推测。"
            ),
            user_prompt=json.dumps(
                {
                    "child": child.model_dump(),
                    "message": message,
                    "analysis": analysis.model_dump(),
                    "story": story.model_dump(),
                },
                ensure_ascii=False,
            ),
            output_model=ParentGuidance,
        )
