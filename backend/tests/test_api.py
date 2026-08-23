"""
Unit tests for the FastAPI API layer.
"""
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.api.main import app

client = TestClient(app)

class TestAPI:
    @patch("backend.api.routes.get_store")
    def test_health_endpoint(self, mock_get_store):
        # Mock the store
        mock_store = MagicMock()
        mock_store.get_count.return_value = 50
        mock_store.get_last_ingestion.return_value = "2026-08-23T10:00:00Z"
        mock_get_store.return_value = mock_store
        
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["vector_store_count"] == 50
        assert data["last_ingestion"] == "2026-08-23T10:00:00Z"

    @patch("backend.api.routes.get_generator")
    def test_chat_endpoint_success(self, mock_get_generator):
        mock_generator = MagicMock()
        mock_generator.generate_response.return_value = {
            "answer": "The expense ratio is 0.75%.",
            "source": "https://groww.in/mock",
            "last_updated": "2026-08-23",
            "refused": False
        }
        mock_get_generator.return_value = mock_generator

        response = client.post(
            "/api/chat",
            json={"message": "What is the expense ratio?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "The expense ratio is 0.75%."
        assert data["source"] == "https://groww.in/mock"
        assert data["last_updated"] == "2026-08-23"
        assert data["refused"] is False

    @patch("backend.api.routes.get_generator")
    def test_chat_endpoint_refusal(self, mock_get_generator):
        mock_generator = MagicMock()
        mock_generator.generate_response.return_value = {
            "answer": "Refused due to advisory intent.",
            "source": "https://amfiindia.com",
            "last_updated": None,
            "refused": True
        }
        mock_get_generator.return_value = mock_generator

        response = client.post(
            "/api/chat",
            json={"message": "Should I invest?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Refused due to advisory intent."
        assert data["refused"] is True

    def test_chat_endpoint_validation_error(self):
        # Missing message field
        response = client.post(
            "/api/chat",
            json={}
        )
        assert response.status_code == 422
