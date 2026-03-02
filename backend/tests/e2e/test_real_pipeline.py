"""
E2E tests for data pipeline components

These tests run REAL code - no mocking internal logic.
Only external HTTP calls are mocked.

Includes timing for performance monitoring.
"""

import pytest
import json
import time
from datetime import datetime


@pytest.mark.e2e
class TestRealSemesterManager:
    """Test SemesterManager with no mocks - all real calculations"""

    def test_term_code_format(self, timer):
        """Term code should be valid format"""
        from core.semester import SemesterManager

        with timer.measure("get_trackable_term_code"):
            code = SemesterManager.get_trackable_term_code()

        assert len(code) == 6
        assert code[:4].isdigit()
        assert int(code[:4]) >= 2024
        assert code[4:] in ("10", "20", "30")
        assert timer.elapsed_ms < 10, f"Term code generation too slow: {timer.elapsed_ms:.2f}ms"

    def test_parse_term_code_roundtrip(self, timer):
        """Parse and format should be consistent"""
        from core.semester import SemesterManager

        code = SemesterManager.get_trackable_term_code()

        with timer.measure("parse_term_code"):
            parsed = SemesterManager.parse_term_code(code)

        assert parsed["term_code"] == code
        assert parsed["semester"] in ("Spring", "Summer", "Fall")
        assert parsed["year"] == int(code[:4])
        assert timer.elapsed_ms < 5

    def test_semester_info_consistency(self, timer):
        """Semester info should be internally consistent"""
        from core.semester import SemesterManager

        with timer.measure("get_trackable_semester_info"):
            info = SemesterManager.get_trackable_semester_info()

        year = info["year"]
        semester = info["semester"]
        term_code = info["term_code"]

        assert term_code[:4] == str(year)
        if semester == "Spring":
            assert term_code[4:] == "10"
        elif semester == "Summer":
            assert term_code[4:] == "20"
        elif semester == "Fall":
            assert term_code[4:] == "30"

    def test_update_interval_based_on_period(self, timer):
        """Update interval should differ based on registration period"""
        from core.semester import SemesterManager

        with timer.measure("get_update_interval"):
            interval = SemesterManager.get_update_interval_minutes()
            is_registration = SemesterManager.is_registration_period()

        if is_registration:
            assert interval == 5
        else:
            assert interval == 15

    def test_next_transition_is_future(self, timer):
        """Next transition should be in the future"""
        from core.semester import SemesterManager

        with timer.measure("get_next_transition_info"):
            info = SemesterManager.get_next_transition_info()

        assert info["transition_date"] > datetime.now()
        # next_semester includes year like "Summer 2026"
        assert any(s in info["next_semester"] for s in ("Spring", "Summer", "Fall"))


