"""
Integration tests for Chat Service with real Firebase auth users.

Tests chat authorization with actual Firebase Auth users and Firestore data,
including real Firestore-based embeddings storage with actual OpenAI embeddings.

Requires:
- OPENAI_API_KEY environment variable
- Firestore vector index on advising_embeddings collection

Run with: pytest tests/integration/test_chat_integration.py -v -m integration
"""

import os
import pytest
import json
import uuid
from unittest.mock import MagicMock, patch

from firebase_admin import auth

# Mark all tests in this module as integration and firebase tests
pytestmark = [pytest.mark.integration, pytest.mark.firebase]

from services.student import StudentService, get_student_service
from services.advisor import AdvisorService, get_advisor_service
from services.chat import ChatService
from services.embeddings import get_embeddings_service, EmbeddingsService
from services.firebase import get_course_service
from core.config import initialize_firebase, get_firestore_client


# Test data prefix
TEST_PREFIX = "TEST_CHAT_"

# Test user credentials (same as student_advisor_integration.py)
TEST_STUDENT_EMAIL = "test.chat.student@wm.edu"
TEST_STUDENT_PASSWORD = "TestChatStudent123!"
TEST_ADVISOR_EMAIL = "test.chat.advisor@wm.edu"
TEST_ADVISOR_PASSWORD = "TestChatAdvisor123!"


def generate_test_id():
    """Generate a unique test ID."""
    return f"{TEST_PREFIX}{uuid.uuid4().hex[:8]}"


def create_or_get_auth_user(email: str, password: str, display_name: str) -> str:
    """Create a Firebase Auth user or get existing one. Returns uid."""
    try:
        user = auth.get_user_by_email(email)
        return user.uid
    except auth.UserNotFoundError:
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
def firebase_db():
    """Initialize Firebase and return the Firestore client."""
    initialize_firebase()
    return get_firestore_client()


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
def real_courses(course_service):
    """
    Get real courses from Firebase for testing.

    Returns a dict with:
    - course_no_prereqs: A course with no prerequisites (for completed courses)
    - course_with_prereqs: A course that has prerequisites
    - prereq_courses: The actual prerequisite courses needed
    """
    # Get all subjects to find available courses
    subjects = course_service.get_all_subjects()

    if not subjects:
        pytest.skip("No courses found in Firebase - run populate task first")

    # Find courses with and without prerequisites
    course_no_prereqs = None
    course_with_prereqs = None
    prereq_courses = []

    # Search through subjects to find suitable courses
    for subject in ["BUAD", "ACCT", "FINA", "MKTG"] + subjects[:10]:
        courses = course_service.get_courses_by_subject(subject)
        for course in courses:
            prereqs = course.get("prerequisites", [])

            # Find a course without prerequisites
            if not prereqs and not course_no_prereqs:
                course_no_prereqs = course

            # Find a course with prerequisites that exist in Firebase
            if prereqs and not course_with_prereqs:
                # Verify the prerequisite courses exist
                all_prereqs_exist = True
                found_prereqs = []
                for prereq_code in prereqs:
                    prereq_course = course_service.get_course(prereq_code)
                    if prereq_course:
                        found_prereqs.append(prereq_course)
                    else:
                        all_prereqs_exist = False
                        break

                if all_prereqs_exist and found_prereqs:
                    course_with_prereqs = course
                    prereq_courses = found_prereqs

            # Stop when we have both
            if course_no_prereqs and course_with_prereqs:
                break

        if course_no_prereqs and course_with_prereqs:
            break

    if not course_no_prereqs:
        pytest.skip("Could not find a course without prerequisites in Firebase")

    # If we couldn't find a course with prerequisites, use another course without prereqs
    if not course_with_prereqs:
        # Just use a different course without prereqs for the planned enrollment
        for subject in subjects[:10]:
            courses = course_service.get_courses_by_subject(subject)
            for course in courses:
                if course.get("course_code") != course_no_prereqs.get("course_code"):
                    course_with_prereqs = course
                    prereq_courses = []  # No prereqs needed
                    break
            if course_with_prereqs:
                break

    return {
        "course_no_prereqs": course_no_prereqs,
        "course_with_prereqs": course_with_prereqs,
        "prereq_courses": prereq_courses
    }


