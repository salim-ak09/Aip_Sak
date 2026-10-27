from __future__ import annotations

import uvicorn


def serve_api(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Starts the Uvicorn ASGI server with the FastAPI application."""
    uvicorn.run("venice_pt.server.app:app", host=host, port=port, reload=reload)
