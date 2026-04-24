ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.9.18
ARG PYTHON_BASE_IMAGE=python:3.13-slim-bookworm

FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_BASE_IMAGE}

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy

ENV PATH="/workspace/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_DYNAMIC_VERSIONING_BYPASS=0.0.0 \
    UV_LINK_MODE=copy \
    UV_PYTHON=3.13

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash nicos

COPY --from=uv /uv /uvx /usr/local/bin/
COPY --chown=nicos:nicos . .

RUN uv sync --all-packages --locked --group dev \
    && chown -R nicos:nicos /workspace

USER nicos

CMD ["uv", "run", "pytest", "-q", "integration_test/smoke/test_smoke.py"]
