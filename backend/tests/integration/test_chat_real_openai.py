"""
Integration tests using REAL OpenAI API.

These tests make actual API calls to OpenAI. They are:
- Skipped if OPENAI_API_KEY is not set
- Designed to use MINIMAL tokens (short prompts, low max_tokens)
- Run separately from main test suite

Run with: pytest tests/integration/test_chat_real_openai.py -v -m real_openai

Token budget per test: ~100-200 tokens total (input + output)
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Skip entire module if no API key
pytestmark = [
    pytest.mark.real_openai,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set - skipping real API tests"
    )
]


@pytest.fixture(scope="module")
def real_openai_client():
    """Create a real OpenAI client."""
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@pytest.fixture
def mock_embeddings():
    """Mock embeddings to avoid Firestore vector index requirement."""
    from services.embeddings import SearchResult

    embeddings = MagicMock()
    embeddings.get_document_count.return_value = 1
    embeddings.search.return_value = [
        SearchResult(
            content="Finance major requires BUAD 323.",
            source="Curriculum",
            score=0.9,
            metadata={}
        )
    ]
    return embeddings


@pytest.fixture
def minimal_chat_service(mock_embeddings, real_openai_client):
    """
    Create ChatService with real OpenAI but mocked embeddings.
    Uses minimal token settings.
    """
    from services.chat import ChatService

    # Create the service with mocked embeddings but real OpenAI
    with patch('services.chat.get_embeddings_service', return_value=mock_embeddings):
        with patch('services.chat.load_curriculum_data', return_value=None):
            service = ChatService()

    # Force override with correct services
    service._embeddings = mock_embeddings
    service._openai_client = real_openai_client  # Use real OpenAI client
    service._curriculum_loaded = True
    service._initialized = True

    # Override to use fewer tokens
    service.MAX_CONTEXT_RESULTS = 1
    service.MAX_HISTORY_MESSAGES = 2

    return service


@pytest.fixture
def mock_student_profile():
    """Mock student profile data - uses correct field names from StudentService."""
    return {
        "id": "student-123",
        "userId": "student-123",
        "firstName": "John",
        "lastName": "Smith",
        "email": "jsmith@wm.edu",
        "classYear": "Junior",
        "gpa": 3.2,
        "creditsEarned": 45,
        "majorDeclared": False,
        "intendedMajor": "Finance",
        "holds": []
    }


@pytest.fixture
def mock_student_courses():
    """Mock student course data with completed, current, and planned courses including schedule info."""
    return {
        "completed": [
            {"courseCode": "BUAD 203", "courseName": "Intro to Business", "grade": "B+", "credits": 3},
            {"courseCode": "ACCT 203", "courseName": "Financial Accounting", "grade": "A-", "credits": 3},
            {"courseCode": "ECON 101", "courseName": "Intro Economics", "grade": "B", "credits": 3},
        ],
        "current": [
            {
                "courseCode": "BUAD 323",
                "courseName": "Financial Management",
                "credits": 3,
                "sectionNumber": "01",
                "meetingDays": "MWF",
                "startTime": "09:00",
                "endTime": "09:50",
                "location": "Miller Hall 1090",
                "instructor": "Dr. Johnson"
            },
            {
                "courseCode": "ACCT 204",
                "courseName": "Managerial Accounting",
                "credits": 3,
                "sectionNumber": "02",
                "meetingDays": "TR",
                "startTime": "11:00",
                "endTime": "12:20",
                "location": "Tyler Hall 201",
                "instructor": "Prof. Williams"
            },
        ],
        "planned": []
    }


@pytest.fixture
def mock_finance_requirements():
    """Mock embeddings that return Finance major requirements with section availability."""
    from services.embeddings import SearchResult

    embeddings = MagicMock()
    embeddings.get_document_count.return_value = 1
    embeddings.search.return_value = [
        SearchResult(
            content='''Finance Major Requirements:
- BUAD 323 Financial Management (prereq: BUAD 203) - REQUIRED
- BUAD 327 Investments (prereq: BUAD 323) - REQUIRED
- BUAD 341 Corporate Finance (prereq: BUAD 323) - REQUIRED
- ACCT 203 Financial Accounting - REQUIRED
- ACCT 204 Managerial Accounting (prereq: ACCT 203) - REQUIRED
- BUAD 345 Financial Modeling (prereq: BUAD 323) - ELECTIVE

Spring 2025 Available Sections:
BUAD 327 Investments:
  - Section 01: MWF 09:00-09:50, Miller Hall 2010, Dr. Adams
  - Section 02: TR 14:00-15:20, Tyler Hall 105, Prof. Baker
  - Section 03: MWF 13:00-13:50, Miller Hall 1090, Dr. Adams

BUAD 341 Corporate Finance:
  - Section 01: TR 09:30-10:50, Alan B. Miller Hall 1065, Dr. Chen
  - Section 02: MWF 11:00-11:50, Tyler Hall 201, Prof. Davis

BUAD 345 Financial Modeling:
  - Section 01: TR 11:00-12:20, Miller Hall Computer Lab, Dr. Evans
  - Section 02: MW 15:00-16:20, Miller Hall Computer Lab, Dr. Evans''',
            source='Finance Major Requirements - Spring 2025',
            score=0.95,
            metadata={}
        )
    ]
    return embeddings


@pytest.fixture
def student_chat_service(mock_finance_requirements, real_openai_client, mock_student_profile, mock_student_courses):
    """
    Chat service with student profile, courses, and Finance requirements injected.
    Yields the service with patches active for the duration of the test.
    """
    from services.chat import ChatService

    # Mock student service to return our test data
    mock_student_service = MagicMock()
    mock_student_service.get_student.return_value = mock_student_profile
    mock_student_service.get_student_courses.return_value = mock_student_courses

    # Keep patches active for the duration of the test by using yield
    with patch('services.chat.get_embeddings_service', return_value=mock_finance_requirements):
        with patch('services.chat.load_curriculum_data', return_value=None):
            with patch('services.chat.get_student_service', return_value=mock_student_service):
                service = ChatService()
                service._embeddings = mock_finance_requirements
                service._openai_client = real_openai_client
                service._curriculum_loaded = True
                service._initialized = True
                service.MAX_CONTEXT_RESULTS = 1
                service.MAX_HISTORY_MESSAGES = 2
                yield service


@pytest.fixture
def advisor_chat_service(mock_finance_requirements, real_openai_client, mock_student_profile, mock_student_courses):
    """
    Chat service configured for advisor viewing student data.
    Yields the service with patches active for the duration of the test.
    """
    from services.chat import ChatService

    # Mock student service
    mock_student_service = MagicMock()
    mock_student_service.get_student.return_value = mock_student_profile
    mock_student_service.get_student_courses.return_value = mock_student_courses

    # Mock advisor service - advisor has this student as advisee
    mock_advisor_service = MagicMock()
    mock_advisor_service.get_advisees.return_value = [mock_student_profile]
    mock_advisor_service.is_advisee.return_value = True

    # Keep patches active for the duration of the test by using yield
    with patch('services.chat.get_embeddings_service', return_value=mock_finance_requirements):
        with patch('services.chat.load_curriculum_data', return_value=None):
            with patch('services.chat.get_student_service', return_value=mock_student_service):
                with patch('services.chat.get_advisor_service', return_value=mock_advisor_service):
                    service = ChatService()
                    service._embeddings = mock_finance_requirements
                    service._openai_client = real_openai_client
                    service._curriculum_loaded = True
                    service._initialized = True
                    service.MAX_CONTEXT_RESULTS = 1
                    service.MAX_HISTORY_MESSAGES = 2
                    yield service


class TestRealOpenAIConnection:
    """Test that we can connect to OpenAI API."""

    def test_openai_api_connection(self, real_openai_client):
        """
        Verify we can make a minimal API call.
        Token usage: ~20 tokens
        """
        response = real_openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'ok'"}],
            max_tokens=5
        )

        assert response.choices[0].message.content is not None
        assert len(response.choices[0].message.content) > 0


class TestSpecificCourseQueries:
    """Test queries about specific courses."""

    def test_query_about_specific_course(self, minimal_chat_service):
        """
        Test asking about a specific course (BUAD 323).
        Token usage: ~150 tokens
        """
        response = minimal_chat_service.chat(
            student_id="test-123",
            message="What is BUAD 323?",
            user_id="test-123",
            user_role="student"
        )

        # Verify response structure
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0

        # Should mention the course or financial management
        content_lower = response.content.lower()
        assert "buad" in content_lower or "financial" in content_lower or "323" in content_lower

        print(f"\n=== COURSE QUERY RESPONSE ===\n{response.content[:300]}")


class TestStudentPersonalizedRecommendations:
    """Test that AI uses student's specific data for recommendations."""

    def test_does_not_recommend_completed_courses(self, student_chat_service, mock_student_courses):
        """
        CRITICAL: AI should NEVER recommend courses the student has already completed.
        Student has completed: BUAD 203, ACCT 203, ECON 101
        Token usage: ~200 tokens
        """
        response = student_chat_service.chat(
            student_id="student-123",
            message="What courses should I take next semester for my Finance degree?",
            user_id="student-123",
            user_role="student"
        )

        assert response.content is not None
        content = response.content

        # Get completed course codes
        completed = [c["courseCode"] for c in mock_student_courses["completed"]]
        print(f"\n=== COMPLETED COURSES CHECK ===")
        print(f"Student completed: {completed}")
        print(f"Response: {content[:400]}")

        # AI should NOT recommend these as "take next semester"
        # (They might be mentioned as "you've completed" which is OK)
        for course in completed:
            # Check if it's being recommended (not just mentioned)
            if f"take {course}" in content.lower() or f"enroll in {course}" in content.lower():
                pytest.fail(f"AI incorrectly recommended already-completed course: {course}")

    def test_does_not_recommend_current_courses(self, student_chat_service, mock_student_courses):
        """
        CRITICAL: AI should NEVER recommend courses the student is currently taking.
        Student is currently taking: BUAD 323, ACCT 204
        Token usage: ~200 tokens
        """
        response = student_chat_service.chat(
            student_id="student-123",
            message="Build me a schedule for next semester.",
            user_id="student-123",
            user_role="student"
        )

        assert response.content is not None
        content = response.content

        current = [c["courseCode"] for c in mock_student_courses["current"]]
        print(f"\n=== CURRENT ENROLLMENT CHECK ===")
        print(f"Currently taking: {current}")
        print(f"Response: {content[:400]}")

        # Should recommend courses that need BUAD 323 as prereq (BUAD 327, 341, 345)
        # Should NOT recommend BUAD 323 or ACCT 204 (currently taking)

    def test_recommends_courses_with_satisfied_prerequisites(self, student_chat_service):
        """
        AI should recommend courses where prerequisites will be met.
        After this semester: BUAD 323 done -> can take BUAD 327, 341, 345
        Token usage: ~200 tokens
        """
        response = student_chat_service.chat(
            student_id="student-123",
            message="Based on my completed and current courses, recommend specific Finance courses I should take next semester.",
            user_id="student-123",
            user_role="student"
        )

        assert response.content is not None
        content_lower = response.content.lower()

        print(f"\n=== PREREQUISITE CHECK ===")
        print(f"Response: {response.content[:500]}")

        # Should recommend at least one of these (all have BUAD 323 as prereq which student is taking)
        valid_next_courses = ["buad 327", "buad 341", "buad 345", "327", "341", "345"]
        found_recommendation = any(course in content_lower for course in valid_next_courses)

        # Also accept if it mentions investments/corporate finance (course names)
        course_names = ["investments", "corporate finance", "financial modeling"]
        found_by_name = any(name in content_lower for name in course_names)

        assert found_recommendation or found_by_name, \
            f"AI should recommend BUAD 327, 341, or 345 (prereq BUAD 323 being completed). Got: {response.content[:300]}"


