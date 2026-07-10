# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from dream import __version__
from dream.api.routes import router

DEFAULT_CORS_ORIGINS = (
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:4201",
    "http://127.0.0.1:4201",
    "http://localhost:4300",
    "http://127.0.0.1:4300",
    "http://localhost:4310",
    "http://127.0.0.1:4310",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="DREAM AI Engineering Copilot",
        description="Domain-aware Requirements, Engineering Automation & Memory",
        version=__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    _mount_frontend(app)
    return app


def _cors_origins() -> list[str]:
    configured = [
        origin.strip()
        for origin in os.getenv("DREAM_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return list(dict.fromkeys([*DEFAULT_CORS_ORIGINS, *configured]))


def _frontend_dist() -> Path:
    configured = os.getenv("DREAM_FRONTEND_DIST", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "dist"
        / "frontend"
        / "browser"
    ).resolve()


def _mount_frontend(app: FastAPI) -> None:
    frontend_dir = _frontend_dist()
    index_file = frontend_dir / "index.html"
    if not index_file.is_file():
        return

    @app.get("/{frontend_path:path}", include_in_schema=False)
    def serve_frontend(frontend_path: str) -> FileResponse:
        requested_file = (frontend_dir / frontend_path).resolve()
        try:
            requested_file.relative_to(frontend_dir)
        except ValueError:
            return FileResponse(index_file)

        if frontend_path and requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(index_file)


app = create_app()
