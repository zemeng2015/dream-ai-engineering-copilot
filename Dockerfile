# SPDX-License-Identifier: Apache-2.0

FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE NOTICE ./
COPY dream ./dream
COPY knowledge_packs ./knowledge_packs
COPY examples ./examples
COPY docs ./docs
COPY deploy ./deploy

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "dream.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