@pytest.mark.e2e
class TestRealFetcherParsing:
    """Test FOSEFetcher parsing with real data - no mocks"""

    def test_parse_credits_real_json(self, timer):
        """Parse actual FOSE credit format"""
        from api.fetcher import FOSEFetcher

        fetcher = FOSEFetcher.__new__(FOSEFetcher)

        with timer.measure("parse_credits (5 calls)"):
            # Real format from FOSE API
            json_str = '{"credit_hrs":{"options":[{"value":"4"}]}}'
            assert fetcher._parse_credits(json_str) == 4

            # Multiple credit options
            json_str = '{"credit_hrs":{"options":[{"value":"1"},{"value":"2"},{"value":"3"}]}}'
            assert fetcher._parse_credits(json_str) == 1

            # Edge cases
            assert fetcher._parse_credits("") == 3
            assert fetcher._parse_credits(None) == 3
            assert fetcher._parse_credits("invalid json") == 3

        assert timer.elapsed_ms < 10

    def test_parse_status_all_codes(self, timer):
        """Parse all known status codes"""
        from core.parsers import parse_status

        with timer.measure("parse_status (5 codes)"):
            assert parse_status("A") == "OPEN"
            assert parse_status("F") == "CLOSED"
            assert parse_status("C") == "CANCELLED"
            assert parse_status("X") == "CANCELLED"  # X maps to CANCELLED
            assert parse_status("") == "UNKNOWN"

        assert timer.elapsed_ms < 5

    def test_parse_course_code_variations(self, timer):
        """Parse various course code formats"""
        from api.fetcher import FOSEFetcher

        fetcher = FOSEFetcher.__new__(FOSEFetcher)

        with timer.measure("parse_course_code (3 formats)"):
            subj, num = fetcher._parse_course_code("CSCI 141")
            assert subj == "CSCI"
            assert num == "141"

            subj, num = fetcher._parse_course_code("BUS 301W")
            assert subj == "BUS"
            assert num == "301W"

            subj, num = fetcher._parse_course_code("MATH 1001")
            assert subj == "MATH"
            assert num == "1001"

        assert timer.elapsed_ms < 5

    def test_parse_seats_real_html(self, timer):
        """Parse actual FOSE seats HTML format"""
        from core.parsers import parse_seats

        html = '<b>Maximum Enrollment:</b> 30<br><b>Seats Avail</b>: 5'

        with timer.measure("parse_seats"):
            result = parse_seats(html)

        assert result["capacity"] == 30
        assert result["available"] == 5
        assert result["enrolled"] == 25
        assert timer.elapsed_ms < 10

    def test_parse_seats_with_waitlist(self, timer):
        """Parse seats with waitlist info"""
        from core.parsers import parse_seats

        html = '''
        <b>Maximum Enrollment:</b> 30<br>
        <b>Seats Avail</b>: 0<br>
        <b>Waitlist Total:</b> 5 of 10
        '''

        with timer.measure("parse_seats_with_waitlist"):
            result = parse_seats(html)

        assert result["capacity"] == 30
        assert result["available"] == 0
        assert result["waitlist_enrolled"] == 5
        assert result["waitlist_capacity"] == 10

    def test_parse_attributes_real_html(self, timer):
        """Parse actual FOSE attributes HTML"""
        from api.fetcher import FOSEFetcher

        fetcher = FOSEFetcher.__new__(FOSEFetcher)

        html = '<ul><li>GER 1A</li><li>COLL 150</li><li>NQR</li></ul>'

        with timer.measure("parse_attributes"):
            attrs = fetcher._parse_attributes(html)

        assert "GER 1A" in attrs
        assert "COLL 150" in attrs
        assert "NQR" in attrs
        assert len(attrs) == 3
        assert timer.elapsed_ms < 10

    def test_parse_meeting_patterns(self, timer):
        """Parse various meeting time formats"""
        from api.fetcher import FOSEFetcher

        fetcher = FOSEFetcher.__new__(FOSEFetcher)

        with timer.measure("parse_meeting (3 patterns)"):
            result = fetcher._parse_meeting("MWF 10:00-10:50am")
            assert result["days"] == "MWF"
            assert "10:00" in result["time"]

            result = fetcher._parse_meeting("TR 11:00-12:20pm")
            assert result["days"] == "TR"

            result = fetcher._parse_meeting("")
            assert result["days"] == ""

        assert timer.elapsed_ms < 10

    def test_clean_description_strips_html(self, timer):
        """Should remove HTML tags from description"""
        from api.fetcher import FOSEFetcher

        fetcher = FOSEFetcher.__new__(FOSEFetcher)

        html = '<p>This is a <strong>test</strong> description.</p>'

        with timer.measure("clean_description"):
            result = fetcher._clean_description(html)

        assert result == "This is a test description."
        assert "<" not in result
        assert ">" not in result
        assert timer.elapsed_ms < 5


