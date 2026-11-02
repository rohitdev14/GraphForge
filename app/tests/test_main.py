"""M5 integration tests against a dedicated disposable PostgreSQL database."""
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from main import app, SessionLocal, Dataset, SourceRecord, ImportMetadata
from graph import GraphNode, GraphProposal, ReviewAudit
import ai

client = TestClient(app)

def unique_csv() -> bytes:
    token = uuid.uuid4().hex
    return f"equipment_id,fault,action\nPUMP-{token},Vibration,Inspect bearing\n".encode()

def upload_csv(data: bytes):
    return client.post("/upload", files={"file": ("maintenance.csv", data, "text/csv")})

def mapping(dataset_id: int):
    return {"dataset_id": dataset_id,
            "entities": [
                {"entity_type": "equipment", "key_field": "equipment_id"},
                {"entity_type": "fault", "key_field": "fault"},
                {"entity_type": "action", "key_field": "action"}],
            "relations": [
                {"source_type": "equipment", "target_type": "fault", "relation_type": "HAS_FAULT"},
                {"source_type": "fault", "target_type": "action", "relation_type": "REQUIRES_ACTION"}]}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_csv_ingestion_and_duplicate():
    content = unique_csv()
    first = upload_csv(content)
    assert first.status_code == 200, first.text
    dataset_id = first.json()["dataset_id"]
    db = SessionLocal()
    try:
        dataset = db.get(Dataset, dataset_id)
        assert dataset.original_data == content
        assert len(db.query(SourceRecord).filter_by(dataset_id=dataset_id).all()) == 1
        assert db.query(ImportMetadata).filter_by(dataset_id=dataset_id, status="success").count() == 1
    finally:
        db.close()
    duplicate = upload_csv(content)
    assert duplicate.status_code == 409

def test_json_ingestion():
    content = json.dumps([{"equipment_id": uuid.uuid4().hex, "fault": "Leak"}]).encode()
    response = client.post("/upload", files={"file": ("maintenance.json", content, "application/json")})
    assert response.status_code == 200, response.text
    db = SessionLocal()
    try:
        records = db.query(SourceRecord).filter_by(dataset_id=response.json()["dataset_id"]).all()
        assert len(records) == 1
        assert json.loads(records[0].record_data)["fault"] == "Leak"
    finally:
        db.close()

@pytest.mark.parametrize("name,content,mime", [
    ("file.txt", b"hello", "text/plain"),
    ("bad.json", b"{", "application/json"),
    ("empty.json", b"[]", "application/json"),
    ("empty.csv", b"equipment_id,fault\n", "text/csv"),
])
def test_reject_invalid_upload(name, content, mime):
    response = client.post("/upload", files={"file": (name, content, mime)})
    assert response.status_code == 400, response.text

def test_mapping_review_export_and_idempotence():
    response = upload_csv(unique_csv())
    assert response.status_code == 200, response.text
    dataset_id = response.json()["dataset_id"]
    spec = mapping(dataset_id)
    first = client.post("/api/mappings", json=spec)
    assert first.status_code == 200, first.text
    assert first.json()["new_proposals"] == 2
    again = client.post("/api/mappings", json=spec)
    assert again.status_code == 200, again.text
    assert again.json()["new_proposals"] == 0
    proposals = client.get("/api/proposals", params={"dataset_id": dataset_id})
    assert proposals.status_code == 200
    items = proposals.json()
    assert len(items) == 2
    assert all(p["status"] == "pending" and p["evidence"]["source_record_id"] == p["source_record_id"] for p in items)
    before = client.get(f"/api/graph/{dataset_id}").json()
    assert before["edges"] == []
    approve = client.post(f"/api/proposals/{items[0]['id']}/review",
                          json={"action": "approved", "reviewer": "M5-test"})
    assert approve.status_code == 200, approve.text
    reject = client.post(f"/api/proposals/{items[1]['id']}/review",
                         json={"action": "rejected", "reviewer": "M5-test"})
    assert reject.status_code == 200, reject.text
    repeated = client.post(f"/api/proposals/{items[0]['id']}/review",
                           json={"action": "approved", "reviewer": "M5-test"})
    assert repeated.status_code == 409
    exported = client.get(f"/api/graph/{dataset_id}/export")
    assert exported.status_code == 200
    graph = exported.json()
    assert len(graph["edges"]) == 1
    assert len(graph["nodes"]) == 2
    db = SessionLocal()
    try:
        assert db.query(ReviewAudit).filter(ReviewAudit.proposal_id.in_([p["id"] for p in items])).count() == 2
    finally:
        db.close()

def test_ai_suggestions_pending_and_grounded(monkeypatch):
    response = upload_csv(unique_csv())
    assert response.status_code == 200
    dataset_id = response.json()["dataset_id"]
    spec = mapping(dataset_id)
    # Map entities without deterministic relationships; AI must not approve anything.
    spec["relations"] = []
    result = client.post("/api/mappings", json=spec)
    assert result.status_code == 200, result.text
    db = SessionLocal()
    try:
        nodes = db.query(GraphNode).filter_by(dataset_id=dataset_id).all()
        ids = {n.entity_type: n.id for n in nodes}
    finally:
        db.close()
    def fake_ollama(payload):
        return {"relations": [
            {"source_node_id": ids["equipment"], "target_node_id": ids["fault"], "relation_type": "HAS_FAULT"},
            {"source_node_id": 99999999, "target_node_id": ids["fault"], "relation_type": "HAS_FAULT"},
            {"source_node_id": ids["equipment"], "target_node_id": ids["fault"], "relation_type": "UNAPPROVED_TYPE"}]}
    monkeypatch.setattr(ai, "ask_ollama", fake_ollama)
    first = client.post("/api/ai/suggest", json={"dataset_id": dataset_id, "relation_types": ["HAS_FAULT"]})
    assert first.status_code == 200, first.text
    assert first.json()["new_proposals"] == 1
    second = client.post("/api/ai/suggest", json={"dataset_id": dataset_id, "relation_types": ["HAS_FAULT"]})
    assert second.status_code == 200, second.text
    assert second.json()["new_proposals"] == 0
    proposals = client.get("/api/proposals", params={"dataset_id": dataset_id}).json()
    assert len(proposals) == 1
    assert proposals[0]["origin"] == "ollama"
    assert proposals[0]["status"] == "pending"
    assert client.get(f"/api/graph/{dataset_id}").json()["edges"] == []

def test_reject_oversized_upload():
    content = b"equipment_id,fault\n" + b"x" * (5 * 1024 * 1024)
    response = upload_csv(content)
    assert response.status_code == 413

def test_reject_excessive_json_records():
    content = json.dumps([{"equipment_id": "x"}] * 10001).encode()
    response = client.post("/upload", files={"file": ("many.json", content, "application/json")})
    assert response.status_code == 413

def test_reject_excessive_csv_records():
    content = b"equipment_id,fault\n" + b"PUMP-1,Leak\n" * 10001
    response = upload_csv(content)
    assert response.status_code == 400
