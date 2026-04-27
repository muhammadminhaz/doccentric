"""
API endpoint tests for DocCentric
"""
import pytest
from fastapi.testclient import TestClient


class TestPatientEndpoints:
    """Test patient CRUD endpoints"""

    def test_create_patient(self, client, sample_patient_data):
        response = client.post("/api/patients", json=sample_patient_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_patient_data["name"]
        assert data["age"] == sample_patient_data["age"]
        assert data["phone"] == sample_patient_data["phone"]
        assert "id" in data

    def test_list_patients(self, client, sample_patient_data):
        # Create a patient first
        client.post("/api/patients", json=sample_patient_data)

        response = client.get("/api/patients")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_patient(self, client, sample_patient_data):
        # Create a patient
        create_response = client.post("/api/patients", json=sample_patient_data)
        patient_id = create_response.json()["id"]

        response = client.get(f"/api/patients/{patient_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == patient_id
        assert data["name"] == sample_patient_data["name"]

    def test_get_patient_not_found(self, client):
        response = client.get("/api/patients/99999")
        assert response.status_code == 404

    def test_update_patient(self, client, sample_patient_data):
        # Create a patient
        create_response = client.post("/api/patients", json=sample_patient_data)
        patient_id = create_response.json()["id"]

        update_data = {"name": "Updated Name", "age": 50}
        response = client.put(f"/api/patients/{patient_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["age"] == 50

    def test_delete_patient(self, client, sample_patient_data):
        # Create a patient
        create_response = client.post("/api/patients", json=sample_patient_data)
        patient_id = create_response.json()["id"]

        response = client.delete(f"/api/patients/{patient_id}")
        assert response.status_code == 200

        # Verify deleted
        response = client.get(f"/api/patients/{patient_id}")
        assert response.status_code == 404


class TestVisitEndpoints:
    """Test visit CRUD endpoints"""

    def test_create_visit(self, client, sample_patient_data, sample_visit_data):
        # Create patient first
        patient_response = client.post("/api/patients", json=sample_patient_data)
        patient_id = patient_response.json()["id"]

        visit_data = {**sample_visit_data, "patient_id": patient_id}
        response = client.post("/api/visits", json=visit_data)
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["doctor_id"] == sample_visit_data["doctor_id"]

    def test_create_visit_patient_not_found(self, client, sample_visit_data):
        visit_data = {**sample_visit_data, "patient_id": 99999}
        response = client.post("/api/visits", json=visit_data)
        assert response.status_code == 404

    def test_get_visit(self, client, sample_patient_data, sample_visit_data):
        # Create patient and visit
        patient_response = client.post("/api/patients", json=sample_patient_data)
        patient_id = patient_response.json()["id"]

        visit_data = {**sample_visit_data, "patient_id": patient_id}
        visit_response = client.post("/api/visits", json=visit_data)
        visit_id = visit_response.json()["id"]

        response = client.get(f"/api/visits/{visit_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == visit_id

    def test_get_patient_visits(self, client, sample_patient_data, sample_visit_data):
        # Create patient and visit
        patient_response = client.post("/api/patients", json=sample_patient_data)
        patient_id = patient_response.json()["id"]

        visit_data = {**sample_visit_data, "patient_id": patient_id}
        client.post("/api/visits", json=visit_data)

        response = client.get(f"/api/patients/{patient_id}/visits")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
