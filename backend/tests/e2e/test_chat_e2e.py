"""
E2E tests for Chat, Prerequisites, and Authenticated endpoints.

These tests run the real FastAPI server with mocked external services
(OpenAI, Firebase Auth) to test the actual HTTP layer behavior:
- Request validation
- Authentication/authorization enforcement
- Error handling and response formats
- Correct parameter passing to services
- Response transformation and serialization

We mock external services (OpenAI, Firestore) but test that our code
correctly validates, routes, and transforms requests/responses.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def mock_student_data():
    """Sample student data for testing."""
    return {
        "id": "test-student-123",
        "userId": "test-student-123",
        "name": "Test Student",
        "email": "teststudent@wm.edu",
        "classYear": 2026,
        "gpa": 3.5,
        "creditsEarned": 60,
        "declared": True,
        "intendedMajor": "Finance",
        "holds": []
    }


@pytest.fixture(scope="module")
def mock_prerequisite_data():
    """Sample prerequisite data for testing."""
    return {
        "BUAD 327": {
            "course_code": "BUAD 327",
            "course_name": "Investments",
            "credits": 3.0,
            "prerequisites": ["BUAD 323"],
            "semester_offered": "F/S"
        },
        "BUAD 323": {
            "course_code": "BUAD 323",
            "course_name": "Financial Management",
            "credits": 3.0,
            "prerequisites": ["BUAD 203", "ACCT 203"],
            "semester_offered": "F/S"
        },
        "BUAD 203": {
            "course_code": "BUAD 203",
            "course_name": "Introduction to Business",
            "credits": 3.0,
            "prerequisites": [],
            "semester_offered": "F/S"
        }
    }


@pytest.fixture(scope="module")
def authenticated_app_client(mock_student_data, mock_prerequisite_data):
    """
    Create a test client with mocked authentication and services.

    Note: We test that our server code correctly:
    - Validates incoming requests
    - Enforces authentication
    - Calls services with correct parameters
    - Transforms responses correctly
    - Handles errors appropriately
    """
    # Mock Firestore
    mock_db = MagicMock()
    mock_db.collection.return_value.stream.return_value = []
    mock_db.collection.return_value.select.return_value.stream.return_value = []
    mock_db.collection.return_value.where.return_value.stream.return_value = []
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []

    # Mock student service - return different data based on student ID
    mock_student_service = MagicMock()

    def get_student_by_id(student_id):
        if student_id == "test-student-123":
            return mock_student_data
        elif student_id == "nonexistent-student":
            return None
        return None

    mock_student_service.get_student.side_effect = get_student_by_id
    mock_student_service.get_student_courses.return_value = {
        "completed": [
            {"id": "1", "studentId": "test-student-123", "courseCode": "BUAD 203",
             "term": "202310", "grade": "A", "status": "completed", "credits": 3}
        ],
        "current": [
            {"id": "2", "studentId": "test-student-123", "courseCode": "BUAD 323",
             "term": "202410", "grade": None, "status": "enrolled", "credits": 3}
        ],
        "planned": []
    }
    mock_student_service.get_degree_milestones.return_value = []

    # Mock prerequisite engine with real lookup logic
    mock_prereq_engine = MagicMock()

    class MockPrereqInfo:
        def __init__(self, data):
            self.course_code = data["course_code"]
            self.course_name = data["course_name"]
            self.credits = data["credits"]
            self.prerequisites = data["prerequisites"]
            self.semester_offered = data["semester_offered"]

    def get_prerequisites(course_code):
        code = course_code.replace("_", " ")
        if code in mock_prerequisite_data:
            return MockPrereqInfo(mock_prerequisite_data[code])
        return None  # Returns None for unknown courses

    mock_prereq_engine.get_prerequisites.side_effect = get_prerequisites

    def get_prerequisite_chain(course_code):
        code = course_code.replace("_", " ")
        if code == "BUAD 327":
            return {
                "course": "BUAD 327",
                "prerequisites": [
                    {
                        "course": "BUAD 323",
                        "prerequisites": [
                            {"course": "BUAD 203", "prerequisites": []},
                            {"course": "ACCT 203", "prerequisites": []}
                        ]
                    }
                ]
            }
        elif code in mock_prerequisite_data:
            return {"course": code, "prerequisites": []}
        return {"course": code, "prerequisites": []}

    mock_prereq_engine.get_prerequisite_chain.side_effect = get_prerequisite_chain

    # Mock authenticated user
    from core.auth import AuthenticatedUser, UserRole, get_current_user, get_current_advisor
    mock_user = AuthenticatedUser(
        uid="test-student-123",
        email="teststudent@wm.edu",
        email_verified=True,
        role=UserRole.STUDENT
    )

    mock_advisor = AuthenticatedUser(
        uid="test-advisor-123",
        email="testadvisor@wm.edu",
        email_verified=True,
        role=UserRole.ADVISOR
    )

    with patch('core.config.initialize_firebase'):
        with patch('core.auth.initialize_firebase'):
            with patch('core.config.get_firestore_client', return_value=mock_db):
                with patch('server.initialize_firebase'):
                    with patch('server.get_firestore_client', return_value=mock_db):
                        with patch('server.get_student_service', return_value=mock_student_service):
                            with patch('server.get_prerequisite_engine', return_value=mock_prereq_engine):
                                from server import app
                                app.state.enable_scheduler = False

                                async def mock_get_current_user():
                                    return mock_user

                                async def mock_get_current_advisor():
                                    return mock_advisor

                                app.dependency_overrides[get_current_user] = mock_get_current_user
                                app.dependency_overrides[get_current_advisor] = mock_get_current_advisor

                                with patch('server.verify_user_access', return_value=True):
                                    with TestClient(app) as client:
                                        yield {
                                            "client": client,
                                            "mock_db": mock_db,
                                            "mock_student_service": mock_student_service,
                                            "mock_prereq_engine": mock_prereq_engine,
                                            "mock_user": mock_user,
                                            "mock_advisor": mock_advisor,
                                        }

                                app.dependency_overrides.clear()


@pytest.mark.e2e
class TestPrerequisitesEndpoints:
    """
    Test prerequisite endpoints - verifying the server correctly:
    - Routes requests to the prerequisite engine
    - Transforms engine responses to API format
    - Handles missing courses with 404
    - Handles URL encoding of course codes
    """

    def test_get_course_prerequisites_calls_engine(self, authenticated_app_client, timed_request):
        """Verify server calls prerequisite engine with correct course code."""
        client = authenticated_app_client["client"]
        mock_engine = authenticated_app_client["mock_prereq_engine"]
        mock_engine.get_prerequisites.reset_mock()

        response, elapsed = timed_request(client, "GET", "/api/courses/BUAD_327/prerequisites")

        assert response.status_code == 200
        # Server converts underscores to spaces before calling engine
        mock_engine.get_prerequisites.assert_called_once_with("BUAD 327")

        # Verify response contains transformed data
        data = response.json()
        assert data["course_code"] == "BUAD 327"
        assert data["course_name"] == "Investments"
        assert "BUAD 323" in data["prerequisites"]

    def test_get_course_prerequisites_not_found_returns_404(self, authenticated_app_client, timed_request):
        """Verify server returns 404 when engine returns None."""
        client = authenticated_app_client["client"]

        response, elapsed = timed_request(client, "GET", "/api/courses/FAKE_999/prerequisites")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_prerequisite_chain_returns_nested_structure(self, authenticated_app_client, timed_request):
        """Verify chain endpoint returns nested prerequisite tree."""
        client = authenticated_app_client["client"]
        mock_engine = authenticated_app_client["mock_prereq_engine"]
        mock_engine.get_prerequisite_chain.reset_mock()

        response, elapsed = timed_request(client, "GET", "/api/courses/BUAD_327/prerequisite-chain")

        assert response.status_code == 200
        mock_engine.get_prerequisite_chain.assert_called_once()

        data = response.json()
        # Verify nested structure is preserved
        assert data["course"] == "BUAD 327"
        assert len(data["prerequisites"]) == 1
        assert data["prerequisites"][0]["course"] == "BUAD 323"
        assert len(data["prerequisites"][0]["prerequisites"]) == 2

    def test_url_encoded_course_code_handled(self, authenticated_app_client, timed_request):
        """Verify URL-encoded course codes (with %20 for space) work."""
        client = authenticated_app_client["client"]

        # Using URL encoding for space
        response, elapsed = timed_request(client, "GET", "/api/courses/BUAD%20327/prerequisites")

        # Should work the same as underscore
        assert response.status_code == 200
        data = response.json()
        assert data["course_code"] == "BUAD 327"


@pytest.mark.e2e
class TestStudentProfileEndpoints:
    """
    Test student profile endpoints - verifying the server:
    - Calls student service with correct IDs
    - Transforms service responses to API format
    - Returns correct structure for courses endpoint
    """

    def test_get_student_profile_calls_service(self, authenticated_app_client, timed_request):
        """Verify server calls student service and transforms response."""
        client = authenticated_app_client["client"]
        mock_service = authenticated_app_client["mock_student_service"]
        mock_service.get_student.reset_mock()

        response, elapsed = timed_request(client, "GET", "/api/student/test-student-123/profile")

        assert response.status_code == 200
        # Verify service was called with correct student ID
        mock_service.get_student.assert_called_with("test-student-123")

        data = response.json()
        assert data["userId"] == "test-student-123"
        assert data["classYear"] == 2026
        assert data["gpa"] == 3.5

    def test_get_student_courses_returns_grouped_data(self, authenticated_app_client, timed_request):
        """Verify courses endpoint returns properly grouped enrollments."""
        client = authenticated_app_client["client"]
        mock_service = authenticated_app_client["mock_student_service"]

        response, elapsed = timed_request(client, "GET", "/api/student/test-student-123/courses")

        assert response.status_code == 200
        mock_service.get_student_courses.assert_called()

        data = response.json()
        # Verify all three groups exist
        assert "completed" in data
        assert "current" in data
        assert "planned" in data
        # Verify data matches what service returned
        assert len(data["completed"]) == 1
        assert data["completed"][0]["courseCode"] == "BUAD 203"


@pytest.mark.e2e
class TestMilestonesEndpoints:
    """Test milestone endpoints."""

    def test_get_degree_milestones_returns_list(self, authenticated_app_client, timed_request):
        """Verify milestones endpoint returns a list."""
        client = authenticated_app_client["client"]

        response, elapsed = timed_request(client, "GET", "/api/milestones")

        assert response.status_code == 200
        assert elapsed < 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.e2e
class TestChatEndpointValidation:
    """
    Test chat endpoint request validation and error handling.
    These tests verify the server correctly validates requests
    before they reach the chat service.
    """

    def test_chat_requires_student_id(self, authenticated_app_client, timed_request):
        """Chat endpoint should require studentId in request."""
        client = authenticated_app_client["client"]

        with patch('server.get_chat_service') as mock_get_chat:
            mock_chat = MagicMock()
            mock_get_chat.return_value = mock_chat

            response, elapsed = timed_request(
                client, "POST", "/api/chat/message",
                json={
                    # Missing studentId
                    "message": "Hello",
                    "chatHistory": []
                }
            )

        # Should fail validation before reaching chat service
        assert response.status_code == 422  # Validation error

    def test_chat_requires_message(self, authenticated_app_client, timed_request):
        """Chat endpoint should require message in request."""
        client = authenticated_app_client["client"]

        with patch('server.get_chat_service') as mock_get_chat:
            mock_chat = MagicMock()
            mock_get_chat.return_value = mock_chat

            response, elapsed = timed_request(
                client, "POST", "/api/chat/message",
                json={
                    "studentId": "test-student-123",
                    # Missing message
                    "chatHistory": []
                }
            )

        assert response.status_code == 422

    def test_chat_student_not_found_returns_404(self, authenticated_app_client, timed_request):
        """Chat should return 404 when student doesn't exist."""
        client = authenticated_app_client["client"]

        with patch('server.get_chat_service') as mock_get_chat:
            mock_chat = MagicMock()
            mock_get_chat.return_value = mock_chat

            response, elapsed = timed_request(
                client, "POST", "/api/chat/message",
                json={
                    "studentId": "nonexistent-student",
                    "message": "Hello",
                    "chatHistory": []
                }
            )

        # Student service returns None for nonexistent-student
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        # Chat service should NOT be called for nonexistent student
        mock_chat.chat.assert_not_called()


