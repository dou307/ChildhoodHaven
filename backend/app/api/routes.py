import asyncio
from secrets import compare_digest

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.models import ConfirmedMemory, ConfirmMemoryRequest, TurnRequest, TurnResponse
from app.services.agent_runtime import ConversationOwnershipError, run_agent_turn

router = APIRouter(prefix="/api/v1")
bearer_scheme = HTTPBearer(auto_error=False)
bearer_dependency = Depends(bearer_scheme)


async def require_api_access(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> None:
    configured = request.app.state.settings.app_api_token
    if configured is None or not configured.get_secret_value().strip():
        return
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少服务访问令牌")
    if not compare_digest(credentials.credentials, configured.get_secret_value()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="服务访问令牌无效")


api_access_dependency = Depends(require_api_access)


@router.get("/health")
async def health(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "environment": settings.app_env,
        "model_provider": settings.model_provider,
        "model": settings.bailian_model if settings.model_provider == "bailian" else None,
        "persistence": "postgres" if settings.database_url else "memory",
    }


@router.get("/health/live")
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request) -> dict:
    try:
        async with asyncio.timeout(2):
            await request.app.state.memory_repository.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务依赖尚未就绪",
        ) from exc
    return {"status": "ready"}


@router.post("/conversations/{conversation_id}/turns", response_model=TurnResponse)
async def create_turn(
    conversation_id: str,
    payload: TurnRequest,
    request: Request,
    _access: None = api_access_dependency,
) -> TurnResponse:
    try:
        return await run_agent_turn(
            request.app.state.agent_graph,
            request.app.state.memory_repository,
            conversation_id,
            payload,
        )
    except ConversationOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/children/{child_id}/memories",
    response_model=ConfirmedMemory,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_memory(
    child_id: str,
    payload: ConfirmMemoryRequest,
    request: Request,
    _access: None = api_access_dependency,
) -> ConfirmedMemory:
    if not payload.guardian_confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="长期记忆必须由监护人明确确认",
        )
    return await request.app.state.memory_repository.add(child_id, payload.candidate)


@router.get("/children/{child_id}/memories", response_model=list[ConfirmedMemory])
async def list_memories(
    child_id: str,
    request: Request,
    _access: None = api_access_dependency,
) -> list[ConfirmedMemory]:
    return await request.app.state.memory_repository.list_for_child(child_id)


@router.delete("/children/{child_id}/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    child_id: str,
    memory_id: str,
    request: Request,
    _access: None = api_access_dependency,
) -> None:
    deleted = await request.app.state.memory_repository.delete(child_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该记忆")
