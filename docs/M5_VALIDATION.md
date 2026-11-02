# M5 — integration and validation

The V0.1 integration PR #1 was merged into `main` after successful GitHub Actions and local acceptance. CI runs for pull requests targeting `main` and pushes to `main` and the release-preparation branch. It checks:

1. Python 3.12 syntax compilation.
2. PostgreSQL 16-backed API integration tests for CSV/JSON import, duplicate detection, invalid files, deterministic mappings, idempotence, source-record evidence, review audit, approved-only export, and local AI output validation (mocked Ollama).
3. React/TypeScript frontend compilation and Vite production build.

No live Ollama model inference is exercised by CI. That requires a separate local acceptance check.

## Local startup

From the repository root, copy `.env.example` to `.env` and set a unique local database password, then use:

```powershell
docker compose -f app/docker-compose.yml up --build -d
```

Open `http://localhost:5173` for the UI or `http://localhost:8000/docs` for the API.

The Compose file is for trusted local development only; unauthenticated review endpoints are not suitable for network-exposed production use.

## Local end-to-end acceptance

1. Upload CSV with columns `equipment_id,fault,action`.
2. Create entity mappings and relationship types.
3. Review evidence and approve one proposal; reject another.
4. Verify the graph displays only the approved relationship.
5. Export graph JSON.
6. Upload the identical file again and confirm HTTP 409 (no duplicate records).
7. Optionally enable local Ollama and verify AI proposals remain pending until reviewed.

M5 initial acceptance completed: 9 backend tests passed locally, the frontend build succeeded, CI passed, and the dataset-to-approved-graph UI flow was observed. Live Ollama inference remains untested. Public-release security hardening is tracked separately.
