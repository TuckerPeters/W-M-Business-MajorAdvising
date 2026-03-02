"""
Integration test fixtures and configuration

These tests hit the real W&M FOSE API and optionally Firebase.
They are slower and require network access.

Run integration tests with: pytest tests/integration -m integration
Skip integration tests with: pytest -m "not integration"
"""

import pytest
import os
from pathlib import Path

# Add backend to path for imports
import sys
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may be slow, requires network)"
    )
    config.addinivalue_line(
        "markers", "firebase: marks tests that require Firebase connection"
    )


@pytest.fixture
def real_term_code():
    """Get current real term code for testing"""
    from core.semester import SemesterManager
    return SemesterManager.get_trackable_term_code()


@pytest.fixture
def firebase_available():
    """Check if Firebase credentials are available"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        return False

    # Check for service account key
    from dotenv import load_dotenv
    load_dotenv(env_path)

    key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if not key_path:
        return False

    full_path = Path(__file__).parent.parent.parent / key_path
    return full_path.exists()
