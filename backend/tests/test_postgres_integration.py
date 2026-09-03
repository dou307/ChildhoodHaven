import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not configured"),
]


def payload(message: str, child_id: str) -> dict:
    return {
        "message": message,
        "child": {"child_id": child_id, "nickname": "集成测试", "age": 7},
    }


def open_client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_postgres_persists_memory_and_conversation_checkpoints_across_restarts():
    suffix = uuid4().hex
    child_id = f"integration-{suffix}"
    conversation_id = f"integration-{suffix}"
    settings = Settings(
        app_env="test",
        model_provider="mock",
        database_url=TEST_DATABASE_URL,
    )

    first_app = create_app(settings)
    async with first_app.router.lifespan_context(first_app):
        async with open_client(first_app) as client:
            first_turn = await client.post(
                f"/api/v1/conversations/{conversation_id}/turns",
                json=payload("今天画画分组时，他们没有先选我，我有一点难过。", child_id),
            )
            assert first_turn.status_code == 200

            confirmed = await client.post(
                f"/api/v1/children/{child_id}/memories",
                json={
                    "candidate": first_turn.json()["memory_candidate"],
                    "guardian_confirmed": True,
                },
            )
            assert confirmed.status_code == 201
            memory_id = confirmed.json()["memory_id"]

    second_app = create_app(settings)
    async with second_app.router.lifespan_context(second_app):
        async with open_client(second_app) as client:
            memories = await client.get(f"/api/v1/children/{child_id}/memories")
            assert memories.status_code == 200
            assert [item["memory_id"] for item in memories.json()] == [memory_id]

            second_turn = await client.post(
                f"/api/v1/conversations/{conversation_id}/turns",
                json=payload("然后呢", child_id),
            )
            assert second_turn.status_code == 200
            assert second_turn.json()["analysis"]["event_summary"] == (
                "今天画画分组时，他们没有先选我，我有一点难过。"
            )

            deleted = await client.delete(f"/api/v1/children/{child_id}/memories/{memory_id}")
            assert deleted.status_code == 204
