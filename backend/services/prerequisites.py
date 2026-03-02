"""
Prerequisite Engine Service

Validates course prerequisites, credit limits, and schedule constraints.
Provides schedule validation and risk assessment for student course planning.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

from core.config import get_firestore_client, initialize_firebase
from scrapers.curriculum_scraper import load_curriculum_data, fetch_and_parse_curriculum


class RiskLevel(Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PrerequisiteInfo:
    """Prerequisite information for a course"""
    course_code: str
    course_name: str
    credits: float
    prerequisites: List[str]
    semester_offered: str  # F, S, F/S


@dataclass
class MissingPrerequisite:
    """Details about a missing prerequisite"""
    course_code: str
    missing_prereqs: List[str]
    can_take_concurrently: bool = False


@dataclass
class RiskFlag:
    """A risk flag for schedule validation"""
    type: str  # credit_overload, missing_prereq, workload, etc.
    severity: RiskLevel
    message: str
    course_code: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleScore:
    """Overall schedule quality score"""
    overall: int  # 0-100
    workload: int  # 0-100
    prerequisite_alignment: int  # 0-100
    balance: int  # 0-100
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Complete validation result for a proposed schedule"""
    valid: bool
    warnings: List[str]
    errors: List[str]
    missing_prereqs: Dict[str, List[str]]  # course -> list of missing prereqs
    risk_flags: List[Dict[str, Any]]
    schedule_score: Dict[str, Any]
    total_credits: int
    course_details: List[Dict[str, Any]]


