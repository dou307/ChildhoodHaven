import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app


@pytest.fixture
async def client():
    app = create_app(Settings(app_env="test", model_provider="mock", database_url=None))
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client


def payload(message: str, *, child_id: str = "child-1", turn_id: str | None = None) -> dict:
    result = {
        "message": message,
        "child": {"child_id": child_id, "nickname": "小雨", "age": 6},
    }
    if turn_id is not None:
        result["turn_id"] = turn_id
    return result


@pytest.mark.asyncio
async def test_health_exposes_model_mode(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["model_provider"] == "mock"
    assert response.headers["x-request-id"]
    assert float(response.headers["x-response-time-ms"]) >= 0


@pytest.mark.asyncio
async def test_liveness_and_readiness_are_separate(client: AsyncClient):
    live = await client.get("/api/v1/health/live")
    ready = await client.get("/api/v1/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_readiness_reports_dependency_failure(client: AsyncClient):
    class UnavailableRepository:
        async def ping(self) -> None:
            raise RuntimeError("database unavailable")

    client._transport.app.state.memory_repository = UnavailableRepository()
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


@pytest.mark.asyncio
async def test_request_id_is_echoed_and_validation_error_is_structured(client: AsyncClient):
    response = await client.post(
        "/api/v1/conversations/invalid/turns",
        headers={"X-Request-ID": "client-test-request"},
        json={"message": "", "child": {"child_id": "", "nickname": "", "age": 1}},
    )

    assert response.status_code == 422
    assert response.headers["x-request-id"] == "client-test-request"
    assert response.json()["code"] == "invalid_request"
    assert response.json()["request_id"] == "client-test-request"
    assert response.json()["details"]


@pytest.mark.asyncio
async def test_unsafe_request_id_is_replaced(client: AsyncClient):
    response = await client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "private child message"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "private child message"


@pytest.mark.asyncio
async def test_agent_asks_when_information_is_missing(client: AsyncClient):
    response = await client.post(
        "/api/v1/conversations/conv-question/turns",
        json=payload("我不开心"),
    )
    body = response.json()
    assert response.status_code == 200
    assert body["action"] == "ask_child"
    assert body["story"] is None
    assert body["analysis"]["missing_information"]


@pytest.mark.asyncio
async def test_agent_calls_story_and_parent_tools(client: AsyncClient):
    response = await client.post(
        "/api/v1/conversations/conv-story/turns",
        json=payload("今天画画分组时，他们没有先选我，我有一点难过。"),
    )
    body = response.json()
    nodes = [item["node"] for item in body["tool_trace"]]
    assert response.status_code == 200
    assert body["action"] == "create_story"
    assert len(body["story"]["pages"]) == 3
    assert body["parent_guidance"] is not None
    assert "create_story" in nodes
    assert "parent_guidance" in nodes
    assert "propose_memory" in nodes
    assert body["memory_candidate"]["requires_guardian_confirmation"] is True
    assert body["model_provider"] == "mock"


@pytest.mark.asyncio
async def test_urgent_signal_stops_generation(client: AsyncClient):
    response = await client.post(
        "/api/v1/conversations/conv-urgent/turns",
        json=payload("救命，有人打我，我流血了"),
    )
    body = response.json()
    nodes = [item["node"] for item in body["tool_trace"]]
    assert response.status_code == 200
    assert body["action"] == "escalate_guardian"
    assert body["safety"]["risk_level"] == "urgent"
    assert body["story"] is None
    assert "create_story" not in nodes


@pytest.mark.asyncio
async def test_each_turn_resets_transient_story_and_trace(client: AsyncClient):
    conversation = "/api/v1/conversations/conv-multi-turn/turns"
    first = await client.post(
        conversation,
        json=payload("今天画画分组时，他们没有先选我，我有一点难过。"),
    )
    assert first.json()["story"] is not None

    second = await client.post(conversation, json=payload("我不开心"))
    body = second.json()
    nodes = [item["node"] for item in body["tool_trace"]]
    assert body["action"] == "ask_child"
    assert body["story"] is None
    assert nodes == ["safety_screen", "understand_context", "decide", "ask_child", "finalize"]


@pytest.mark.asyncio
async def test_agent_keeps_child_and_assistant_messages_between_turns(client: AsyncClient):
    conversation = "/api/v1/conversations/conv-history/turns"
    first_message = "今天画画分组时，他们没有先选我，我有一点难过。"
    first = await client.post(conversation, json=payload(first_message))
    assert first.status_code == 200

    second = await client.post(conversation, json=payload("然后呢"))
    body = second.json()

    assert second.status_code == 200
    assert body["action"] == "create_story"
    assert body["analysis"]["event_summary"] == first_message

    snapshot = await client._transport.app.state.agent_graph.aget_state(
        {"configurable": {"thread_id": "conv-history"}}
    )
    assert snapshot.values["messages"] == [
        {"role": "child", "content": first_message},
        {"role": "assistant", "content": first.json()["child_message"]},
        {"role": "child", "content": "然后呢"},
        {"role": "assistant", "content": body["child_message"]},
    ]


@pytest.mark.asyncio
async def test_repeated_turn_id_returns_cached_response_without_duplicating_history(
    client: AsyncClient,
):
    conversation = "/api/v1/conversations/conv-idempotent/turns"
    body = payload("今天画画时我被同学忽略了，我很难过。", turn_id="turn-001")

    first = await client.post(conversation, json=body)
    second = await client.post(conversation, json=body)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    snapshot = await client._transport.app.state.agent_graph.aget_state(
        {"configurable": {"thread_id": "conv-idempotent"}}
    )
    assert len(snapshot.values["messages"]) == 2


@pytest.mark.asyncio
async def test_conversation_cannot_be_reused_by_another_child(client: AsyncClient):
    conversation = "/api/v1/conversations/conv-owned/turns"
    first = await client.post(conversation, json=payload("今天我和朋友一起画画。"))
    conflict = await client.post(
        conversation,
        json=payload("这是另一个孩子。", child_id="child-2"),
    )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "conflict"


@pytest.mark.asyncio
async def test_memory_requires_guardian_confirmation_and_can_be_deleted(client: AsyncClient):
    story = await client.post(
        "/api/v1/conversations/conv-memory/turns",
        json=payload("今天画画分组时，他们没有先选我，我有一点难过。"),
    )
    candidate = story.json()["memory_candidate"]

    rejected = await client.post(
        "/api/v1/children/child-1/memories",
        json={"candidate": candidate, "guardian_confirmed": False},
    )
    assert rejected.status_code == 422

    confirmed = await client.post(
        "/api/v1/children/child-1/memories",
        json={"candidate": candidate, "guardian_confirmed": True},
    )
    assert confirmed.status_code == 201
    memory_id = confirmed.json()["memory_id"]

    listed = await client.get("/api/v1/children/child-1/memories")
    assert [item["memory_id"] for item in listed.json()] == [memory_id]

    deleted = await client.delete(f"/api/v1/children/child-1/memories/{memory_id}")
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/children/child-1/memories")).json() == []


@pytest.mark.asyncio
async def test_confirmed_memory_is_reused_across_conversations(client: AsyncClient):
    first = await client.post(
        "/api/v1/conversations/memory-source/turns",
        json=payload("今天画画分组时，他们没有先选我，我有一点难过。"),
    )
    candidate = first.json()["memory_candidate"]
    confirmed = await client.post(
        "/api/v1/children/child-1/memories",
        json={"candidate": candidate, "guardian_confirmed": True},
    )
    assert confirmed.status_code == 201

    follow_up = await client.post(
        "/api/v1/conversations/memory-new-conversation/turns",
        json=payload("还是那件事"),
    )
    body = follow_up.json()
    assert body["action"] == "create_story"
    assert body["analysis"]["event_summary"] == candidate["summary"]
    assert "读取 1 条家长确认记忆" in body["tool_trace"][1]["summary"]


def test_bailian_mode_requires_key():
    from app.providers import create_model_provider

    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        create_model_provider(
            Settings(app_env="test", model_provider="bailian", dashscope_api_key=None)
        )


def test_staging_allows_explicit_mock_with_database_and_api_token():
    settings = Settings(
        app_env="staging",
        model_provider="mock",
        database_url="postgresql://example.invalid/childhood_haven",
        app_api_token=SecretStr("staging-token"),
    )

    assert settings.app_env == "staging"
    assert settings.model_provider == "mock"


def test_staging_requires_database_and_api_token():
    with pytest.raises(ValueError, match="Staging requires DATABASE_URL"):
        Settings(
            app_env="staging",
            model_provider="mock",
            database_url=None,
            app_api_token=None,
        )


def test_production_requires_bailian_and_api_key():
    common = {
        "app_env": "production",
        "database_url": "postgresql://example.invalid/childhood_haven",
        "app_api_token": SecretStr("production-token"),
    }

    with pytest.raises(ValueError, match="Production requires MODEL_PROVIDER=bailian"):
        Settings(model_provider="mock", **common)

    with pytest.raises(ValueError, match="Production requires DASHSCOPE_API_KEY"):
        Settings(model_provider="bailian", dashscope_api_key=None, **common)

    with pytest.raises(ValueError, match="Staging requires APP_API_TOKEN"):
        Settings(
            app_env="staging",
            model_provider="mock",
            database_url="postgresql://example.invalid/childhood_haven",
            app_api_token=None,
        )


@pytest.mark.asyncio
async def test_configured_api_token_is_required():
    app = create_app(
        Settings(
            app_env="test",
            model_provider="mock",
            database_url=None,
            app_api_token=SecretStr("test-token"),
        )
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            denied = await client.post(
                "/api/v1/conversations/auth-test/turns",
                json=payload("今天我和朋友一起画了一幅画，我很开心。"),
            )
            accepted = await client.post(
                "/api/v1/conversations/auth-test/turns",
                headers={"Authorization": "Bearer test-token"},
                json=payload("今天我和朋友一起画了一幅画，我很开心。"),
            )

    assert denied.status_code == 401
    assert denied.json()["code"] == "unauthorized"
    assert denied.json()["request_id"] == denied.headers["x-request-id"]
    assert accepted.status_code == 200
