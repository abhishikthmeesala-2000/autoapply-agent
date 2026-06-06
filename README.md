# CareerOS AI / AutoApply Agent

CareerOS AI is a local-first job search and application assistant. This repository is being built in phases, starting with the monorepo foundation.

## Phase 1 Included

- `apps/web`: Next.js dashboard shell
- `apps/api`: FastAPI service with `/health`
- `apps/extension`: Plasmo extension side panel
- `packages/shared`: shared type placeholder package
- `infra/docker-compose.yml`: Postgres and Qdrant
- `Makefile`: dev, test, lint, format commands

## Prerequisites

- Node.js 20+ recommended
- Python 3.9+
- Docker and Docker Compose for local databases

## Install

```bash
npm install
python3 -m pip install -r apps/api/requirements.txt
```

## Run

Start the web app:

```bash
cd apps/web && npm run dev
```

Start the API:

```bash
cd apps/api && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the extension in development mode:

```bash
cd apps/extension && npm run dev
```

Or run everything with Make:

```bash
make dev
```

## Verify

```bash
make test
make lint
make format
```

## Databases

If Docker is available:

```bash
docker compose -f infra/docker-compose.yml up -d
```

This starts:

- PostgreSQL on `localhost:5432`
- Qdrant on `localhost:6333`