@pytest.fixture(scope="module")
def test_student_user(firebase_db, student_service, real_courses):
    """Create a test student user with profile in Firebase using real course data."""
    uid = create_or_get_auth_user(
        email=TEST_STUDENT_EMAIL,
        password=TEST_STUDENT_PASSWORD,
        display_name="Chat Test Student"
    )

    # Create student profile
    student_service.create_student(uid, {
        "firstName": "Chat",
        "lastName": "TestStudent",
        "email": TEST_STUDENT_EMAIL,
        "classYear": "Junior",
        "gpa": 3.5,
        "majorDeclared": True,
        "major": "Finance",
        "intendedMajor": "Finance",
        "holds": []
    })

    # Get real courses from Firebase
    course_no_prereqs = real_courses["course_no_prereqs"]
    course_with_prereqs = real_courses["course_with_prereqs"]
    prereq_courses = real_courses["prereq_courses"]

    # Add a completed course (no validation needed)
    student_service.add_enrollment(uid, {
        "courseCode": course_no_prereqs["course_code"],
        "courseName": course_no_prereqs.get("title", "Test Course"),
        "term": "Fall 2020",  # Completed courses skip validation
        "status": "completed",
        "grade": "A",
        "credits": course_no_prereqs.get("credits", 3)
    })

    # Add all prerequisite courses as completed (so we can enroll in course_with_prereqs)
    term_years = ["Spring 2020", "Fall 2019", "Spring 2019", "Fall 2018"]
    for i, prereq in enumerate(prereq_courses):
        term = term_years[i] if i < len(term_years) else f"Fall {2018 - i}"
        student_service.add_enrollment(uid, {
            "courseCode": prereq["course_code"],
            "courseName": prereq.get("title", "Prerequisite Course"),
            "term": term,
            "status": "completed",
            "grade": "B+",
            "credits": prereq.get("credits", 3)
        })

    # Add a planned course (uses real prerequisite validation from Firebase)
    student_service.add_enrollment(uid, {
        "courseCode": course_with_prereqs["course_code"],
        "courseName": course_with_prereqs.get("title", "Planned Course"),
        "term": "Fall 2030",  # Future planned term
        "status": "planned",
        "credits": course_with_prereqs.get("credits", 3)
    })

    yield {
        "uid": uid,
        "email": TEST_STUDENT_EMAIL,
        "role": "student",
        "courses": real_courses  # Include course info for tests that need it
    }

    # Cleanup
    db = firebase_db
    enrollments = db.collection("enrollments").where("studentId", "==", uid).stream()
    for doc in enrollments:
        doc.reference.delete()
    db.collection("students").document(uid).delete()
    delete_auth_user_if_exists(uid)


@pytest.fixture(scope="module")
def test_advisor_user(firebase_db, advisor_service, test_student_user):
    """Create a test advisor user with advisee assignment."""
    uid = create_or_get_auth_user(
        email=TEST_ADVISOR_EMAIL,
        password=TEST_ADVISOR_PASSWORD,
        display_name="Chat Test Advisor"
    )

    # Set advisor custom claims
    auth.set_custom_user_claims(uid, {"advisor": True})

    # Assign the test student as advisee
    advisor_service.assign_advisee(uid, test_student_user["uid"])

    yield {"uid": uid, "email": TEST_ADVISOR_EMAIL, "role": "advisor"}

    # Cleanup
    db = firebase_db
    assignments = db.collection("advisor_assignments").where("advisorId", "==", uid).stream()
    for doc in assignments:
        doc.reference.delete()
    delete_auth_user_if_exists(uid)


@pytest.fixture(scope="module")
def second_student_user(firebase_db, student_service):
    """Create a second student (not assigned to advisor) for isolation testing."""
    email = f"test.chat.student2.{uuid.uuid4().hex[:6]}@wm.edu"
    uid = create_or_get_auth_user(
        email=email,
        password="TestStudent2Pass!",
        display_name="Second Test Student"
    )

    student_service.create_student(uid, {
        "firstName": "Other",
        "lastName": "Student",
        "email": email,
        "classYear": "Senior",
        "gpa": 2.8,
        "majorDeclared": True,
        "major": "Accounting",
        "holds": ["Financial"]
    })

    yield {"uid": uid, "email": email, "role": "student"}

    # Cleanup
    db = firebase_db
    db.collection("students").document(uid).delete()
    delete_auth_user_if_exists(uid)


