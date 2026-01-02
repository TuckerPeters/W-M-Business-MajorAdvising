"""
Tests for api/fetcher.py - Course data fetching and parsing
"""

import pytest
from datetime import datetime

from api.fetcher import FOSEFetcher, CourseData, SectionData
from core.parsers import parse_seats, parse_status


class TestSectionData:
    """Tests for SectionData dataclass"""

    def test_create_section(self):
        """Should create section with all fields"""
        section = SectionData(
            crn="12345",
            section_number="01",
            instructor="Smith, John",
            meeting_days="MWF",
            meeting_time="10:00-10:50",
            meeting_times_raw="MWF 10:00-10:50am",
            building="Morton",
            room="201",
            status="OPEN",
            capacity=30,
            enrolled=25,
            available=5
        )

        assert section.crn == "12345"
        assert section.status == "OPEN"
        assert section.available == 5

    def test_section_defaults(self):
        """Should have sensible defaults"""
        section = SectionData(
            crn="12345",
            section_number="01",
            instructor="",
            meeting_days="",
            meeting_time="",
            meeting_times_raw="",
            building="",
            room="",
            status="OPEN",
            capacity=0,
            enrolled=0,
            available=0
        )

        assert section.waitlist_capacity == 0
        assert section.waitlist_enrolled == 0
        assert section.instruction_method == ""


class TestCourseData:
    """Tests for CourseData dataclass"""

    def test_create_course(self):
        """Should create course with sections"""
        section = SectionData(
            crn="12345",
            section_number="01",
            instructor="Smith",
            meeting_days="MWF",
            meeting_time="10:00",
            meeting_times_raw="MWF 10:00am",
            building="Morton",
            room="201",
            status="OPEN",
            capacity=30,
            enrolled=25,
            available=5
        )

        course = CourseData(
            course_code="CSCI 141",
            subject_code="CSCI",
            course_number="141",
            title="Computational Problem Solving",
            description="Intro to CS",
            credits=4,
            attributes=["GER 1A"],
            sections=[section]
        )

        assert course.course_code == "CSCI 141"
        assert len(course.sections) == 1

    def test_to_dict(self):
        """Should convert to dictionary for Firebase"""
        course = CourseData(
            course_code="CSCI 141",
            subject_code="CSCI",
            course_number="141",
            title="Test",
            description="Test desc",
            credits=3,
            attributes=["GER 1A"],
            sections=[]
        )

        result = course.to_dict()

        assert result["course_code"] == "CSCI 141"
        assert result["subject_code"] == "CSCI"
        assert result["is_active"] is True
        assert "updated_at" in result
        assert isinstance(result["sections"], list)


