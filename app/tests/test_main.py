import pytest
from fastapi.testclient import TestClient
from main import app, Base, engine, SessionLocal
import os

client = TestClient(app)

# Setup and teardown
@pytest.fixture(scope="session")
def setup_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after tests
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    yield session
    
    transaction.rollback()
    connection.close()

def test_upload_csv(setup_database):
    # Test successful CSV upload
    csv_content = "name,age\nJohn,25\nJane,30"
    response = client.post(
        "/upload",
        files={"file": ("test.csv", csv_content, "text/csv")}
    )
    assert response.status_code == 200
    assert "message" in response.json()

def test_upload_json(setup_database):
    # Test successful JSON upload
    json_content = '{"name": "John", "age": 25}'
    response = client.post(
        "/upload",
        files={"file": ("test.json", json_content, "application/json")}
    )
    assert response.status_code == 200
    assert "message" in response.json()

def test_upload_invalid_file(setup_database):
    # Test invalid file type upload
    txt_content = "This is not a CSV or JSON"
    response = client.post(
        "/upload",
        files={"file": ("test.txt", txt_content, "text/plain")}
    )
    assert response.status_code == 400

def test_upload_duplicate_file(setup_database):
    # Test duplicate file upload
    csv_content = "name,age\nJohn,25\nJane,30"
    
    # First upload
    response1 = client.post(
        "/upload",
        files={"file": ("test.csv", csv_content, "text/csv")}
    )
    assert response1.status_code == 200
    
    # Second upload of same file
    response2 = client.post(
        "/upload",
        files={"file": ("test.csv", csv_content, "text/csv")}
    )
    assert response2.status_code == 409

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