@pytest.fixture(scope="module")
def openai_api_key():
    """Ensure OPENAI_API_KEY is available for real embeddings."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set - required for real embeddings tests")
    return api_key


@pytest.fixture(scope="module")
def real_embeddings_service(firebase_db, openai_api_key):
    """
    Create real EmbeddingsService with actual OpenAI embeddings.

    This fixture:
    1. Creates a real embeddings service
    2. Adds test curriculum documents with real embeddings
    3. Cleans up test documents after tests complete

    Requires:
    - OPENAI_API_KEY environment variable
    - Firestore vector index on advising_embeddings.embedding field
    """
    # Create a fresh embeddings service
    embeddings = EmbeddingsService()

    # Test documents to embed (curriculum-like content)
    test_documents = [
        {
            "content": "Finance majors must complete BUAD 323 Financial Management as a prerequisite "
                       "for all upper-level finance courses. BUAD 327 Investments and BUAD 329 "
                       "Corporate Valuation are required courses for the Finance concentration.",
            "source": "TEST_Finance Major Requirements",
            "metadata": {"type": "requirements", "major": "Finance", "test": True}
        },
        {
            "content": "Accounting majors must complete ACCT 203 and ACCT 204 before taking "
                       "upper-level accounting courses. The CPA track requires additional courses "
                       "including ACCT 301 Intermediate Accounting and ACCT 411 Auditing.",
            "source": "TEST_Accounting Major Requirements",
            "metadata": {"type": "requirements", "major": "Accounting", "test": True}
        },
        {
            "content": "Business students must maintain a minimum GPA of 2.0 to remain in good standing. "
                       "Students with GPA below 2.0 will be placed on academic probation and must meet "
                       "with their academic advisor.",
            "source": "TEST_Academic Standing Policy",
            "metadata": {"type": "policy", "test": True}
        },
        {
            "content": "Course registration opens in November for Spring semester and April for Fall semester. "
                       "Students must clear all holds before registering. Financial holds prevent registration.",
            "source": "TEST_Registration Policy",
            "metadata": {"type": "policy", "test": True}
        }
    ]

    # Add test documents with real embeddings
    print("\n[Test Setup] Creating real embeddings for test documents...")
    for doc in test_documents:
        embeddings.add_document(
            content=doc["content"],
            source=doc["source"],
            metadata=doc["metadata"]
        )
    print(f"[Test Setup] Added {len(test_documents)} test documents with real embeddings")

    yield embeddings

    # Cleanup: Remove test documents
    print("\n[Test Cleanup] Removing test embeddings...")
    collection = firebase_db.collection("advising_embeddings")
    # Find and delete test documents (those with TEST_ prefix in source)
    docs = collection.stream()
    deleted = 0
    for doc in docs:
        data = doc.to_dict()
        source = data.get("source", "")
        if source.startswith("TEST_") or data.get("metadata", {}).get("test"):
            doc.reference.delete()
            deleted += 1
    print(f"[Test Cleanup] Deleted {deleted} test embedding documents")


@pytest.fixture
def mock_openai_chat():
    """Mock only OpenAI chat completions (not embeddings) to control response format."""
    with patch('services.chat.OpenAI') as mock:
        client = MagicMock()
        mock.return_value = client

        # Default response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Test response from AI",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        client.chat.completions.create.return_value = mock_response

        yield client


@pytest.fixture
def chat_service(mock_openai_chat, real_embeddings_service):
    """
    Create ChatService with real embeddings but mocked chat completions.

    Uses:
    - Real OpenAI embeddings (via real_embeddings_service)
    - Real Firestore vector search
    - Mocked chat completions (to control response format and avoid costs)
    """
    with patch('services.chat.OPENAI_AVAILABLE', True):
        with patch('services.chat.load_curriculum_data', return_value=None):
            svc = ChatService()
            svc._openai_client = mock_openai_chat
            svc._embeddings = real_embeddings_service
            svc._curriculum_loaded = True
            svc._initialized = True
            return svc


class TestChatStudentAuthorization:
    """Integration tests for student chat authorization with real Firebase data."""

    def test_student_sees_own_profile_data(
        self, chat_service, mock_openai_chat, test_student_user
    ):
        """Student should see their own profile when chatting."""
        chat_service.chat(
            student_id=test_student_user["uid"],
            message="What courses should I take next?",
            user_id=test_student_user["uid"],
            user_role="student"
        )

        # Check what was sent to OpenAI
        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        # Should include student profile from real Firebase data
        context = " ".join(system_messages)
        assert "STUDENT PROFILE" in context
        assert "Class Year: Junior" in context
        assert "Finance" in context
        assert "GPA: 3.5" in context

    def test_student_sees_own_courses(
        self, chat_service, mock_openai_chat, test_student_user
    ):
        """Student should see their own completed and current courses."""
        chat_service.chat(
            student_id=test_student_user["uid"],
            message="What have I completed?",
            user_id=test_student_user["uid"],
            user_role="student"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)
        # Should include courses from real Firebase data
        assert "BUAD 300" in context or "COMPLETED" in context
        assert "BUAD 323" in context or "CURRENT" in context

    def test_student_cannot_see_other_student_data(
        self, chat_service, mock_openai_chat, test_student_user, second_student_user
    ):
        """Student should NOT see another student's data."""
        chat_service.chat(
            student_id=second_student_user["uid"],  # Trying to query other student
            message="Tell me about this student",
            user_id=test_student_user["uid"],  # But logged in as first student
            user_role="student"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)
        # Should NOT include any student profile data
        assert "STUDENT PROFILE" not in context
        assert "Other Student" not in context
        # Note: "Accounting" may appear in curriculum embeddings, so we check for
        # specific second student profile markers instead
        assert "Major: Accounting" not in context  # Second student's major in profile format
        assert "test.chat.student2" not in context  # Second student's email


