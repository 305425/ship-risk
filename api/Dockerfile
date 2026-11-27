FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RULES_PATH=/app/rules.yaml \
    FASTEMBED_CACHE_PATH=/var/cache/fastembed

WORKDIR /app
COPY pyproject.toml ./
RUN mkdir -p app ingest config && touch app/__init__.py ingest/__init__.py
RUN pip install --no-cache-dir -e .
COPY app ./app
COPY ingest ./ingest
COPY config ./config
COPY alembic.ini rules.yaml entrypoint.py chainlit.md ./
COPY alembic ./alembic
COPY public ./public
COPY chainlit/config.toml ./.chainlit/config.toml

RUN useradd --system --no-create-home app
USER root

EXPOSE 8000
ENTRYPOINT ["python", "entrypoint.py"]
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
