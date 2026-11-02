# M3 local Ollama suggestions

Requires M2 graph models and routes. Configure `OLLAMA_URL` and `OLLAMA_MODEL` in the API container.

`POST /api/ai/suggest`
```json
{"dataset_id":1,"relation_types":["HAS_FAULT","REQUIRES_ACTION"],"max_records":20}
```

M3 sends one source record and its matching pre-mapped nodes at a time to local Ollama. Returned IDs and relationship types are checked against the supplied candidates. Only pending proposals are stored, with source-record evidence. Review through M2 endpoints; AI never approves.

Integration: `import ai` then `app.include_router(ai.router)` in `main.py` after graph registration. The application must be able to reach the local Ollama service.
