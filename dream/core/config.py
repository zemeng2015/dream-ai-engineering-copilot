# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from pydantic import BaseModel, Field

from dream.core.paths import DEFAULT_DB_PATH


class DreamConfig(BaseModel):
    llm_provider: str = Field(default="mock")
    audit_db_path: Path = Field(default=DEFAULT_DB_PATH)
    openai_compatible_base_url: str = Field(default="https://api.openai.com/v1")
    openai_compatible_model: str = Field(default="gpt-4o-mini")
    openai_compatible_api_key: str | None = Field(default=None)


def load_config() -> DreamConfig:
    return DreamConfig(
        llm_provider=os.getenv("DREAM_LLM_PROVIDER", "mock"),
        audit_db_path=Path(os.getenv("DREAM_AUDIT_DB_PATH", str(DEFAULT_DB_PATH))),
        openai_compatible_base_url=os.getenv(
            "OPENAI_COMPATIBLE_BASE_URL", "https://api.openai.com/v1"
        ),
        openai_compatible_model=os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4o-mini"),
        openai_compatible_api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY") or None,
    )

