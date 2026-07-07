# SPDX-License-Identifier: Apache-2.0

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dream import __version__
from dream.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="DREAM AI Engineering Copilot",
        description="Domain-aware Requirements, Engineering Automation & Memory",
        version=__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:4200",
            "http://127.0.0.1:4200",
            "http://localhost:4201",
            "http://127.0.0.1:4201",
            "http://localhost:4300",
            "http://127.0.0.1:4300",
            "http://localhost:5000",
            "http://127.0.0.1:5000",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
