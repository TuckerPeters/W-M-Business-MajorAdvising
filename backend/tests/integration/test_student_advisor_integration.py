"""
Integration tests for Student and Advisor services with real Firebase.

These tests create actual data in Firebase and clean up after.
Run with: pytest tests/integration/ -v -m integration
"""

import pytest
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from firebase_admin import auth

# Mark all tests in this module as integration and firebase tests
pytestmark = [pytest.mark.integration, pytest.mark.firebase]

from services.student import (
    StudentService, get_student_service,
    InvalidTermError, ScheduleConflictError,
    CourseNotFoundError, SectionNotFoundError
)
from services.advisor import AdvisorService, get_advisor_service
from services.firebase import get_course_service
from core.config import initialize_firebase, get_firestore_client


# Test data prefix to identify test records
TEST_PREFIX = "TEST_INTEGRATION_"

# Test user credentials
TEST_STUDENT_EMAIL = "test.student.integration@wm.edu"
TEST_STUDENT_PASSWORD = "TestStudent123!"
TEST_ADVISOR_EMAIL = "test.advisor.integration@wm.edu"
TEST_ADVISOR_PASSWORD = "TestAdvisor123!"


def generate_test_id():
    """Generate a unique test ID."""
    return f"{TEST_PREFIX}{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def firebase_db():
    """Initialize Firebase and return the Firestore client."""
    initialize_firebase()
    return get_firestore_client()


def create_or_get_auth_user(email: str, password: str, display_name: str) -> str:
    """Create a Firebase Auth user or get existing one. Returns uid."""
    try:
        # Try to get existing user
        user = auth.get_user_by_email(email)
        return user.uid
    except auth.UserNotFoundError:
        # Create new user
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=True
        )
        return user.uid


def delete_auth_user_if_exists(uid: str):
    """Delete a Firebase Auth user if they exist."""
    try:
        auth.delete_user(uid)
    except auth.UserNotFoundError:
        pass
    except Exception as e:
        print(f"Warning: Failed to delete auth user {uid}: {e}")


@pytest.fixture(scope="module")
def test_student_auth_user(firebase_db):
    """
    Create a test student user in Firebase Auth.
    Returns tuple of (uid, email).
    """
    uid = create_or_get_auth_user(
        email=TEST_STUDENT_EMAIL,
        password=TEST_STUDENT_PASSWORD,
        display_name="Integration Test Student"
    )

    yield (uid, TEST_STUDENT_EMAIL)

    # Cleanup: Delete auth user
    delete_auth_user_if_exists(uid)


@pytest.fixture(scope="module")
def test_advisor_auth_user(firebase_db):
    """
    Create a test advisor user in Firebase Auth with advisor custom claims.
    Returns tuple of (uid, email).
    """
    uid = create_or_get_auth_user(
        email=TEST_ADVISOR_EMAIL,
        password=TEST_ADVISOR_PASSWORD,
        display_name="Integration Test Advisor"
    )

    # Set advisor custom claims
    auth.set_custom_user_claims(uid, {"advisor": True})

    yield (uid, TEST_ADVISOR_EMAIL)

    # Cleanup: Delete auth user
    delete_auth_user_if_exists(uid)


@pytest.fixture(scope="module")
def student_service(firebase_db):
    """Get StudentService instance."""
    return StudentService()


@pytest.fixture(scope="module")
def advisor_service(firebase_db):
    """Get AdvisorService instance."""
    return AdvisorService()


@pytest.fixture(scope="module")
def course_service(firebase_db):
    """Get FirebaseCourseService instance for real course data."""
    return get_course_service()


@pytest.fixture(scope="module")
def real_courses(course_service) -> Dict[str, Any]:
    """
    Get real courses from Firebase for testing.

    Returns a dict with different course codes for testing:
    - course1, course2: Two different courses for conflict tests
    - course_with_sections: A course that has sections
    """
    # Get all subjects to find available courses
    subjects = course_service.get_all_subjects()

    if not subjects:
        pytest.skip("No courses found in Firebase - run populate task first")

    # Try to get BUAD courses first (most common for business school)
    test_courses = []
    for subject in ["BUAD", "ACCT", "FINA", "MKTG"] + subjects[:5]:
        courses = course_service.get_courses_by_subject(subject)
        for course in courses:
            if course.get("course_code"):
                test_courses.append(course)
                if len(test_courses) >= 3:
                    break
        if len(test_courses) >= 3:
            break

    if len(test_courses) < 2:
        pytest.skip("Not enough courses in Firebase for testing")

    return {
        "course1": test_courses[0],
        "course2": test_courses[1] if len(test_courses) > 1 else test_courses[0],
        "course_with_sections": next(
            (c for c in test_courses if c.get("sections")),
            test_courses[0]
        )
    }


