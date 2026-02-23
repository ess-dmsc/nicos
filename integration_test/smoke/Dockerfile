ARG PYTHON_BASE_IMAGE=python:3.8-slim-bullseye
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash nicos

COPY requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir \
        "requests<2.30.0" \
        Pillow \
        lxml \
        mock \
        pytest \
        pytest-timeout

COPY --chown=nicos:nicos . .
RUN chown nicos:nicos /workspace

USER nicos

CMD ["pytest", "-q", "integration_test/smoke/test_smoke.py", "--junitxml=integration_test/runtime/smoke-junit.xml"]
