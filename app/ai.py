"""Local Ollama candidate suggestions; all output is untrusted and pending review."""
import json
import os
import urllib.request
import urllib.error
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from main import SessionLocal, SourceRecord, Dataset
from graph import GraphNode, GraphProposal

router = APIRouter(prefix="/api/ai", tags=["local-ai"])
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

class SuggestRequest(BaseModel):
    dataset_id: int
    relation_types: list[str] = Field(min_length=1)
    max_records: int = Field(default=20, ge=1, le=100)

def ask_ollama(payload: dict) -> dict:
    request = urllib.request.Request(
        OLLAMA_URL + "/api/generate",
        data=json.dumps({"model": OLLAMA_MODEL, "prompt": json.dumps(payload),
                         "stream": False, "format": "json",
                         "options": {"temperature": 0}}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            answer = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise HTTPException(503, "Local Ollama is unavailable") from exc
    try:
        result = json.loads(answer["response"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(502, "Ollama returned invalid JSON") from exc
    if not isinstance(result, dict) or not isinstance(result.get("relations"), list):
        raise HTTPException(502, "Ollama response must contain relations array")
    return result

@router.post("/suggest")
def suggest(request: SuggestRequest):
    db = SessionLocal()
    try:
        if not db.get(Dataset, request.dataset_id):
            raise HTTPException(404, "Dataset not found")
        records = db.query(SourceRecord).filter_by(dataset_id=request.dataset_id).order_by(SourceRecord.order).limit(request.max_records).all()
        nodes = db.query(GraphNode).filter_by(dataset_id=request.dataset_id).all()
        if not nodes:
            raise HTTPException(422, "Create deterministic entity mappings first")
        allowed = set(request.relation_types)
        if any(not value or len(value) > 100 for value in allowed):
            raise HTTPException(422, "Invalid relation type")
        created = 0
        for record in records:
            try:
                data = json.loads(record.record_data)
            except ValueError:
                continue
            # A model can only select existing node IDs for the CURRENT record.
            # Its claims are never accepted without human review.
            node_catalog = [{"id": n.id, "type": n.entity_type, "key": n.entity_key}
                            for n in nodes if n.entity_key in {str(v).strip() for v in data.values()}] if isinstance(data, dict) else []
            if len(node_catalog) < 2:
                continue
            ids = {n["id"] for n in node_catalog}
            result = ask_ollama({
                "instruction": "Return JSON only: {relations:[{source_node_id:int,target_node_id:int,relation_type:str}]}. "
                               "Use only supplied node IDs and allowed relation types. "
                               "Suggest only relationships directly supported by this record. "
                               "Never invent entities or evidence. Empty array if uncertain.",
                "record": data, "record_id": record.id,
                "nodes": node_catalog, "allowed_relation_types": sorted(allowed)})
            for item in result["relations"][:30]:
                if not isinstance(item, dict):
                    continue
                a, b, kind = item.get("source_node_id"), item.get("target_node_id"), item.get("relation_type")
                if type(a) is not int or type(b) is not int or a not in ids or b not in ids or a == b or kind not in allowed:
                    continue
                existing = db.query(GraphProposal).filter_by(source_record_id=record.id,
                    source_node_id=a, target_node_id=b, relation_type=kind).first()
                if existing:
                    continue
                evidence = {"dataset_id": request.dataset_id, "source_record_id": record.id,
                            "record_order": record.order, "source_fields": data}
                db.add(GraphProposal(dataset_id=request.dataset_id, source_record_id=record.id,
                    source_node_id=a, target_node_id=b, relation_type=kind,
                    status="pending", origin="ollama", evidence_json=json.dumps(evidence)))
                db.flush()
                created += 1
        db.commit()
        return {"dataset_id": request.dataset_id, "new_proposals": created, "status": "pending"}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
