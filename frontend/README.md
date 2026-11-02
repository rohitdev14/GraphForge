# GraphForge frontend (M4)

React + TypeScript + Cytoscape.js interface for CSV/JSON upload, deterministic mappings, optional local AI suggestions, evidence inspection, individual approve/reject, approved graph visualization, and JSON export.

Requires the M1 API, M2 graph API, and M3 AI API for the full workflow.

From `frontend/`: `npm install`, then `npm run dev`. Vite proxies `/api` and `/upload` to `http://localhost:8000`.

Production: set up a reverse proxy to the backend for the same paths. The V0.1 review interface is intended for trusted local use; it is not a multi-user authentication system.
