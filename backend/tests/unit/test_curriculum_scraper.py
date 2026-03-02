"""
Tests for scrapers/curriculum_scraper.py - Curriculum PDF scraper and parser
"""

import pytest
import json
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

from scrapers.curriculum_scraper import (
    Course,
    CourseGroup,
    Major,
    Concentration,
    CurriculumData,
    CurriculumPDFDownloader,
    CurriculumPDFParser,
    dataclass_to_dict,
    save_curriculum_data,
    load_curriculum_data,
    CACHE_DIR,
    PDF_URL,
    BASE_URL,
)


# Data Model Tests

class TestCourseDataclass:
    """Tests for Course dataclass"""

    def test_create_course_minimal(self):
        """Should create course with minimal fields"""
        course = Course(
            code="BUAD 301",
            name="Financial Reporting & Analysis",
            credits=3
        )
        assert course.code == "BUAD 301"
        assert course.name == "Financial Reporting & Analysis"
        assert course.credits == 3
        assert course.semester == ""
        assert course.prerequisites == []

    def test_create_course_full(self):
        """Should create course with all fields"""
        course = Course(
            code="BUAD 302",
            name="Advanced Financial Reporting",
            credits=3,
            semester="F/S",
            prerequisites=["BUAD 301"],
            notes="Required for Accounting major"
        )
        assert course.semester == "F/S"
        assert "BUAD 301" in course.prerequisites
        assert course.notes == "Required for Accounting major"

    def test_course_with_multiple_prerequisites(self):
        """Should handle multiple prerequisites"""
        course = Course(
            code="BUAD 424",
            name="Derivatives & Risk Management",
            credits=3,
            prerequisites=["BUAD 323", "BUAD 327"]
        )
        assert len(course.prerequisites) == 2
        assert "BUAD 323" in course.prerequisites
        assert "BUAD 327" in course.prerequisites


class TestCourseGroupDataclass:
    """Tests for CourseGroup dataclass"""

    def test_create_course_group_required(self):
        """Should create group where all courses are required"""
        courses = [
            Course(code="BUAD 301", name="Course 1", credits=3),
            Course(code="BUAD 302", name="Course 2", credits=3),
        ]
        group = CourseGroup(
            description="Required Courses",
            courses=courses
        )
        assert group.description == "Required Courses"
        assert group.required_count is None  # All required
        assert len(group.courses) == 2

    def test_create_course_group_elective(self):
        """Should create group where N courses are required"""
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


class TestMajorDataclass:
    """Tests for Major dataclass"""

    def test_create_major(self):
        """Should create major with requirements"""
        required = CourseGroup(
            description="Required",
            courses=[Course(code="BUAD 301", name="Test", credits=3)]
        )
        elective = CourseGroup(
            description="Choose 1",
            required_count=1,
            courses=[
                Course(code="BUAD 304", name="Option 1", credits=3),
                Course(code="BUAD 305", name="Option 2", credits=3),
            ]
        )
        major = Major(
            name="Accounting",
            credits_required=15,
            description="15 credits in addition to core",
            required_courses=[required],
            elective_courses=[elective]
        )
        assert major.name == "Accounting"
        assert major.credits_required == 15
        assert len(major.required_courses) == 1
        assert len(major.elective_courses) == 1


class TestConcentrationDataclass:
    """Tests for Concentration dataclass"""

    def test_create_concentration(self):
        """Should create concentration"""
        group = CourseGroup(
            description="Choose 2 courses",
            required_count=2,
            courses=[
                Course(code="BUAD 327", name="Investments", credits=3),
                Course(code="BUAD 329", name="Corporate Valuation", credits=3),
            ]
        )
        concentration = Concentration(
            name="Finance",
            credits_required=6,
            description="Choose 2 courses including 327 or 329",
            course_groups=[group]
        )
        assert concentration.name == "Finance"
        assert concentration.credits_required == 6


class TestCurriculumDataDataclass:
    """Tests for CurriculumData dataclass"""

    def test_create_curriculum_data(self):
        """Should create complete curriculum data"""
        data = CurriculumData(
            academic_year="2025-2026",
            revision_date="Summer 2025",
            pdf_hash="abc123",
            parsed_at="2025-01-01T00:00:00",
            source_url=PDF_URL
        )
        assert data.academic_year == "2025-2026"
        assert data.revision_date == "Summer 2025"
        assert data.majors == []
        assert data.concentrations == []


# Serialization Tests