@pytest.fixture(scope="module")
def test_students(student_service):
    """Create test students and clean up after tests."""
    created_ids = []

    # Create test students
    students_data = [
        {
            "id": generate_test_id(),
            "name": "Test Student One",
            "email": "teststudent1@wm.edu",
            "classYear": 2027,
            "gpa": 3.5,
            "creditsEarned": 45,
            "declared": True,
            "intendedMajor": "Finance"
        },
        {
            "id": generate_test_id(),
            "name": "Test Student Two",
            "email": "teststudent2@wm.edu",
            "classYear": 2028,
            "gpa": None,  # First semester freshman
            "creditsEarned": 0,
            "declared": False,
            "intendedMajor": None,
            "apCredits": None
        },
        {
            "id": generate_test_id(),
            "name": "Test Student Low GPA",
            "email": "teststudent3@wm.edu",
            "classYear": 2026,
            "gpa": 1.8,  # Below 2.0 - should trigger alert
            "creditsEarned": 90,
            "declared": False,  # Undeclared senior - should trigger alert
            "intendedMajor": None,
            "holds": ["Academic Hold"]  # Has hold - should trigger alert
        }
    ]

    created_students = []
    for data in students_data:
        student_id = data.pop("id")
        student = student_service.create_student(student_id, data)
        created_ids.append(student_id)
        created_students.append(student)

    yield created_students

    # Cleanup: Delete all test students
    db = get_firestore_client()
    for student_id in created_ids:
        try:
            db.collection("students").document(student_id).delete()
        except Exception as e:
            print(f"Warning: Failed to delete student {student_id}: {e}")


@pytest.fixture(scope="module")
def test_advisor_id():
    """Generate a test advisor ID."""
    return generate_test_id()


@pytest.fixture(scope="module")
def cleanup_advisor_data(test_advisor_id, test_students):
    """Clean up advisor-related data after tests."""
    yield

    # Cleanup: Delete all test assignments and notes
    db = get_firestore_client()

    # Delete assignments
    assignments = db.collection("advisor_assignments").where(
        "advisorId", "==", test_advisor_id
    ).stream()
    for doc in assignments:
        doc.reference.delete()

    # Delete notes
    notes = db.collection("advisor_notes").where(
        "advisorId", "==", test_advisor_id
    ).stream()
    for doc in notes:
        doc.reference.delete()


