"""
Unit tests for the AI chat service.

Tests chat functionality with mocked OpenAI and embeddings service.
"""

import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock


class TestChatService:
    """Tests for ChatService"""

    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI client"""
        with patch('services.chat.OpenAI') as mock:
            client = MagicMock()
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_embeddings(self):
        """Mock embeddings service"""
        with patch('services.chat.get_embeddings_service') as mock:
            embeddings = MagicMock()
            mock.return_value = embeddings
            embeddings.get_document_count.return_value = 10
            embeddings.search.return_value = []
            yield embeddings

    @pytest.fixture
    def mock_student_service(self):
        """Mock student service"""
        with patch('services.chat.get_student_service') as mock:
            student_svc = MagicMock()
            mock.return_value = student_svc

            # Mock student profile
            student_svc.get_student.return_value = {
                'firstName': 'Test',
                'lastName': 'Student',
                'classYear': 'Junior',
                'gpa': 3.5,
                'majorDeclared': True,
                'major': 'Finance',
                'intendedMajor': None,
                'concentration': None,
                'apCredits': 6,
                'holds': []
            }

            # Mock enrollments
            student_svc.get_student_courses.return_value = {
                'completed': [
                    {'courseCode': 'BUAD 300', 'courseName': 'Business Foundations', 'grade': 'A', 'credits': 3},
                    {'courseCode': 'BUAD 311', 'courseName': 'Marketing', 'grade': 'B+', 'credits': 3}
                ],
                'current': [
                    {'courseCode': 'BUAD 323', 'courseName': 'Financial Management', 'credits': 3}
                ],
                'planned': [
                    {'courseCode': 'BUAD 327', 'courseName': 'Investments', 'semester': 'Fall 2025'}
                ]
            }

            yield student_svc

    @pytest.fixture
    def service(self, mock_openai, mock_embeddings, mock_student_service):
        """Create ChatService with mocked dependencies"""
        with patch('services.chat.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                with patch('services.chat.load_curriculum_data', return_value=None):
                    from services.chat import ChatService
                    svc = ChatService()
                    svc._openai_client = mock_openai
                    svc._embeddings = mock_embeddings
                    svc._curriculum_loaded = True
                    svc._initialized = True
                    return svc

    def test_chat_basic_response(self, service, mock_openai):
        """Should return chat response"""
        # Mock OpenAI response with JSON
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Test response",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        result = service.chat(
            student_id="student123",
            message="What courses should I take?"
        )

        assert result.content == "Test response"
        assert isinstance(result.citations, list)
        assert isinstance(result.risks, list)
        assert isinstance(result.nextSteps, list)

    def test_chat_with_citations(self, service, mock_openai):
        """Should parse citations from response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "BUAD 327 requires BUAD 323.",
            "citations": [
                {"source": "Finance Major Requirements", "excerpt": "BUAD 327 prerequisites: BUAD 323"}
            ],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        result = service.chat(
            student_id="student123",
            message="What are prerequisites for BUAD 327?"
        )

        assert len(result.citations) == 1
        assert result.citations[0].source == "Finance Major Requirements"
        assert "BUAD 323" in result.citations[0].excerpt

    def test_chat_with_risks(self, service, mock_openai):
        """Should parse risks from response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "You should complete BUAD 323 first.",
            "citations": [],
            "risks": [
                {"type": "prerequisite", "severity": "high", "message": "Missing BUAD 323"}
            ],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        result = service.chat(
            student_id="student123",
            message="Can I take BUAD 327 next semester?"
        )

        assert len(result.risks) == 1
        assert result.risks[0].type == "prerequisite"
        assert result.risks[0].severity == "high"

    def test_chat_with_next_steps(self, service, mock_openai):
        """Should parse next steps from response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Here's your plan.",
            "citations": [],
            "risks": [],
            "nextSteps": [
                {"action": "Complete BUAD 323", "priority": "high", "deadline": "Fall 2025"},
                {"action": "Meet with advisor", "priority": "medium"}
            ]
        })
        mock_openai.chat.completions.create.return_value = mock_response

        result = service.chat(
            student_id="student123",
            message="How do I prepare for the Finance major?"
        )

        assert len(result.nextSteps) == 2
        assert result.nextSteps[0].action == "Complete BUAD 323"
        assert result.nextSteps[0].priority == "high"
        assert result.nextSteps[0].deadline == "Fall 2025"
        assert result.nextSteps[1].deadline is None

    def test_chat_with_history(self, service, mock_openai):
        """Should include chat history in request"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Response with context",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        history = [
            {"role": "user", "content": "I'm interested in Finance"},
            {"role": "assistant", "content": "Great choice!"}
        ]

        service.chat(
            student_id="student123",
            message="What courses do I need?",
            chat_history=history
        )

        # Verify history was passed
        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs['messages']

        # Should have system + context + history + current message
        user_messages = [m for m in messages if m['role'] == 'user']
        assert len(user_messages) >= 2  # History + current

    def test_chat_fallback_on_invalid_json(self, service, mock_openai):
        """Should fallback to raw text if JSON parsing fails"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a plain text response without JSON."
        mock_openai.chat.completions.create.return_value = mock_response

        result = service.chat(
            student_id="student123",
            message="Hello"
        )

        assert result.content == "This is a plain text response without JSON."
        assert len(result.citations) == 0
        assert len(result.risks) == 0
        assert len(result.nextSteps) == 0

    def test_chat_uses_context_from_rag(self, service, mock_openai, mock_embeddings):
        """Should include RAG context in chat request"""
        # Mock search results
        from services.embeddings import SearchResult
        mock_embeddings.search.return_value = [
            SearchResult(
                content="Finance major requires 21 credits",
                source="Finance Requirements",
                score=0.9,
                metadata={}
            )
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Response",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        service.chat(
            student_id="student123",
            message="How many credits for Finance?"
        )

        # Verify search was called
        mock_embeddings.search.assert_called_once()

        # Verify context was included in messages
        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']
        context_included = any('Finance Requirements' in msg for msg in system_messages)
        assert context_included

    def test_chat_includes_student_context(self, service, mock_openai, mock_student_service):
        """Should include student profile and courses in chat context"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Based on your completed courses...",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        service.chat(
            student_id="student123",
            message="What courses should I take next?"
        )

        # Verify student service was called
        mock_student_service.get_student.assert_called_once_with("student123")
        mock_student_service.get_student_courses.assert_called_once_with("student123")

        # Verify student context was included in messages
        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        # Check student profile info
        student_context = [msg for msg in system_messages if 'STUDENT PROFILE' in msg]
        assert len(student_context) == 1
        assert 'Test Student' in student_context[0]
        assert 'Finance' in student_context[0]
        assert 'GPA: 3.5' in student_context[0]

        # Check completed courses
        assert 'COMPLETED COURSES' in student_context[0]
        assert 'BUAD 300' in student_context[0]

        # Check current enrollment
        assert 'CURRENT ENROLLMENT' in student_context[0]
        assert 'BUAD 323' in student_context[0]

        # Check planned courses
        assert 'PLANNED COURSES' in student_context[0]
        assert 'BUAD 327' in student_context[0]

    def test_chat_handles_missing_student(self, service, mock_openai, mock_student_service):
        """Should handle gracefully when student not found"""
        mock_student_service.get_student.return_value = None

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "I can help with general advising questions.",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        result = service.chat(
            student_id="unknown123",
            message="What courses are available?"
        )

        # Should still return a response
        assert result.content == "I can help with general advising questions."

    def test_chat_includes_student_holds_alert(self, service, mock_openai, mock_student_service):
        """Should include holds as alerts in context"""
        mock_student_service.get_student.return_value = {
            'firstName': 'Test',
            'lastName': 'Student',
            'classYear': 'Junior',
            'gpa': 2.0,
            'majorDeclared': False,
            'major': None,
            'intendedMajor': 'Accounting',
            'holds': ['Academic', 'Financial']
        }
        mock_student_service.get_student_courses.return_value = {
            'completed': [],
            'current': [],
            'planned': []
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Response with holds",
            "citations": [],
            "risks": [{"type": "hold", "severity": "high", "message": "Active holds on account"}],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        service.chat(
            student_id="student123",
            message="Can I register for classes?"
        )

        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        # Verify holds are included
        student_context = [msg for msg in system_messages if 'STUDENT PROFILE' in msg]
        assert 'ALERT - Active Holds' in student_context[0]
        assert 'Academic' in student_context[0]
        assert 'Financial' in student_context[0]

        # Verify intended major shown for undeclared
        assert 'Intended Major: Accounting (not yet declared)' in student_context[0]

    def test_student_can_only_see_own_data(self, service, mock_openai, mock_student_service):
        """Students should only see their own data, not other students"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "I can help with general questions.",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        # Student trying to query another student's data
        service.chat(
            student_id="other_student456",
            message="What courses has this student taken?",
            user_id="student123",
            user_role="student"
        )

        # Verify student service was NOT called for the other student
        # (student123 should not be able to see other_student456's data)
        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        # Should NOT include student profile data
        student_context = [msg for msg in system_messages if 'STUDENT PROFILE' in msg]
        assert len(student_context) == 0

    def test_student_sees_own_data_when_querying_self(self, service, mock_openai, mock_student_service):
        """Students should see their own data when querying themselves"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Based on your profile...",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        # Student querying their own data
        service.chat(
            student_id="student123",
            message="What courses should I take?",
            user_id="student123",
            user_role="student"
        )

        # Verify student context IS included
        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        student_context = [msg for msg in system_messages if 'STUDENT PROFILE' in msg]
        assert len(student_context) == 1
        assert 'Test Student' in student_context[0]


class TestAdvisorChatContext:
    """Tests for advisor-specific chat context"""

    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI client"""
        with patch('services.chat.OpenAI') as mock:
            client = MagicMock()
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_embeddings(self):
        """Mock embeddings service"""
        with patch('services.chat.get_embeddings_service') as mock:
            embeddings = MagicMock()
            mock.return_value = embeddings
            embeddings.get_document_count.return_value = 10
            embeddings.search.return_value = []
            yield embeddings

    @pytest.fixture
    def mock_student_service(self):
        """Mock student service"""
        with patch('services.chat.get_student_service') as mock:
            student_svc = MagicMock()
            mock.return_value = student_svc

            # Return different profiles based on student ID
            def get_student(student_id):
                students = {
                    'student1': {
                        'firstName': 'Alice',
                        'lastName': 'Smith',
                        'classYear': 'Junior',
                        'gpa': 3.8,
                        'majorDeclared': True,
                        'major': 'Finance',
                        'holds': []
                    },
                    'student2': {
                        'firstName': 'Bob',
                        'lastName': 'Jones',
                        'classYear': 'Senior',
                        'gpa': 2.5,
                        'majorDeclared': True,
                        'major': 'Accounting',
                        'holds': ['Academic']
                    }
                }
                return students.get(student_id)

            student_svc.get_student.side_effect = get_student
            student_svc.get_student_courses.return_value = {
                'completed': [],
                'current': [],
                'planned': []
            }

            yield student_svc

    @pytest.fixture
    def mock_advisor_service(self):
        """Mock advisor service"""
        with patch('services.chat.get_advisor_service') as mock:
            advisor_svc = MagicMock()
            mock.return_value = advisor_svc

            # Mock advisees list
            advisor_svc.get_advisees.return_value = [
                {'studentId': 'student1'},
                {'studentId': 'student2'}
            ]

            yield advisor_svc

    @pytest.fixture
    def service(self, mock_openai, mock_embeddings, mock_student_service, mock_advisor_service):
        """Create ChatService with mocked dependencies"""
        with patch('services.chat.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                with patch('services.chat.load_curriculum_data', return_value=None):
                    from services.chat import ChatService
                    svc = ChatService()
                    svc._openai_client = mock_openai
                    svc._embeddings = mock_embeddings
                    svc._curriculum_loaded = True
                    svc._initialized = True
                    return svc

    def test_advisor_sees_all_advisees(self, service, mock_openai, mock_advisor_service):
        """Advisors should see all their advisees when no specific student is targeted"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Here's an overview of your advisees...",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        # Advisor querying without specific student
        service.chat(
            student_id=None,
            message="How are my advisees doing?",
            user_id="advisor123",
            user_role="advisor"
        )

        # Verify advisor service was called
        mock_advisor_service.get_advisees.assert_called_once_with("advisor123")

        # Verify context includes advisor view
        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        advisor_context = [msg for msg in system_messages if 'ADVISOR VIEW' in msg]
        assert len(advisor_context) == 1
        assert 'Alice Smith' in advisor_context[0]
        assert 'Bob Jones' in advisor_context[0]

    def test_advisor_sees_specific_student_detail(self, service, mock_openai, mock_advisor_service):
        """Advisors should see full detail for a specific advisee"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Here's Alice's information...",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        # Advisor querying specific student
        service.chat(
            student_id="student1",
            message="Tell me about Alice's progress",
            user_id="advisor123",
            user_role="advisor"
        )

        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        # Should include advisor view with student details
        advisor_context = [msg for msg in system_messages if 'ADVISOR VIEW' in msg]
        assert len(advisor_context) == 1
        # Should have full student profile for Alice
        assert 'STUDENT PROFILE' in advisor_context[0]
        assert 'Alice' in advisor_context[0]

    def test_advisor_sees_holds_for_advisees(self, service, mock_openai, mock_advisor_service):
        """Advisors should see holds/alerts for their advisees"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "content": "Some advisees have holds...",
            "citations": [],
            "risks": [],
            "nextSteps": []
        })
        mock_openai.chat.completions.create.return_value = mock_response

        service.chat(
            student_id=None,
            message="Do any of my advisees have holds?",
            user_id="advisor123",
            user_role="advisor"
        )

        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_messages = [m['content'] for m in messages if m['role'] == 'system']

        advisor_context = [msg for msg in system_messages if 'ADVISOR VIEW' in msg]
        # Bob has an Academic hold
        assert 'HOLDS' in advisor_context[0] or 'Academic' in advisor_context[0]


class TestChatServiceInitialization:
    """Tests for ChatService initialization"""

    def test_missing_api_key_raises_error(self):
        """Should raise error if OPENAI_API_KEY not set"""
        with patch('services.chat.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {}, clear=True):
                import os
                if 'OPENAI_API_KEY' in os.environ:
                    del os.environ['OPENAI_API_KEY']

                from services.chat import ChatService
                service = ChatService()

                with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                    service._ensure_initialized()

    def test_missing_openai_package(self):
        """Should raise error if openai package not available"""
        with patch('services.chat.OPENAI_AVAILABLE', False):
            from services.chat import ChatService
            service = ChatService()

            with pytest.raises(RuntimeError, match="OpenAI package not installed"):
                service._ensure_initialized()


class TestChatServiceCurriculumLoading:
    """Tests for curriculum data loading"""

    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI client"""
        with patch('services.chat.OpenAI') as mock:
            client = MagicMock()
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_embeddings(self):
        """Mock embeddings service"""
        embeddings = MagicMock()
        embeddings.get_document_count.return_value = 0
        embeddings.add_documents = MagicMock()
        return embeddings

    def test_load_curriculum_data(self, mock_openai, mock_embeddings):
        """Should load curriculum into vector store"""
        curriculum_data = {
            "academic_year": "2025-2026",
            "core_curriculum": [
                {
                    "description": "Foundation",
                    "courses": [
                        {"code": "BUAD 300", "name": "Business Foundations", "credits": 3, "prerequisites": []}
                    ]
                }
            ],
            "majors": [
                {
                    "name": "Finance",
                    "credits_required": 21,
                    "required_courses": [
                        {
                            "description": "Required",
                            "courses": [
                                {"code": "BUAD 327", "name": "Investments", "credits": 3, "prerequisites": ["BUAD 323"]}
                            ]
                        }
                    ],
                    "elective_courses": []
                }
            ],
            "concentrations": []
        }

        with patch('services.chat.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                with patch('services.chat.load_curriculum_data', return_value=curriculum_data):
                    with patch('services.chat.get_embeddings_service', return_value=mock_embeddings):
                        from services.chat import ChatService
                        service = ChatService()
                        service._openai_client = mock_openai
                        service._embeddings = mock_embeddings
                        service._initialized = True
                        service._curriculum_loaded = False

                        service._load_curriculum_if_needed()

                        # Should have called add_documents
                        mock_embeddings.add_documents.assert_called_once()
                        docs = mock_embeddings.add_documents.call_args[0][0]
                        assert len(docs) > 0

    def test_skip_loading_if_already_loaded(self, mock_embeddings):
        """Should skip loading if curriculum already loaded"""
        with patch('services.chat.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                from services.chat import ChatService
                service = ChatService()
                service._embeddings = mock_embeddings
                service._curriculum_loaded = True

                service._load_curriculum_if_needed()

                mock_embeddings.add_documents.assert_not_called()

    def test_skip_loading_if_documents_exist(self, mock_embeddings):
        """Should skip loading if documents already in vector store"""
        mock_embeddings.get_document_count.return_value = 100

        with patch('services.chat.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                from services.chat import ChatService
                service = ChatService()
                service._embeddings = mock_embeddings
                service._curriculum_loaded = False

                service._load_curriculum_if_needed()

                mock_embeddings.add_documents.assert_not_called()
                assert service._curriculum_loaded is True


class TestChatDataClasses:
    """Tests for chat data classes"""

    def test_citation_creation(self):
        """Should create Citation with all fields"""
        from services.chat import Citation

        citation = Citation(
            source="Test Source",
            excerpt="Test excerpt",
            relevance=0.95
        )

        assert citation.source == "Test Source"
        assert citation.excerpt == "Test excerpt"
        assert citation.relevance == 0.95

    def test_risk_flag_creation(self):
        """Should create RiskFlag with all fields"""
        from services.chat import RiskFlag

        risk = RiskFlag(
            type="prerequisite",
            severity="high",
            message="Missing BUAD 323"
        )

        assert risk.type == "prerequisite"
        assert risk.severity == "high"
        assert risk.message == "Missing BUAD 323"

    def test_next_step_creation(self):
        """Should create NextStep with all fields"""
        from services.chat import NextStep

        step = NextStep(
            action="Complete BUAD 323",
            priority="high",
            deadline="Fall 2025"
        )

        assert step.action == "Complete BUAD 323"
        assert step.priority == "high"
        assert step.deadline == "Fall 2025"

    def test_next_step_optional_deadline(self):
        """Should allow NextStep without deadline"""
        from services.chat import NextStep

        step = NextStep(
            action="Meet with advisor",
            priority="medium"
        )

        assert step.deadline is None

    def test_chat_response_creation(self):
        """Should create ChatResponse with all fields"""
        from services.chat import ChatResponse, Citation, RiskFlag, NextStep

        response = ChatResponse(
            content="Test response",
            citations=[Citation("Source", "Excerpt", 0.9)],
            risks=[RiskFlag("test", "low", "Test message")],
            nextSteps=[NextStep("Action", "high")]
        )

        assert response.content == "Test response"
        assert len(response.citations) == 1
        assert len(response.risks) == 1
        assert len(response.nextSteps) == 1

    def test_chat_response_defaults(self):
        """Should create ChatResponse with default empty lists"""
        from services.chat import ChatResponse

        response = ChatResponse(content="Just text")

        assert response.content == "Just text"
        assert response.citations == []
        assert response.risks == []
        assert response.nextSteps == []


class TestResponseParsing:
    """Tests for response parsing logic"""

    @pytest.fixture
    def service(self):
        """Create minimal service for parsing tests"""
        with patch('services.chat.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                from services.chat import ChatService
                svc = ChatService()
                svc._initialized = True
                svc._curriculum_loaded = True
                return svc

    def test_parse_valid_json(self, service):
        """Should parse valid JSON response"""
        response_text = json.dumps({
            "content": "Here is the answer",
            "citations": [{"source": "Source A", "excerpt": "Quote"}],
            "risks": [{"type": "deadline", "severity": "medium", "message": "Deadline soon"}],
            "nextSteps": [{"action": "Register", "priority": "high"}]
        })

        result = service._parse_response(response_text)

        assert result.content == "Here is the answer"
        assert len(result.citations) == 1
        assert len(result.risks) == 1
        assert len(result.nextSteps) == 1

    def test_parse_json_in_markdown(self, service):
        """Should extract JSON from markdown code blocks"""
        response_text = '''Here is some text before.

```json
{
    "content": "The answer",
    "citations": [],
    "risks": [],
    "nextSteps": []
}
```

And some text after.'''

        result = service._parse_response(response_text)

        assert result.content == "The answer"

    def test_parse_plain_text_fallback(self, service):
        """Should use plain text when no JSON found"""
        response_text = "This is just plain text without any JSON structure."

        result = service._parse_response(response_text)

        assert result.content == response_text
        assert len(result.citations) == 0

    def test_parse_partial_json(self, service):
        """Should handle JSON with missing optional fields"""
        response_text = json.dumps({
            "content": "Response with minimal data"
        })

        result = service._parse_response(response_text)

        assert result.content == "Response with minimal data"
        assert result.citations == []
        assert result.risks == []
        assert result.nextSteps == []
