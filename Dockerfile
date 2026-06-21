# Test-Agent V2.0.0 Docker image
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Test-Agent"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.description="AI-powered testing framework"
LABEL org.opencontainers.image.source="https://github.com/Wool-xing/Test-Agent"

WORKDIR /app

COPY pyproject.toml .
COPY runtime/ runtime/
COPY utils/ utils/
COPY ai/ ai/

RUN pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir playwright && \
    playwright install chromium --with-deps

ENV TAGENT_LLM_PROVIDER=stub
ENV TAGENT_DEPLOYMENT_MODE=enterprise

EXPOSE 8800

ENTRYPOINT ["python", "-m", "runtime.cli.main"]
CMD ["--help"]
