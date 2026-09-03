from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import build_agent_graph
from app.api.errors import install_exception_handlers
from app.api.routes import router
from app.config import Settings, get_settings
from app.persistence import open_persistence
from app.providers import create_model_provider


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        provider = create_model_provider(resolved_settings)
        async with open_persistence(resolved_settings.database_url) as persistence:
            app.state.settings = resolved_settings
            app.state.memory_repository = persistence.memory_repository
            app.state.agent_graph = build_agent_graph(provider, persistence.checkpointer)
            yield

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def attach_request_context(request: Request, call_next) -> Response:
        supplied_request_id = request.headers.get("x-request-id", "").strip()
        request_id = supplied_request_id[:64] if supplied_request_id else str(uuid4())
        request.state.request_id = request_id
        started_at = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{(perf_counter() - started_at) * 1000:.1f}"
        return response

    install_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()