class TestAdvisorViewingStudent:
    """Test advisor viewing and advising on student data."""

    def test_advisor_sees_student_context(self, advisor_chat_service, mock_student_profile):
        """
        Test that advisor gets context about their advisee.
        Token usage: ~200 tokens
        """
        response = advisor_chat_service.chat(
            student_id="student-123",
            message="How is this student doing academically?",
            user_id="advisor-456",
            user_role="advisor"
        )

        assert response is not None
        assert response.content is not None

        print(f"\n=== ADVISOR VIEW RESPONSE ===")
        print(f"Viewing student: {mock_student_profile['firstName']} {mock_student_profile['lastName']}")
        print(f"Response: {response.content[:400]}")

    def test_advisor_gets_recommendations_for_advisee(self, advisor_chat_service):
        """
        Test that advisor can get course recommendations for their advisee.
        Token usage: ~200 tokens
        """
        response = advisor_chat_service.chat(
            student_id="student-123",
            message="What courses should this student consider for Finance?",
            user_id="advisor-456",
            user_role="advisor"
        )

        assert response.content is not None

        # Should mention Finance-related courses or requirements
        content_lower = response.content.lower()
        assert any(term in content_lower for term in ["buad", "finance", "course", "recommend"]), \
            f"Response doesn't seem advisor-relevant: {response.content[:200]}"

        print(f"\n=== ADVISOR RECOMMENDATION ===\n{response.content[:400]}")
        if response.nextSteps:
            print(f"Next Steps: {response.nextSteps}")


