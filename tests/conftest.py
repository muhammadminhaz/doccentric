import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from main import app

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    return TestClient(app)


@pytest.fixture(scope="function")
def sample_patient_data():
    return {
        "name": "Test Patient",
        "age": 45,
        "gender": "male",
        "phone": "+8801712345678",
        "email": "test@example.com",
        "address": "123 Test Street, Dhaka",
        "blood_type": "O+",
        "allergies": "None",
        "emergency_contact": "+8801812345678"
    }


@pytest.fixture(scope="function")
def sample_visit_data():
    return {
        "doctor_id": "DR001",
        "chief_complaint": "Headache and fever",
        "symptoms": "High fever for 3 days",
        "diagnosis": "Common cold",
        "tests": "Blood test",
        "prescription": "Paracetamol 500mg",
        "suggestions": "Rest and hydrate",
        "notes": "Follow up in 5 days",
        "visit_type": "initial"
    }
