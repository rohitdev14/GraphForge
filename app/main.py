from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import hashlib
import csv
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, LargeBinary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/graphforge")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI app
app = FastAPI(title="GraphForge Backend", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    dataset_id = Column(Integer)
    import_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String)
    message = Column(Text)

# Helper functions
def get_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()

def validate_csv(file_content: bytes) -> list:
    try:
        decoded_content = file_content.decode('utf-8')
        reader = csv.DictReader(decoded_content.splitlines())
        rows = list(reader)
        if not rows:
            raise ValueError("CSV file is empty")
        return rows
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")

def validate_json(file_content: bytes) -> list:
    try:
        data = json.loads(file_content.decode('utf-8'))
        if not isinstance(data, (list, dict)):
            raise ValueError("JSON must be an object or array")
        if isinstance(data, dict):
            return [data]
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")

def parse_csv_content(content: bytes) -> list:
    rows = validate_csv(content)
    return rows

def parse_json_content(content: bytes) -> list:
    data = validate_json(content)
    return data

# API endpoints
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Check file type
    if not file.content_type or (file.content_type != "text/csv" and not file.content_type.startswith("application/json")):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV and JSON files are allowed.")
    
    # Read file content
    content = await file.read()
    
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        db.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Register graph models and routes before creating database tables
import graph
app.include_router(graph.router)

# Create tables
Base.metadata.create_all(bind=engine)
