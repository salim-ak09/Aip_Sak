from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from venice_pt.server.routes.control import router as control_router
from venice_pt.server.routes.engagements import router as engagements_router
from venice_pt.server.routes.findings import router as findings_router
from venice_pt.server.ws import websocket_endpoint

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("server_startup", service="venice-pt-api")
    yield
    logger.info("server_shutdown", service="venice-pt-api")


def create_app() -> FastAPI:
    app = FastAPI(
        title="venice-pt API",
        version="0.1.0",
        description="Autonomous AI Pentest Platform - REST & WebSocket Control API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(engagements_router)
    app.include_router(findings_router)
    app.include_router(control_router)

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "venice-pt"}

    @app.websocket("/ws")
    async def ws_route(websocket: WebSocket, since: str | None = None) -> None:
        await websocket_endpoint(websocket, since=since)

    return app


app = create_app()
