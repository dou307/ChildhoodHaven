import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.api.a2a import _stable_id
from app.config import Settings
from app.main import create_app


def rpc_request(message: str, *, rpc_id: str = "rpc-1", session_id: str = "session-1") -> dict:
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": "message/stream",
        "params": {
            "id": f"task-{rpc_id}",
            "sessionId": session_id,
            "message": {"role": "user", "parts": [{"kind": "text", "text": message}]},
        },
    }


def sse_events(body: str) -> list[dict]:
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]


@pytest.fixture
async def client():
    app = create_app(Settings(app_env="test", model_provider="mock", database_url=None))
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client


@pytest.mark.asyncio
async def test_message_stream_adapts_agent_result_to_huawei_sse(client: AsyncClient):
    response = await client.post(
        "/api/v1/a2a",
        json=rpc_request("今天画画分组时，他们没有先选我，我有一点难过。"),
    )
    events = sse_events(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [event["result"]["kind"] for event in events] == [
        "status-update",
        "artifact-update",
    ]
    assert events[0]["result"]["status"]["state"] == "working"
    artifact = events[1]["result"]
    assert artifact["final"] is True
    answer = artifact["artifact"]["parts"][0]["text"]
    assert "《" in answer and "》" in answer
    assert answer.count("\n\n") >= 4


@pytest.mark.asyncio
async def test_message_stream_marks_clarification_as_input_required(client: AsyncClient):
    response = await client.post("/api/v1/a2a", json=rpc_request("我不开心"))
    events = sse_events(response.text)

    assert [event["result"]["kind"] for event in events] == [
        "status-update",
        "artifact-update",
        "status-update",
    ]
    assert events[-1]["result"]["status"]["state"] == "input-required"
    assert events[-1]["result"]["final"] is True


@pytest.mark.asyncio
async def test_a2a_session_is_pseudonymous_and_clearable(client: AsyncClient):
    raw_session_id = "private-user-session"
    response = await client.post(
        "/api/v1/a2a",
        json=rpc_request("我不开心", session_id=raw_session_id),
    )
    assert response.status_code == 200

    conversation_id = _stable_id("a2a-conversation", raw_session_id)
    snapshot = await client._transport.app.state.agent_graph.aget_state(
        {"configurable": {"thread_id": conversation_id}}
    )
    assert snapshot.values["conversation_id"] == conversation_id
    assert raw_session_id not in conversation_id

    cleared = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "id": "clear-1",
            "method": "clearContext",
            "sessionId": raw_session_id,
        },
    )
    empty_snapshot = await client._transport.app.state.agent_graph.aget_state(
        {"configurable": {"thread_id": conversation_id}}
    )

    assert cleared.json()["result"]["status"]["state"] == "cleared"
    assert empty_snapshot.values == {}


@pytest.mark.asyncio
async def test_unknown_method_and_missing_params_return_jsonrpc_errors(client: AsyncClient):
    unknown = await client.post(
        "/api/v1/a2a",
        json={"jsonrpc": "2.0", "id": "bad-1", "method": "unknown"},
    )
    invalid = await client.post(
        "/api/v1/a2a",
        json={"jsonrpc": "2.0", "id": "bad-2", "method": "message/stream"},
    )

    assert unknown.json()["error"]["code"] == -32601
    assert invalid.json()["error"]["code"] == -32602


@pytest.mark.asyncio
async def test_a2a_uses_existing_bearer_authentication():
    app = create_app(
        Settings(
            app_env="test",
            model_provider="mock",
            database_url=None,
            app_api_token=SecretStr("a2a-token"),
        )
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            denied = await client.post("/api/v1/a2a", json=rpc_request("我不开心"))
            accepted = await client.post(
                "/api/v1/a2a",
                headers={"Authorization": "Bearer a2a-token"},
                json=rpc_request("我不开心"),
            )

    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert sse_events(accepted.text)[-1]["result"]["final"] is True


@pytest.mark.asyncio
async def test_cancel_without_active_task_returns_unknown(client: AsyncClient):
    response = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "id": "cancel-1",
            "method": "tasks/cancel",
            "sessionId": "idle-session",
        },
    )

    assert response.json()["result"]["status"]["state"] == "unknown"


@pytest.mark.asyncio
async def test_cancel_stops_active_task_for_session(client: AsyncClient):
    raw_session_id = "busy-session"
    conversation_id = _stable_id("a2a-conversation", raw_session_id)
    active_task = asyncio.create_task(asyncio.sleep(60))
    client._transport.app.state.a2a_tasks[conversation_id] = active_task

    response = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "id": "cancel-active",
            "method": "tasks/cancel",
            "sessionId": raw_session_id,
        },
    )

    assert response.json()["result"]["status"]["state"] == "canceled"
    assert active_task.cancelled()
