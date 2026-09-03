import json
import logging

import pytest
from httpx import ASGITransport, AsyncClient

from app.agent.graph import build_agent_graph
from app.config import Settings
from app.main import create_app
from app.observability import logger as observability_logger
from app.providers.mock import MockProvider


def events_from(caplog) -> list[dict]:
    return [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "childhood_haven.observability"
    ]


def payload(message: str) -> dict:
    return {
        "message": message,
        "child": {"child_id": "private-child-id", "nickname": "隐私昵称", "age": 7},
    }


@pytest.fixture
def observability_logs(caplog):
    caplog.set_level(logging.INFO, logger="childhood_haven.observability")
    observability_logger.addHandler(caplog.handler)
    try:
        yield caplog
    finally:
        observability_logger.removeHandler(caplog.handler)


@pytest.mark.asyncio
async def test_observability_records_request_and_agent_latency_without_private_content(
    observability_logs,
):
    app = create_app(Settings(app_env="test", model_provider="mock", database_url=None))
    private_message = "只有家长可以知道的秘密内容"

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/conversations/private-conversation-id/turns",
                headers={"X-Request-ID": "observable-request"},
                json=payload(private_message),
            )

    assert response.status_code == 200
    events = events_from(observability_logs)
    request_event = next(item for item in events if item["event"] == "request.completed")
    node_events = [item for item in events if item["event"] == "agent.node.completed"]

    assert request_event["request_id"] == "observable-request"
    assert request_event["route"] == "/api/v1/conversations/{conversation_id}/turns"
    assert request_event["status_code"] == 200
    assert request_event["duration_ms"] >= 0
    assert {item["node"] for item in node_events} >= {
        "safety_screen",
        "understand_context",
        "decide",
        "finalize",
    }
    assert all(item["duration_ms"] >= 0 for item in node_events)

    serialized_events = "\n".join(record.message for record in observability_logs.records)
    assert private_message not in serialized_events
    assert "隐私昵称" not in serialized_events
    assert "private-child-id" not in serialized_events
    assert "private-conversation-id" not in serialized_events


class FailingProvider(MockProvider):
    async def analyze(self, message, history, confirmed_memories, child):
        raise RuntimeError(f"provider failed with private input: {message}")


@pytest.mark.asyncio
async def test_observability_records_error_type_without_exception_message(observability_logs):
    app = create_app(Settings(app_env="test", model_provider="mock", database_url=None))
    private_message = "不应进入错误日志的儿童原话"

    async with app.router.lifespan_context(app):
        app.state.agent_graph = build_agent_graph(FailingProvider())
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/conversations/error-conversation-id/turns",
                json=payload(private_message),
            )

    assert response.status_code == 500
    events = events_from(observability_logs)
    node_error = next(
        item
        for item in events
        if item["event"] == "agent.node.completed" and item["outcome"] == "error"
    )
    request_error = next(item for item in events if item["event"] == "request.error")

    assert node_error["node"] == "understand_context"
    assert node_error["error_type"] == "RuntimeError"
    assert request_error["error_type"] == "RuntimeError"
    serialized_events = "\n".join(record.message for record in observability_logs.records)
    assert private_message not in serialized_events
    assert "provider failed" not in serialized_events
