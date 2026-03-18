FROM ghcr.io/astral-sh/uv:latest AS uv_base
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv_base /uv /uvx /bin/
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project || echo "Continue"

COPY . .
RUN uv sync --no-dev
RUN mkdir -p data

CMD ["python", "main.py"]
