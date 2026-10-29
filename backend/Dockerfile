FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /usr/local/bin/uv
WORKDIR /app

# Dependencies first so code edits don't reinstall them
# Generous timeout: slow networks otherwise fail the build mid-download
ENV UV_HTTP_TIMEOUT=120
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 FASTEMBED_CACHE_PATH=/models
# Bake the embedding and re-ranking models (~150 MB) into the image, so the first upload
# doesn't wait on a download and the container works offline
RUN python -c "from fastembed import TextEmbedding; from fastembed.rerank.cross_encoder import TextCrossEncoder; TextEmbedding('BAAI/bge-small-en-v1.5'); TextCrossEncoder('Xenova/ms-marco-MiniLM-L-6-v2')"

COPY app ./app
RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown app /data
USER app
ENV DATA_DIR=/data DATABASE_URL=sqlite:////data/papertrail.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