class TestStudentIntegration:
    """Integration tests for StudentService."""

    def test_create_and_get_student(self, student_service, test_students):
        """Should create student and retrieve it."""
        student = test_students[0]
        student_id = student["id"]

        retrieved = student_service.get_student(student_id)

        assert retrieved is not None
        assert retrieved["name"] == "Test Student One"
        assert retrieved["email"] == "teststudent1@wm.edu"
        assert retrieved["gpa"] == 3.5

    def test_student_with_null_fields(self, student_service, test_students):
        """Should handle null fields correctly."""
        student = test_students[1]
        student_id = student["id"]

        retrieved = student_service.get_student(student_id)

        assert retrieved is not None
        assert retrieved["gpa"] is None
        assert retrieved["intendedMajor"] is None
        assert retrieved["declared"] is False

    def test_update_student(self, student_service, test_students):
        """Should update student profile."""
        student = test_students[1]
        student_id = student["id"]

        # Update GPA (first semester ended)
        updated = student_service.update_student(student_id, {"gpa": 3.2})

        assert updated is not None
        assert updated["gpa"] == 3.2

        # Verify persistence
        retrieved = student_service.get_student(student_id)
        assert retrieved["gpa"] == 3.2

    def test_declare_major(self, student_service, test_students):
        """Should declare major for student."""
        student = test_students[1]
        student_id = student["id"]

        updated = student_service.declare_major(student_id, "Accounting")

        assert updated is not None
        assert updated["intendedMajor"] == "Accounting"
        assert updated["declared"] is True
        assert "declaredAt" in updated

    def test_add_enrollment(self, student_service, test_students):
        """Should add course enrollment."""
        student = test_students[0]
        student_id = student["id"]

        enrollment = student_service.add_enrollment(student_id, {
            "courseCode": "BUAD 203",
            "term": "Fall 2020",  # Past term with completed status skips validation
            "status": "completed",
            "grade": "A",
            "credits": 3
        })

        assert enrollment is not None
        assert enrollment["courseCode"] == "BUAD 203"
        assert enrollment["id"] is not None

        # Cleanup
        student_service.delete_enrollment(enrollment["id"])

    def test_get_student_courses(self, student_service, test_students, real_courses):
        """Should get courses grouped by status using real Firebase course data."""
        student = test_students[0]
        student_id = student["id"]

        # Use real courses from Firebase
        course1 = real_courses["course1"]
        course2 = real_courses["course2"]

        current_term = student_service.get_current_term()

        # Add test enrollments
        completed = student_service.add_enrollment(student_id, {
            "courseCode": "HIST 101",  # Completed courses skip validation
            "term": "Fall 2020",  # Past term - completed skips validation
            "status": "completed",
            "grade": "B+"
        })

        # Use real course codes for enrolled/planned (these are validated)
        current = student_service.add_enrollment(student_id, {
            "courseCode": course1["course_code"],
            "term": current_term,
            "status": "enrolled"
        })
        planned = student_service.add_enrollment(student_id, {
            "courseCode": course2["course_code"],
            "term": "Fall 2030",  # Future term
            "status": "planned"
        })

        courses = student_service.get_student_courses(student_id)

        assert "completed" in courses
        assert "current" in courses
        assert "planned" in courses

        # Cleanup
        student_service.delete_enrollment(completed["id"])
        student_service.delete_enrollment(current["id"])
        student_service.delete_enrollment(planned["id"])


class TestAdvisorIntegration:
    """Integration tests for AdvisorService."""

    def test_assign_advisee(self, advisor_service, test_students, test_advisor_id, cleanup_advisor_data):
        """Should assign student to advisor."""
        student = test_students[0]
        student_id = student["id"]

        assignment = advisor_service.assign_advisee(test_advisor_id, student_id)

        assert assignment is not None
        assert assignment["advisorId"] == test_advisor_id
        assert assignment["studentId"] == student_id
        assert "assignedDate" in assignment

    def test_get_advisees(self, advisor_service, test_students, test_advisor_id, cleanup_advisor_data):
        """Should get all advisees for advisor."""
        # Assign multiple students
        for student in test_students:
            advisor_service.assign_advisee(test_advisor_id, student["id"])

        advisees = advisor_service.get_advisees(test_advisor_id)

        assert len(advisees) >= len(test_students)

    def test_get_advisee_details(self, advisor_service, test_students, test_advisor_id, cleanup_advisor_data):
        """Should get specific advisee details."""
        student = test_students[0]
        student_id = student["id"]

        # Ensure assigned
        advisor_service.assign_advisee(test_advisor_id, student_id)

        advisee = advisor_service.get_advisee(test_advisor_id, student_id)

        assert advisee is not None
        assert advisee["userId"] == student_id
        assert advisee["name"] == "Test Student One"

    def test_create_and_get_notes(self, advisor_service, test_students, test_advisor_id, cleanup_advisor_data):
        """Should create and retrieve notes."""
        student = test_students[0]
        student_id = student["id"]

        # Ensure assigned
        advisor_service.assign_advisee(test_advisor_id, student_id)

        # Create note
        note = advisor_service.create_note(
            test_advisor_id,
            student_id,
            "Student is making great progress toward graduation.",
            "private"
        )

        assert note is not None
        assert note["note"] == "Student is making great progress toward graduation."
        assert note["visibility"] == "private"

        # Get notes
        notes = advisor_service.get_notes(test_advisor_id, student_id)
        assert len(notes) >= 1

    def test_update_note(self, advisor_service, test_students, test_advisor_id, cleanup_advisor_data):
        """Should update existing note."""
        student = test_students[0]
        student_id = student["id"]

        # Create note
        note = advisor_service.create_note(
            test_advisor_id,
            student_id,
            "Original note content",
            "private"
        )

        # Update note
        updated = advisor_service.update_note(
            test_advisor_id,
            note["id"],
            note="Updated note content",
            visibility="shared"
        )

        assert updated is not None
        assert updated["note"] == "Updated note content"
        assert updated["visibility"] == "shared"

    def test_delete_note(self, advisor_service, test_students, test_advisor_id, cleanup_advisor_data):
        """Should delete note."""
        student = test_students[0]
        student_id = student["id"]

        # Create note
        note = advisor_service.create_note(
            test_advisor_id,
            student_id,
            "Note to be deleted",
            "private"
        )

        # Delete note
        result = advisor_service.delete_note(test_advisor_id, note["id"])
        assert result is True

        # Verify deleted
        notes = advisor_service.get_notes(test_advisor_id, student_id)
        note_ids = [n["id"] for n in notes]
        assert note["id"] not in note_ids

    def test_get_alerts(self, advisor_service, test_students, test_advisor_id, cleanup_advisor_data):
        """Should get alerts for advisees with issues."""
        # Assign all students including one with problems
        for student in test_students:
            advisor_service.assign_advisee(test_advisor_id, student["id"])

        alerts = advisor_service.get_alerts(test_advisor_id)

        # Should have alerts for student with low GPA, hold, and undeclared status
        assert len(alerts) >= 1

        alert_types = [a["type"] for a in alerts]
        # Student 3 has: low GPA, hold, undeclared senior
        assert "gpa" in alert_types or "hold" in alert_types or "declaration" in alert_types

    def test_remove_advisee(self, advisor_service, test_students, test_advisor_id, cleanup_advisor_data):
        """Should remove advisee from advisor."""
        student = test_students[0]
        student_id = student["id"]

        # Ensure assigned
        advisor_service.assign_advisee(test_advisor_id, student_id)

        # Remove
        result = advisor_service.remove_advisee(test_advisor_id, student_id)
        assert result is True

        # Verify removed
        advisee = advisor_service.get_advisee(test_advisor_id, student_id)
        assert advisee is None


