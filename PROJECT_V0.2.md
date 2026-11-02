# GraphForge V0.2 — Project Specification

Status: Proposed implementation scope
Baseline: GraphForge V0.1 (see [PROJECT.md](PROJECT.md))

## Objective
Extend the local-first, evidence-backed graph builder to integrate multiple structured datasets, resolve shared entities, persist evolving graphs, and enable practical exploration and structured queries. Preserve human control over AI-assisted changes.

## Scope and Priorities

### P0 — Core data integrity
- **GF2-01 Multi-dataset ingestion:** Import multiple CSV/JSON datasets; validate schemas and record import metadata, source identifiers, version/checksum and errors. Keep originals unchanged.
- **GF2-02 Entity resolution:** Detect candidate duplicates and cross-dataset identity matches using deterministic rules first. Display match rationale, confidence when applicable, and conflicting attributes. Require human approval for uncertain merges; support rejection and prevent unintended automatic merges.
- **GF2-03 Provenance:** Preserve source dataset, record and mapping references for every node, edge, merge decision and proposed relationship; trace back to immutable raw evidence.
- **GF2-04 Incremental persistence:** Save, reopen and update approved graphs without duplicate nodes or edges when identical data is reimported. Maintain review and change history.

### P1 — Usability and interoperability
- **GF2-05 Graph Explorer V2:** Search nodes, filter by type/source, expand neighborhoods, inspect relationship details and source evidence.
- **GF2-06 Query API:** Provide documented, read-only structured endpoints for entities, relationships, neighborhoods and provenance, with pagination and bounded query limits.
- **GF2-07 AI-assisted discovery:** Use optional local Ollama to propose evidence-linked relationships or matches; never publish AI suggestions without human approval. Clearly separate deterministic results from AI proposals.
- **GF2-08 Export:** Export approved graph data to JSON and CSV with stable identifiers and provenance references.

### P2 — Analysis and benchmarking
- **GF2-09 Graph analytics:** Connected components, degree-based node importance and disconnected entities; label algorithms and limitations.
- **GF2-10 Benchmarking:** Measure ingestion time, entity-resolution quality, query latency and memory usage on documented datasets and hardware.

## Architecture
CSV/JSON datasets → validation and immutable raw storage → deterministic mapping and entity-resolution proposals → human review → approved PostgreSQL graph (nodes, edges, provenance) → React/Cytoscape explorer, structured API and export.

Optional Ollama provides proposals only; it is not required for ingestion, querying or visualization.

Existing stack: Python 3.12, FastAPI, PostgreSQL 16, React, TypeScript, Cytoscape.js, Docker Compose, pytest and frontend tests.

## Milestones
- **M6 — Multi-source ingestion and provenance:** Dataset identity/versioning, repeat-import safety, evidence traceability and regression tests.
- **M7 — Entity resolution:** Candidate matching, conflict handling, approval/rejection and audit trail.
- **M8 — Persistent graph and explorer:** Incremental graph updates, save/reopen, search/filter/neighborhood exploration and bounded read-only API.
- **M9 — AI proposals and export:** Optional local suggestions with review workflow; JSON/CSV exports preserving provenance.
- **M10 — Validation and release:** Cross-dataset end-to-end acceptance tests, quality/performance benchmarks, documentation and security checks.

## Acceptance Test
1. Import three related CSV/JSON datasets containing overlapping equipment, maintenance and action records.
2. Confirm raw records and per-record provenance remain accessible and unchanged.
3. Identify shared entities and present candidate matches with rationale; approve or reject them.
4. Build a connected graph of approved entities and evidence-backed relationships without auto-approving AI suggestions.
5. Search for an entity, inspect its neighborhood and trace each displayed relationship to source records.
6. Save/reopen the graph; reimport an identical dataset and confirm no duplicates.
7. Query the graph via the bounded read-only API and export approved JSON/CSV.
8. Pass automated integration, regression and security checks; record benchmark methodology and results.

## Out of Scope for V0.2
Neo4j migration, RAG pipelines, autonomous graph-editing agents, cloud AI services and real-time streaming ingestion.

## Engineering and Release Constraints
- Remain local-first; no cloud AI dependency.
- Imported content is untrusted; do not execute uploaded code or scripts.
- Never mutate original source data; retain immutable evidence.
- Require human approval for AI suggestions and ambiguous entity merges.
- Validate relationship types, preserve source references and record review actions.
- Prevent duplicates on identical reimport; handle conflicting identities explicitly.
- Work on dedicated Git branches; test changes in an isolated environment.
- Follow V0.1 controlled coding-agent rules: no network or secrets in execution sandbox, at most three repair attempts, automated tests after edits.
- Never merge into `main` or change repository visibility without explicit human approval.

## Delivery Artifacts
Implementation code and migrations; API specification; automated tests; example multi-dataset fixtures; benchmark report; updated README and release notes.

## Implementation Gate
This document defines the agreed V0.2 scope. Implementation starts with M6 only after review/approval of this specification.