@pytest.mark.e2e
class TestChatServiceIntegration:
    """
    Test that chat endpoint correctly integrates with chat service.
    Verifies the server passes correct parameters to the service
    and correctly transforms responses.
    """

    def test_chat_passes_correct_params_to_service(self, authenticated_app_client, timed_request):
        """Verify server passes all parameters to chat service correctly."""
        client = authenticated_app_client["client"]
        mock_user = authenticated_app_client["mock_user"]

        with patch('server.get_chat_service') as mock_get_chat:
            from services.chat import ChatResponse

            mock_chat = MagicMock()
            mock_chat.chat.return_value = ChatResponse(content="Test response")
            mock_get_chat.return_value = mock_chat

            response, elapsed = timed_request(
                client, "POST", "/api/chat/message",
                json={
                    "studentId": "test-student-123",
                    "message": "What courses should I take?",
                    "chatHistory": [
                        {"role": "user", "content": "Previous question"},
                        {"role": "assistant", "content": "Previous answer"}
                    ]
                }
            )

        assert response.status_code == 200

        # Verify chat service was called with correct parameters
        mock_chat.chat.assert_called_once()
        call_kwargs = mock_chat.chat.call_args.kwargs

        assert call_kwargs["student_id"] == "test-student-123"
        assert call_kwargs["message"] == "What courses should I take?"
        assert len(call_kwargs["chat_history"]) == 2
        assert call_kwargs["user_id"] == mock_user.uid
        assert call_kwargs["user_role"] == mock_user.role.value

    def test_chat_transforms_citations_correctly(self, authenticated_app_client, timed_request):
        """Verify server correctly transforms citations from service response."""
        client = authenticated_app_client["client"]

        with patch('server.get_chat_service') as mock_get_chat:
            from services.chat import ChatResponse, Citation

            mock_chat = MagicMock()
            mock_chat.chat.return_value = ChatResponse(
                content="Response with citations",
                citations=[
                    Citation(source="Policy Doc", excerpt="Some text", relevance=0.95),
                    Citation(source="Curriculum", excerpt="Other text", relevance=0.8)
                ]
            )
            mock_get_chat.return_value = mock_chat

            response, elapsed = timed_request(
                client, "POST", "/api/chat/message",
                json={
                    "studentId": "test-student-123",
                    "message": "Question",
                    "chatHistory": []
                }
            )

        assert response.status_code == 200
        data = response.json()

        # Verify citations were transformed to API format
        assert len(data["citations"]) == 2
        assert data["citations"][0]["source"] == "Policy Doc"
        assert data["citations"][0]["excerpt"] == "Some text"
        assert data["citations"][0]["relevance"] == 0.95

    def test_chat_transforms_risks_correctly(self, authenticated_app_client, timed_request):
        """Verify server correctly transforms risk flags from service response."""
        client = authenticated_app_client["client"]

        with patch('server.get_chat_service') as mock_get_chat:
            from services.chat import ChatResponse, RiskFlag

            mock_chat = MagicMock()
            mock_chat.chat.return_value = ChatResponse(
                content="Response with risks",
                risks=[
                    RiskFlag(type="prerequisite", severity="high", message="Missing prereq"),
                    RiskFlag(type="workload", severity="medium", message="Heavy load")
                ]
            )
            mock_get_chat.return_value = mock_chat

            response, elapsed = timed_request(
                client, "POST", "/api/chat/message",
                json={
                    "studentId": "test-student-123",
                    "message": "Question",
                    "chatHistory": []
                }
            )

        assert response.status_code == 200
        data = response.json()

        # Verify risks were transformed to API format
        assert len(data["risks"]) == 2
        assert data["risks"][0]["type"] == "prerequisite"
        assert data["risks"][0]["severity"] == "high"
        assert data["risks"][1]["severity"] == "medium"

    def test_chat_transforms_next_steps_correctly(self, authenticated_app_client, timed_request):
        """Verify server correctly transforms next steps from service response."""
        client = authenticated_app_client["client"]

        with patch('server.get_chat_service') as mock_get_chat:
            from services.chat import ChatResponse, NextStep

            mock_chat = MagicMock()
            mock_chat.chat.return_value = ChatResponse(
                content="Response with steps",
                nextSteps=[
                    NextStep(action="Complete BUAD 323", priority="high", deadline="Fall 2025"),
                    NextStep(action="Meet advisor", priority="medium", deadline=None)
                ]
            )
            mock_get_chat.return_value = mock_chat

            response, elapsed = timed_request(
                client, "POST", "/api/chat/message",
                json={
                    "studentId": "test-student-123",
                    "message": "Question",
                    "chatHistory": []
                }
            )

        assert response.status_code == 200
        data = response.json()

        # Verify next steps were transformed correctly
        assert len(data["nextSteps"]) == 2
        assert data["nextSteps"][0]["action"] == "Complete BUAD 323"
        assert data["nextSteps"][0]["deadline"] == "Fall 2025"
        assert data["nextSteps"][1]["deadline"] is None