class TestStudentAdvisorWorkflow:
    """Integration tests for complete student-advisor workflow."""

    def test_complete_workflow(self, student_service, advisor_service, firebase_db, real_courses):
        """Test complete workflow: create student, assign to advisor, add notes, cleanup."""
        # Generate unique IDs for this test
        student_id = generate_test_id()
        advisor_id = generate_test_id()

        # Use real course from Firebase
        real_course = real_courses["course1"]

        try:
            # 1. Create student profile
            student = student_service.create_student(student_id, {
                "name": "Workflow Test Student",
                "email": "workflow@wm.edu",
                "classYear": 2027,
                "gpa": 3.0,
                "declared": False
            })
            assert student is not None

            # 2. Advisor assigns student
            assignment = advisor_service.assign_advisee(advisor_id, student_id)
            assert assignment is not None

            # 3. Advisor views advisee
            advisee = advisor_service.get_advisee(advisor_id, student_id)
            assert advisee is not None
            assert advisee["name"] == "Workflow Test Student"

            # 4. Advisor adds note
            note = advisor_service.create_note(
                advisor_id, student_id,
                "Initial meeting - discussed major options",
                "private"
            )
            assert note is not None

            # 5. Student declares major
            updated_student = student_service.declare_major(student_id, "Marketing")
            assert updated_student["declared"] is True

            # 6. Advisor updates note
            updated_note = advisor_service.update_note(
                advisor_id, note["id"],
                note="Student declared Marketing major after our discussion"
            )
            assert updated_note is not None

            # 7. Add enrollment using real course from Firebase
            enrollment = student_service.add_enrollment(student_id, {
                "courseCode": real_course["course_code"],
                "term": "Fall 2030",  # Future term
                "status": "planned"
            })
            assert enrollment is not None

            # 8. Check courses
            courses = student_service.get_student_courses(student_id)
            assert len(courses["planned"]) >= 1

        finally:
            # Cleanup
            db = firebase_db

            # Delete enrollments
            enrollments = db.collection("enrollments").where(
                "studentId", "==", student_id
            ).stream()
            for doc in enrollments:
                doc.reference.delete()

            # Delete notes
            notes = db.collection("advisor_notes").where(
                "advisorId", "==", advisor_id
            ).stream()
            for doc in notes:
                doc.reference.delete()

            # Delete assignment
            assignments = db.collection("advisor_assignments").where(
                "advisorId", "==", advisor_id
            ).stream()
            for doc in assignments:
                doc.reference.delete()

            # Delete student
            db.collection("students").document(student_id).delete()


