"""
Student Profile Service

Handles all Firestore operations for student profiles, enrollments, and milestones.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from core.config import get_firestore_client, initialize_firebase


class ScheduleConflictError(Exception):
    """Raised when a time conflict is detected between courses."""
    def __init__(self, message: str, conflicting_course: Dict[str, Any]):
        super().__init__(message)
        self.conflicting_course = conflicting_course


class InvalidTermError(Exception):
    """Raised when an invalid term is specified for enrollment status."""
    pass


class CourseNotFoundError(Exception):
    """Raised when a course doesn't exist in the catalog."""
    pass


class SectionNotFoundError(Exception):
    """Raised when a section doesn't exist for a course."""
    pass


class NoSeatsAvailableError(Exception):
    """Raised when a section has no available seats."""
    def __init__(self, message: str, section_info: Dict[str, Any]):
        super().__init__(message)
        self.section_info = section_info


class PrerequisitesNotMetError(Exception):
    """Raised when a course's prerequisites have not been completed."""
    def __init__(self, message: str, missing_prerequisites: List[str]):
        super().__init__(message)
        self.missing_prerequisites = missing_prerequisites


class StudentService:
    """Service for managing student data in Firebase Firestore."""

    STUDENTS_COLLECTION = "students"
    ENROLLMENTS_COLLECTION = "enrollments"
    MILESTONES_COLLECTION = "milestones"

    def __init__(self):
        self.db = get_firestore_client()

    # --- Term/Semester Utilities ---

    def get_current_term(self) -> str:
        """
        Get the current academic term based on date.
        Returns format: "Fall 2025", "Spring 2025", "Summer 2025"
        """
        now = datetime.utcnow()
        year = now.year
        month = now.month

        # Academic calendar (approximate):
        # Spring: January - May
        # Summer: June - July
        # Fall: August - December
        if month <= 5:
            return f"Spring {year}"
        elif month <= 7:
            return f"Summer {year}"
        else:
            return f"Fall {year}"

    def parse_term(self, term: str) -> Tuple[str, int]:
        """
        Parse a term string into (season, year).
        Example: "Fall 2025" -> ("Fall", 2025)
        """
        parts = term.strip().split()
        if len(parts) != 2:
            raise ValueError(f"Invalid term format: {term}. Expected 'Season Year' (e.g., 'Fall 2025')")

        season = parts[0].capitalize()
        if season not in ["Fall", "Spring", "Summer"]:
            raise ValueError(f"Invalid season: {season}. Must be Fall, Spring, or Summer")

        try:
            year = int(parts[1])
        except ValueError:
            raise ValueError(f"Invalid year in term: {parts[1]}")

        return season, year

    def compare_terms(self, term1: str, term2: str) -> int:
        """
        Compare two terms chronologically.
        Returns: -1 if term1 < term2, 0 if equal, 1 if term1 > term2
        """
        season_order = {"Spring": 0, "Summer": 1, "Fall": 2}

        season1, year1 = self.parse_term(term1)
        season2, year2 = self.parse_term(term2)

        if year1 != year2:
            return -1 if year1 < year2 else 1

        return -1 if season_order[season1] < season_order[season2] else (
            0 if season_order[season1] == season_order[season2] else 1
        )

    def is_current_or_future_term(self, term: str) -> bool:
        """Check if a term is the current term or a future term."""
        current = self.get_current_term()
        return self.compare_terms(term, current) >= 0

    def is_current_term(self, term: str) -> bool:
        """Check if a term is exactly the current term."""
        current = self.get_current_term()
        return self.compare_terms(term, current) == 0

    # --- Time Conflict Detection ---

    def _parse_time(self, time_str: str) -> int:
        """Convert time string (HH:MM) to minutes since midnight."""
        if not time_str:
            return 0
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0

    def _days_overlap(self, days1: str, days2: str) -> bool:
        """Check if two meeting day patterns overlap."""
        if not days1 or not days2:
            return False

        # Expand day patterns
        def expand_days(pattern: str) -> set:
            days = set()
            pattern = pattern.upper()
            if "M" in pattern:
                days.add("M")
            if "T" in pattern and "TH" not in pattern and "TR" not in pattern:
                days.add("T")
            if "W" in pattern:
                days.add("W")
            if "TH" in pattern or "TR" in pattern or "R" in pattern:
                days.add("R")
            if "F" in pattern:
                days.add("F")
            # Handle TR pattern (Tuesday/Thursday)
            if pattern == "TR":
                days = {"T", "R"}
            return days

        set1 = expand_days(days1)
        set2 = expand_days(days2)
        return bool(set1 & set2)

    def _times_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        """Check if two time ranges overlap."""
        if not all([start1, end1, start2, end2]):
            return False

        s1 = self._parse_time(start1)
        e1 = self._parse_time(end1)
        s2 = self._parse_time(start2)
        e2 = self._parse_time(end2)

        # Times overlap if one starts before the other ends
        return s1 < e2 and s2 < e1

    def check_time_conflict(
        self,
        user_id: str,
        new_course: Dict[str, Any],
        term: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a new course conflicts with existing courses in the same term.

        Returns the conflicting course if found, None otherwise.
        """
        new_days = new_course.get("meetingDays")
        new_start = new_course.get("startTime")
        new_end = new_course.get("endTime")

        # If no schedule info, can't check conflicts
        if not new_days or not new_start or not new_end:
            return None

        # Get all enrollments for this term (current + planned)
        enrollments = self.get_student_enrollments(user_id)

        for enrollment in enrollments:
            # Only check same term
            if enrollment.get("term") != term:
                continue

            # Skip if no schedule info
            existing_days = enrollment.get("meetingDays")
            existing_start = enrollment.get("startTime")
            existing_end = enrollment.get("endTime")

            if not existing_days or not existing_start or not existing_end:
                continue

            # Check for overlap
            if (self._days_overlap(new_days, existing_days) and
                self._times_overlap(new_start, new_end, existing_start, existing_end)):
                return enrollment

        return None

    # --- Course/Section Validation ---

    def validate_course_section(
        self,
        course_code: str,
        section_number: Optional[str] = None,
        check_seats: bool = True
    ) -> Dict[str, Any]:
        """
        Validate that a course exists and optionally check section availability.

        Args:
            course_code: The course code (e.g., "BUAD 327")
            section_number: Optional section number to validate
            check_seats: Whether to check for available seats

        Returns:
            Course data with section info if found

        Raises:
            CourseNotFoundError: If course doesn't exist
            SectionNotFoundError: If section doesn't exist for course
            NoSeatsAvailableError: If section has no available seats
        """
        from services.firebase import get_course_service

        course_service = get_course_service()
        course = course_service.get_course(course_code)

        if not course:
            raise CourseNotFoundError(
                f"Course '{course_code}' not found in catalog"
            )

        # If no section specified, just return course exists
        if not section_number:
            return course

        # Find the specific section
        sections = course.get("sections", [])
        target_section = None

        for section in sections:
            if section.get("section_number") == section_number:
                target_section = section
                break

        if not target_section:
            available_sections = [s.get("section_number") for s in sections]
            raise SectionNotFoundError(
                f"Section '{section_number}' not found for {course_code}. "
                f"Available sections: {', '.join(available_sections) if available_sections else 'none'}"
            )

        # Check seat availability
        if check_seats:
            seats_available = target_section.get("seats_available", 0)
            if seats_available <= 0:
                raise NoSeatsAvailableError(
                    f"No seats available in {course_code} Section {section_number}",
                    section_info=target_section
                )

        return {
            "course": course,
            "section": target_section
        }

    # --- Student Profile Operations ---

    def get_student(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a student profile by user ID."""
        doc = self.db.collection(self.STUDENTS_COLLECTION).document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None

    def create_student(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new student profile."""
        doc_ref = self.db.collection(self.STUDENTS_COLLECTION).document(user_id)

        student_data = {
            "userId": user_id,
            "name": data.get("name"),  # Required
            "email": data.get("email"),  # Required
            "classYear": data.get("classYear"),  # Required
            "gpa": data.get("gpa"),  # Optional - null for first semester freshmen
            "creditsEarned": data.get("creditsEarned", 0),
            "declared": data.get("declared", False),
            "intendedMajor": data.get("intendedMajor"),  # Optional until declared
            "apCredits": data.get("apCredits"),  # Optional - null if no AP credits
            "holds": data.get("holds", []),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }

        doc_ref.set(student_data)
        student_data["id"] = user_id
        return student_data

    def update_student(self, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing student profile."""
        doc_ref = self.db.collection(self.STUDENTS_COLLECTION).document(user_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        update_data = {k: v for k, v in data.items() if v is not None}
        update_data["updatedAt"] = datetime.utcnow().isoformat()

        doc_ref.update(update_data)

        updated_doc = doc_ref.get()
        result = updated_doc.to_dict()
        result["id"] = user_id
        return result

    def declare_major(self, user_id: str, major: str) -> Optional[Dict[str, Any]]:
        """Declare or update a student's major."""
        return self.update_student(user_id, {
            "intendedMajor": major,
            "declared": True,
            "declaredAt": datetime.utcnow().isoformat()
        })

    # --- Enrollment Operations ---

    def get_student_enrollments(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all enrollments for a student, optionally filtered by status."""
        query = self.db.collection(self.ENROLLMENTS_COLLECTION).where("studentId", "==", user_id)

        if status:
            query = query.where("status", "==", status)

        enrollments = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            enrollments.append(data)

        return enrollments

    def get_student_courses(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get completed, current, and planned courses for a student."""
        enrollments = self.get_student_enrollments(user_id)

        return {
            "completed": [e for e in enrollments if e.get("status") == "completed"],
            "current": [e for e in enrollments if e.get("status") == "enrolled"],
            "planned": [e for e in enrollments if e.get("status") == "planned"]
        }

    def add_enrollment(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a course enrollment for a student.

        Validates:
        - Term must be valid format (e.g., "Fall 2025")
        - Enrolled status: term must be current semester
        - Planned status: term must be current or future semester
        - Course exists in catalog
        - Section exists (if specified)
        - No time conflicts with existing courses in the same term
        - Prerequisites are met (for enrolled/planned courses)

        If a section is full, the enrollment is still added but with
        waitlistRequired=True to indicate the student will need to be
        added to the waitlist.

        Raises:
            InvalidTermError: If term is invalid for the enrollment status
            CourseNotFoundError: If course doesn't exist in catalog
            SectionNotFoundError: If section doesn't exist for course
            ScheduleConflictError: If course conflicts with existing schedule
            PrerequisitesNotMetError: If course prerequisites have not been completed
        """
        status = data.get("status", "planned")
        term = data.get("term")
        course_code = data.get("courseCode")
        section_number = data.get("sectionNumber")

        # Validate term is provided
        if not term:
            raise InvalidTermError("Term is required for enrollment")

        # Validate term format
        try:
            self.parse_term(term)
        except ValueError as e:
            raise InvalidTermError(str(e))

        # Validate term based on enrollment status
        # Note: Course catalog data is only stored for the current term.
        # Future term validation allows planning but course existence
        # can only be verified against current term data.
        if status == "enrolled":
            # Currently enrolled courses must be in the current semester
            if not self.is_current_term(term):
                current = self.get_current_term()
                raise InvalidTermError(
                    f"Enrolled courses must be in the current semester ({current}). "
                    f"Cannot enroll in {term}."
                )
        elif status == "planned":
            # Planned courses must be in current or future semester
            if not self.is_current_or_future_term(term):
                current = self.get_current_term()
                raise InvalidTermError(
                    f"Planned courses must be in current or future semesters. "
                    f"Cannot plan courses for {term} (current: {current})."
                )

        # Validate course and section exist
        # Only check for planned/enrolled courses (not completed - those are historical)
        waitlist_required = False
        if status in ["enrolled", "planned"] and course_code:
            # Don't check seats - we'll handle waitlist separately
            validation_result = self.validate_course_section(
                course_code=course_code,
                section_number=section_number,
                check_seats=False  # Never block on seats
            )
            # Check if waitlist is needed for planned courses with a section
            if status == "planned" and section_number and isinstance(validation_result, dict):
                section = validation_result.get("section")
                if section and section.get("seats_available", 0) <= 0:
                    waitlist_required = True

        # Check for time conflicts (only for enrolled or planned courses with schedule info)
        if status in ["enrolled", "planned"]:
            conflict = self.check_time_conflict(user_id, data, term)
            if conflict:
                raise ScheduleConflictError(
                    f"Time conflict with {conflict.get('courseCode')} "
                    f"({conflict.get('meetingDays')} {conflict.get('startTime')}-{conflict.get('endTime')})",
                    conflicting_course=conflict
                )

        # Check prerequisites (for enrolled or planned courses) - Potential Slight Redundancy (if frontend uses get_eligible_courses)
        if status in ["enrolled", "planned"] and course_code:
            from services.prerequisites import get_prerequisite_engine

            prereq_engine = get_prerequisite_engine()
            completed = prereq_engine.get_student_completed_courses(user_id)
            current = prereq_engine.get_student_current_courses(user_id)
            available_courses = completed.union(current)

            prereqs_met, missing = prereq_engine.check_prerequisites_met(
                course_code, available_courses
            )

            if not prereqs_met:
                raise PrerequisitesNotMetError(
                    f"Cannot enroll in {course_code}: missing prerequisites: {', '.join(missing)}",
                    missing_prerequisites=missing
                )

        enrollment_data = {
            "studentId": user_id,
            "courseCode": data.get("courseCode"),
            "courseName": data.get("courseName"),
            "term": term,
            "grade": data.get("grade"),
            "status": status,
            "credits": data.get("credits", 3),
            # Section scheduling info
            "sectionNumber": data.get("sectionNumber"),  # e.g., "01", "02"
            "meetingDays": data.get("meetingDays"),  # e.g., "MWF", "TR"
            "startTime": data.get("startTime"),  # e.g., "09:00"
            "endTime": data.get("endTime"),  # e.g., "09:50"
            "location": data.get("location"),  # e.g., "Miller Hall 1090"
            "instructor": data.get("instructor"),  # e.g., "Dr. Smith"
            "waitlistRequired": waitlist_required,  # True if section is full
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }

        doc_ref = self.db.collection(self.ENROLLMENTS_COLLECTION).document()
        doc_ref.set(enrollment_data)

        enrollment_data["id"] = doc_ref.id

        # Run validation checks and return warnings (but don't save them yet)
        # User must acknowledge warnings before they are persisted
        validation_warnings = None
        if status in ["enrolled", "planned"]:
            from services.prerequisites import get_prerequisite_engine
            prereq_engine = get_prerequisite_engine()
            validation_warnings = prereq_engine.compute_student_validation_flags(
                user_id, term=term
            )

        enrollment_data["validationWarnings"] = validation_warnings
        return enrollment_data

    def acknowledge_enrollment_warnings(self, user_id: str) -> Dict[str, Any]:
        """
        Acknowledge and save validation warnings for a student's enrollments.

        This should be called after the user has reviewed and accepted
        the validation warnings returned from add_enrollment.

        The warnings are persisted to the student's document so they can be
        shown to advisors and included in chat context.

        Args:
            user_id: The student's ID

        Returns:
            The saved validation flags
        """
        from services.prerequisites import get_prerequisite_engine

        prereq_engine = get_prerequisite_engine()
        return prereq_engine.save_validation_flags(user_id)

    def update_enrollment(self, enrollment_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an enrollment record."""
        doc_ref = self.db.collection(self.ENROLLMENTS_COLLECTION).document(enrollment_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        update_data = {k: v for k, v in data.items() if v is not None}
        update_data["updatedAt"] = datetime.utcnow().isoformat()

        doc_ref.update(update_data)

        updated_doc = doc_ref.get()
        result = updated_doc.to_dict()
        result["id"] = enrollment_id
        return result

    def delete_enrollment(self, enrollment_id: str) -> bool:
        """Delete an enrollment record."""
        doc_ref = self.db.collection(self.ENROLLMENTS_COLLECTION).document(enrollment_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        doc_ref.delete()
        return True

    # --- Milestone Operations ---

    def get_milestones(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get milestones, optionally for a specific student."""
        if user_id:
            query = self.db.collection(self.MILESTONES_COLLECTION).where("studentId", "==", user_id)
        else:
            query = self.db.collection(self.MILESTONES_COLLECTION)

        milestones = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            milestones.append(data)

        return milestones

    def get_degree_milestones(self) -> List[Dict[str, Any]]:
        """Get standard degree milestones (not student-specific)."""
        query = self.db.collection(self.MILESTONES_COLLECTION).where("type", "==", "degree")

        milestones = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            milestones.append(data)

        return milestones

    def get_student_milestone_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """Get milestones with completion status for a student."""
        degree_milestones = self.get_degree_milestones()
        student_milestones = self.get_milestones(user_id)

        student_completed = {m.get("milestoneId") for m in student_milestones if m.get("completed")}

        result = []
        for milestone in degree_milestones:
            milestone_data = milestone.copy()
            milestone_data["completed"] = milestone["id"] in student_completed

            student_specific = next(
                (m for m in student_milestones if m.get("milestoneId") == milestone["id"]),
                None
            )
            if student_specific:
                milestone_data["completedAt"] = student_specific.get("completedAt")
                milestone_data["notes"] = student_specific.get("notes")

            result.append(milestone_data)

        return result

    def update_milestone_progress(
        self, user_id: str, milestone_id: str, completed: bool, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a student's progress on a milestone."""
        query = self.db.collection(self.MILESTONES_COLLECTION)\
            .where("studentId", "==", user_id)\
            .where("milestoneId", "==", milestone_id)\
            .limit(1)

        docs = list(query.stream())

        progress_data = {
            "studentId": user_id,
            "milestoneId": milestone_id,
            "completed": completed,
            "notes": notes,
            "updatedAt": datetime.utcnow().isoformat()
        }

        if completed:
            progress_data["completedAt"] = datetime.utcnow().isoformat()

        if docs:
            doc_ref = docs[0].reference
            doc_ref.update(progress_data)
            progress_data["id"] = doc_ref.id
        else:
            progress_data["createdAt"] = datetime.utcnow().isoformat()
            doc_ref = self.db.collection(self.MILESTONES_COLLECTION).document()
            doc_ref.set(progress_data)
            progress_data["id"] = doc_ref.id

        return progress_data


_student_service: Optional[StudentService] = None


def get_student_service() -> StudentService:
    """Get singleton instance of StudentService."""
    global _student_service
    if _student_service is None:
        initialize_firebase()
        _student_service = StudentService()
    return _student_service