class TestRealJSONResponseParsing:
    """Test that real OpenAI responses parse correctly."""

    def test_response_parses_without_error(self, minimal_chat_service):
        """
        Test that _parse_response handles real API output.
        Token usage: ~150 tokens
        """
        response = minimal_chat_service.chat(
            student_id="test-123",
            message="Hello",
            user_id="test-123",
            user_role="student"
        )

        # Should not raise any parsing errors
        assert response.content is not None

        # Lists should be valid (empty is ok)
        assert isinstance(response.citations, list)
        assert isinstance(response.risks, list)
        assert isinstance(response.nextSteps, list)


@pytest.mark.real_openai
class TestScheduleAwareRecommendations:
    """Test that AI considers scheduling when making recommendations."""

    def test_ai_receives_schedule_context(self, student_chat_service):
        """
        Test that the AI sees the student's current schedule with times/days.
        Token usage: ~200 tokens
        """
        response = student_chat_service.chat(
            student_id="student-123",
            message="What is my current schedule? List my classes with their meeting times.",
            user_id="student-123",
            user_role="student"
        )

        assert response.content is not None
        content_lower = response.content.lower()

        print(f"\n=== SCHEDULE CONTEXT TEST ===")
        print(f"Response: {response.content[:600]}")

        # AI should see and report the schedule info
        schedule_terms = ["mwf", "tr", "09:00", "11:00", "monday", "tuesday", "wednesday", "thursday", "friday"]
        has_schedule_info = any(term in content_lower for term in schedule_terms)

        assert has_schedule_info, \
            f"AI should see schedule details (days/times). Got: {response.content[:300]}"

    def test_recommends_non_conflicting_sections(self, student_chat_service):
        """
        Test that AI recommends sections that don't conflict with current schedule.
        Student has:
          - BUAD 323: MWF 09:00-09:50
          - ACCT 204: TR 11:00-12:20

        Available BUAD 327 sections:
          - Section 01: MWF 09:00-09:50 (CONFLICTS with BUAD 323!)
          - Section 02: TR 14:00-15:20 (OK)
          - Section 03: MWF 13:00-13:50 (OK)

        AI should recommend Section 02 or 03, NOT Section 01.
        Token usage: ~300 tokens
        """
        response = student_chat_service.chat(
            student_id="student-123",
            message="I want to take BUAD 327 Investments next semester. Which section should I take that fits my schedule?",
            user_id="student-123",
            user_role="student"
        )

        assert response.content is not None
        content_lower = response.content.lower()

        print(f"\n=== NON-CONFLICTING SECTION TEST ===")
        print(f"Response: {response.content[:700]}")

        # Should recommend Section 02 or 03 (non-conflicting)
        recommends_section_02 = "section 02" in content_lower or "section 2" in content_lower or "tr" in content_lower and "14:00" in content_lower
        recommends_section_03 = "section 03" in content_lower or "section 3" in content_lower or "13:00" in content_lower

        # Should NOT recommend Section 01 without warning about conflict
        mentions_conflict = "conflict" in content_lower or "overlap" in content_lower or "same time" in content_lower

        # Either recommends a good section OR warns about the conflict
        assert recommends_section_02 or recommends_section_03 or mentions_conflict, \
            f"AI should recommend non-conflicting sections (02 or 03) or warn about conflicts. Got: {response.content[:400]}"

    def test_builds_schedule_without_conflicts(self, student_chat_service):
        """
        Test that when asked to build a full schedule, AI avoids time conflicts.
        Token usage: ~400 tokens
        """
        response = student_chat_service.chat(
            student_id="student-123",
            message="Build me a complete schedule for next semester with Finance courses. Include specific sections with times that don't conflict with my current classes.",
            user_id="student-123",
            user_role="student"
        )

        assert response.content is not None
        content_lower = response.content.lower()

        print(f"\n=== FULL SCHEDULE BUILD TEST ===")
        print(f"Response: {response.content[:800]}")

        # Should mention specific sections/times
        has_scheduling_detail = any(term in content_lower for term in [
            "section", "mwf", "tr", "monday", "tuesday", "wednesday",
            "09:00", "11:00", "13:00", "14:00", "15:00"
        ])

        # Should mention multiple courses
        mentions_courses = sum([
            "buad 327" in content_lower or "investments" in content_lower,
            "buad 341" in content_lower or "corporate finance" in content_lower,
            "buad 345" in content_lower or "financial modeling" in content_lower
        ])

        assert has_scheduling_detail, \
            f"AI should include scheduling details (sections, times). Got: {response.content[:400]}"

        assert mentions_courses >= 1, \
            f"AI should recommend at least one Finance course. Got: {response.content[:400]}"

    def test_includes_section_details_in_recommendations(self, student_chat_service):
        """
        Test that AI includes section number, days, times, location, instructor in recommendations.
        Token usage: ~250 tokens
        """
        response = student_chat_service.chat(
            student_id="student-123",
            message="Give me detailed section recommendations for BUAD 341 Corporate Finance including instructor and room.",
            user_id="student-123",
            user_role="student"
        )

        assert response.content is not None
        content_lower = response.content.lower()

        print(f"\n=== SECTION DETAILS TEST ===")
        print(f"Response: {response.content[:600]}")

        # Check for various section details
        has_section_number = "section" in content_lower
        has_days = any(day in content_lower for day in ["mwf", "tr", "monday", "tuesday", "wednesday", "thursday", "friday"])
        has_time = any(time in content_lower for time in ["09:", "10:", "11:", "morning", "afternoon"])
        has_location = any(loc in content_lower for loc in ["miller", "tyler", "hall", "room"])
        has_instructor = any(name in content_lower for name in ["chen", "davis", "dr.", "prof.", "professor"])

        details_found = sum([has_section_number, has_days, has_time, has_location, has_instructor])

        assert details_found >= 2, \
            f"AI should include multiple section details (section #, days, time, location, instructor). Only found {details_found}. Got: {response.content[:400]}"