class TestFirebaseAuthUsers:
    """Integration tests for Firebase Auth user creation and role management."""

    def test_create_student_auth_user(self, test_student_auth_user):
        """Should create a student user in Firebase Auth."""
        uid, email = test_student_auth_user

        # Verify user exists
        user = auth.get_user(uid)

        assert user is not None
        assert user.email == TEST_STUDENT_EMAIL
        assert user.display_name == "Integration Test Student"
        assert user.email_verified is True

    def test_create_advisor_auth_user(self, test_advisor_auth_user):
        """Should create an advisor user in Firebase Auth with custom claims."""
        uid, email = test_advisor_auth_user

        # Verify user exists
        user = auth.get_user(uid)

        assert user is not None
        assert user.email == TEST_ADVISOR_EMAIL
        assert user.display_name == "Integration Test Advisor"

        # Verify advisor custom claims
        assert user.custom_claims is not None
        assert user.custom_claims.get("advisor") is True

    def test_student_has_no_advisor_claims(self, test_student_auth_user):
        """Student user should not have advisor claims."""
        uid, _ = test_student_auth_user

        user = auth.get_user(uid)

        # Student should not have advisor claims
        if user.custom_claims:
            assert user.custom_claims.get("advisor") is not True
            assert user.custom_claims.get("admin") is not True

    def test_can_set_admin_claims(self, firebase_db):
        """Should be able to set admin claims on a user."""
        # Create temporary admin user
        admin_email = f"test.admin.{uuid.uuid4().hex[:8]}@wm.edu"
        admin_uid = None

        try:
            admin_uid = create_or_get_auth_user(
                email=admin_email,
                password="TestAdmin123!",
                display_name="Test Admin User"
            )

            # Set admin claims
            auth.set_custom_user_claims(admin_uid, {"admin": True})

            # Verify claims
            user = auth.get_user(admin_uid)
            assert user.custom_claims is not None
            assert user.custom_claims.get("admin") is True

        finally:
            if admin_uid:
                delete_auth_user_if_exists(admin_uid)


