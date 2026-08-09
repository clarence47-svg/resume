FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

RUN set -eux; \
    for attempt in 1 2 3; do \
        apt-get -o Acquire::Retries=5 update \
        && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
            libreoffice-core libreoffice-writer libreoffice-impress \
            libmagic1 fonts-wqy-zenhei \
        && rm -rf /var/lib/apt/lists/* \
        && exit 0; \
        sleep 5; \
    done; \
    exit 1

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .

CMD [".venv/bin/python", "src/run_service.py"]