@pytest.mark.e2e
class TestChatErrorHandling:
    """Test chat endpoint error handling."""

    def test_chat_service_unavailable_returns_503(self, authenticated_app_client, timed_request):
        """Verify 503 when chat service throws RuntimeError."""
        client = authenticated_app_client["client"]

        with patch('server.get_chat_service') as mock_get_chat:
            mock_chat = MagicMock()
            mock_chat.chat.side_effect = RuntimeError("OpenAI API key not configured")
            mock_get_chat.return_value = mock_chat

            response, elapsed = timed_request(
                client, "POST", "/api/chat/message",
                json={
                    "studentId": "test-student-123",
                    "message": "Hello",
                    "chatHistory": []
                }
            )

        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()

    def test_chat_empty_response_handled(self, authenticated_app_client, timed_request):
        """Verify server handles empty chat response gracefully."""
        client = authenticated_app_client["client"]

        with patch('server.get_chat_service') as mock_get_chat:
            from services.chat import ChatResponse

            mock_chat = MagicMock()
            # Minimal response with just content
            mock_chat.chat.return_value = ChatResponse(content="")
            mock_get_chat.return_value = mock_chat

            response, elapsed = timed_request(
                client, "POST", "/api/chat/message",
                json={
                    "studentId": "test-student-123",
                    "message": "Hello",
                    "chatHistory": []
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == ""
        assert data["citations"] == []
        assert data["risks"] == []
        assert data["nextSteps"] == []


@pytest.mark.e2e
class TestConversationEndpoints:
    """
    Test conversation CRUD endpoints.
    Verifies server correctly routes, validates, and transforms
    conversation requests/responses.
    """

    def test_create_conversation(self, authenticated_app_client, timed_request):
        """Should create a conversation and return it."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.create_conversation.return_value = {
            "id": "conv_123",
            "studentId": "test-student-123",
            "userId": "test-student-123",
            "userRole": "student",
            "title": "",
            "status": "active",
            "messageCount": 0,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
            "lastMessagePreview": ""
        }

        with patch('server.get_conversation_service', return_value=mock_conv_service):
            response, elapsed = timed_request(
                client, "POST", "/api/conversations",
                json={"studentId": "test-student-123"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "conv_123"
        assert data["studentId"] == "test-student-123"
        assert data["status"] == "active"

    def test_list_conversations(self, authenticated_app_client, timed_request):
        """Should list conversations for a student."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.list_conversations.return_value = [
            {
                "id": "conv_1",
                "studentId": "test-student-123",
                "userId": "test-student-123",
                "userRole": "student",
                "title": "Course Planning",
                "status": "active",
                "messageCount": 4,
                "createdAt": "2025-01-01T00:00:00",
                "updatedAt": "2025-01-02T00:00:00",
                "lastMessagePreview": "Thanks for the help!"
            }
        ]

        with patch('server.get_conversation_service', return_value=mock_conv_service):
            response, elapsed = timed_request(
                client, "GET", "/api/student/test-student-123/conversations"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["conversations"][0]["title"] == "Course Planning"
        assert data["conversations"][0]["messageCount"] == 4

    def test_get_conversation(self, authenticated_app_client, timed_request):
        """Should get a single conversation by ID."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.get_conversation.return_value = {
            "id": "conv_123",
            "studentId": "test-student-123",
            "userId": "test-student-123",
            "userRole": "student",
            "title": "Finance Questions",
            "status": "active",
            "messageCount": 2,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
            "lastMessagePreview": "I recommend BUAD 327"
        }

        with patch('server.get_conversation_service', return_value=mock_conv_service):
            response, elapsed = timed_request(
                client, "GET", "/api/conversations/conv_123"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "conv_123"
        assert data["title"] == "Finance Questions"

    def test_get_conversation_not_found(self, authenticated_app_client, timed_request):
        """Should return 404 for nonexistent conversation."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.get_conversation.return_value = None

        with patch('server.get_conversation_service', return_value=mock_conv_service):
            response, elapsed = timed_request(
                client, "GET", "/api/conversations/nonexistent"
            )

        assert response.status_code == 404

    def test_get_conversation_messages(self, authenticated_app_client, timed_request):
        """Should return messages in chronological order."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.get_conversation.return_value = {
            "id": "conv_123",
            "studentId": "test-student-123",
            "userId": "test-student-123",
            "userRole": "student",
            "title": "Chat",
            "status": "active",
            "messageCount": 2,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
            "lastMessagePreview": ""
        }
        mock_conv_service.get_messages.return_value = [
            {
                "id": "msg_1",
                "conversationId": "conv_123",
                "role": "user",
                "content": "What courses should I take?",
                "citations": [],
                "risks": [],
                "nextSteps": [],
                "createdAt": "2025-01-01T00:00:00"
            },
            {
                "id": "msg_2",
                "conversationId": "conv_123",
                "role": "assistant",
                "content": "I recommend BUAD 327.",
                "citations": [{"source": "Finance Req", "excerpt": "...", "relevance": 0.9}],
                "risks": [],
                "nextSteps": [],
                "createdAt": "2025-01-01T00:00:01"
            }
        ]

        with patch('server.get_conversation_service', return_value=mock_conv_service):
            response, elapsed = timed_request(
                client, "GET", "/api/conversations/conv_123/messages"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        assert len(data["messages"][1]["citations"]) == 1

    def test_update_conversation_title(self, authenticated_app_client, timed_request):
        """Should update conversation title."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.get_conversation.return_value = {
            "id": "conv_123",
            "studentId": "test-student-123",
            "userId": "test-student-123",
            "userRole": "student",
            "title": "Old Title",
            "status": "active",
            "messageCount": 0,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
            "lastMessagePreview": ""
        }
        mock_conv_service.update_conversation_title.return_value = {
            "id": "conv_123",
            "studentId": "test-student-123",
            "userId": "test-student-123",
            "userRole": "student",
            "title": "New Title",
            "status": "active",
            "messageCount": 0,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:01",
            "lastMessagePreview": ""
        }

        with patch('server.get_conversation_service', return_value=mock_conv_service):
            response, elapsed = timed_request(
                client, "PUT", "/api/conversations/conv_123/title",
                json={"title": "New Title"}
            )

        assert response.status_code == 200
        assert response.json()["title"] == "New Title"

    def test_archive_conversation(self, authenticated_app_client, timed_request):
        """Should archive a conversation."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.get_conversation.return_value = {
            "id": "conv_123",
            "studentId": "test-student-123",
            "userId": "test-student-123",
            "userRole": "student",
            "title": "Chat",
            "status": "active",
            "messageCount": 0,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
            "lastMessagePreview": ""
        }
        mock_conv_service.archive_conversation.return_value = {
            "id": "conv_123",
            "studentId": "test-student-123",
            "userId": "test-student-123",
            "userRole": "student",
            "title": "Chat",
            "status": "archived",
            "messageCount": 0,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:01",
            "lastMessagePreview": ""
        }

        with patch('server.get_conversation_service', return_value=mock_conv_service):
            response, elapsed = timed_request(
                client, "PUT", "/api/conversations/conv_123/archive"
            )

        assert response.status_code == 200
        assert response.json()["status"] == "archived"


@pytest.mark.e2e
class TestChatWithConversationPersistence:
    """
    Test that the chat endpoint correctly integrates with conversation persistence.
    Verifies messages are saved and conversationId is returned.
    """

    def test_chat_auto_creates_conversation(self, authenticated_app_client, timed_request):
        """Chat without conversationId should auto-create and return one."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.create_conversation.return_value = {
            "id": "auto_conv_1",
            "studentId": "test-student-123",
            "userId": "test-student-123",
            "userRole": "student",
            "title": "",
            "status": "active",
            "messageCount": 0,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
            "lastMessagePreview": ""
        }

        with patch('server.get_chat_service') as mock_get_chat:
            from services.chat import ChatResponse
            mock_chat = MagicMock()
            mock_chat.chat.return_value = ChatResponse(content="Hello!")
            mock_get_chat.return_value = mock_chat

            with patch('server.get_conversation_service', return_value=mock_conv_service):
                response, elapsed = timed_request(
                    client, "POST", "/api/chat/message",
                    json={
                        "studentId": "test-student-123",
                        "message": "Hello",
                        "chatHistory": []
                    }
                )

        assert response.status_code == 200
        data = response.json()
        assert data["conversationId"] == "auto_conv_1"

        # Verify both user and assistant messages were persisted
        assert mock_conv_service.add_message.call_count == 2
        user_call = mock_conv_service.add_message.call_args_list[0]
        assert user_call[0] == ("auto_conv_1", "user", "Hello")
        assistant_call = mock_conv_service.add_message.call_args_list[1]
        assert assistant_call[0][0] == "auto_conv_1"
        assert assistant_call[0][1] == "assistant"

    def test_chat_with_conversation_id_loads_history(self, authenticated_app_client, timed_request):
        """Chat with conversationId should load history from DB."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.get_conversation.return_value = {
            "id": "existing_conv",
            "studentId": "test-student-123",
            "userId": "test-student-123",
            "userRole": "student",
            "title": "Prior Chat",
            "status": "active",
            "messageCount": 2,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
            "lastMessagePreview": ""
        }
        mock_conv_service.get_messages.return_value = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]

        with patch('server.get_chat_service') as mock_get_chat:
            from services.chat import ChatResponse
            mock_chat = MagicMock()
            mock_chat.chat.return_value = ChatResponse(content="Follow up answer")
            mock_get_chat.return_value = mock_chat

            with patch('server.get_conversation_service', return_value=mock_conv_service):
                response, elapsed = timed_request(
                    client, "POST", "/api/chat/message",
                    json={
                        "studentId": "test-student-123",
                        "message": "Follow up",
                        "conversationId": "existing_conv"
                    }
                )

        assert response.status_code == 200
        data = response.json()
        assert data["conversationId"] == "existing_conv"

        # Verify chat service received loaded history
        chat_call = mock_chat.chat.call_args.kwargs
        assert len(chat_call["chat_history"]) == 2
        assert chat_call["chat_history"][0]["content"] == "Previous question"

    def test_chat_with_invalid_conversation_returns_404(self, authenticated_app_client, timed_request):
        """Chat with nonexistent conversationId should return 404."""
        client = authenticated_app_client["client"]

        mock_conv_service = MagicMock()
        mock_conv_service.get_conversation.return_value = None

        with patch('server.get_chat_service') as mock_get_chat:
            mock_chat = MagicMock()
            mock_get_chat.return_value = mock_chat

            with patch('server.get_conversation_service', return_value=mock_conv_service):
                response, elapsed = timed_request(
                    client, "POST", "/api/chat/message",
                    json={
                        "studentId": "test-student-123",
                        "message": "Hello",
                        "conversationId": "nonexistent"
                    }
                )

        assert response.status_code == 404