class TestAuthenticatedWorkflow:
    """Integration tests for complete authenticated workflow."""

    def test_student_creates_own_profile(
        self, test_student_auth_user, student_service, firebase_db
    ):
        """Student should be able to create their own profile."""
        uid, email = test_student_auth_user

        try:
            # Create student profile using their auth uid
            student = student_service.create_student(uid, {
                "name": "Auth Test Student",
                "email": email,
                "classYear": 2027,
                "gpa": 3.5,
                "declared": False
            })

            assert student is not None
            assert student["userId"] == uid
            assert student["email"] == email

            # Verify can retrieve
            retrieved = student_service.get_student(uid)
            assert retrieved is not None
            assert retrieved["name"] == "Auth Test Student"

        finally:
            # Cleanup
            firebase_db.collection("students").document(uid).delete()

    def test_advisor_manages_student(
        self,
        test_student_auth_user,
        test_advisor_auth_user,
        student_service,
        advisor_service,
        firebase_db
    ):
        """Advisor should be able to manage student as advisee."""
        student_uid, student_email = test_student_auth_user
        advisor_uid, advisor_email = test_advisor_auth_user

        try:
            # Create student profile
            student = student_service.create_student(student_uid, {
                "name": "Advisee Test Student",
                "email": student_email,
                "classYear": 2027,
                "declared": False
            })

            # Advisor assigns student
            assignment = advisor_service.assign_advisee(advisor_uid, student_uid)
            assert assignment is not None
            assert assignment["advisorId"] == advisor_uid
            assert assignment["studentId"] == student_uid

            # Advisor views advisee
            advisee = advisor_service.get_advisee(advisor_uid, student_uid)
            assert advisee is not None
            assert advisee["name"] == "Advisee Test Student"

            # Advisor adds note
            note = advisor_service.create_note(
                advisor_uid, student_uid,
                "Auth workflow test note",
                "private"
            )
            assert note is not None

            # Advisor gets notes
            notes = advisor_service.get_notes(advisor_uid, student_uid)
            assert len(notes) >= 1

        finally:
            # Cleanup
            db = firebase_db

            # Delete notes
            notes = db.collection("advisor_notes").where(
                "advisorId", "==", advisor_uid
            ).stream()
            for doc in notes:
                doc.reference.delete()

            # Delete assignments
            assignments = db.collection("advisor_assignments").where(
                "advisorId", "==", advisor_uid
            ).stream()
            for doc in assignments:
                doc.reference.delete()

            # Delete student
            db.collection("students").document(student_uid).delete()

    def test_complete_auth_workflow(
        self,
        student_service,
        advisor_service,
        firebase_db,
        real_courses
    ):
        """Test complete workflow with freshly created auth users."""
        # Generate unique emails for this test
        unique_id = uuid.uuid4().hex[:8]
        student_email = f"workflow.student.{unique_id}@wm.edu"
        advisor_email = f"workflow.advisor.{unique_id}@wm.edu"

        # Use real course from Firebase
        real_course = real_courses["course1"]

        student_uid = None
        advisor_uid = None

        try:
            # 1. Create student auth user
            student_uid = create_or_get_auth_user(
                email=student_email,
                password="WorkflowStudent123!",
                display_name="Workflow Test Student"
            )
            assert student_uid is not None

            # Verify student user
            student_user = auth.get_user(student_uid)
            assert student_user.email == student_email

            # 2. Create advisor auth user with claims
            advisor_uid = create_or_get_auth_user(
                email=advisor_email,
                password="WorkflowAdvisor123!",
                display_name="Workflow Test Advisor"
            )
            auth.set_custom_user_claims(advisor_uid, {"advisor": True})

            # Verify advisor claims
            advisor_user = auth.get_user(advisor_uid)
            assert advisor_user.custom_claims.get("advisor") is True

            # 3. Student creates profile
            student = student_service.create_student(student_uid, {
                "name": "Workflow Test Student",
                "email": student_email,
                "classYear": 2027,
                "gpa": 3.2,
                "declared": False
            })
            assert student["userId"] == student_uid

            # 4. Advisor assigns student
            assignment = advisor_service.assign_advisee(advisor_uid, student_uid)
            assert assignment["studentId"] == student_uid

            # 5. Student declares major
            updated = student_service.declare_major(student_uid, "Finance")
            assert updated["declared"] is True
            assert updated["intendedMajor"] == "Finance"

            # 6. Advisor views and adds note
            advisee = advisor_service.get_advisee(advisor_uid, student_uid)
            assert advisee["intendedMajor"] == "Finance"

            note = advisor_service.create_note(
                advisor_uid, student_uid,
                "Student declared Finance major!",
                "shared"
            )
            assert note["visibility"] == "shared"

            # 7. Student adds enrollment using real course from Firebase
            current_term = student_service.get_current_term()
            enrollment = student_service.add_enrollment(student_uid, {
                "courseCode": real_course["course_code"],
                "term": current_term,
                "status": "enrolled"
            })
            assert enrollment["courseCode"] == real_course["course_code"]

            # 8. Verify complete state
            final_student = student_service.get_student(student_uid)
            assert final_student["declared"] is True

            courses = student_service.get_student_courses(student_uid)
            assert len(courses["current"]) >= 1

        finally:
            # Cleanup
            db = firebase_db

            if student_uid:
                # Delete enrollments
                enrollments = db.collection("enrollments").where(
                    "studentId", "==", student_uid
                ).stream()
                for doc in enrollments:
                    doc.reference.delete()

                # Delete student
                db.collection("students").document(student_uid).delete()

                # Delete auth user
                delete_auth_user_if_exists(student_uid)

            if advisor_uid:
                # Delete notes
                notes = db.collection("advisor_notes").where(
                    "advisorId", "==", advisor_uid
                ).stream()
                for doc in notes:
                    doc.reference.delete()

                # Delete assignments
                assignments = db.collection("advisor_assignments").where(
                    "advisorId", "==", advisor_uid
                ).stream()
                for doc in assignments:
                    doc.reference.delete()

                # Delete auth user
                delete_auth_user_if_exists(advisor_uid)