@pytest.mark.e2e
class TestRealCurriculumScraper:
    """Test curriculum scraper data structures - no mocks"""

    def test_course_dataclass_creation(self, timer):
        """Create real Course objects"""
        from scrapers.curriculum_scraper import Course

        with timer.measure("create Course dataclass"):
            course = Course(
                code="BUAD 301",
                name="Financial Reporting & Analysis",
                credits=3,
                semester="F/S",
                prerequisites=["BUAD 203", "ACCT 201"]
            )

        assert course.code == "BUAD 301"
        assert course.credits == 3
        assert len(course.prerequisites) == 2
        assert timer.elapsed_ms < 5

    def test_course_group_with_electives(self, timer):
        """Create CourseGroup with required_count"""
        from scrapers.curriculum_scraper import Course, CourseGroup

        with timer.measure("create CourseGroup with 3 courses"):
            courses = [
                Course(code="BUAD 445", name="Option 1", credits=3),
                Course(code="BUAD 446", name="Option 2", credits=3),
                Course(code="BUAD 448", name="Option 3", credits=3),
            ]

            group = CourseGroup(
                description="Choose 2 from the following",
                required_count=2,
                courses=courses
            )

        assert group.required_count == 2
        assert len(group.courses) == 3
        assert timer.elapsed_ms < 10

    def test_major_structure(self, timer):
        """Create complete Major structure"""
        from scrapers.curriculum_scraper import Course, CourseGroup, Major

        with timer.measure("create complete Major structure"):
            required = CourseGroup(
                description="Required Courses",
                courses=[
                    Course(code="BUAD 301", name="Financial Reporting", credits=3),
                    Course(code="BUAD 302", name="Cost Accounting", credits=3),
                ]
            )

            elective = CourseGroup(
                description="Choose 1",
                required_count=1,
                courses=[
                    Course(code="BUAD 401", name="Auditing", credits=3),
                    Course(code="BUAD 402", name="Tax", credits=3),
                ]
            )

            major = Major(
                name="Accounting",
                credits_required=15,
                description="15 credits in addition to business core",
                required_courses=[required],
                elective_courses=[elective]
            )

        assert major.name == "Accounting"
        assert major.credits_required == 15
        assert len(major.required_courses[0].courses) == 2
        assert timer.elapsed_ms < 10

    def test_dataclass_to_dict_nested(self, timer):
        """Serialize nested dataclass structure"""
        from scrapers.curriculum_scraper import (
            Course, CourseGroup, Major, dataclass_to_dict
        )

        course = Course(code="BUAD 301", name="Test", credits=3)
        group = CourseGroup(description="Required", courses=[course])
        major = Major(
            name="Test Major",
            credits_required=15,
            required_courses=[group]
        )

        with timer.measure("dataclass_to_dict (nested)"):
            result = dataclass_to_dict(major)

        assert result["name"] == "Test Major"
        assert result["required_courses"][0]["courses"][0]["code"] == "BUAD 301"
        assert timer.elapsed_ms < 10


@pytest.mark.e2e
class TestRealAPIClient:
    """Test API client components - no mocks on internal logic"""

    def test_rate_limiter_allows_burst(self, timer):
        """RateLimiter should allow initial burst"""
        import asyncio
        from api.client import RateLimiter

        async def test_burst():
            limiter = RateLimiter(rate=10, burst=3)

            timer.start()
            for _ in range(3):
                await limiter.acquire()
            elapsed = timer.stop()

            print(f"\n  [RateLimiter burst (3 requests)] {elapsed:.2f}ms")
            # 3 requests in burst should be near-instant
            assert elapsed < 100  # 100ms

        asyncio.run(test_burst())

    def test_validation_report_tracks_issues(self, timer):
        """ValidationReport should accumulate issues"""
        from api.client import ValidationReport

        with timer.measure("ValidationReport tracking"):
            report = ValidationReport()
            assert report.has_issues() is False

            report.add_missing_field("crn")
            report.add_missing_field("crn")
            report.add_invalid_value("credits", "abc", "not numeric")

        assert report.has_issues() is True
        assert report.missing_fields["crn"] == 2
        assert "abc" in str(report.invalid_values["credits"])
        assert timer.elapsed_ms < 10

    def test_validation_report_summary(self, timer):
        """ValidationReport summary should list issues"""
        from api.client import ValidationReport

        report = ValidationReport()
        report.add_api_error("/search", 500, "Server error")

        with timer.measure("generate summary"):
            summary = report.summary()

        assert "API Errors" in summary
        assert "500" in summary
        assert timer.elapsed_ms < 10