class PrerequisiteEngine:
    """
    Engine for parsing and validating course prerequisites.

    Features:
    - Parse prerequisites from curriculum data
    - Validate prerequisite completion
    - Enforce credit limits (12-18 max, >15 heavy workload warning)
    - Detect missing prerequisites
    - Generate risk flags
    - Calculate schedule scores
    """

    # Credit limit constants
    MIN_CREDITS = 12
    MAX_CREDITS = 18  # Hard cap - anything above is invalid
    CREDITS_WARNING_THRESHOLD = 15  # Above this generates heavy workload warning

    # Collections
    STUDENTS_COLLECTION = "students"
    ENROLLMENTS_COLLECTION = "enrollments"
    COURSES_COLLECTION = "courses"

    def __init__(self):
        self.db = get_firestore_client()
        self._prereq_map: Dict[str, PrerequisiteInfo] = {}
        self._course_credits: Dict[str, float] = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Ensure prerequisite data is loaded"""
        if not self._loaded:
            self._load_prerequisite_data()
            self._loaded = True

    def _load_prerequisite_data(self):
        """Load prerequisite data from curriculum scraper"""
        # Try to load cached data first
        data = load_curriculum_data()

        if not data:
            # Fetch and parse if no cache
            data = fetch_and_parse_curriculum()

        if not data:
            print("Warning: Could not load curriculum data for prerequisites")
            return

        # Build prerequisite map from curriculum data
        self._build_prereq_map(data)

    def _build_prereq_map(self, curriculum_data: Dict[str, Any]):
        """Build prerequisite lookup map from curriculum data"""

        def process_course(course: Dict[str, Any]):
            """Process a single course into the prereq map"""
            code = course.get("code", "")
            if code:
                self._prereq_map[code] = PrerequisiteInfo(
                    course_code=code,
                    course_name=course.get("name", ""),
                    credits=course.get("credits", 3),
                    prerequisites=course.get("prerequisites", []),
                    semester_offered=course.get("semester", "F/S")
                )
                self._course_credits[code] = course.get("credits", 3)

        def process_course_group(group: Dict[str, Any]):
            """Process a course group"""
            for course in group.get("courses", []):
                process_course(course)

        # Process core curriculum
        for group in curriculum_data.get("core_curriculum", []):
            process_course_group(group)

        # Process majors
        for major in curriculum_data.get("majors", []):
            for group in major.get("required_courses", []):
                process_course_group(group)
            for group in major.get("elective_courses", []):
                process_course_group(group)

        # Process concentrations
        for concentration in curriculum_data.get("concentrations", []):
            for group in concentration.get("course_groups", []):
                process_course_group(group)

        # Process prerequisites section
        prereqs = curriculum_data.get("prerequisites")
        if prereqs:
            process_course_group(prereqs)

        print(f"Loaded {len(self._prereq_map)} courses with prerequisite data")

    def get_prerequisites(self, course_code: str) -> Optional[PrerequisiteInfo]:
        """Get prerequisite information for a course"""
        self._ensure_loaded()
        return self._prereq_map.get(course_code)

    def get_all_prerequisites(self) -> Dict[str, PrerequisiteInfo]:
        """Get all prerequisite data"""
        self._ensure_loaded()
        return self._prereq_map.copy()

    def get_course_credits(self, course_code: str) -> float:
        """Get credits for a course"""
        self._ensure_loaded()

        # Check prereq map first
        if course_code in self._course_credits:
            return self._course_credits[course_code]

        # Fall back to Firebase courses collection
        try:
            doc = self.db.collection(self.COURSES_COLLECTION).document(
                course_code.replace(" ", "_")
            ).get()
            if doc.exists:
                return doc.to_dict().get("credits", 3)
        except Exception:
            pass

        return 3  # Default to 3 credits

    def get_course_prerequisites_from_firebase(self, course_code: str) -> Optional[List[str]]:
        """
        Get prerequisites for a course from Firebase.

        This is the primary source for course-specific prerequisites.
        The curriculum scraper should only be used for major/entrance requirements.

        Args:
            course_code: The course code (e.g., "BUAD 323")

        Returns:
            List of prerequisite course codes, or None if course not found
        """
        try:
            doc_id = course_code.replace(" ", "_")
            doc = self.db.collection(self.COURSES_COLLECTION).document(doc_id).get()

            if doc.exists:
                data = doc.to_dict()
                return data.get("prerequisites", [])
        except Exception as e:
            print(f"Error fetching prerequisites from Firebase for {course_code}: {e}")

        return None

    def get_student_completed_courses(self, student_id: str) -> Set[str]:
        """Get set of courses a student has completed"""
        completed = set()

        query = self.db.collection(self.ENROLLMENTS_COLLECTION).where(
            "studentId", "==", student_id
        ).where(
            "status", "==", "completed"
        )

        for doc in query.stream():
            data = doc.to_dict()
            course_code = data.get("courseCode", "")
            if course_code:
                completed.add(course_code)

        return completed

    def get_student_current_courses(self, student_id: str) -> Set[str]:
        """Get set of courses a student is currently enrolled in"""
        current = set()

        query = self.db.collection(self.ENROLLMENTS_COLLECTION).where(
            "studentId", "==", student_id
        ).where(
            "status", "==", "enrolled"
        )

        for doc in query.stream():
            data = doc.to_dict()
            course_code = data.get("courseCode", "")
            if course_code:
                current.add(course_code)

        return current

    def check_prerequisites_met(
        self,
        course_code: str,
        completed_courses: Set[str],
        concurrent_courses: Optional[Set[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Check if prerequisites are met for a specific course.

        Uses Firebase course data as the source for course-specific prerequisites.
        This is separate from major/pathway validation which uses curriculum scraper.

        Args:
            course_code: The course to check
            completed_courses: Set of completed course codes
            concurrent_courses: Optional set of courses being taken concurrently

        Returns:
            Tuple of (prereqs_met: bool, missing_prereqs: list)
        """
        # Build set of all courses the student has access to
        all_courses = completed_courses.copy()
        if concurrent_courses:
            all_courses.update(concurrent_courses)

        # Get prerequisites from Firebase (course catalog data)
        firebase_prereqs = self.get_course_prerequisites_from_firebase(course_code)

        # If course not in Firebase or has no prereqs, allow enrollment
        if firebase_prereqs is None or not firebase_prereqs:
            return True, []

        missing = []
        for prereq in firebase_prereqs:
            # Handle special cases like "Statistics" (could be multiple courses)
            if prereq == "Statistics":
                stats_courses = {"MATH 106", "MATH 351", "BUAD 231"}
                if not any(c in all_courses for c in stats_courses):
                    missing.append(prereq)
            elif prereq not in all_courses:
                missing.append(prereq)

        return len(missing) == 0, missing

    def check_major_pathway(
        self,
        student_id: str,
        major_name: str
    ) -> Dict[str, Any]:
        """
        Check if a student's courses align with their declared major requirements.

        Uses curriculum scraper data to validate overall major pathway.

        Args:
            student_id: The student's ID
            major_name: The declared major (e.g., "Finance", "Accounting")

        Returns:
            Dict with pathway validation results:
            - aligned: bool - True if on track
            - completed_requirements: List of completed major requirements
            - remaining_requirements: List of courses still needed
            - recommendations: List of suggested next courses
        """
        self._ensure_loaded()

        completed = self.get_student_completed_courses(student_id)
        current = self.get_student_current_courses(student_id)
        all_courses = completed.union(current)

        result = {
            "aligned": True,
            "major": major_name,
            "completed_requirements": [],
            "remaining_requirements": [],
            "recommendations": []
        }

        # Find major in curriculum data
        for code, info in self._prereq_map.items():
            # Check if this course is part of the major's requirements
            # This would need curriculum data to have major association
            if code in all_courses:
                result["completed_requirements"].append({
                    "code": code,
                    "name": info.course_name,
                    "credits": info.credits
                })

        return result

    def validate_schedule(
        self,
        student_id: str,
        proposed_courses: List[str]
    ) -> ValidationResult:
        """
        Validate a proposed course schedule for a student.

        Args:
            student_id: The student's ID
            proposed_courses: List of course codes the student wants to take

        Returns:
            ValidationResult with detailed validation information
        """
        self._ensure_loaded()

        # Get student's completed and current courses
        completed = self.get_student_completed_courses(student_id)
        current = self.get_student_current_courses(student_id)

        # Combine for prerequisite checking
        available_courses = completed.union(current)
        proposed_set = set(proposed_courses)

        # Initialize result tracking
        warnings = []
        errors = []
        missing_prereqs = {}
        risk_flags = []
        course_details = []
        total_credits = 0

        # Validate each proposed course
        for course_code in proposed_courses:
            # Get course info
            prereq_info = self._prereq_map.get(course_code)
            credits = self.get_course_credits(course_code)
            total_credits += credits

            # Check if already completed
            if course_code in completed:
                warnings.append(f"{course_code}: Already completed")
                risk_flags.append(asdict(RiskFlag(
                    type="already_completed",
                    severity=RiskLevel.LOW,
                    message=f"You have already completed {course_code}",
                    course_code=course_code
                )))

            # Check if currently enrolled
            if course_code in current:
                warnings.append(f"{course_code}: Currently enrolled")
                risk_flags.append(asdict(RiskFlag(
                    type="currently_enrolled",
                    severity=RiskLevel.LOW,
                    message=f"You are currently enrolled in {course_code}",
                    course_code=course_code
                )))

            # Check prerequisites
            # Allow other proposed courses as concurrent
            other_proposed = proposed_set - {course_code}
            prereqs_met, missing = self.check_prerequisites_met(
                course_code,
                available_courses,
                other_proposed
            )

            if not prereqs_met:
                missing_prereqs[course_code] = missing
                errors.append(f"{course_code}: Missing prerequisites: {', '.join(missing)}")
                risk_flags.append(asdict(RiskFlag(
                    type="missing_prerequisite",
                    severity=RiskLevel.HIGH,
                    message=f"Missing prerequisites for {course_code}: {', '.join(missing)}",
                    course_code=course_code,
                    details={"missing": missing}
                )))

            # Add course details
            course_details.append({
                "code": course_code,
                "name": prereq_info.course_name if prereq_info else "Unknown",
                "credits": credits,
                "prerequisites": prereq_info.prerequisites if prereq_info else [],
                "prerequisites_met": prereqs_met,
                "missing_prerequisites": missing
            })

        # Check credit limits
        credit_risk = self._check_credit_limits(total_credits)
        if credit_risk:
            risk_flags.append(asdict(credit_risk))
            if credit_risk.severity == RiskLevel.CRITICAL:
                # Credit overload makes schedule invalid
                errors.append(credit_risk.message)
            elif credit_risk.severity == RiskLevel.MEDIUM:
                warnings.append(credit_risk.message)

        # Check workload balance
        workload_flags = self._check_workload_balance(proposed_courses, course_details)
        for flag in workload_flags:
            risk_flags.append(asdict(flag))
            warnings.append(flag.message)

        # Calculate schedule score
        score = self._calculate_schedule_score(
            proposed_courses,
            missing_prereqs,
            total_credits,
            course_details
        )

        # Determine overall validity
        valid = len(errors) == 0 and len(missing_prereqs) == 0

        return ValidationResult(
            valid=valid,
            warnings=warnings,
            errors=errors,
            missing_prereqs=missing_prereqs,
            risk_flags=risk_flags,
            schedule_score=asdict(score),
            total_credits=total_credits,
            course_details=course_details
        )

    def _check_credit_limits(self, total_credits: int) -> Optional[RiskFlag]:
        """Check if credit load is within acceptable limits"""

        if total_credits > self.MAX_CREDITS:
            # Hard cap exceeded - this makes schedule invalid
            return RiskFlag(
                type="credit_overload",
                severity=RiskLevel.CRITICAL,
                message=f"Credit load ({total_credits}) exceeds maximum allowed ({self.MAX_CREDITS}). Schedule is invalid.",
                details={
                    "total_credits": total_credits,
                    "max_allowed": self.MAX_CREDITS,
                    "invalid": True
                }
            )
        elif total_credits > self.CREDITS_WARNING_THRESHOLD:
            # Heavy workload warning
            return RiskFlag(
                type="heavy_workload",
                severity=RiskLevel.MEDIUM,
                message=f"Heavy course load ({total_credits} credits). Consider balancing workload.",
                details={"total_credits": total_credits}
            )
        elif total_credits < self.MIN_CREDITS:
            return RiskFlag(
                type="underload",
                severity=RiskLevel.MEDIUM,
                message=f"Below full-time status ({total_credits} credits). Minimum is {self.MIN_CREDITS}.",
                details={
                    "total_credits": total_credits,
                    "minimum": self.MIN_CREDITS
                }
            )

        return None

    def _check_workload_balance(
        self,
        courses: List[str],
        course_details: List[Dict]
    ) -> List[RiskFlag]:
        """Check for workload balance issues"""
        flags = []

        # Check for too many upper-level courses
        upper_level = [c for c in courses if any(c.endswith(str(n)) for n in "456789")]
        if len(upper_level) >= 4:
            flags.append(RiskFlag(
                type="workload_imbalance",
                severity=RiskLevel.MEDIUM,
                message=f"Heavy upper-level load: {len(upper_level)} 400+ level courses",
                details={"upper_level_courses": upper_level}
            ))

        # Check for courses with many prerequisites (complex courses)
        complex_courses = [
            d["code"] for d in course_details
            if len(d.get("prerequisites", [])) >= 2
        ]
        if len(complex_courses) >= 3:
            flags.append(RiskFlag(
                type="complexity_warning",
                severity=RiskLevel.LOW,
                message=f"Multiple courses with complex prerequisites: {', '.join(complex_courses)}",
                details={"complex_courses": complex_courses}
            ))

        return flags

    def _calculate_schedule_score(
        self,
        courses: List[str],
        missing_prereqs: Dict[str, List[str]],
        total_credits: int,
        course_details: List[Dict]
    ) -> ScheduleScore:
        """Calculate an overall schedule quality score"""

        recommendations = []

        # Prerequisite alignment score (0-100)
        if courses:
            prereq_score = int(100 * (len(courses) - len(missing_prereqs)) / len(courses))
        else:
            prereq_score = 100

        if prereq_score < 100:
            recommendations.append("Complete prerequisite courses before attempting advanced courses")

        # Workload score (optimal is 12-15 credits)
        if self.MIN_CREDITS <= total_credits <= self.CREDITS_WARNING_THRESHOLD:
            workload_score = 100
        elif total_credits < self.MIN_CREDITS:
            workload_score = int(100 * total_credits / self.MIN_CREDITS)
            recommendations.append("Consider adding courses to reach full-time status")
        elif total_credits <= self.MAX_CREDITS:
            # Linear decrease from 100 to 70 between 15-18 credits
            workload_score = 100 - int(10 * (total_credits - self.CREDITS_WARNING_THRESHOLD))
            recommendations.append("Heavy course load. Consider balancing workload.")
        else:
            # Above max credits - schedule is invalid
            workload_score = 0
            recommendations.append("Credit load exceeds maximum. Remove courses to continue.")

        # Balance score (variety of course types)
        subject_codes = set(c.split()[0] for c in courses if " " in c)
        if len(subject_codes) >= 3:
            balance_score = 100
        elif len(subject_codes) == 2:
            balance_score = 80
        elif len(subject_codes) == 1 and len(courses) > 2:
            balance_score = 60
            recommendations.append("Consider diversifying your course selection")
        else:
            balance_score = 70

        # Overall score (weighted average)
        overall = int(
            prereq_score * 0.4 +
            workload_score * 0.35 +
            balance_score * 0.25
        )

        if overall >= 90:
            recommendations.insert(0, "Excellent schedule! Well balanced with proper prerequisites.")
        elif overall >= 70:
            recommendations.insert(0, "Good schedule with minor adjustments recommended.")
        else:
            recommendations.insert(0, "Schedule needs attention. Review warnings and errors.")

        return ScheduleScore(
            overall=overall,
            workload=workload_score,
            prerequisite_alignment=prereq_score,
            balance=balance_score,
            recommendations=recommendations
        )

    def get_eligible_courses(self, student_id: str) -> List[Dict[str, Any]]:
        """Get all courses a student is eligible to take based on prerequisites"""
        self._ensure_loaded()

        completed = self.get_student_completed_courses(student_id)
        current = self.get_student_current_courses(student_id)
        available = completed.union(current)

        eligible = []

        for code, info in self._prereq_map.items():
            # Skip if already completed or enrolled
            if code in available:
                continue

            prereqs_met, missing = self.check_prerequisites_met(code, available)

            if prereqs_met:
                eligible.append({
                    "code": code,
                    "name": info.course_name,
                    "credits": info.credits,
                    "semester_offered": info.semester_offered,
                    "prerequisites": info.prerequisites
                })

        # Sort by course code
        eligible.sort(key=lambda x: x["code"])

        return eligible

    def get_all_courses_with_eligibility(self, student_id: str) -> List[Dict[str, Any]]:
        """
        Get ALL courses with eligibility status for a student.

        Returns all known courses with:
        - eligible: True if student can take it (prereqs met, not already taken)
        - status: 'eligible', 'completed', 'enrolled', 'missing_prereqs'
        - missing_prerequisites: List of missing prereqs if any

        This is useful for the UI to show all courses and indicate which are available.
        """
        self._ensure_loaded()

        completed = self.get_student_completed_courses(student_id)
        current = self.get_student_current_courses(student_id)
        available = completed.union(current)

        all_courses = []

        for code, info in self._prereq_map.items():
            course_data = {
                "code": code,
                "name": info.course_name,
                "credits": info.credits,
                "semester_offered": info.semester_offered,
                "prerequisites": info.prerequisites,
                "eligible": False,
                "status": "unknown",
                "missing_prerequisites": []
            }

            # Check status
            if code in completed:
                course_data["status"] = "completed"
                course_data["eligible"] = False
            elif code in current:
                course_data["status"] = "enrolled"
                course_data["eligible"] = False
            else:
                # Check prerequisites
                prereqs_met, missing = self.check_prerequisites_met(code, available)

                if prereqs_met:
                    course_data["status"] = "eligible"
                    course_data["eligible"] = True
                else:
                    course_data["status"] = "missing_prereqs"
                    course_data["eligible"] = False
                    course_data["missing_prerequisites"] = missing

            all_courses.append(course_data)

        # Sort by course code
        all_courses.sort(key=lambda x: x["code"])

        return all_courses

    def get_courses_by_status(self, student_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get courses grouped by eligibility status.

        Returns:
        {
            "eligible": [...],       # Can take now
            "completed": [...],      # Already finished
            "enrolled": [...],       # Currently taking
            "missing_prereqs": [...] # Need more prereqs first
        }
        """
        all_courses = self.get_all_courses_with_eligibility(student_id)

        grouped = {
            "eligible": [],
            "completed": [],
            "enrolled": [],
            "missing_prereqs": []
        }

        for course in all_courses:
            status = course.get("status", "unknown")
            if status in grouped:
                grouped[status].append(course)

        return grouped

    def get_prerequisite_chain(self, course_code: str) -> Dict[str, Any]:
        """Get the full prerequisite chain for a course"""
        self._ensure_loaded()

        def build_chain(code: str, visited: Set[str]) -> Dict[str, Any]:
            if code in visited:
                return {"code": code, "circular": True}

            visited.add(code)
            info = self._prereq_map.get(code)

            result = {
                "code": code,
                "name": info.course_name if info else "Unknown",
                "credits": info.credits if info else 3,
                "prerequisites": []
            }

            if info and info.prerequisites:
                for prereq in info.prerequisites:
                    result["prerequisites"].append(
                        build_chain(prereq, visited.copy())
                    )

            return result

        return build_chain(course_code, set())

    def compute_student_validation_flags(self, student_id: str, term: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute validation flags for a student's current/planned enrollments.

        This runs credit limit checks, workload balance, and generates warnings
        that should be displayed to students and advisors.

        Note: Prerequisites are checked at enrollment time and block invalid enrollments.
        These flags are for advisory warnings that don't block enrollment.

        Args:
            student_id: The student's ID
            term: Optional term to filter enrollments (defaults to all current/planned)

        Returns:
            Dict with validation results including flags, warnings, and score
        """
        self._ensure_loaded()

        # Get student's enrollments
        enrollments = []
        query = self.db.collection(self.ENROLLMENTS_COLLECTION).where(
            "studentId", "==", student_id
        )

        for doc in query.stream():
            data = doc.to_dict()
            status = data.get("status", "")
            # Only check current and planned courses
            if status in ["enrolled", "planned"]:
                if term is None or data.get("term") == term:
                    enrollments.append(data)

        if not enrollments:
            return {
                "flags": [],
                "warnings": [],
                "total_credits": 0,
                "schedule_score": None
            }

        # Group enrollments by term
        by_term: Dict[str, List[Dict]] = {}
        for enrollment in enrollments:
            t = enrollment.get("term", "Unknown")
            if t not in by_term:
                by_term[t] = []
            by_term[t].append(enrollment)

        all_flags = []
        all_warnings = []

        # Validate each term's schedule
        for term_name, term_enrollments in by_term.items():
            course_codes = [e.get("courseCode") for e in term_enrollments if e.get("courseCode")]
            total_credits = sum(self.get_course_credits(c) for c in course_codes)

            # Check credit limits
            credit_flag = self._check_credit_limits(total_credits)
            if credit_flag:
                flag_dict = asdict(credit_flag)
                flag_dict["term"] = term_name
                all_flags.append(flag_dict)
                if credit_flag.severity in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    all_warnings.append(f"{term_name}: {credit_flag.message}")

            # Check workload balance
            course_details = []
            for code in course_codes:
                info = self._prereq_map.get(code)
                course_details.append({
                    "code": code,
                    "name": info.course_name if info else "Unknown",
                    "credits": self.get_course_credits(code),
                    "prerequisites": info.prerequisites if info else []
                })

            workload_flags = self._check_workload_balance(course_codes, course_details)
            for flag in workload_flags:
                flag_dict = asdict(flag)
                flag_dict["term"] = term_name
                all_flags.append(flag_dict)
                all_warnings.append(f"{term_name}: {flag.message}")

        # Calculate overall schedule score for current term
        current_term_courses = []
        for enrollment in enrollments:
            if enrollment.get("status") == "enrolled":
                code = enrollment.get("courseCode")
                if code:
                    current_term_courses.append(code)

        schedule_score = None
        if current_term_courses:
            total_credits = sum(self.get_course_credits(c) for c in current_term_courses)
            course_details = []
            for code in current_term_courses:
                info = self._prereq_map.get(code)
                course_details.append({
                    "code": code,
                    "prerequisites": info.prerequisites if info else []
                })
            schedule_score = asdict(self._calculate_schedule_score(
                current_term_courses,
                {},  # No missing prereqs - those are blocked at enrollment
                total_credits,
                course_details
            ))

        return {
            "flags": all_flags,
            "warnings": all_warnings,
            "total_credits_by_term": {
                t: sum(self.get_course_credits(e.get("courseCode", "")) for e in courses)
                for t, courses in by_term.items()
            },
            "schedule_score": schedule_score
        }

    def save_validation_flags(self, student_id: str) -> Dict[str, Any]:
        """
        Compute and save validation flags for a student.

        Stores flags in the student's document for quick retrieval.

        Returns:
            The computed validation flags
        """
        flags = self.compute_student_validation_flags(student_id)

        # Save to student document
        try:
            self.db.collection(self.STUDENTS_COLLECTION).document(student_id).update({
                "validationFlags": flags,
                "validationFlagsUpdatedAt": datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"Warning: Could not save validation flags for {student_id}: {e}")

        return flags

    def get_saved_validation_flags(self, student_id: str) -> Optional[Dict[str, Any]]:
        """
        Get previously saved validation flags for a student.

        Returns None if no flags have been saved.
        """
        try:
            doc = self.db.collection(self.STUDENTS_COLLECTION).document(student_id).get()
            if doc.exists:
                data = doc.to_dict()
                return data.get("validationFlags")
        except Exception as e:
            print(f"Warning: Could not get validation flags for {student_id}: {e}")

        return None


# Singleton instance
_prerequisite_engine: Optional[PrerequisiteEngine] = None


def get_prerequisite_engine() -> PrerequisiteEngine:
    """Get singleton instance of PrerequisiteEngine"""
    global _prerequisite_engine
    if _prerequisite_engine is None:
        initialize_firebase()
        _prerequisite_engine = PrerequisiteEngine()
    return _prerequisite_engine
