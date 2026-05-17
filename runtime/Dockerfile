# ── Stage 1: build ──
FROM python:3.11-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --root-user-action=ignore -e . --target /build/deps

# ── Stage 2: run ──
FROM python:3.11-slim AS run

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash tagent

WORKDIR /app

COPY --from=build /build/deps /usr/local/lib/python3.11/site-packages/
COPY . /app/runtime/

RUN chown -R tagent:tagent /app

USER tagent

EXPOSE 8800

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8800/health || exit 1

CMD ["uvicorn", "runtime.api.main:app", "--host", "0.0.0.0", "--port", "8800"]
