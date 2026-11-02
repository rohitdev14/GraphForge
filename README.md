# GraphForge

**V0.1 — initial validated baseline (phase closed, 2 November 2026)**

GraphForge is a **local-first, evidence-backed knowledge graph builder** for structured data. It turns CSV/JSON records into proposed entities and relationships, requires a person to review proposals, and visualizes the approved graph. Original source records remain traceable.

> **Status:** M1–M5 implementation merged into `main` through [PR #1](https://github.com/rohitdev14/GraphForge/pull/1). Initial local acceptance and GitHub Actions validation passed. This is a development prototype, **not** a production deployment.

## Workflow

```text
Import CSV/JSON
    ↓
Validate and preserve source records
    ↓
Define entity / relationship mappings
    ↓
Generate evidence-linked proposals
    ↓
Human review: approve or reject
    ↓
Explore / export approved graph
```

Optional local Ollama suggestions follow the same human-review gate. **Live Ollama inference was not tested during V0.1 acceptance.**

## Implemented capabilities

- FastAPI ingestion with PostgreSQL persistence, source metadata, and duplicate-import protection.
- Deterministic entity mapping and evidence-linked relationship proposals.
- Human approval/rejection, review audit trail, and approved-only graph output.
- Local Ollama suggestion endpoint with constrained proposal validation; covered by mocked tests, not a live model acceptance test.
- React + TypeScript interface with Cytoscape.js graph visualization and JSON export.
- Docker Compose development environment and automated backend/frontend checks.

## Stack

| Layer | Technology |
| --- | --- |
| API | Python 3.12, FastAPI, SQLAlchemy |
| Storage | PostgreSQL 16 |
| UI | React, TypeScript, Vite, Cytoscape.js |
| Optional local AI | Ollama |
| Deployment | Docker Compose |
| Validation | Pytest, TypeScript/Vite build, GitHub Actions |

## Run locally

Prerequisites: Docker Desktop with Docker Compose, plus a checkout of this repository.

From the **repository root**, create your local configuration before starting (edit the generated `.env` and replace the example password):

```powershell
Copy-Item .env.example .env
notepad .env
```

**Existing V0.1 users:** The earlier Compose setup created PostgreSQL role `user` with a fixed development password. The new Compose configuration uses role `graphforge` and a password from `.env`. An existing PostgreSQL data volume will **not** automatically migrate credentials. Before restarting against an existing volume, migrate the database role/password or back up and deliberately recreate the development database. Do not run `docker compose down -v` unless you intend to delete stored datasets.

Then run:

```powershell
docker compose -f app/docker-compose.yml up --build -d
```

- Interface: http://localhost:5173
- API documentation: http://localhost:8000/docs

Stop services while preserving the PostgreSQL data volume:

```powershell
docker compose -f app/docker-compose.yml down
```

Run the backend test suite:

```powershell
docker compose -f app/docker-compose.yml exec backend python -m pytest -q
```

Run the frontend production build:

```powershell
docker compose -f app/docker-compose.yml exec frontend npm run build
```

The optional Ollama connection defaults to `http://host.docker.internal:11434` with model `qwen3:8b`; override with `OLLAMA_URL` and `OLLAMA_MODEL` if needed.

## V0.1 validation record

| Check | Outcome |
| --- | --- |
| Docker backend, frontend, PostgreSQL startup | Passed |
| PostgreSQL health | Passed |
| Backend integration tests | **9 passed** |
| Frontend TypeScript and Vite build | Passed |
| CSV import and mapped proposals | Observed in UI |
| Source evidence traceability | Observed in UI |
| Human approval and approved graph | Observed in UI |
| Rejection behavior | User-verified |
| GitHub Actions M5 validation | Passed |
| Live Ollama inference | **Not tested** |

Known non-blocking issues: graph edge-label overlap in the UI, frontend bundle-size warning, and dependency deprecation warnings. The V0.1 acceptance did not establish production readiness or complete coverage of every requirement in `PROJECT.md`.

## Open-source license

Released under the [MIT License](LICENSE). Copyright (c) 2026 Rohit Khurana.

## Security and scope

**Local development only.** The supplied Compose setup requires a local password in an ignored `.env`, binds exposed ports to 127.0.0.1, and does not implement authentication/authorization for review endpoints. Uploads are limited to 5 MiB and 10,000 records. Do not expose these services to untrusted networks or upload sensitive operational data without additional controls. See [SECURITY.md](SECURITY.md). AI suggestions must never be automatically approved.

## Project records

- [PROJECT.md](PROJECT.md) — objectives, requirements, engineering constraints, milestones, and acceptance criteria.
- [M5 validation notes](docs/M5_VALIDATION.md) — automated checks and acceptance procedure.
- [PR #1](https://github.com/rohitdev14/GraphForge/pull/1) — reviewed integration history.

**Phase conclusion:** V0.1 baseline is merged and initial validation is complete. The local test containers were shut down after testing, with the database volume preserved. Further enhancements belong to a subsequent phase.
