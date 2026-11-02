# GraphForge M2 API contract

All routes use the existing FastAPI service.

- `POST /api/mappings`: `{"dataset_id":1,"entities":[{"entity_type":"equipment","key_field":"equipment_id"},{"entity_type":"fault","key_field":"fault"}],"relations":[{"source_type":"equipment","target_type":"fault","relation_type":"HAS_FAULT"}]}`
- `GET /api/proposals?dataset_id=1&status=pending`: candidates with source-record evidence.
- `POST /api/proposals/{id}/review`: `{"action":"approved","reviewer":"operator"}` or `rejected`.
- `GET /api/graph/{dataset_id}`: approved nodes and edges only.
- `GET /api/graph/{dataset_id}/export`: approved graph JSON.

Graph proposal IDs are stable. Reapplying the same mapping does not create duplicate proposals. Review decisions are immutable in V0.1. No automatic approval.

Integration: import `graph` and register `graph.router` from `main.py` after defining the existing ORM models; call `Base.metadata.create_all(bind=engine)` after graph models have been imported.
