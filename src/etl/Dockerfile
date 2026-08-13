FROM python:3.12-slim AS base

WORKDIR /opt/etl

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .python-version ./
RUN uv sync --no-cache
COPY . ./
RUN uv pip install -e .

ENV PATH="/opt/etl/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

FROM base AS server

EXPOSE 4200

RUN mkdir -p /data/.prefect

CMD ["prefect", "server", "start", "--host", "0.0.0.0", "--port", "4200"]

FROM base AS worker

CMD ["/bin/sh", "-c", "\
    python /opt/etl/deploy_all.py && \
    prefect worker start --pool default --limit 1 --type process \
"]
