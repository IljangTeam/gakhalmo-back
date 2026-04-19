# syntax=docker/dockerfile:1
# asyncmy 0.2.11 은 Python 3.14 aarch64 휠이 없어 sdist 컴파일이 필요.
# builder 스테이지에서 gcc 로 빌드, runtime 스테이지는 슬림 이미지에 venv 만 복사.

FROM python:3.14-slim AS builder

WORKDIR /app

RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


FROM python:3.14-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
