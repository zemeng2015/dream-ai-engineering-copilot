# SPDX-License-Identifier: Apache-2.0

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    return app


def _cors_origins() -> list[str]:
    configured = [
        origin.strip()
        for origin in os.getenv("DREAM_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return list(dict.fromkeys([*DEFAULT_CORS_ORIGINS, *configured]))


app = create_app()