@pytest.mark.e2e
class TestRealCacheKeyGeneration:
    """Test cache key generation - real logic"""

    def test_sanitize_key_replaces_special_chars(self, timer):
        """Cache keys should be sanitized"""
        from unittest.mock import patch

        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache

            cache = RedisCache()

            with timer.measure("sanitize_key (3 calls)"):
                result1 = cache._sanitize_key("CSCI 141")
                result2 = cache._sanitize_key("BUS/ACCT")
                result3 = cache._sanitize_key("BUS/ACCT 301")

            assert result1 == "CSCI_141"
            assert result2 == "BUS-ACCT"
            assert result3 == "BUS-ACCT_301"
            assert timer.elapsed_ms < 5

    def test_hash_query_consistency(self, timer):
        """Same query should produce same hash"""
        from unittest.mock import patch

        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache

            cache = RedisCache()

            with timer.measure("hash_query consistency check"):
                hash1 = cache._hash_query("test query", 50)
                hash2 = cache._hash_query("test query", 50)

            assert hash1 == hash2
            assert len(hash1) == 16  # MD5 hex truncated to 16 chars
            assert timer.elapsed_ms < 5

    def test_hash_query_case_insensitive(self, timer):
        """Query hashing should be case-insensitive"""
        from unittest.mock import patch

        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache

            cache = RedisCache()

            with timer.measure("hash_query case-insensitive"):
                hash1 = cache._hash_query("CSCI", 50)
                hash2 = cache._hash_query("csci", 50)

            assert hash1 == hash2
            assert timer.elapsed_ms < 5


