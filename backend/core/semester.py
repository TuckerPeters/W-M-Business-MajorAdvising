"""
Semester Management Utilities

Trackable Semester Logic:
- Nov 1 to May 31: Track Spring courses (next year if Nov-Dec)
- Jun 1 to Jul 31: Track Summer courses (same year)
- Aug 1 to Oct 31: Track Fall courses (same year)

Term Code Format: YYYYSS
- 10 = Spring
- 20 = Summer
- 30 = Fall
"""

from datetime import datetime
from typing import Dict, Union


class SemesterManager:
    """Manages dynamic semester detection and transitions"""

    # Transition dates (month, day)
    FALL_TO_SPRING_CUTOFF = (11, 1)    # November 1st -> Spring
    SPRING_TO_SUMMER_CUTOFF = (6, 1)   # June 1st -> Summer
    SUMMER_TO_FALL_CUTOFF = (8, 1)     # August 1st -> Fall

    @staticmethod
    def get_trackable_semester_info() -> Dict[str, Union[str, int]]:
        """
        Determine which semester users can currently track courses for.

        Returns:
            Dict with year, semester, semester_code, term_code, display_name
        """
        now = datetime.now()
        month = now.month
        year = now.year

        if month >= 11 or month <= 5:  # November through May -> Spring
            term_year = year + 1 if month >= 11 else year
            return {
                "year": term_year,
                "semester": "Spring",
                "semester_code": "10",
                "term_code": f"{term_year}10",
                "display_name": f"Spring {term_year}"
            }
        elif 6 <= month <= 7:  # June through July -> Summer
            return {
                "year": year,
                "semester": "Summer",
                "semester_code": "20",
                "term_code": f"{year}20",
                "display_name": f"Summer {year}"
            }
        else:  # August through October -> Fall
            return {
                "year": year,
                "semester": "Fall",
                "semester_code": "30",
                "term_code": f"{year}30",
                "display_name": f"Fall {year}"
            }

    @staticmethod
    def get_trackable_term_code() -> str:
        """Get the term code for the currently trackable semester"""
        info = SemesterManager.get_trackable_semester_info()
        return info["term_code"]

    @staticmethod
    def get_trackable_display_name() -> str:
        """Get human-readable name for trackable semester"""
        info = SemesterManager.get_trackable_semester_info()
        return info["display_name"]

    @staticmethod
    def is_term_trackable(term_code: str) -> bool:
        """Check if a given term code is currently trackable"""
        return term_code == SemesterManager.get_trackable_term_code()

    @staticmethod
    def get_next_transition_info() -> Dict[str, Union[str, datetime]]:
        """
        Get information about the next semester transition.

        Returns:
            Dict with transition_date, current/next trackable info
        """
        now = datetime.now()
        month = now.month
        year = now.year

        current = SemesterManager.get_trackable_semester_info()

        if month >= 11 or month <= 5:  # Currently tracking Spring
            transition_year = year + 1 if month >= 11 else year
            transition_date = datetime(transition_year, 6, 1)
            next_term_code = f"{transition_year}20"
            next_semester = f"Summer {transition_year}"
        elif 6 <= month <= 7:  # Currently tracking Summer
            transition_date = datetime(year, 8, 1)
            next_term_code = f"{year}30"
            next_semester = f"Fall {year}"
        else:  # Currently tracking Fall (Aug-Oct)
            transition_date = datetime(year, 11, 1)
            next_term_code = f"{year + 1}10"
            next_semester = f"Spring {year + 1}"

        return {
            "transition_date": transition_date,
            "current_trackable": current["term_code"],
            "current_semester": current["display_name"],
            "next_trackable": next_term_code,
            "next_semester": next_semester
        }

    @staticmethod
    def parse_term_code(term_code: str) -> Dict[str, Union[str, int]]:
        """Parse a term code into its components"""
        if len(term_code) != 6:
            raise ValueError(f"Invalid term code: {term_code}")

        year = int(term_code[:4])
        semester_code = term_code[4:]

        semester_map = {
            "10": "Spring",
            "20": "Summer",
            "30": "Fall"
        }

        semester = semester_map.get(semester_code, "Unknown")

        return {
            "year": year,
            "semester": semester,
            "semester_code": semester_code,
            "term_code": term_code,
            "display_name": f"{semester} {year}"
        }

    @staticmethod
    def is_registration_period() -> bool:
        """
        Check if we're in a registration period.

        Registration typically happens:
        - April: Registration for Fall
        - November: Registration for Spring

        During registration, enrollment updates should run more frequently.
        """
        month = datetime.now().month
        return month in (4, 11)

    @staticmethod
    def get_update_interval_minutes() -> int:
        """
        Get the recommended enrollment update interval.

        Returns:
            5 minutes during registration periods, 15 minutes otherwise
        """
        if SemesterManager.is_registration_period():
            return 5
        return 15


def get_current_term_code() -> str:
    """Convenience function to get current trackable term code"""
    return SemesterManager.get_trackable_term_code()