class TestFOSEFetcherParsing:
    """Tests for FOSEFetcher parsing methods"""

    def setup_method(self):
        """Create fetcher instance for testing"""
        self.fetcher = FOSEFetcher.__new__(FOSEFetcher)

    def test_parse_credits_json(self):
        """Should extract credits from cart_opts JSON"""
        cart_opts = '{"credit_hrs":{"options":[{"value":"4"}]}}'
        assert self.fetcher._parse_credits(cart_opts) == 4

    def test_parse_credits_empty(self):
        """Should return default for empty input"""
        assert self.fetcher._parse_credits("") == 3
        assert self.fetcher._parse_credits(None) == 3

    def test_parse_credits_invalid_json(self):
        """Should return default for invalid JSON"""
        assert self.fetcher._parse_credits("not json") == 3

    def test_parse_status_open(self):
        """Should parse open status"""
        assert parse_status("A") == "OPEN"

    def test_parse_status_closed(self):
        """Should parse closed status"""
        assert parse_status("F") == "CLOSED"

    def test_parse_status_cancelled(self):
        """Should parse cancelled status"""
        assert parse_status("C") == "CANCELLED"

    def test_parse_status_unknown(self):
        """Should return UNKNOWN for unrecognized status"""
        assert parse_status("X") == "CANCELLED"  # X maps to CANCELLED
        assert parse_status("") == "UNKNOWN"

    def test_parse_course_code(self):
        """Should split course code into subject and number"""
        subject, number = self.fetcher._parse_course_code("CSCI 141")
        assert subject == "CSCI"
        assert number == "141"

    def test_parse_course_code_with_letter(self):
        """Should handle course numbers with letters"""
        subject, number = self.fetcher._parse_course_code("BUS 301W")
        assert subject == "BUS"
        assert number == "301W"

    def test_parse_course_code_invalid(self):
        """Should handle invalid course codes"""
        subject, number = self.fetcher._parse_course_code("INVALID")
        assert subject == "INVALID"
        assert number == ""

    def test_parse_seats_full(self):
        """Should parse enrollment data from HTML"""
        html = '<b>Maximum Enrollment:</b> 30<br><b>Seats Avail</b>: 5'
        result = parse_seats(html)

        assert result['capacity'] == 30
        assert result['available'] == 5
        assert result['enrolled'] == 25

    def test_parse_seats_with_waitlist(self):
        """Should parse waitlist data"""
        html = '''
        <b>Maximum Enrollment:</b> 30<br>
        <b>Seats Avail</b>: 0<br>
        <b>Waitlist Total:</b> 5 of 10
        '''
        result = parse_seats(html)

        assert result['waitlist_enrolled'] == 5
        assert result['waitlist_capacity'] == 10

    def test_parse_seats_empty(self):
        """Should return zeros for empty input"""
        result = parse_seats("")
        assert result['capacity'] == 0
        assert result['available'] == 0
        assert result['enrolled'] == 0

    def test_parse_attributes(self):
        """Should extract attributes from HTML list"""
        html = '<ul><li>GER 1A</li><li>COLL 150</li></ul>'
        result = self.fetcher._parse_attributes(html)

        assert "GER 1A" in result
        assert "COLL 150" in result
        assert len(result) == 2

    def test_parse_attributes_empty(self):
        """Should return empty list for no attributes"""
        assert self.fetcher._parse_attributes("") == []
        assert self.fetcher._parse_attributes(None) == []

    def test_parse_meeting_full(self):
        """Should parse meeting days and time"""
        result = self.fetcher._parse_meeting("MWF 10:00-10:50am")

        assert result['days'] == "MWF"
        assert "10:00" in result['time']
        assert result['raw'] == "MWF 10:00-10:50am"

    def test_parse_meeting_tuesday_thursday(self):
        """Should parse TR meeting pattern"""
        result = self.fetcher._parse_meeting("TR 11:00-12:20pm")

        assert result['days'] == "TR"

    def test_parse_meeting_empty(self):
        """Should handle empty meeting info"""
        result = self.fetcher._parse_meeting("")
        assert result['days'] == ""
        assert result['time'] == ""

    def test_parse_location(self):
        """Should extract building and room"""
        html = '<span>MWF 10:00-10:50am in Morton 201</span>'
        result = self.fetcher._parse_location(html)

        assert result['building'] == "Morton"
        assert result['room'] == "201"

    def test_parse_location_empty(self):
        """Should handle empty location"""
        result = self.fetcher._parse_location("")
        assert result['building'] == ""
        assert result['room'] == ""

    def test_clean_description(self):
        """Should remove HTML tags from description"""
        html = '<p>This is a <strong>test</strong> description.</p>'
        result = self.fetcher._clean_description(html)

        assert result == "This is a test description."
        assert "<" not in result

    def test_clean_description_empty(self):
        """Should handle empty description"""
        assert self.fetcher._clean_description("") == ""
        assert self.fetcher._clean_description(None) == ""


class TestFOSEFetcherIntegration:
    """Integration-style tests for FOSEFetcher"""

    @pytest.mark.asyncio
    async def test_fetcher_context_manager(self):
        """Should properly initialize with context manager"""
        async with FOSEFetcher(use_cache=False) as fetcher:
            assert fetcher.client is not None

    def test_course_grouping(self, sample_search_results):
        """Should group sections by course code"""
        courses_map = {}
        for section in sample_search_results:
            code = section.get('code', '')
            if code:
                if code not in courses_map:
                    courses_map[code] = []
                courses_map[code].append(section)

        # CSCI 141 should have 2 sections
        assert len(courses_map['CSCI 141']) == 2
        # CSCI 243 should have 1 section
        assert len(courses_map['CSCI 243']) == 1