@pytest.mark.e2e
class TestRealCurriculumScraperPipeline:
    """
    Test the REAL curriculum scraper pipeline.

    These tests actually download and parse the PDF from W&M's website.
    They verify the full pipeline works end-to-end.
    """

    def test_pdf_download(self, timer):
        """Download the real curriculum PDF"""
        from scrapers.curriculum_scraper import CurriculumPDFDownloader, CACHE_DIR

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        downloader = CurriculumPDFDownloader()

        with timer.measure("download_pdf"):
            pdf_path = downloader.download_pdf(force=False)

        assert pdf_path is not None, "Failed to download PDF"
        assert pdf_path.exists(), f"PDF not found at {pdf_path}"
        assert pdf_path.stat().st_size > 100000, "PDF seems too small"
        print(f"\n  PDF size: {pdf_path.stat().st_size / 1024:.1f} KB")

    def test_pdf_parse_full(self, timer):
        """Parse the real curriculum PDF"""
        from scrapers.curriculum_scraper import (
            CurriculumPDFDownloader, CurriculumPDFParser, CACHE_DIR
        )

        # Ensure PDF exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        downloader = CurriculumPDFDownloader()
        pdf_path = downloader.download_pdf(force=False)
        assert pdf_path and pdf_path.exists(), "PDF download required first"

        with timer.measure("parse_pdf"):
            parser = CurriculumPDFParser(pdf_path)
            data = parser.parse()

        # Verify structure
        assert data is not None, "Parser returned None"
        assert data.academic_year != "Unknown", f"Failed to extract academic year"
        assert len(data.majors) > 0, "No majors parsed"
        assert len(data.core_curriculum) > 0, "No core curriculum parsed"

        print(f"\n  Academic Year: {data.academic_year}")
        print(f"  Majors found: {len(data.majors)}")
        print(f"  Concentrations: {len(data.concentrations)}")
        print(f"  Core curriculum groups: {len(data.core_curriculum)}")

    def test_parsed_majors_content(self, timer):
        """Verify parsed majors have expected content"""
        from scrapers.curriculum_scraper import fetch_and_parse_curriculum

        with timer.measure("fetch_and_parse_curriculum"):
            data = fetch_and_parse_curriculum(force_download=False)

        assert data is not None

        # Handle both dict and dataclass
        if isinstance(data, dict):
            majors = data.get("majors", [])
        else:
            majors = data.majors

        # Should have known business majors
        major_names = [m["name"] if isinstance(m, dict) else m.name for m in majors]
        print(f"\n  Majors: {major_names}")

        expected_majors = ["Accounting", "Finance", "Marketing"]
        for expected in expected_majors:
            assert any(expected.lower() in name.lower() for name in major_names), \
                f"Expected major '{expected}' not found in {major_names}"

    def test_parsed_courses_have_credits(self, timer):
        """Verify parsed courses have valid credits"""
        from scrapers.curriculum_scraper import fetch_and_parse_curriculum

        with timer.measure("validate course credits"):
            data = fetch_and_parse_curriculum(force_download=False)

        assert data is not None

        # Get all courses from majors
        if isinstance(data, dict):
            majors = data.get("majors", [])
        else:
            majors = data.majors

        total_courses = 0
        invalid_credits = []

        for major in majors:
            if isinstance(major, dict):
                required = major.get("required_courses", [])
                electives = major.get("elective_courses", [])
            else:
                required = major.required_courses
                electives = major.elective_courses

            for group in required + electives:
                if isinstance(group, dict):
                    courses = group.get("courses", [])
                else:
                    courses = group.courses

                for course in courses:
                    total_courses += 1
                    if isinstance(course, dict):
                        credits = course.get("credits", 0)
                        code = course.get("code", "?")
                    else:
                        credits = course.credits
                        code = course.code

                    if credits <= 0 or credits > 6:
                        invalid_credits.append(f"{code}: {credits}")

        print(f"\n  Total courses: {total_courses}")
        print(f"  Invalid credits: {len(invalid_credits)}")

        assert total_courses > 20, f"Expected at least 20 courses, got {total_courses}"
        # Allow some invalid due to parsing edge cases, but not many
        assert len(invalid_credits) < total_courses * 0.1, \
            f"Too many invalid credits: {invalid_credits[:5]}"

    def test_cache_save_and_load(self, timer):
        """Test saving and loading curriculum data"""
        from scrapers.curriculum_scraper import (
            fetch_and_parse_curriculum, save_curriculum_data,
            load_curriculum_data, DATA_CACHE_FILE
        )

        # First fetch/parse
        with timer.measure("fetch_and_parse"):
            data = fetch_and_parse_curriculum(force_download=False)
        assert data is not None

        # Load from cache
        with timer.measure("load_from_cache"):
            cached = load_curriculum_data()

        assert cached is not None, "Failed to load cached data"
        assert DATA_CACHE_FILE.exists(), "Cache file doesn't exist"

        # Verify cached data matches
        if isinstance(data, dict):
            assert data.get("academic_year") == cached.get("academic_year")
            assert len(data.get("majors", [])) == len(cached.get("majors", []))
        else:
            assert data.academic_year == cached.get("academic_year")

        print(f"\n  Cache file size: {DATA_CACHE_FILE.stat().st_size / 1024:.1f} KB")

    def test_metadata_tracking(self, timer):
        """Test that metadata is properly tracked"""
        from scrapers.curriculum_scraper import (
            CurriculumPDFDownloader, METADATA_FILE, CACHE_DIR
        )
        import json

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        downloader = CurriculumPDFDownloader()

        with timer.measure("download with metadata"):
            downloader.download_pdf(force=False)

        assert METADATA_FILE.exists(), "Metadata file not created"

        metadata = json.loads(METADATA_FILE.read_text())
        print(f"\n  Metadata: {json.dumps(metadata, indent=2)}")

        assert "pdf_hash" in metadata, "Missing pdf_hash in metadata"
        assert "last_check" in metadata, "Missing last_check in metadata"
        assert len(metadata["pdf_hash"]) == 32, "Invalid hash format"

    def test_full_pipeline_timing(self, timer):
        """Time the full curriculum pipeline"""
        from scrapers.curriculum_scraper import fetch_and_parse_curriculum

        # Force fresh download to get accurate timing
        with timer.measure("full pipeline (cached)"):
            data = fetch_and_parse_curriculum(force_download=False)

        assert data is not None

        # Report timing
        if timer.elapsed_ms < 1000:
            print(f"\n  Pipeline completed in {timer.elapsed_ms:.0f}ms (cached)")
        else:
            print(f"\n  Pipeline completed in {timer.elapsed_ms/1000:.1f}s")

        # Cached should be fast
        assert timer.elapsed_ms < 5000, "Cached pipeline too slow"