class TestEnrollmentValidationIntegration:
    """Integration tests for enrollment validation errors using real Firebase course data."""

    def test_add_enrollment_invalid_term_format(self, student_service, test_students, real_courses):
        """Should raise InvalidTermError for bad term format."""
        student = test_students[0]
        student_id = student["id"]
        course_code = real_courses["course1"]["course_code"]

        with pytest.raises(InvalidTermError) as exc_info:
            student_service.add_enrollment(student_id, {
                "courseCode": course_code,
                "term": "202510",  # Old format - should fail
                "status": "planned"
            })

        assert "Invalid term format" in str(exc_info.value)

    def test_add_enrollment_missing_term(self, student_service, test_students, real_courses):
        """Should raise InvalidTermError when term is missing."""
        student = test_students[0]
        student_id = student["id"]
        course_code = real_courses["course1"]["course_code"]

        with pytest.raises(InvalidTermError) as exc_info:
            student_service.add_enrollment(student_id, {
                "courseCode": course_code,
                "status": "planned"
            })

        assert "Term is required" in str(exc_info.value)

    def test_add_enrollment_enrolled_must_be_current_term(self, student_service, test_students, real_courses):
        """Should raise InvalidTermError when enrolling in non-current term."""
        student = test_students[0]
        student_id = student["id"]
        course_code = real_courses["course1"]["course_code"]

        with pytest.raises(InvalidTermError) as exc_info:
            student_service.add_enrollment(student_id, {
                "courseCode": course_code,
                "term": "Fall 2020",  # Past term
                "status": "enrolled"
            })

        assert "current semester" in str(exc_info.value)

    def test_add_enrollment_planned_cannot_be_past(self, student_service, test_students, real_courses):
        """Should raise InvalidTermError when planning for past term."""
        student = test_students[0]
        student_id = student["id"]
        course_code = real_courses["course1"]["course_code"]

        with pytest.raises(InvalidTermError) as exc_info:
            student_service.add_enrollment(student_id, {
                "courseCode": course_code,
                "term": "Spring 2020",  # Past term
                "status": "planned"
            })

        assert "current or future" in str(exc_info.value)

    def test_add_enrollment_time_conflict_detected(self, student_service, firebase_db, real_courses):
        """Should raise ScheduleConflictError when courses overlap using real Firebase courses."""
        student_id = generate_test_id()
        enrollment_ids = []

        # Use real courses from Firebase
        course1 = real_courses["course1"]
        course2 = real_courses["course2"]

        try:
            # Create test student
            student_service.create_student(student_id, {
                "name": "Time Conflict Test Student",
                "email": "timeconflict@wm.edu",
                "classYear": 2027
            })

            # Get current term for testing
            current_term = student_service.get_current_term()

            # Add first enrollment with schedule using enrolled status
            enrollment1 = student_service.add_enrollment(student_id, {
                "courseCode": course1["course_code"],
                "term": current_term,
                "status": "enrolled",
                "meetingDays": "MWF",
                "startTime": "09:00",
                "endTime": "09:50"
            })
            enrollment_ids.append(enrollment1["id"])

            # Try to add conflicting enrollment
            with pytest.raises(ScheduleConflictError) as exc_info:
                student_service.add_enrollment(student_id, {
                    "courseCode": course2["course_code"],
                    "term": current_term,
                    "status": "enrolled",
                    "meetingDays": "MW",  # Overlaps with MWF
                    "startTime": "09:00",  # Same time
                    "endTime": "09:50"
                })

            assert exc_info.value.conflicting_course is not None
            assert exc_info.value.conflicting_course["courseCode"] == course1["course_code"]

        finally:
            # Cleanup
            for eid in enrollment_ids:
                try:
                    student_service.delete_enrollment(eid)
                except Exception:
                    pass
            firebase_db.collection("students").document(student_id).delete()

    def test_add_enrollment_no_conflict_different_days(self, student_service, firebase_db, real_courses):
        """Should allow enrollments on different days using real Firebase courses."""
        student_id = generate_test_id()
        enrollment_ids = []

        # Use real courses from Firebase
        course1 = real_courses["course1"]
        course2 = real_courses["course2"]

        try:
            # Create test student
            student_service.create_student(student_id, {
                "name": "No Conflict Test Student",
                "email": "noconflict@wm.edu",
                "classYear": 2027
            })

            current_term = student_service.get_current_term()

            # Add MWF morning class
            enrollment1 = student_service.add_enrollment(student_id, {
                "courseCode": course1["course_code"],
                "term": current_term,
                "status": "enrolled",
                "meetingDays": "MWF",
                "startTime": "09:00",
                "endTime": "09:50"
            })
            enrollment_ids.append(enrollment1["id"])

            # Add TR class at same time - should NOT conflict
            enrollment2 = student_service.add_enrollment(student_id, {
                "courseCode": course2["course_code"],
                "term": current_term,
                "status": "enrolled",
                "meetingDays": "TR",  # Different days
                "startTime": "09:00",
                "endTime": "09:50"
            })
            enrollment_ids.append(enrollment2["id"])

            assert enrollment2 is not None
            assert enrollment2["courseCode"] == course2["course_code"]

        finally:
            # Cleanup
            for eid in enrollment_ids:
                try:
                    student_service.delete_enrollment(eid)
                except Exception:
                    pass
            firebase_db.collection("students").document(student_id).delete()

    def test_add_enrollment_no_conflict_different_times(self, student_service, firebase_db, real_courses):
        """Should allow enrollments at different times on same day using real Firebase courses."""
        student_id = generate_test_id()
        enrollment_ids = []

        # Use real courses from Firebase
        course1 = real_courses["course1"]
        course2 = real_courses["course2"]

        try:
            # Create test student
            student_service.create_student(student_id, {
                "name": "Different Times Test Student",
                "email": "difftimes@wm.edu",
                "classYear": 2027
            })

            current_term = student_service.get_current_term()

            # Add morning class
            enrollment1 = student_service.add_enrollment(student_id, {
                "courseCode": course1["course_code"],
                "term": current_term,
                "status": "enrolled",
                "meetingDays": "MWF",
                "startTime": "09:00",
                "endTime": "09:50"
            })
            enrollment_ids.append(enrollment1["id"])

            # Add afternoon class on same days - should NOT conflict
            enrollment2 = student_service.add_enrollment(student_id, {
                "courseCode": course2["course_code"],
                "term": current_term,
                "status": "enrolled",
                "meetingDays": "MWF",
                "startTime": "14:00",  # Different time
                "endTime": "14:50"
            })
            enrollment_ids.append(enrollment2["id"])

            assert enrollment2 is not None

        finally:
            # Cleanup
            for eid in enrollment_ids:
                try:
                    student_service.delete_enrollment(eid)
                except Exception:
                    pass
            firebase_db.collection("students").document(student_id).delete()

    def test_add_enrollment_no_conflict_different_terms(self, student_service, firebase_db, real_courses):
        """Should allow same time/day in different terms using real Firebase courses."""
        student_id = generate_test_id()
        enrollment_ids = []

        # Use real courses from Firebase
        course1 = real_courses["course1"]
        course2 = real_courses["course2"]

        try:
            # Create test student
            student_service.create_student(student_id, {
                "name": "Different Terms Test Student",
                "email": "diffterms@wm.edu",
                "classYear": 2027
            })

            # Add class in Fall 2030 (future term)
            enrollment1 = student_service.add_enrollment(student_id, {
                "courseCode": course1["course_code"],
                "term": "Fall 2030",
                "status": "planned",
                "meetingDays": "MWF",
                "startTime": "09:00",
                "endTime": "09:50"
            })
            enrollment_ids.append(enrollment1["id"])

            # Add same time/day in Spring 2031 - should NOT conflict (different term)
            enrollment2 = student_service.add_enrollment(student_id, {
                "courseCode": course2["course_code"],
                "term": "Spring 2031",  # Different term
                "status": "planned",
                "meetingDays": "MWF",
                "startTime": "09:00",
                "endTime": "09:50"
            })
            enrollment_ids.append(enrollment2["id"])

            assert enrollment2 is not None

        finally:
            # Cleanup
            for eid in enrollment_ids:
                try:
                    student_service.delete_enrollment(eid)
                except Exception:
                    pass
            firebase_db.collection("students").document(student_id).delete()

    def test_completed_enrollment_skips_all_validation(self, student_service, firebase_db):
        """Completed enrollments should skip course and term validation."""
        student_id = generate_test_id()
        enrollment_id = None

        try:
            # Create test student
            student_service.create_student(student_id, {
                "name": "Completed Test Student",
                "email": "completed@wm.edu",
                "classYear": 2027
            })

            # Add completed enrollment for past term - should work
            enrollment = student_service.add_enrollment(student_id, {
                "courseCode": "FAKE 999",  # Course that doesn't exist
                "term": "Fall 2015",  # Past term
                "status": "completed",
                "grade": "A"
            })
            enrollment_id = enrollment["id"]

            assert enrollment is not None
            assert enrollment["courseCode"] == "FAKE 999"
            assert enrollment["term"] == "Fall 2015"

        finally:
            # Cleanup
            if enrollment_id:
                try:
                    student_service.delete_enrollment(enrollment_id)
                except Exception:
                    pass
            firebase_db.collection("students").document(student_id).delete()
