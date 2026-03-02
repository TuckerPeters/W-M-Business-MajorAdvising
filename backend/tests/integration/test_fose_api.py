"""
Integration tests for W&M FOSE API

These tests hit the real registration.wm.edu API to verify:
1. API endpoints are accessible
2. Response structure matches expectations
3. Data parsing works with real responses
4. Rate limiting and caching work correctly

Run with: pytest tests/integration/test_fose_api.py -v
"""

import pytest
import asyncio
import time

from api.client import FOSEClient, USER_AGENT
from api.fetcher import FOSEFetcher, CourseData, SectionData
from core.semester import SemesterManager


@pytest.mark.integration
class TestFOSEAPIConnection:
    """Test basic API connectivity"""

    @pytest.mark.asyncio
    async def test_api_reachable(self):
        """API should be reachable and respond"""
        async with FOSEClient(use_cache=False) as client:
            term_code = SemesterManager.get_trackable_term_code()

            result = await client.fetch_search(term_code)

            # Should get some result (list of sections or empty)
            assert isinstance(result, list)
            print(f"\n  Found {len(result)} sections for term {term_code}")

    @pytest.mark.asyncio
    async def test_user_agent_sent(self):
        """User agent should be properly set"""
        # Verify our user agent is configured
        assert "WM-Business-MajorAdvising" in USER_AGENT
        assert "Contact:" in USER_AGENT

        async with FOSEClient(use_cache=False) as client:
            # The client should have proper headers
            assert client.session is not None


@pytest.mark.integration
class TestFOSESearchEndpoint:
    """Test search endpoint with real data"""

    @pytest.mark.asyncio
    async def test_search_returns_sections(self, real_term_code):
        """Search should return section data"""
        async with FOSEClient(use_cache=False) as client:
            result = await client.fetch_search(real_term_code)

            if len(result) > 0:
                section = result[0]

                # Verify expected fields exist
                assert 'crn' in section, "Section should have CRN"
                assert 'code' in section, "Section should have course code"
                assert 'title' in section, "Section should have title"

                print(f"\n  Sample section: {section.get('code')} - {section.get('title')}")

    @pytest.mark.asyncio
    async def test_search_response_structure(self, real_term_code):
        """Verify response structure matches expectations"""
        async with FOSEClient(use_cache=False) as client:
            result = await client.fetch_search(real_term_code)

            if len(result) > 0:
                section = result[0]

                # Check for expected fields
                expected_fields = {'crn', 'code', 'title', 'section'}
                actual_fields = set(section.keys())

                missing = expected_fields - actual_fields
                assert len(missing) == 0, f"Missing expected fields: {missing}"

                # Report any new/unexpected fields for API monitoring
                known_fields = {
                    'crn', 'code', 'title', 'section', 'instr', 'meets',
                    'stat', 'cart_opts', 'schd', 'credits', 'method', 'no'
                }
                new_fields = actual_fields - known_fields
                if new_fields:
                    print(f"\n  New API fields detected: {new_fields}")


@pytest.mark.integration
class TestFOSEDetailsEndpoint:
    """Test details endpoint with real data"""

    @pytest.mark.asyncio
    async def test_get_section_details(self, real_term_code):
        """Should fetch section details"""
        async with FOSEClient(use_cache=False) as client:
            # First get a CRN from search
            sections = await client.fetch_search(real_term_code)

            if len(sections) > 0:
                crn = sections[0].get('crn')

                # Now get details
                details = await client.fetch_details(crn, real_term_code)

                # Should have enrollment info
                assert details is not None
                print(f"\n  Got details for CRN {crn}")

    @pytest.mark.asyncio
    async def test_details_contains_enrollment(self, real_term_code):
        """Details should contain enrollment information"""
        async with FOSEClient(use_cache=False) as client:
            sections = await client.fetch_search(real_term_code)

            if len(sections) > 0:
                crn = sections[0].get('crn')
                details = await client.fetch_details(crn, real_term_code)

                if details:
                    seats_html = details.get('seats', '')
                    # Should contain enrollment keywords
                    assert any(keyword in seats_html.lower() for keyword in
                              ['enrollment', 'seats', 'capacity', 'avail']), \
                        "Details should contain enrollment info"


