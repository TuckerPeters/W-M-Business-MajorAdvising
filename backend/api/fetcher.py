"""
FOSE API Fetcher for William & Mary Course Catalog

Fetches course data from W&M's FOSE (Faculty-Offering-Section-Enrollment) API.
This is the official course registration API - no web scraping required.

Features:
- Rate limiting to avoid overwhelming the API
- Response caching to reduce redundant requests
- Clear user-agent identification
- Validation and error reporting
"""

import asyncio
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from .client import FOSEClient, ValidationReport
from core.parsers import parse_seats, parse_status


@dataclass
class SectionData:
    """Data structure for a course section."""
    crn: str
    section_number: str
    instructor: str
    meeting_days: str
    meeting_time: str
    meeting_times_raw: str
    building: str
    room: str
    status: str
    capacity: int
    enrolled: int
    available: int
    waitlist_capacity: int = 0
    waitlist_enrolled: int = 0
    waitlist_available: int = 0
    instruction_method: str = ""


@dataclass
class CourseData:
    """Data structure for a course with its sections."""
    course_code: str
    subject_code: str
    course_number: str
    title: str
    description: str
    credits: int
    attributes: List[str] = field(default_factory=list)
    sections: List[SectionData] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    corequisites: List[str] = field(default_factory=list)
    registration_restrictions: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage."""
        return {
            "course_code": self.course_code,
            "subject_code": self.subject_code,
            "course_number": self.course_number,
            "title": self.title,
            "description": self.description,
            "credits": self.credits,
            "attributes": self.attributes,
            "prerequisites": self.prerequisites,
            "corequisites": self.corequisites,
            "registration_restrictions": self.registration_restrictions,
            "sections": [
                {
                    "crn": s.crn,
                    "section_number": s.section_number,
                    "instructor": s.instructor,
                    "meeting_days": s.meeting_days,
                    "meeting_time": s.meeting_time,
                    "meeting_times_raw": s.meeting_times_raw,
                    "building": s.building,
                    "room": s.room,
                    "status": s.status,
                    "capacity": s.capacity,
                    "enrolled": s.enrolled,
                    "available": s.available,
                    "waitlist_capacity": s.waitlist_capacity,
                    "waitlist_enrolled": s.waitlist_enrolled,
                    "waitlist_available": s.waitlist_available,
                    "instruction_method": s.instruction_method
                }
                for s in self.sections
            ],
            "updated_at": datetime.utcnow().isoformat(),
            "is_active": True
        }


class FOSEFetcher:
    """Fetches course catalog data from W&M's FOSE API."""

    def __init__(self, concurrency: int = 50, use_cache: bool = True):
        self.concurrency = concurrency
        self.use_cache = use_cache
        self.client: Optional[FOSEClient] = None
        self._report: Optional[ValidationReport] = None

    async def __aenter__(self):
        self.client = FOSEClient(
            concurrency=self.concurrency,
            use_cache=self.use_cache
        )
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def report(self) -> Optional[ValidationReport]:
        """Get the validation report"""
        return self.client.report if self.client else None

    async def fetch_all_courses(self, term_code: str) -> List[CourseData]:
        """
        Fetch all courses for a given term.

        Args:
            term_code: Term code in YYYYSS format (e.g., "202610" for Fall 2025)

        Returns:
            List of CourseData objects with all course information
        """
        print(f"[{datetime.now()}] Fetching course catalog for term {term_code}...")
        self.client.report.term_code = term_code

        # Step 1: Fetch all sections from Search API
        search_results = await self.client.fetch_search(term_code)
        print(f"[{datetime.now()}] Found {len(search_results)} sections in search results")

        if not search_results:
            return []

        # Step 2: Validate and group sections by course code
        courses_map: Dict[str, List[Dict]] = {}
        valid_sections = 0

        for section in search_results:
            # Validate section
            if self.client.validate_section(section):
                valid_sections += 1

            code = section.get('code', '')
            if code:
                # Validate course code format
                self.client.validate_course_code(code)

                if code not in courses_map:
                    courses_map[code] = []
                courses_map[code].append(section)

        print(f"[{datetime.now()}] Grouped into {len(courses_map)} unique courses ({valid_sections} valid sections)")
        self.client.report.total_courses = len(courses_map)

        # Step 3: Fetch details for all CRNs (for descriptions, attributes, enrollment)
        crns = [s.get('crn') for s in search_results if s.get('crn')]
        print(f"[{datetime.now()}] Fetching details for {len(crns)} sections...")

        def progress(completed, total):
            print(f"[{datetime.now()}] Fetched {completed}/{total} section details...")

        details_map = await self.client.fetch_details_batch(crns, term_code, progress)
        print(f"[{datetime.now()}] Fetched {len(details_map)} section details")

        # Check for high failure rate
        failure_rate = self.client.report.failed_details / max(len(crns), 1)
        if failure_rate > 0.1:  # More than 10% failures
            self.client.report.add_warning(
                f"High detail fetch failure rate: {failure_rate:.1%} ({self.client.report.failed_details}/{len(crns)})"
            )

        # Step 4: Build CourseData objects
        courses = []
        for course_code, sections_data in courses_map.items():
            subject_code, course_number = self._parse_course_code(course_code)

            # Get first section for course-level info
            first_section = sections_data[0]
            first_crn = first_section.get('crn', '')
            first_details = details_map.get(first_crn, {})

            # Parse course info
            description = self._clean_description(first_details.get('description', ''))
            attributes = self._parse_attributes(first_details.get('attr', ''))
            credits = self._parse_credits(first_section.get('cart_opts', ''))

            # Parse registration restrictions and prerequisites
            registration_restrictions = first_details.get('registration_restrictions', '')
            prerequisites = self._parse_prerequisites(registration_restrictions)

            # Parse corequisites from course and section level
            course_coreqs = first_details.get('course_coreqs', '')
            section_coreqs = first_details.get('section_coreqs', '')
            corequisites = self._parse_corequisites(course_coreqs, section_coreqs)

            # Build sections
            section_list = []
            for sec in sections_data:
                crn = sec.get('crn', '')
                details = details_map.get(crn, {})

                # Parse meeting info
                meeting = self._parse_meeting(sec.get('meets', ''))
                location = self._parse_location(details.get('meeting', ''))
                enrollment = parse_seats(details.get('seats', ''))

                section_list.append(SectionData(
                    crn=crn,
                    section_number=sec.get('section', sec.get('no', '')),
                    instructor=sec.get('instr', ''),
                    meeting_days=meeting['days'],
                    meeting_time=meeting['time'],
                    meeting_times_raw=meeting['raw'],
                    building=location['building'],
                    room=location['room'],
                    status=parse_status(sec.get('stat', '')),
                    capacity=enrollment['capacity'],
                    enrolled=enrollment['enrolled'],
                    available=enrollment['available'],
                    waitlist_capacity=enrollment['waitlist_capacity'],
                    waitlist_enrolled=enrollment['waitlist_enrolled'],
                    waitlist_available=enrollment['waitlist_available'],
                ))

            courses.append(CourseData(
                course_code=course_code,
                subject_code=subject_code,
                course_number=course_number,
                title=first_section.get('title', ''),
                description=description,
                credits=credits,
                attributes=attributes,
                sections=section_list,
                prerequisites=prerequisites,
                corequisites=corequisites,
                registration_restrictions=registration_restrictions,
            ))

        print(f"[{datetime.now()}] Processed {len(courses)} unique courses")

        # Print validation report if there are issues
        if self.client.report.has_issues():
            print("\n" + self.client.report.summary())

        return courses

    # Parsing Helpers

    def _parse_credits(self, cart_opts: str) -> int:
        """Extract credits from cart_opts JSON."""
        try:
            opts = json.loads(cart_opts) if cart_opts else {}
            credit_opts = opts.get('credit_hrs', {}).get('options', [])
            if credit_opts:
                return int(credit_opts[0].get('value', 3))
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
        return 3

    def _parse_attributes(self, attr_html: str) -> List[str]:
        """Extract attributes from HTML."""
        if not attr_html:
            return []
        attrs = re.findall(r'<li>([^<]+)</li>', attr_html)
        return [a.strip() for a in attrs if a.strip()]

    def _parse_meeting(self, meets: str) -> Dict[str, str]:
        """Parse meeting days/time from meets string."""
        result = {'days': '', 'time': '', 'raw': meets or ''}
        if not meets:
            return result

        match = re.search(r'([MTWRFSU]+)\s+(\d{1,2}[:\d]*[-–]\d{1,2}[:\d]*[ap]?m?)', meets, re.I)
        if match:
            result['days'] = match.group(1)
            result['time'] = match.group(2)
        return result

    def _parse_location(self, meeting_html: str) -> Dict[str, str]:
        """Extract building/room from meeting HTML."""
        result = {'building': '', 'room': ''}
        if not meeting_html:
            return result

        match = re.search(r'in\s+(.+?)\s+(\d+[A-Za-z]?)\s*</span>', meeting_html)
        if match:
            result['building'] = match.group(1).strip()
            result['room'] = match.group(2)

        return result

    def _clean_description(self, desc: str) -> str:
        """Remove HTML tags from description."""
        if not desc:
            return ""
        return re.sub(r'<[^>]+>', '', desc).strip()

    def _parse_prerequisites(self, registration_restrictions: str) -> List[str]:
        """
        Extract prerequisite course codes from registration_restrictions HTML.

        The HTML contains prereq info in <p class="prereq"> tags.
        Example: '<p class="prereq">Prerequisite: BUAD 323.<br/>A minimum grade of D- is required in BUAD 323.</p>'

        Returns:
            List of prerequisite course codes (e.g., ["BUAD 323", "BUAD 203"])
        """
        if not registration_restrictions:
            return []

        prerequisites = []

        # Extract content from prereq paragraphs
        prereq_matches = re.findall(r'<p class="prereq"[^>]*>(.*?)</p>', registration_restrictions, re.DOTALL | re.IGNORECASE)

        for prereq_text in prereq_matches:
            # Remove HTML tags to get plain text
            plain_text = re.sub(r'<[^>]+>', ' ', prereq_text)

            # Find all course codes (SUBJ NNN pattern, e.g., "BUAD 323", "CSCI 141")
            # Course codes are typically 3-4 uppercase letters followed by space and 3-4 digits
            course_codes = re.findall(r'\b([A-Z]{2,4})\s+(\d{3}[A-Z]?)\b', plain_text)

            for subj, num in course_codes:
                course_code = f"{subj} {num}"
                if course_code not in prerequisites:
                    prerequisites.append(course_code)

        return prerequisites

    def _parse_corequisites(self, course_coreqs: str, section_coreqs: str = "") -> List[str]:
        """
        Extract corequisite course codes from course_coreqs and section_coreqs fields.

        Args:
            course_coreqs: Course-level corequisites (e.g., "AMST 200D")
            section_coreqs: Section-specific corequisites

        Returns:
            List of corequisite course codes
        """
        corequisites = []

        # Parse course-level corequisites
        if course_coreqs:
            # Course coreqs may be comma-separated or contain multiple course codes
            codes = re.findall(r'\b([A-Z]{2,4})\s+(\d{3}[A-Z]?)\b', course_coreqs)
            for subj, num in codes:
                course_code = f"{subj} {num}"
                if course_code not in corequisites:
                    corequisites.append(course_code)

        # Parse section-specific corequisites
        if section_coreqs:
            codes = re.findall(r'\b([A-Z]{2,4})\s+(\d{3}[A-Z]?)\b', section_coreqs)
            for subj, num in codes:
                course_code = f"{subj} {num}"
                if course_code not in corequisites:
                    corequisites.append(course_code)

        return corequisites

    def _parse_course_code(self, code: str) -> Tuple[str, str]:
        """Split course code into subject and number."""
        parts = code.split(maxsplit=1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return code, ''


# Re-export from core.semester for backwards compatibility
from core.semester import get_current_term_code


async def fetch_courses(term_code: Optional[str] = None, use_cache: bool = True) -> List[CourseData]:
    """
    Convenience function to fetch all courses.

    Args:
        term_code: Optional term code. If not provided, uses current trackable term.
        use_cache: Whether to use response caching (default True)

    Returns:
        List of CourseData objects
    """
    if term_code is None:
        term_code = get_current_term_code()

    async with FOSEFetcher(use_cache=use_cache) as fetcher:
        courses = await fetcher.fetch_all_courses(term_code)

        # Return report along with courses for inspection
        return courses


async def fetch_courses_with_report(
    term_code: Optional[str] = None,
    use_cache: bool = True
) -> Tuple[List[CourseData], ValidationReport]:
    """
    Fetch courses and return validation report.

    Returns:
        Tuple of (courses, validation_report)
    """
    if term_code is None:
        term_code = get_current_term_code()

    async with FOSEFetcher(use_cache=use_cache) as fetcher:
        courses = await fetcher.fetch_all_courses(term_code)
        return courses, fetcher.report
