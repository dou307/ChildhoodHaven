import asyncio
import json
from contextlib import suppress
from hashlib import sha256
from typing import Any, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.routes import api_access_dependency
from app.domain.models import AgentAction, ChildProfile, TurnRequest, TurnResponse
from app.services.agent_runtime import run_agent_turn

a2a_router = APIRouter(prefix="/api/v1", dependencies=[api_access_dependency])


class JsonRpcRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    jsonrpc: Literal["2.0"]
    id: str | int | None = None
    method: str = Field(min_length=1, max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)
    sessionId: str | None = Field(default=None, min_length=1, max_length=512)


def _jsonrpc_error(request_id: str | int | None, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    )


def _stable_id(prefix: str, value: str) -> str:
    digest = sha256(value.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}-{digest}"


def _session_id(rpc: JsonRpcRequest) -> str | None:
    value = rpc.params.get("sessionId") or rpc.sessionId
    return value if isinstance(value, str) and value.strip() else None


def _task_id(rpc: JsonRpcRequest) -> str:
    value = rpc.params.get("id", rpc.id)
    return str(value) if value is not None else _stable_id("task", json.dumps(rpc.params))


def _message_text(rpc: JsonRpcRequest) -> str | None:
    message = rpc.params.get("message")
    if not isinstance(message, dict):
        return None
    parts = message.get("parts")
    if not isinstance(parts, list):
        return None
    text_parts = [
        part.get("text", "").strip()
        for part in parts
        if isinstance(part, dict) and part.get("kind") == "text"
    ]
    text = "\n".join(item for item in text_parts if item)
    return text or None


def _visible_answer(response: TurnResponse) -> str:
    if response.story is None:
        return response.child_message
    pages = "\n\n".join(page.text for page in response.story.pages)
    return f"{response.child_message}\n\n《{response.story.title}》\n\n{pages}"


def _rpc_event(request_id: str | int | None, result: dict[str, Any]) -> str:
    body = {"jsonrpc": "2.0", "id": request_id, "result": result}
    return f"data: {json.dumps(body, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _status_event(
    request_id: str | int | None,
    task_id: str,
    state: str,
    text: str,
    *,
    final: bool,
) -> str:
    return _rpc_event(
        request_id,
        {
            "taskId": task_id,
            "kind": "status-update",
            "final": final,
            "status": {
                "message": {"role": "agent", "parts": [{"kind": "text", "text": text}]},
                "state": state,
            },
        },
    )


def _artifact_event(
    request_id: str | int | None,
    task_id: str,
    text: str,
    *,
    final: bool,
) -> str:
    return _rpc_event(
        request_id,
        {
            "taskId": task_id,
            "kind": "artifact-update",
            "append": False,
            "lastChunk": True,
            "final": final,
            "artifact": {
                "artifactId": _stable_id("artifact", task_id),
                "parts": [{"kind": "text", "text": text}],
            },
        },
    )


async def _register_task(app, conversation_id: str, task: asyncio.Task) -> bool:
    async with app.state.a2a_tasks_lock:
        current = app.state.a2a_tasks.get(conversation_id)
        if current is not None and not current.done():
            return False
        app.state.a2a_tasks[conversation_id] = task
        return True


async def _remove_task(app, conversation_id: str, task: asyncio.Task) -> None:
    async with app.state.a2a_tasks_lock:
        if app.state.a2a_tasks.get(conversation_id) is task:
            app.state.a2a_tasks.pop(conversation_id, None)


async def _cancel_task(app, conversation_id: str) -> bool:
    async with app.state.a2a_tasks_lock:
        task = app.state.a2a_tasks.get(conversation_id)
        if task is None or task.done():
            return False
        task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    return True


async def _stream_turn(
    request: Request,
    rpc: JsonRpcRequest,
    conversation_id: str,
    payload: TurnRequest,
    task_id: str,
):
    yield _status_event(rpc.id, task_id, "working", "正在理解你的心情", final=False)
    agent_task = asyncio.create_task(
        run_agent_turn(
            request.app.state.agent_graph,
            request.app.state.memory_repository,
            conversation_id,
            payload,
        )
    )
    if not await _register_task(request.app, conversation_id, agent_task):
        agent_task.cancel()
        with suppress(asyncio.CancelledError):
            await agent_task
        yield _status_event(rpc.id, task_id, "failed", "当前会话已有任务正在处理", final=True)
        return

    try:
        response = await agent_task
        requires_input = response.action == AgentAction.ASK_CHILD
        yield _artifact_event(
            rpc.id,
            task_id,
            _visible_answer(response),
            final=not requires_input,
        )
        if requires_input:
            yield _status_event(
                rpc.id,
                task_id,
                "input-required",
                "等待你的补充",
                final=True,
            )
    except asyncio.CancelledError:
        yield _status_event(rpc.id, task_id, "canceled", "任务已取消", final=True)
    except Exception:
        yield _status_event(rpc.id, task_id, "failed", "服务暂时无法完成请求", final=True)
    finally:
        await _remove_task(request.app, conversation_id, agent_task)


@a2a_router.post("/a2a")
async def handle_a2a(body: dict[str, Any], request: Request) -> Response:
    try:
        rpc = JsonRpcRequest.model_validate(body)
    except ValidationError:
        return _jsonrpc_error(body.get("id"), -32600, "无效的JSON-RPC请求")

    if rpc.method == "message/stream":
        session_id = _session_id(rpc)
        text = _message_text(rpc)
        if session_id is None or text is None:
            return _jsonrpc_error(rpc.id, -32602, "缺少sessionId或文本消息")
        try:
            payload = TurnRequest(
                message=text,
                child=ChildProfile(
                    child_id=_stable_id("a2a-child", session_id),
                    nickname="小朋友",
                    age=6,
                ),
                turn_id=_stable_id("a2a-turn", _task_id(rpc)),
            )
        except ValidationError:
            return _jsonrpc_error(rpc.id, -32602, "消息参数不符合要求")
        conversation_id = _stable_id("a2a-conversation", session_id)
        return StreamingResponse(
            _stream_turn(request, rpc, conversation_id, payload, _task_id(rpc)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if rpc.method == "tasks/cancel":
        session_id = _session_id(rpc)
        if session_id is None:
            return _jsonrpc_error(rpc.id, -32602, "缺少sessionId")
        conversation_id = _stable_id("a2a-conversation", session_id)
        canceled = await _cancel_task(request.app, conversation_id)
        state = "canceled" if canceled else "unknown"
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": rpc.id,
                "result": {"id": _task_id(rpc), "status": {"state": state}},
            }
        )

    if rpc.method == "clearContext":
        session_id = _session_id(rpc)
        if session_id is None:
            return _jsonrpc_error(rpc.id, -32602, "缺少sessionId")
        conversation_id = _stable_id("a2a-conversation", session_id)
        await _cancel_task(request.app, conversation_id)
        checkpointer = request.app.state.agent_graph.checkpointer
        await checkpointer.adelete_thread(conversation_id)
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": rpc.id,
                "result": {"status": {"state": "cleared"}},
            }
        )

    return _jsonrpc_error(rpc.id, -32601, "暂不支持该JSON-RPC方法")