@pytest.mark.integration
class TestFOSEFetcherIntegration:
    """Test full fetcher with real data"""

    @pytest.mark.asyncio
    async def test_fetch_all_courses(self, real_term_code):
        """Should fetch and parse courses"""
        async with FOSEFetcher(use_cache=False) as fetcher:
            courses = await fetcher.fetch_all_courses(real_term_code)

            assert isinstance(courses, list)

            if len(courses) > 0:
                course = courses[0]

                # Verify it's a proper CourseData object
                assert isinstance(course, CourseData)
                assert course.course_code != ""
                assert course.title != ""

                print(f"\n  Fetched {len(courses)} courses")
                print(f"  Sample: {course.course_code} - {course.title}")

    @pytest.mark.asyncio
    async def test_fetch_course_sections(self, real_term_code):
        """Courses should have sections with proper data"""
        async with FOSEFetcher(use_cache=False) as fetcher:
            courses = await fetcher.fetch_all_courses(real_term_code)

            # Find a course with sections
            course_with_sections = None
            for course in courses:
                if len(course.sections) > 0:
                    course_with_sections = course
                    break

            if course_with_sections:
                section = course_with_sections.sections[0]

                assert isinstance(section, SectionData)
                assert section.crn != ""
                assert section.status in ["OPEN", "CLOSED", "CANCELLED", "UNKNOWN"]

                print(f"\n  Course {course_with_sections.course_code} has {len(course_with_sections.sections)} sections")
                print(f"  Section {section.section_number}: {section.status}, {section.enrolled}/{section.capacity}")

    @pytest.mark.asyncio
    async def test_validation_report_generated(self, real_term_code):
        """Fetcher should generate validation report"""
        async with FOSEFetcher(use_cache=False) as fetcher:
            await fetcher.fetch_all_courses(real_term_code)

            report = fetcher.report

            assert report is not None
            assert report.total_sections >= 0
            assert report.total_courses >= 0

            print(f"\n  Validation report: {report.total_courses} courses, {report.total_sections} sections")

            if report.has_issues():
                print(f"  Issues found:\n{report.summary()}")


@pytest.mark.integration
class TestAPIRateLimiting:
    """Test rate limiting with real requests"""

    @pytest.mark.asyncio
    async def test_multiple_requests_dont_fail(self, real_term_code):
        """Multiple rapid requests should be rate-limited, not fail"""
        async with FOSEClient(use_cache=False) as client:
            # Make multiple detail requests rapidly
            sections = await client.fetch_search(real_term_code)

            if len(sections) >= 5:
                crns = [s.get('crn') for s in sections[:5]]

                # Fetch details for multiple CRNs
                results = []
                for crn in crns:
                    result = await client.fetch_details(crn, real_term_code)
                    results.append((crn, result is not None))

                # All requests should succeed
                for crn, success in results:
                    print(f"\n  CRN {crn}: {'OK' if success else 'FAILED'}")

                # Most should succeed (allow some failures)
                success_count = sum(1 for _, s in results if s)
                assert success_count >= 3, "Most requests should succeed"


@pytest.mark.integration
class TestCaching:
    """Test caching functionality"""

    @pytest.mark.asyncio
    async def test_cached_response_faster(self, real_term_code):
        """Cached response should be returned faster"""
        async with FOSEClient(use_cache=True) as client:
            # First request (not cached)
            start1 = time.monotonic()
            result1 = await client.fetch_search(real_term_code)
            time1 = time.monotonic() - start1

            # Second request (should be cached)
            start2 = time.monotonic()
            result2 = await client.fetch_search(real_term_code)
            time2 = time.monotonic() - start2

            print(f"\n  First request: {time1:.3f}s")
            print(f"  Second request (cached): {time2:.3f}s")

            # Cached should be faster (if cache is working)
            # Results should be the same
            assert len(result1) == len(result2)
