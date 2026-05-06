FROM python:3.13-slim-trixie AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=python3.13

COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM base AS runtime
WORKDIR /app

RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --no-create-home app

COPY --from=builder --chown=app:app /app ./
ENV PATH="/app/.venv/bin:$PATH"

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
