"""
E2E test fixtures and configuration

These tests verify the full application pipeline:
- Server startup and API endpoints
- Data fetching from FOSE API
- Storage in Firebase/Firestore
- Redis caching layer
- Curriculum PDF scraping

Run e2e tests with: pytest tests/e2e -m e2e
"""

import pytest
import sys
import time
from pathlib import Path
from contextlib import contextmanager

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests (full pipeline)"
    )


class Timer:
    """Simple timer for measuring execution time"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed_ms = None

    def start(self):
        self.start_time = time.perf_counter()
        return self

    def stop(self):
        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000
        return self.elapsed_ms

    @contextmanager
    def measure(self, label: str = ""):
        """Context manager for timing a block of code"""
        self.start()
        yield self
        elapsed = self.stop()
        if label:
            print(f"\n  [{label}] {elapsed:.2f}ms")


@pytest.fixture
def timer():
    """Provide a timer instance for tests"""
    return Timer()


@pytest.fixture
def timed_request(timer):
    """Factory for making timed HTTP requests"""
    def _timed_request(client, method: str, url: str, **kwargs):
        timer.start()
        if method.upper() == "GET":
            response = client.get(url, **kwargs)
        elif method.upper() == "POST":
            response = client.post(url, **kwargs)
        elif method.upper() == "OPTIONS":
            response = client.options(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")
        elapsed = timer.stop()
        print(f"\n  [{method.upper()} {url}] {elapsed:.2f}ms - Status: {response.status_code}")
        return response, elapsed
    return _timed_request


@pytest.fixture
def backend_root():
    """Return the backend root directory"""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def project_root():
    """Return the project root directory"""
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
def sample_course_data():
    """Sample course data for pipeline tests"""
    return {
        "course_code": "CSCI 141",
        "subject_code": "CSCI",
        "course_number": "141",
        "title": "Computational Problem Solving",
        "description": "Introduction to computational problem solving",
        "credits": 4,
        "attributes": ["GER 1A", "COLL 150"],
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
            },
            {
                "crn": "12346",
                "section_number": "02",
                "instructor": "Jones, Jane",
                "status": "OPEN",
                "capacity": 30,
                "enrolled": 28,
                "available": 2,
                "meeting_days": "TR",
                "meeting_time": "11:00-12:20",
                "building": "Morton",
                "room": "202"
            }
        ]
    }


@pytest.fixture
def sample_fose_response():
    """Sample FOSE API response for testing"""
    return {
        "results": [
            {
                "crn": "12345",
                "code": "CSCI 141",
                "title": "Computational Problem Solving",
                "section": "01",
                "instr": "Smith, John",
                "meets": "MWF 10:00-10:50am",
                "stat": "A",
                "cart_opts": '{"credit_hrs":{"options":[{"value":"4"}]}}'
            }
        ]
    }
