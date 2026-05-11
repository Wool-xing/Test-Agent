FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/runtime/pyproject.toml
COPY . /app/runtime/

WORKDIR /app
RUN pip install -e ./runtime

EXPOSE 8800

CMD ["uvicorn", "runtime.api.main:app", "--host", "0.0.0.0", "--port", "8800"]
