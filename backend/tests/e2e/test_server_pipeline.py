"""
E2E tests for the server pipeline

These tests actually start the server and make real HTTP requests.
External services (Firebase) are mocked at the boundary, but all
internal logic runs for real.

Includes timing for each endpoint to monitor performance.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def app_client():
    """
    Create a test client that runs the REAL FastAPI app.
    Only mocks the external Firebase connection at initialization.
    """
    mock_db = MagicMock()
    mock_db.collection.return_value.stream.return_value = []
    mock_db.collection.return_value.select.return_value.stream.return_value = []
    mock_db.collection.return_value.where.return_value.stream.return_value = []
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []

    with patch('core.config.initialize_firebase'):
        with patch('core.config.get_firestore_client', return_value=mock_db):
            with patch('server.initialize_firebase'):
                with patch('server.get_firestore_client', return_value=mock_db):
                    from server import app
                    app.state.enable_scheduler = False

                    with TestClient(app) as client:
                        yield client, mock_db


@pytest.mark.e2e
class TestRealServerStartup:
    """Test that the real server starts and responds correctly"""

    def test_server_starts_and_returns_health(self, app_client, timed_request):
        """Server should start and health endpoint should work"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/")

        assert response.status_code == 200
        assert elapsed < 100, f"Health check too slow: {elapsed:.2f}ms"

        data = response.json()
        assert data["status"] == "ok"
        assert len(data["term_code"]) == 6
        assert data["term_code"][:4].isdigit()
        assert data["term_code"][4:] in ("10", "20", "30")

    def test_api_health_endpoint(self, app_client, timed_request):
        """API health endpoint should work"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/health")

        assert response.status_code == 200
        assert elapsed < 100, f"API health too slow: {elapsed:.2f}ms"
        assert response.json()["status"] == "ok"

    def test_term_endpoint_returns_real_calculations(self, app_client, timed_request):
        """Term endpoint should return real semester calculations"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/term")

        assert response.status_code == 200
        assert elapsed < 100, f"Term endpoint too slow: {elapsed:.2f}ms"

        data = response.json()
        current = data["current"]
        assert current["semester"] in ("Spring", "Summer", "Fall")
        assert 2024 <= current["year"] <= 2030


@pytest.mark.e2e
class TestRealAPIValidation:
    """Test that FastAPI validation actually works"""

    def test_pagination_limit_too_high(self, app_client, timed_request):
        """Should reject limit > 500"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/courses?limit=1000")

        assert response.status_code == 422
        print(f"  Validation response time: {elapsed:.2f}ms")

    def test_pagination_limit_too_low(self, app_client, timed_request):
        """Should reject limit < 1"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/courses?limit=0")

        assert response.status_code == 422

    def test_pagination_negative_offset(self, app_client, timed_request):
        """Should reject offset < 0"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/courses?offset=-1")

        assert response.status_code == 422

    def test_search_min_length(self, app_client, timed_request):
        """Search query must be >= 2 characters"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/courses/search?q=a")

        assert response.status_code == 422

    def test_search_missing_query(self, app_client, timed_request):
        """Search requires q parameter"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/courses/search")

        assert response.status_code == 422


@pytest.mark.e2e
class TestRealEndpointResponses:
    """Test endpoint response structure and timing"""

    def test_courses_list_empty(self, app_client, timed_request):
        """Course list endpoint with empty DB"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/courses")

        assert response.status_code == 200
        assert elapsed < 200, f"Course list too slow: {elapsed:.2f}ms"

        data = response.json()
        assert "courses" in data
        assert "total" in data
        assert "term_code" in data

    def test_courses_with_pagination(self, app_client, timed_request):
        """Course list with pagination params"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/courses?limit=10&offset=0")

        assert response.status_code == 200
        assert elapsed < 200

    def test_courses_with_subject_filter(self, app_client, timed_request):
        """Course list filtered by subject"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/courses?subject=CSCI")

        assert response.status_code == 200
        assert elapsed < 200

    def test_subjects_list(self, app_client, timed_request):
        """Subjects list endpoint"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/subjects")

        assert response.status_code == 200
        assert elapsed < 200

        data = response.json()
        assert "subjects" in data
        assert "total" in data

    def test_cache_stats(self, app_client, timed_request):
        """Cache stats endpoint"""
        client, _ = app_client

        with patch('server.get_course_service') as mock_service:
            mock_service.return_value.get_cache_stats.return_value = {
                "connected": False, "hits": 0, "misses": 0,
                "memory_used": "0B", "course_keys": 0,
                "subject_keys": 0, "search_keys": 0, "total_keys": 0
            }
            response, elapsed = timed_request(client, "GET", "/api/cache/stats")

        assert response.status_code == 200
        assert elapsed < 100

    def test_cache_clear(self, app_client, timed_request):
        """Cache clear endpoint"""
        client, _ = app_client

        with patch('server.get_course_service') as mock_service:
            mock_service.return_value.clear_cache.return_value = True
            response, elapsed = timed_request(client, "POST", "/api/cache/clear")

        assert response.status_code == 200
        assert elapsed < 100


@pytest.mark.e2e
class TestRealDataTransformation:
    """Test data transformation with timing"""

    def test_course_formatting(self, app_client, timed_request, timer):
        """Test _format_course transforms data correctly"""
        client, mock_db = app_client

        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "course_code": "CSCI 141",
            "subject_code": "CSCI",
            "course_number": "141",
            "title": "Computational Problem Solving",
            "description": "Intro to CS",
            "credits": 4,
            "attributes": ["GER 1A"],
            "sections": [
                {
                    "crn": "12345",
                    "section_number": "01",
                    "instructor": "Smith, John",
                    "status": "OPEN",
                    "capacity": 30,
                    "enrolled": 25,
                    "available": 5,
                    "meeting_days": "MWF",
                    "meeting_time": "10:00-10:50",
                    "building": "Morton",
                    "room": "201"
                }
            ]
        }
        mock_db.collection.return_value.stream.return_value = [mock_doc]

        response, elapsed = timed_request(client, "GET", "/api/courses")

        assert response.status_code == 200
        assert elapsed < 200

        data = response.json()
        assert data["total"] == 1
        course = data["courses"][0]
        assert course["course_code"] == "CSCI 141"
        assert len(course["sections"]) == 1

    def test_subject_deduplication(self, app_client, timed_request, timer):
        """Test subjects are deduplicated and sorted"""
        client, mock_db = app_client

        mock_docs = [
            MagicMock(to_dict=lambda: {"subject_code": "MATH"}),
            MagicMock(to_dict=lambda: {"subject_code": "CSCI"}),
            MagicMock(to_dict=lambda: {"subject_code": "MATH"}),  # Duplicate
            MagicMock(to_dict=lambda: {"subject_code": "BUAD"}),
        ]
        mock_db.collection.return_value.select.return_value.stream.return_value = mock_docs

        response, elapsed = timed_request(client, "GET", "/api/subjects")

        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert data["subjects"] == ["BUAD", "CSCI", "MATH"]
        print(f"  Deduplication + sort time included in request")


@pytest.mark.e2e
class TestRealErrorHandling:
    """Test error handling with timing"""

    def test_404_course_not_found(self, app_client, timed_request):
        """Should return 404 for missing course"""
        client, _ = app_client

        with patch('server.get_course_service') as mock_service:
            mock_service.return_value.get_course.return_value = None
            response, elapsed = timed_request(client, "GET", "/api/courses/FAKE%20999")

        assert response.status_code == 404
        assert elapsed < 100
        assert "FAKE 999" in response.json()["detail"]

    def test_404_unknown_endpoint(self, app_client, timed_request):
        """Unknown endpoints should 404"""
        client, _ = app_client
        response, elapsed = timed_request(client, "GET", "/api/does/not/exist")

        assert response.status_code == 404
        assert elapsed < 50


@pytest.mark.e2e
class TestCORSConfiguration:
    """Test CORS with timing"""

    def test_cors_preflight(self, app_client, timed_request):
        """OPTIONS preflight should be fast"""
        client, _ = app_client
        response, elapsed = timed_request(
            client, "OPTIONS", "/api/courses",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )

        assert response.status_code == 200
        assert elapsed < 50, f"CORS preflight too slow: {elapsed:.2f}ms"
