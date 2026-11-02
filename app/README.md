# GraphForge Backend

This is the backend for GraphForge, a local-first application that transforms structured data into interactive knowledge graphs.

## Features Implemented (M1)

- FastAPI backend with PostgreSQL database
- CSV and JSON file ingestion
- Database models for datasets, source records, and import metadata
- File validation and duplicate detection using SHA-256 hashes
- Docker Compose configuration for backend and PostgreSQL

## Setup

1. Install Docker and Docker Compose
2. Run `docker-compose up` to start the backend and database
3. The API will be available at http://localhost:8000

## API Endpoints

### Upload File
`POST /upload`
- Accepts CSV and JSON files
- Validates file format
- Checks for duplicates using SHA-256 hash
- Stores original data and metadata

### Health Check
`GET /health`
- Returns status of the backend service

## Testing

Run tests with:
