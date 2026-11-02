"""Deterministic evidence-backed graph mapping and human review API."""
import json
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Session
from main import Base, SessionLocal, SourceRecord, Dataset

router = APIRouter(prefix="/api", tags=["graph"])

class GraphNode(Base):
    __tablename__ = "graph_nodes"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_key = Column(String(500), nullable=False)
    attributes_json = Column(Text, nullable=False, default="{}")
    __table_args__ = (UniqueConstraint("dataset_id", "entity_type", "entity_key"),)

class GraphProposal(Base):
    __tablename__ = "graph_proposals"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    source_record_id = Column(Integer, ForeignKey("source_records.id"), nullable=False)
    source_node_id = Column(Integer, ForeignKey("graph_nodes.id"), nullable=False)
    target_node_id = Column(Integer, ForeignKey("graph_nodes.id"), nullable=False)
    relation_type = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    origin = Column(String(20), nullable=False, default="mapping")
    evidence_json = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("source_record_id", "source_node_id", "target_node_id", "relation_type"),)

class ReviewAudit(Base):
    __tablename__ = "review_audit"
    id = Column(Integer, primary_key=True)
    proposal_id = Column(Integer, ForeignKey("graph_proposals.id"), nullable=False)
    action = Column(String(20), nullable=False)
    reviewer = Column(String(200), nullable=False)
    reviewed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class EntityMapping(BaseModel):
    entity_type: str = Field(min_length=1, max_length=100)
    key_field: str = Field(min_length=1)
    attribute_fields: list[str] = Field(default_factory=list)

class RelationMapping(BaseModel):
    source_type: str
    target_type: str
    relation_type: str = Field(min_length=1, max_length=100)

class MappingRequest(BaseModel):
    dataset_id: int
    entities: list[EntityMapping] = Field(min_length=1)
    relations: list[RelationMapping] = Field(default_factory=list)

class ReviewRequest(BaseModel):
    action: str
    reviewer: str = Field(min_length=1, max_length=200)

def _object(record: SourceRecord) -> dict[str, Any]:
    try:
        value = json.loads(record.record_data)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Source record {record.id} is not a JSON object")
    if not isinstance(value, dict):
        raise HTTPException(422, f"Source record {record.id} is not a JSON object")
    return value

def _node(db: Session, dataset_id: int, spec: EntityMapping, record: dict) -> GraphNode | None:
    value = record.get(spec.key_field)
    if value is None or not str(value).strip():
        return None
    key = str(value).strip()
    node = db.query(GraphNode).filter_by(dataset_id=dataset_id, entity_type=spec.entity_type, entity_key=key).first()
    if node is None:
        node = GraphNode(dataset_id=dataset_id, entity_type=spec.entity_type, entity_key=key,
                         attributes_json=json.dumps({k: record[k] for k in spec.attribute_fields if k in record}))
        db.add(node)
        db.flush()
    return node

@router.post("/mappings")
def apply_mapping(request: MappingRequest):
    db = SessionLocal()
    try:
        if not db.get(Dataset, request.dataset_id):
            raise HTTPException(404, "Dataset not found")
        types = {e.entity_type for e in request.entities}
        if len(types) != len(request.entities):
            raise HTTPException(422, "Entity types must be unique")
        for relation in request.relations:
            if relation.source_type not in types or relation.target_type not in types:
                raise HTTPException(422, "Relationship references unmapped entity type")
        created = 0
        records = db.query(SourceRecord).filter_by(dataset_id=request.dataset_id).order_by(SourceRecord.order).all()
        for source in records:
            data = _object(source)
            nodes = {spec.entity_type: _node(db, request.dataset_id, spec, data) for spec in request.entities}
            for relation in request.relations:
                a, b = nodes[relation.source_type], nodes[relation.target_type]
                if a is None or b is None or a.id == b.id:
                    continue
                evidence = {"dataset_id": request.dataset_id, "source_record_id": source.id,
                            "record_order": source.order, "source_fields": data}
                existing = db.query(GraphProposal).filter_by(source_record_id=source.id,
                    source_node_id=a.id, target_node_id=b.id, relation_type=relation.relation_type).first()
                if existing is None:
                    db.add(GraphProposal(dataset_id=request.dataset_id, source_record_id=source.id,
                        source_node_id=a.id, target_node_id=b.id, relation_type=relation.relation_type,
                        evidence_json=json.dumps(evidence)))
                    created += 1
        db.commit()
        return {"dataset_id": request.dataset_id, "new_proposals": created, "records_processed": len(records)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def _proposal(p: GraphProposal) -> dict:
    return {"id": p.id, "dataset_id": p.dataset_id, "source_record_id": p.source_record_id,
            "source_node_id": p.source_node_id, "target_node_id": p.target_node_id,
            "relation_type": p.relation_type, "status": p.status, "origin": p.origin,
            "evidence": json.loads(p.evidence_json)}

@router.get("/proposals")
def list_proposals(dataset_id: int, status: str | None = None):
    db = SessionLocal()
    try:
        q = db.query(GraphProposal).filter_by(dataset_id=dataset_id)
        if status:
            q = q.filter_by(status=status)
        return [_proposal(p) for p in q.order_by(GraphProposal.id).all()]
    finally:
        db.close()

@router.post("/proposals/{proposal_id}/review")
def review(proposal_id: int, request: ReviewRequest):
    if request.action not in ("approved", "rejected"):
        raise HTTPException(422, "Action must be approved or rejected")
    db = SessionLocal()
    try:
        p = db.get(GraphProposal, proposal_id)
        if p is None:
            raise HTTPException(404, "Proposal not found")
        if p.status != "pending":
            raise HTTPException(409, "Proposal already reviewed")
        p.status = request.action
        db.add(ReviewAudit(proposal_id=p.id, action=request.action, reviewer=request.reviewer))
        db.commit()
        return _proposal(p)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

@router.get("/graph/{dataset_id}")
def approved_graph(dataset_id: int):
    db = SessionLocal()
    try:
        if not db.get(Dataset, dataset_id):
            raise HTTPException(404, "Dataset not found")
        edges = db.query(GraphProposal).filter_by(dataset_id=dataset_id, status="approved").all()
        node_ids = {i for edge in edges for i in (edge.source_node_id, edge.target_node_id)}
        nodes = [db.get(GraphNode, i) for i in sorted(node_ids)]
        return {"dataset_id": dataset_id,
                "nodes": [{"id": n.id, "type": n.entity_type, "key": n.entity_key,
                           "attributes": json.loads(n.attributes_json)} for n in nodes],
                "edges": [_proposal(edge) for edge in edges]}
    finally:
        db.close()

@router.get("/graph/{dataset_id}/export")
def export_graph(dataset_id: int):
    return approved_graph(dataset_id)
