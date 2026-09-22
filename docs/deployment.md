# Deployment

## Requirements

- Docker Engine 24+
- Docker Compose v2
- At least 2 GB RAM and a persistent disk volume

## First start

```bash
cp .env.example .env
# Set APP_SECRET_KEY. LLM_API_KEY may remain empty for local deterministic mode.
docker compose up -d --build
curl http://localhost:8080/api/health
```

The API container runs `alembic upgrade head` before starting Uvicorn.

## Persistence

- `studymate_data`: `/data/studymate.db` and `/data/uploads`.
- `chroma_data`: `/chroma/chroma`.

Back up SQLite first, then uploads, then Chroma. If Chroma is lost, upload files and the `documents` table remain the source for `reindex`.

## Upgrade

```bash
docker compose stop api
docker compose run --rm api alembic upgrade head
docker compose up -d --build
curl http://localhost:8080/api/health
```

## Rollback

Keep the previous image tag, SQLite file, upload volume and `.env`. Restore all three and start the previous image. Do not downgrade Alembic unless a tested down migration exists.
