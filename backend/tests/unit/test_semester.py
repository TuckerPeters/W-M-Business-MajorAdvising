"""
Tests for core/semester.py - Semester management
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from core.semester import SemesterManager, get_current_term_code


class TestSemesterManager:
    """Tests for SemesterManager class"""

    def test_parse_term_code_spring(self):
        """Test parsing Spring term code"""
        result = SemesterManager.parse_term_code("202510")
        assert result['year'] == 2025
        assert result['semester'] == "Spring"
        assert result['semester_code'] == "10"
        assert result['display_name'] == "Spring 2025"

    def test_parse_term_code_summer(self):
        """Test parsing Summer term code"""
        result = SemesterManager.parse_term_code("202520")
        assert result['year'] == 2025
        assert result['semester'] == "Summer"
        assert result['semester_code'] == "20"

    def test_parse_term_code_fall(self):
        """Test parsing Fall term code"""
        result = SemesterManager.parse_term_code("202530")
        assert result['year'] == 2025
        assert result['semester'] == "Fall"
        assert result['semester_code'] == "30"

    def test_parse_term_code_invalid(self):
        """Test parsing invalid term code raises error"""
        with pytest.raises(ValueError):
            SemesterManager.parse_term_code("2025")

    @patch('core.semester.datetime')
    def test_trackable_semester_november(self, mock_datetime):
        """November should track Spring of next year"""
        mock_datetime.now.return_value = datetime(2025, 11, 15)
        result = SemesterManager.get_trackable_semester_info()
        assert result['semester'] == "Spring"
        assert result['year'] == 2026
        assert result['term_code'] == "202610"

    @patch('core.semester.datetime')
    def test_trackable_semester_december(self, mock_datetime):
        """December should track Spring of next year"""
        mock_datetime.now.return_value = datetime(2025, 12, 1)
        result = SemesterManager.get_trackable_semester_info()
        assert result['semester'] == "Spring"
        assert result['year'] == 2026

    @patch('core.semester.datetime')
    def test_trackable_semester_january(self, mock_datetime):
        """January should track Spring of same year"""
        mock_datetime.now.return_value = datetime(2026, 1, 15)
        result = SemesterManager.get_trackable_semester_info()
        assert result['semester'] == "Spring"
        assert result['year'] == 2026

    @patch('core.semester.datetime')
    def test_trackable_semester_june(self, mock_datetime):
        """June should track Summer"""
        mock_datetime.now.return_value = datetime(2025, 6, 15)
        result = SemesterManager.get_trackable_semester_info()
        assert result['semester'] == "Summer"
        assert result['year'] == 2025
        assert result['term_code'] == "202520"

    @patch('core.semester.datetime')
    def test_trackable_semester_august(self, mock_datetime):
        """August should track Fall"""
        mock_datetime.now.return_value = datetime(2025, 8, 15)
        result = SemesterManager.get_trackable_semester_info()
        assert result['semester'] == "Fall"
        assert result['year'] == 2025
        assert result['term_code'] == "202530"

    @patch('core.semester.datetime')
    def test_trackable_semester_october(self, mock_datetime):
        """October should track Fall"""
        mock_datetime.now.return_value = datetime(2025, 10, 15)
        result = SemesterManager.get_trackable_semester_info()
        assert result['semester'] == "Fall"
        assert result['year'] == 2025

    @patch('core.semester.datetime')
    def test_is_registration_period_april(self, mock_datetime):
        """April is registration period"""
        mock_datetime.now.return_value = datetime(2025, 4, 15)
        assert SemesterManager.is_registration_period() is True

    @patch('core.semester.datetime')
    def test_is_registration_period_november(self, mock_datetime):
        """November is registration period"""
        mock_datetime.now.return_value = datetime(2025, 11, 15)
        assert SemesterManager.is_registration_period() is True

    @patch('core.semester.datetime')
    def test_is_not_registration_period(self, mock_datetime):
        """March is not registration period"""
        mock_datetime.now.return_value = datetime(2025, 3, 15)
        assert SemesterManager.is_registration_period() is False

    @patch('core.semester.datetime')
    def test_update_interval_registration(self, mock_datetime):
        """During registration, interval should be 5 minutes"""
        mock_datetime.now.return_value = datetime(2025, 4, 15)
        assert SemesterManager.get_update_interval_minutes() == 5

    @patch('core.semester.datetime')
    def test_update_interval_normal(self, mock_datetime):
        """Outside registration, interval should be 15 minutes"""
        mock_datetime.now.return_value = datetime(2025, 3, 15)
        assert SemesterManager.get_update_interval_minutes() == 15

    def test_is_term_trackable(self):
        """Test term trackability check"""
        current = SemesterManager.get_trackable_term_code()
        assert SemesterManager.is_term_trackable(current) is True
        assert SemesterManager.is_term_trackable("199910") is False

    def test_get_next_transition_info(self):
        """Test next transition info returns valid data"""
        result = SemesterManager.get_next_transition_info()
        assert 'transition_date' in result
        assert 'current_trackable' in result
        assert 'next_trackable' in result
        assert 'next_semester' in result


class TestGetCurrentTermCode:
    """Tests for convenience function"""

    def test_returns_string(self):
        """Should return a 6-character string"""
        result = get_current_term_code()
        assert isinstance(result, str)
        assert len(result) == 6

    def test_valid_format(self):
        """Should return valid term code format"""
        result = get_current_term_code()
        year = int(result[:4])
        semester = result[4:]
        assert 2020 <= year <= 2030
        assert semester in ('10', '20', '30')
