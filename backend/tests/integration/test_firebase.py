"""
Integration tests for Firebase/Firestore operations

These tests require valid Firebase credentials and will read/write
to the actual Firestore database.

Run with: pytest tests/integration/test_firebase.py -v -m firebase
Skip with: pytest -m "not firebase"

WARNING: These tests write to your production database!
Consider using a test project or test collections.
"""

import pytest
import os
from pathlib import Path
from datetime import datetime

# Skip all tests if Firebase not configured
pytestmark = pytest.mark.firebase


def firebase_configured():
    """Check if Firebase credentials are available"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        return False

    from dotenv import load_dotenv
    load_dotenv(env_path)

    key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if not key_path:
        return False

    full_path = Path(__file__).parent.parent.parent / key_path
    return full_path.exists()


# Skip entire module if Firebase not configured
if not firebase_configured():
    pytest.skip("Firebase credentials not available", allow_module_level=True)


@pytest.mark.integration
@pytest.mark.firebase
class TestFirebaseConnection:
    """Test Firebase connectivity"""

    def test_firebase_initializes(self):
        """Firebase should initialize without error"""
        from core.config import initialize_firebase, get_firestore_client

        initialize_firebase()
        db = get_firestore_client()

        assert db is not None
        print("\n  Firebase initialized successfully")

    def test_can_read_collections(self):
        """Should be able to list collections"""
        from core.config import initialize_firebase, get_firestore_client

        initialize_firebase()
        db = get_firestore_client()

        # Try to access courses collection
        courses_ref = db.collection("courses")
        assert courses_ref is not None


@pytest.mark.integration
@pytest.mark.firebase
class TestFirebaseCourseService:
    """Test FirebaseCourseService with real database"""

    @pytest.fixture
    def course_service(self):
        """Get real course service"""
        from services.firebase import get_course_service
        return get_course_service()

    @pytest.fixture
    def sample_test_course(self):
        """Create a test course for integration testing"""
        from api.fetcher import CourseData, SectionData

        section = SectionData(
            crn="99999",
            section_number="99",
            instructor="Integration Test",
            meeting_days="MWF",
            meeting_time="12:00-12:50",
            meeting_times_raw="MWF 12:00-12:50pm",
            building="TEST",
            room="999",
            status="OPEN",
            capacity=100,
            enrolled=50,
            available=50
        )

        return CourseData(
            course_code="TEST 999",
            subject_code="TEST",
            course_number="999",
            title="Integration Test Course",
            description="This is a test course for integration testing",
            credits=3,
            attributes=["TEST ATTR"],
            sections=[section]
        )

    def test_store_and_retrieve_course(self, course_service, sample_test_course):
        """Should store and retrieve a course"""
        from core.semester import SemesterManager

        term_code = SemesterManager.get_trackable_term_code()

        # Store the test course
        stats = course_service.store_courses([sample_test_course], term_code)

        assert stats['total_courses'] == 1
        assert stats['errors'] == 0
        print(f"\n  Stored test course: {stats}")

        # Retrieve it
        retrieved = course_service.get_course("TEST 999")

        assert retrieved is not None
        assert retrieved['course_code'] == "TEST 999"
        assert retrieved['title'] == "Integration Test Course"

        print(f"  Retrieved: {retrieved['course_code']} - {retrieved['title']}")

    def test_update_existing_course(self, course_service, sample_test_course):
        """Should update an existing course"""
        from core.semester import SemesterManager
        from api.fetcher import CourseData

        term_code = SemesterManager.get_trackable_term_code()

        # First store
        course_service.store_courses([sample_test_course], term_code)

        # Modify and store again
        updated_course = CourseData(
            course_code="TEST 999",
            subject_code="TEST",
            course_number="999",
            title="Updated Integration Test Course",
            description="Updated description",
            credits=4,
            attributes=["NEW ATTR"],
            sections=sample_test_course.sections
        )

        stats = course_service.store_courses([updated_course], term_code)

        assert stats['updated'] == 1

        # Verify update
        retrieved = course_service.get_course("TEST 999")
        assert retrieved['title'] == "Updated Integration Test Course"
        assert retrieved['credits'] == 4

        print(f"\n  Updated course successfully")

    def test_get_nonexistent_course(self, course_service):
        """Should return None for non-existent course"""
        result = course_service.get_course("NONEXISTENT 999")
        assert result is None

    def test_get_all_subjects(self, course_service):
        """Should retrieve all subject codes"""
        subjects = course_service.get_all_subjects()

        assert isinstance(subjects, list)
        print(f"\n  Found {len(subjects)} subjects in database")

        if len(subjects) > 0:
            print(f"  Sample subjects: {subjects[:5]}")

    def test_get_courses_by_subject(self, course_service):
        """Should filter courses by subject"""
        # First ensure our test course exists
        from core.semester import SemesterManager
        from api.fetcher import CourseData, SectionData

        section = SectionData(
            crn="99998",
            section_number="01",
            instructor="Test",
            meeting_days="TR",
            meeting_time="9:00",
            meeting_times_raw="TR 9:00am",
            building="TEST",
            room="100",
            status="OPEN",
            capacity=30,
            enrolled=15,
            available=15
        )

        course = CourseData(
            course_code="INTTEST 101",
            subject_code="INTTEST",
            course_number="101",
            title="Subject Filter Test",
            description="Test",
            credits=3,
            attributes=[],
            sections=[section]
        )

        term_code = SemesterManager.get_trackable_term_code()
        course_service.store_courses([course], term_code)

        # Now query by subject
        courses = course_service.get_courses_by_subject("INTTEST")

        assert isinstance(courses, list)
        assert len(courses) >= 1

        for c in courses:
            assert c.get('subject_code') == "INTTEST"

        print(f"\n  Found {len(courses)} INTTEST courses")


@pytest.mark.integration
@pytest.mark.firebase
class TestFullPipeline:
    """Test the full fetch-store-retrieve pipeline"""

    @pytest.mark.asyncio
    async def test_fetch_and_store_real_courses(self):
        """Fetch real courses from API and store in Firebase"""
        from api.fetcher import FOSEFetcher
        from services.firebase import get_course_service
        from core.semester import SemesterManager

        term_code = SemesterManager.get_trackable_term_code()

        # Fetch courses (will get all, but we'll just store a few for testing)
        async with FOSEFetcher(use_cache=True) as fetcher:
            courses = await fetcher.fetch_all_courses(term_code)

            print(f"\n  Fetched {len(courses)} courses")

            if len(courses) > 0:
                # Just store first 5 for testing speed
                test_courses = courses[:5]

                service = get_course_service()
                stats = service.store_courses(test_courses, term_code)

                print(f"  Store stats: {stats}")

                assert stats['errors'] == 0

                # Verify we can retrieve one
                retrieved = service.get_course(test_courses[0].course_code)
                assert retrieved is not None
                print(f"  Verified: {retrieved['course_code']}")


@pytest.mark.integration
@pytest.mark.firebase
class TestCleanup:
    """Clean up test data after integration tests"""

    def test_cleanup_test_courses(self):
        """Remove test courses created during integration tests"""
        from core.config import initialize_firebase, get_firestore_client

        initialize_firebase()
        db = get_firestore_client()

        # Delete test courses
        test_course_ids = ["TEST_999", "INTTEST_101"]

        deleted = 0
        for course_id in test_course_ids:
            try:
                db.collection("courses").document(course_id).delete()
                deleted += 1
            except Exception:
                pass

        print(f"\n  Cleaned up {deleted} test documents")
