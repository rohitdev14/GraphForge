from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import hashlib
import csv
import json
import io
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, LargeBinary, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# Database setup
DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI app
app = FastAPI(title="GraphForge Backend", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database models
class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    file_hash = Column(String, unique=True, index=True)
    file_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    original_data = Column(LargeBinary)
    source_records = relationship("SourceRecord", back_populates="dataset")

class SourceRecord(Base):
    __tablename__ = "source_records"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    record_data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    order = Column(Integer)
    dataset = relationship("Dataset", back_populates="source_records")

class ImportMetadata(Base):
    __tablename__ = "import_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    import_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String)
    message = Column(Text)

# Local development limits; enforce before parsing or persisting untrusted uploads.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_RECORDS = 10000

# Helper functions
def get_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()

def validate_csv(file_content: bytes) -> list[dict]:
    try:
        text = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""), restkey="__extra__")
        headers = reader.fieldnames
        if not headers or any(not h or not h.strip() for h in headers):
            raise ValueError("CSV must contain named columns")
        if len(headers) != len(set(headers)) or "__extra__" in headers:
            raise ValueError("CSV contains duplicate or reserved columns")
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) > MAX_RECORDS:
                raise ValueError("CSV exceeds maximum record count")
        if not rows or any("__extra__" in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("CSV must contain complete records")
        return rows
    except (UnicodeError, csv.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {exc}") from exc

def validate_json(file_content: bytes) -> list[dict]:
    try:
        data = json.loads(file_content.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON format") from exc
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data or any(not isinstance(row, dict) for row in data):
        raise HTTPException(status_code=400, detail="JSON must contain one object or a nonempty array of objects")
    if len(data) > MAX_RECORDS:
        raise HTTPException(status_code=413, detail="JSON exceeds maximum record count")
    return data

def parse_csv_content(content: bytes) -> list[dict]:
    return validate_csv(content)

def parse_json_content(content: bytes) -> list[dict]:
    return validate_json(content)

# API endpoints
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Check file type
    if not file.content_type or (file.content_type != "text/csv" and not file.content_type.startswith("application/json")):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV and JSON files are allowed.")
    
    # Read file content
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds 5 MiB limit")
    
    # Check for duplicates using SHA-256 hash
    file_hash = get_file_hash(content)
    
    db = SessionLocal()
    try:
        existing_dataset = db.query(Dataset).filter(Dataset.file_hash == file_hash).first()
        
        if existing_dataset:
            raise HTTPException(status_code=409, detail="File already uploaded.")
        
        # Validate file content
        if file.content_type == "text/csv":
            parsed_data = parse_csv_content(content)
        elif file.content_type.startswith("application/json"):
            parsed_data = parse_json_content(content)
        
        # Check if data is empty
        if not parsed_data:
            raise HTTPException(status_code=400, detail="File contains no data.")
        
        # Save dataset
        dataset = Dataset(
            name=file.filename,
            file_hash=file_hash,
            file_type=file.content_type,
            original_data=content
        )
        
        db.add(dataset)
        db.flush()  # Get the ID without committing
        
        # Insert source records
        for i, record in enumerate(parsed_data):
            if isinstance(record, dict):
                record_text = json.dumps(record, separators=(',', ':'))
            else:
                record_text = str(record)
            
            source_record = SourceRecord(
                dataset_id=dataset.id,
                record_data=record_text,
                order=i
            )
            db.add(source_record)
        
        # Create import metadata
        metadata = ImportMetadata(
            dataset_id=dataset.id,
            status="success",
            message="File uploaded successfully"
        )
        
        db.add(metadata)
        db.commit()
        db.refresh(dataset)
        
        return {"message": "File uploaded successfully", "dataset_id": dataset.id}
    
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="Dataset already exists or violates a database constraint") from e
    except Exception as e:
        db.rollback()
        logging.exception("Dataset import failed")
        raise HTTPException(status_code=500, detail="Dataset import failed") from e
    finally:
        db.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Register graph models and routes before creating database tables
import graph
app.include_router(graph.router)
import ai
app.include_router(ai.router)

# Create tables
Base.metadata.create_all(bind=engine)
