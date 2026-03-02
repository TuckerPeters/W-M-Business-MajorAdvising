"""
Tests for api/client.py - Rate limiting, caching, validation
"""

import pytest
import asyncio
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from api.client import (
    RateLimiter,
    ResponseCache,
    ValidationReport,
    FOSEClient,
    USER_AGENT,
)


class TestRateLimiter:
    """Tests for RateLimiter class"""

    @pytest.mark.asyncio
    async def test_initial_burst(self):
        """Should allow burst of requests initially"""
        limiter = RateLimiter(rate=10, burst=5)

        # Should be able to acquire 5 tokens immediately
        start = time.monotonic()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should complete almost instantly (< 0.1s)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Should throttle after burst exhausted"""
        limiter = RateLimiter(rate=10, burst=2)

        # Exhaust burst
        await limiter.acquire()
        await limiter.acquire()

        # Third request should be delayed
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should take ~0.1s (1/10 rate)
        assert elapsed >= 0.05  # Allow some tolerance


class TestResponseCache:
    """Tests for ResponseCache class"""

    def setup_method(self):
        """Set up test cache directory"""
        self.test_cache_dir = Path(__file__).parent / ".test_cache"
        self.cache = ResponseCache(cache_dir=self.test_cache_dir)

    def teardown_method(self):
        """Clean up test cache"""
        self.cache.clear()
        if self.test_cache_dir.exists():
            import shutil
            shutil.rmtree(self.test_cache_dir)

    def test_cache_miss(self):
        """Should return None for uncached data"""
        result = self.cache.get("endpoint", {"key": "value"}, ttl=60)
        assert result is None

    def test_cache_hit(self):
        """Should return cached data"""
        endpoint = "test_endpoint"
        payload = {"key": "value"}
        data = {"result": "test_data"}

        self.cache.set(endpoint, payload, data, ttl=60)
        result = self.cache.get(endpoint, payload, ttl=60)

        assert result == data

    def test_cache_expiry(self):
        """Should return None for expired cache"""
        endpoint = "test_endpoint"
        payload = {"key": "value"}
        data = {"result": "test_data"}

        # Set with very short TTL
        self.cache.set(endpoint, payload, data, ttl=0)

        # Wait for expiry
        time.sleep(0.1)

        result = self.cache.get(endpoint, payload, ttl=0)
        assert result is None

    def test_cache_clear(self):
        """Should clear all cached data"""
        self.cache.set("endpoint1", {}, {"data": 1}, ttl=60)
        self.cache.set("endpoint2", {}, {"data": 2}, ttl=60)

        self.cache.clear()

        assert self.cache.get("endpoint1", {}, ttl=60) is None
        assert self.cache.get("endpoint2", {}, ttl=60) is None


class TestValidationReport:
    """Tests for ValidationReport class"""

    def test_initial_state(self):
        """Should start with no issues"""
        report = ValidationReport()
        assert report.has_issues() is False
        assert report.total_sections == 0
        assert report.total_courses == 0

    def test_add_missing_field(self):
        """Should track missing fields"""
        report = ValidationReport()
        report.add_missing_field("crn")
        report.add_missing_field("crn")
        report.add_missing_field("title")

        assert report.has_issues() is True
        assert report.missing_fields["crn"] == 2
        assert report.missing_fields["title"] == 1

    def test_add_invalid_value(self):
        """Should track invalid values"""
        report = ValidationReport()
        report.add_invalid_value("crn", "abc", "not numeric")

        assert report.has_issues() is True
        assert "abc (not numeric)" in report.invalid_values["crn"]

    def test_add_api_error(self):
        """Should track API errors"""
        report = ValidationReport()
        report.add_api_error("/search", 500, "Internal error")

        assert report.has_issues() is True
        assert len(report.api_errors) == 1
        assert report.api_errors[0]["status"] == 500

    def test_check_response_shape_unexpected(self):
        """Should detect unexpected fields"""
        report = ValidationReport()
        report.check_response_shape("search", {"crn", "code", "new_field"})

        assert "new_field" in report.unexpected_fields.get("search", set())

    def test_check_response_shape_missing(self):
        """Should detect missing expected fields"""
        report = ValidationReport()
        report.check_response_shape("search", {"crn"})  # Missing code, title, etc.

        assert len(report.missing_expected_fields.get("search", set())) > 0

    def test_summary_no_issues(self):
        """Summary should indicate no issues"""
        report = ValidationReport()
        summary = report.summary()
        assert "No issues detected" in summary

    def test_summary_with_issues(self):
        """Summary should list issues"""
        report = ValidationReport()
        report.add_missing_field("crn")
        report.add_api_error("/test", 500, "error")

        summary = report.summary()
        assert "Missing Fields" in summary
        assert "API Errors" in summary

    def test_to_dict(self):
        """Should convert to dictionary"""
        report = ValidationReport()
        report.term_code = "202610"
        report.total_sections = 100

        result = report.to_dict()
        assert result["term_code"] == "202610"
        assert result["total_sections"] == 100
        assert "has_issues" in result


class TestFOSEClient:
    """Tests for FOSEClient class"""

    def test_user_agent_set(self):
        """User agent should be properly configured"""
        assert "WM-Business-MajorAdvising" in USER_AGENT
        assert "Contact:" in USER_AGENT

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Should properly initialize and cleanup"""
        async with FOSEClient(use_cache=False) as client:
            assert client.session is not None
            assert client.report is not None

    def test_validate_section_valid(self):
        """Should validate correct section"""
        client = FOSEClient.__new__(FOSEClient)
        client.report = ValidationReport()

        section = {
            'crn': '12345',
            'code': 'CSCI 141',
            'title': 'Test Course'
        }

        assert client.validate_section(section) is True

    def test_validate_section_missing_crn(self):
        """Should reject section without CRN"""
        client = FOSEClient.__new__(FOSEClient)
        client.report = ValidationReport()

        section = {
            'code': 'CSCI 141',
            'title': 'Test Course'
        }

        assert client.validate_section(section) is False
        assert client.report.missing_fields.get('crn', 0) > 0

    def test_validate_section_invalid_crn(self):
        """Should flag non-numeric CRN"""
        client = FOSEClient.__new__(FOSEClient)
        client.report = ValidationReport()

        section = {
            'crn': 'ABC',
            'code': 'CSCI 141',
            'title': 'Test Course'
        }

        client.validate_section(section)
        assert 'crn' in client.report.invalid_values

    def test_validate_course_code_valid(self):
        """Should accept valid course codes"""
        client = FOSEClient.__new__(FOSEClient)
        client.report = ValidationReport()

        assert client.validate_course_code("CSCI 141") is True
        assert client.validate_course_code("MATH 211") is True
        assert client.validate_course_code("BUS 301W") is True

    def test_validate_course_code_invalid(self):
        """Should reject invalid course codes"""
        client = FOSEClient.__new__(FOSEClient)
        client.report = ValidationReport()

        assert client.validate_course_code("CS141") is False
        assert client.validate_course_code("123 ABC") is False