class TestDataclassToDict:
    """Tests for dataclass_to_dict function"""

    def test_simple_course(self):
        """Should convert course to dict"""
        course = Course(
            code="BUAD 301",
            name="Test Course",
            credits=3,
            semester="F",
            prerequisites=["BUAD 203"]
        )
        result = dataclass_to_dict(course)

        assert isinstance(result, dict)
        assert result["code"] == "BUAD 301"
        assert result["credits"] == 3
        assert result["prerequisites"] == ["BUAD 203"]

    def test_nested_structures(self):
        """Should handle nested dataclasses"""
        course = Course(code="BUAD 301", name="Test", credits=3)
        group = CourseGroup(description="Required", courses=[course])
        major = Major(
            name="Test Major",
            credits_required=15,
            required_courses=[group]
        )

        result = dataclass_to_dict(major)

        assert result["name"] == "Test Major"
        assert len(result["required_courses"]) == 1
        assert result["required_courses"][0]["courses"][0]["code"] == "BUAD 301"

    def test_full_curriculum_data(self):
        """Should convert full curriculum data to dict"""
        prereqs = CourseGroup(
            description="Prerequisites",
            courses=[Course(code="ECON 101", name="Micro", credits=3)]
        )
        data = CurriculumData(
            academic_year="2025-2026",
            revision_date="Summer 2025",
            prerequisites=prereqs
        )

        result = dataclass_to_dict(data)

        assert isinstance(result, dict)
        assert result["academic_year"] == "2025-2026"
        assert result["prerequisites"]["courses"][0]["code"] == "ECON 101"


# PDF Downloader Tests

class TestCurriculumPDFDownloader:
    """Tests for CurriculumPDFDownloader class"""

    def test_init_creates_cache_dir(self, tmp_path):
        """Should create cache directory on init"""
        with patch('scrapers.curriculum_scraper.CACHE_DIR', tmp_path / "cache"):
            downloader = CurriculumPDFDownloader()
            assert (tmp_path / "cache").exists()

    @patch('scrapers.curriculum_scraper.requests.Session')
    def test_get_pdf_url_from_page_finds_link(self, mock_session_class):
        """Should extract PDF URL from page HTML"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock response with PDF link
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
        <a class="content_button" href="/undergraduate/documents/business-majors-curriculum-guide-2025-2026.pdf">
            Business Major Guide (PDF)
        </a>
        </html>
        '''
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        downloader = CurriculumPDFDownloader()
        downloader.session = mock_session

        url = downloader.get_pdf_url_from_page()

        assert "business-majors-curriculum-guide" in url
        assert url.endswith(".pdf")

    @patch('scrapers.curriculum_scraper.requests.Session')
    def test_get_pdf_url_fallback_on_error(self, mock_session_class):
        """Should fall back to known URL on error"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = Exception("Network error")

        downloader = CurriculumPDFDownloader()
        downloader.session = mock_session

        url = downloader.get_pdf_url_from_page()

        assert url == PDF_URL

    def test_is_cache_valid_no_files(self, tmp_path):
        """Should return False if no cache files exist"""
        with patch('scrapers.curriculum_scraper.CACHE_DIR', tmp_path):
            with patch('scrapers.curriculum_scraper.PDF_CACHE_FILE', tmp_path / "test.pdf"):
                with patch('scrapers.curriculum_scraper.METADATA_FILE', tmp_path / "meta.json"):
                    downloader = CurriculumPDFDownloader()
                    assert downloader._is_cache_valid() is False

    def test_is_cache_valid_with_recent_check(self, tmp_path):
        """Should return True if cache was checked recently"""
        pdf_file = tmp_path / "test.pdf"
        meta_file = tmp_path / "meta.json"

        pdf_file.write_bytes(b"fake pdf content")
        meta_file.write_text(json.dumps({
            "last_check": datetime.now().isoformat(),
            "pdf_hash": "abc123"
        }))

        with patch('scrapers.curriculum_scraper.CACHE_DIR', tmp_path):
            with patch('scrapers.curriculum_scraper.PDF_CACHE_FILE', pdf_file):
                with patch('scrapers.curriculum_scraper.METADATA_FILE', meta_file):
                    downloader = CurriculumPDFDownloader()
                    assert downloader._is_cache_valid() is True


# PDF Parser Tests