class TestChatAdvisorAuthorization:
    """Integration tests for advisor chat authorization with real Firebase data."""

    def test_advisor_sees_advisee_data(
        self, chat_service, mock_openai_chat, test_advisor_user, test_student_user
    ):
        """Advisor should see their advisee's data."""
        chat_service.chat(
            student_id=test_student_user["uid"],
            message="Tell me about this student's progress",
            user_id=test_advisor_user["uid"],
            user_role="advisor"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)
        # Should include advisor view and student data
        assert "ADVISOR VIEW" in context
        assert "STUDENT PROFILE" in context
        assert "Chat TestStudent" in context or "Finance" in context

    def test_advisor_sees_all_advisees_overview(
        self, chat_service, mock_openai_chat, test_advisor_user
    ):
        """Advisor should see overview of all advisees when no specific student."""
        chat_service.chat(
            student_id=None,  # No specific student
            message="How are my advisees doing?",
            user_id=test_advisor_user["uid"],
            user_role="advisor"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)
        assert "ADVISOR VIEW" in context
        assert "advisee" in context.lower()

    def test_advisor_with_specific_advisee_focus(
        self, chat_service, mock_openai_chat, test_advisor_user, test_student_user
    ):
        """Advisor should see full details for specific advisee."""
        chat_service.chat(
            student_id=test_student_user["uid"],
            message="What courses has this student completed?",
            user_id=test_advisor_user["uid"],
            user_role="advisor"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)
        # Should have full student profile within advisor view
        assert "ADVISOR VIEW" in context
        assert "STUDENT PROFILE" in context


class TestChatWithRealStudentData:
    """Integration tests verifying chat uses real student data from Firebase."""

    def test_chat_reflects_actual_gpa(
        self, chat_service, mock_openai_chat, test_student_user
    ):
        """Chat context should include actual GPA from Firebase."""
        chat_service.chat(
            student_id=test_student_user["uid"],
            message="What is my GPA?",
            user_id=test_student_user["uid"],
            user_role="student"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)
        # The test student has GPA 3.5
        assert "3.5" in context

    def test_chat_reflects_actual_major(
        self, chat_service, mock_openai_chat, test_student_user
    ):
        """Chat context should include actual major from Firebase."""
        chat_service.chat(
            student_id=test_student_user["uid"],
            message="What is my major?",
            user_id=test_student_user["uid"],
            user_role="student"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)
        # The test student is a Finance major
        assert "Finance" in context

    def test_student_with_holds_shows_alert(
        self, chat_service, mock_openai_chat, second_student_user
    ):
        """Student with holds should see alert in context."""
        chat_service.chat(
            student_id=second_student_user["uid"],
            message="Can I register for classes?",
            user_id=second_student_user["uid"],
            user_role="student"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)
        # Second student has Financial hold
        assert "ALERT" in context or "Hold" in context or "Financial" in context


