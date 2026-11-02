# GraphForge V0.1 — Project Specification

## Objective
Build a local-first, general-purpose application that transforms structured data into an interactive, evidence-backed knowledge graph.

## Core Workflow
Upload Data -> Validate -> Store -> Map Entities -> AI Suggestions -> Human Approval -> Knowledge Graph -> Explore / Export

## Technology Stack
- Backend: Python 3.12, FastAPI
- Database: PostgreSQL 16
- Frontend: React, TypeScript, Cytoscape.js
- AI: Local Ollama
- Deployment: Docker Compose
- Testing: Pytest and frontend tests
- Coding Agent: Aider with Ollama

## Functional Requirements
GF-01: Import CSV and JSON files.
GF-02: Preserve raw files, records and import metadata.
GF-03: Support user-defined entity and relationship mappings.
GF-04: Generate AI-assisted entity and relationship suggestions.
GF-05: Require human approval before publishing AI suggestions.
GF-06: Store approved nodes and edges in PostgreSQL.
GF-07: Provide interactive graph visualization.
GF-08: Maintain source evidence for every proposed relationship.
GF-09: Export approved graph data as JSON.
GF-10: Maintain an audit trail of review actions.

## Engineering Constraints
- No cloud AI dependency.
- AI suggestions must never be automatically approved.
- Original imported data must remain unchanged.
- Every proposed relationship must reference source evidence.
- Reimporting identical data must not duplicate graph records.
- Invalid or unsupported relationships must be rejected.
- Uploaded content is untrusted and must not execute as code.
- GraphForge must remain separate from existing AI Lab projects.

## Development Milestones
M1: Backend foundation and data ingestion.
M2: Deterministic graph mapping and provenance.
M3: Ollama-based AI suggestions.
M4: Human approval interface and graph visualization.
M5: Automated testing and controlled agent repair workflow.

## Initial Acceptance Test
1. Upload a CSV containing equipment and maintenance records.
2. Validate and store the original dataset.
3. Generate candidate equipment, fault and action entities.
4. Propose relationships with source references.
5. Approve or reject individual suggestions.
6. Display approved entities and relationships.
7. Export the approved graph as JSON.
8. Reimport the same dataset without duplicating records.

## Autonomous Coding Rules
- Work only inside the GraphForge repository.
- Use a dedicated Git task branch.
- Execute generated code only inside an isolated Docker sandbox.
- Disable sandbox network access and avoid mounting secrets.
- Run automated tests after code changes.
- Allow a maximum of three controlled repair attempts.
- Never merge to the main branch without human approval.