class TestCurriculumPDFParser:
    """Tests for CurriculumPDFParser class"""

    def test_extract_academic_year(self, tmp_path):
        """Should extract academic year from text"""
        # Create a mock PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        parser.full_text = "Business Majors Curriculum Guide 2025-2026"

        result = parser._extract_academic_year()
        assert result == "2025-2026"

    def test_extract_academic_year_not_found(self, tmp_path):
        """Should return Unknown if not found"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        parser.full_text = "Some other text"

        result = parser._extract_academic_year()
        assert result == "Unknown"

    def test_extract_revision_date(self, tmp_path):
        """Should extract revision date from text"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        parser.full_text = "(Revised Summer 2025) Course offerings..."

        result = parser._extract_revision_date()
        assert result == "Summer 2025"

    def test_parse_course_line_buad(self, tmp_path):
        """Should parse BUAD course line"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)

        # Test parsing a typical course line
        line = "301 Financial Reporting & Analysis 3 cr F/S (BUAD 203)"
        result = parser._parse_course_line(line)

        assert result is not None
        assert result.code == "BUAD 301"
        assert result.name == "Financial Reporting & Analysis"
        assert result.credits == 3
        assert result.semester == "F/S"
        assert "BUAD 203" in result.prerequisites

    def test_parse_course_line_full_code(self, tmp_path):
        """Should parse course with full code"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)

        line = "ECON 101 Microeconomics 3 cr"
        result = parser._parse_course_line(line)

        assert result is not None
        assert result.code == "ECON 101"
        assert result.name == "Microeconomics"
        assert result.credits == 3

    def test_parse_prerequisites_returns_correct_structure(self, tmp_path):
        """Should return CourseGroup with prerequisites"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        result = parser._parse_prerequisites()

        assert isinstance(result, CourseGroup)
        assert result.required_count == 5
        assert len(result.courses) == 5

        # Check specific courses
        codes = [c.code for c in result.courses]
        assert "ECON 101" in codes
        assert "ECON 102" in codes
        assert "BUAD 203" in codes
        assert "BUAD 231" in codes

    def test_parse_core_curriculum_returns_groups(self, tmp_path):
        """Should return list of course groups for core"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        result = parser._parse_core_curriculum()

        assert isinstance(result, list)
        assert len(result) == 2  # Foundation + Upper Level

        # Check foundation courses
        foundation = result[0]
        assert "Foundation" in foundation.description
        foundation_codes = [c.code for c in foundation.courses]
        assert "BUAD 300" in foundation_codes
        assert "BUAD 311" in foundation_codes
        assert "BUAD 323" in foundation_codes

        # Check upper level courses
        upper = result[1]
        assert "Upper Level" in upper.description
        upper_codes = [c.code for c in upper.courses]
        assert "BUAD 317" in upper_codes
        assert "BUAD 414" in upper_codes

    def test_parse_majors_returns_all_majors(self, tmp_path):
        """Should return all 5 majors"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        result = parser._parse_majors()

        assert isinstance(result, list)
        assert len(result) == 5

        major_names = [m.name for m in result]
        assert "Accounting" in major_names
        assert "Finance" in major_names
        assert "Marketing" in major_names
        assert any("Data Science" in name for name in major_names)
        assert any("Supply Chain" in name for name in major_names)

    def test_parse_majors_accounting_has_correct_credits(self, tmp_path):
        """Accounting major should require 15 credits"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        result = parser._parse_majors()

        accounting = next(m for m in result if m.name == "Accounting")
        assert accounting.credits_required == 15

    def test_parse_majors_finance_has_correct_credits(self, tmp_path):
        """Finance major should require 13 credits"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        result = parser._parse_majors()

        finance = next(m for m in result if m.name == "Finance")
        assert finance.credits_required == 13

    def test_parse_concentrations_returns_all(self, tmp_path):
        """Should return all 9 concentrations"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        result = parser._parse_concentrations()

        assert isinstance(result, list)
        assert len(result) == 9

        conc_names = [c.name for c in result]
        assert "Accounting" in conc_names
        assert "Finance" in conc_names
        assert "Marketing" in conc_names
        assert "Consulting" in conc_names
        assert "Sustainability" in conc_names

    def test_parse_international_emphasis(self, tmp_path):
        """Should return international emphasis requirements"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        parser = CurriculumPDFParser(pdf_file)
        result = parser._parse_international_emphasis()

        assert isinstance(result, dict)
        assert "requirements" in result
        assert len(result["requirements"]) == 4

        # Check study abroad requirement
        study_abroad = result["requirements"][3]
        assert study_abroad["minimum_credits"] == 12


# Cache Persistence Tests

class TestCachePersistence:
    """Tests for cache save/load functions"""

    def test_save_and_load_curriculum_data(self, tmp_path):
        """Should save and load curriculum data correctly"""
        cache_file = tmp_path / "curriculum_data.json"

        # Create test data
        course = Course(code="BUAD 301", name="Test", credits=3)
        prereqs = CourseGroup(description="Prerequisites", courses=[course])
        data = CurriculumData(
            academic_year="2025-2026",
            revision_date="Summer 2025",
            prerequisites=prereqs,
            pdf_hash="testhash123",
            parsed_at="2025-01-01T00:00:00"
        )

        with patch('scrapers.curriculum_scraper.CACHE_DIR', tmp_path):
            with patch('scrapers.curriculum_scraper.DATA_CACHE_FILE', cache_file):
                # Save
                save_curriculum_data(data)

                assert cache_file.exists()

                # Load
                loaded = load_curriculum_data()

                assert loaded is not None
                assert loaded["academic_year"] == "2025-2026"
                assert loaded["pdf_hash"] == "testhash123"
                assert loaded["prerequisites"]["courses"][0]["code"] == "BUAD 301"

    def test_load_returns_none_if_no_file(self, tmp_path):
        """Should return None if no cache file exists"""
        with patch('scrapers.curriculum_scraper.DATA_CACHE_FILE', tmp_path / "nonexistent.json"):
            result = load_curriculum_data()
            assert result is None


# Integration-Style Unit Tests (with mocks)

class TestFetchAndParseCurriculum:
    """Tests for the main fetch_and_parse_curriculum function"""

    @patch('scrapers.curriculum_scraper.CurriculumPDFDownloader')
    @patch('scrapers.curriculum_scraper.CurriculumPDFParser')
    @patch('scrapers.curriculum_scraper.save_curriculum_data')
    def test_fetch_and_parse_success(self, mock_save, mock_parser_class, mock_downloader_class, tmp_path):
        """Should download, parse, and save curriculum data"""
        from scrapers.curriculum_scraper import fetch_and_parse_curriculum

        # Setup mocks
        mock_downloader = MagicMock()
        mock_downloader.download_pdf.return_value = tmp_path / "test.pdf"
        mock_downloader_class.return_value = mock_downloader

        mock_data = CurriculumData(
            academic_year="2025-2026",
            revision_date="Summer 2025"
        )
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_data
        mock_parser_class.return_value = mock_parser

        # Create fake PDF file
        (tmp_path / "test.pdf").write_bytes(b"fake pdf")

        with patch('scrapers.curriculum_scraper.DATA_CACHE_FILE', tmp_path / "data.json"):
            with patch('scrapers.curriculum_scraper.load_curriculum_data', return_value=None):
                result = fetch_and_parse_curriculum(force_download=True)

        assert result is not None
        mock_downloader.download_pdf.assert_called_once()
        mock_parser.parse.assert_called_once()
        mock_save.assert_called_once()

    @patch('scrapers.curriculum_scraper.CurriculumPDFDownloader')
    def test_fetch_returns_none_on_download_failure(self, mock_downloader_class):
        """Should return None if download fails"""
        from scrapers.curriculum_scraper import fetch_and_parse_curriculum

        mock_downloader = MagicMock()
        mock_downloader.download_pdf.return_value = None
        mock_downloader_class.return_value = mock_downloader

        result = fetch_and_parse_curriculum()

        assert result is None


class TestCheckAndUpdateCurriculum:
    """Tests for check_and_update_curriculum function"""

    @patch('scrapers.curriculum_scraper.CurriculumPDFDownloader')
    @patch('scrapers.curriculum_scraper.fetch_and_parse_curriculum')
    def test_updates_when_pdf_changed(self, mock_fetch, mock_downloader_class):
        """Should re-parse when PDF has changed"""
        from scrapers.curriculum_scraper import check_and_update_curriculum

        mock_downloader = MagicMock()
        mock_downloader.check_for_updates.return_value = True
        mock_downloader_class.return_value = mock_downloader

        result = check_and_update_curriculum()

        assert result is True
        mock_fetch.assert_called_once_with(force_download=True)

    @patch('scrapers.curriculum_scraper.CurriculumPDFDownloader')
    @patch('scrapers.curriculum_scraper.fetch_and_parse_curriculum')
    def test_no_update_when_pdf_unchanged(self, mock_fetch, mock_downloader_class):
        """Should not re-parse when PDF unchanged"""
        from scrapers.curriculum_scraper import check_and_update_curriculum

        mock_downloader = MagicMock()
        mock_downloader.check_for_updates.return_value = False
        mock_downloader_class.return_value = mock_downloader

        result = check_and_update_curriculum()

        assert result is False
        mock_fetch.assert_not_called()