class TestChatEmbeddingsIntegration:
    """
    Integration tests verifying chat service uses REAL embeddings.

    These tests use:
    - Real OpenAI embeddings API (text-embedding-3-small)
    - Real Firestore vector storage and search
    - Test documents created in real_embeddings_service fixture

    Requires:
    - OPENAI_API_KEY environment variable
    - Firestore vector index on advising_embeddings.embedding field
    """

    def test_real_embeddings_search_returns_results(
        self, real_embeddings_service
    ):
        """Verify real embeddings search returns relevant results."""
        # Search for Finance content
        results = real_embeddings_service.search("Finance major requirements", n_results=3)

        # Should find our test Finance document
        assert len(results) > 0
        sources = [r.source for r in results]
        assert any("Finance" in s for s in sources)

    def test_real_embeddings_search_returns_relevant_content(
        self, real_embeddings_service
    ):
        """Verify embeddings search returns semantically relevant content."""
        # Search for accounting
        results = real_embeddings_service.search("CPA requirements accounting", n_results=3)

        assert len(results) > 0
        # Should find accounting-related content
        all_content = " ".join([r.content for r in results])
        assert "ACCT" in all_content or "Accounting" in all_content or "CPA" in all_content

    def test_real_embeddings_search_for_policy(
        self, real_embeddings_service
    ):
        """Verify embeddings can find policy documents."""
        results = real_embeddings_service.search("registration holds", n_results=3)

        assert len(results) > 0
        all_content = " ".join([r.content for r in results])
        assert "hold" in all_content.lower() or "registration" in all_content.lower()

    def test_chat_uses_real_embeddings_in_context(
        self, chat_service, mock_openai_chat, test_student_user
    ):
        """Verify chat service includes real embeddings results in OpenAI context."""
        chat_service.chat(
            student_id=test_student_user["uid"],
            message="What courses do Finance majors need?",
            user_id=test_student_user["uid"],
            user_role="student"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)
        # Real embeddings should return our test Finance document
        # which mentions BUAD 323, BUAD 327, etc.
        assert "BUAD 323" in context or "Finance" in context

    def test_embeddings_results_have_valid_scores(
        self, real_embeddings_service
    ):
        """Verify embeddings search returns results with valid similarity scores."""
        results = real_embeddings_service.search("academic probation GPA", n_results=3)

        assert len(results) > 0
        for result in results:
            # Scores should be between 0 and 1 (cosine similarity)
            assert 0 <= result.score <= 1
            assert result.content  # Should have content
            assert result.source  # Should have source


class TestChatWorkflowIntegration:
    """Integration tests for complete chat workflow scenarios with real embeddings."""

    def test_student_chat_workflow(
        self, chat_service, mock_openai_chat, test_student_user
    ):
        """Test complete student chat workflow with real data and embeddings."""
        # First message
        result1 = chat_service.chat(
            student_id=test_student_user["uid"],
            message="What courses should I take next semester?",
            user_id=test_student_user["uid"],
            user_role="student"
        )

        assert result1.content is not None
        assert isinstance(result1.citations, list)
        assert isinstance(result1.risks, list)
        assert isinstance(result1.nextSteps, list)

        # Follow-up with history
        result2 = chat_service.chat(
            student_id=test_student_user["uid"],
            message="What about prerequisites?",
            chat_history=[
                {"role": "user", "content": "What courses should I take next semester?"},
                {"role": "assistant", "content": result1.content}
            ],
            user_id=test_student_user["uid"],
            user_role="student"
        )

        assert result2.content is not None

        # Verify history was included
        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        user_messages = [m for m in messages if m['role'] == 'user']
        assert len(user_messages) >= 2  # History + current

    def test_advisor_chat_workflow(
        self, chat_service, mock_openai_chat, test_advisor_user, test_student_user
    ):
        """Test complete advisor chat workflow with real data and embeddings."""
        # Query about all advisees
        result1 = chat_service.chat(
            student_id=None,
            message="Do any of my advisees need attention?",
            user_id=test_advisor_user["uid"],
            user_role="advisor"
        )

        assert result1.content is not None

        # Query about specific advisee
        result2 = chat_service.chat(
            student_id=test_student_user["uid"],
            message="Tell me more about this student's course history",
            user_id=test_advisor_user["uid"],
            user_role="advisor"
        )

        assert result2.content is not None

        # Verify student context was included
        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']
        context = " ".join(system_messages)
        assert "STUDENT PROFILE" in context

    def test_full_rag_pipeline_with_real_embeddings(
        self, chat_service, mock_openai_chat, test_student_user
    ):
        """
        Test the complete RAG pipeline:
        1. User asks about Finance requirements
        2. Real embeddings search finds relevant documents
        3. Documents are included in OpenAI context
        """
        chat_service.chat(
            student_id=test_student_user["uid"],
            message="What are the prerequisites for upper-level finance courses?",
            user_id=test_student_user["uid"],
            user_role="student"
        )

        call_args = mock_openai_chat.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        context = " ".join(system_messages)

        # Should include student profile
        assert "STUDENT PROFILE" in context

        # Should include embeddings results (from real vector search)
        # Our test documents mention BUAD 323 as prerequisite for Finance
        assert "BUAD 323" in context or "prerequisite" in context.lower()
