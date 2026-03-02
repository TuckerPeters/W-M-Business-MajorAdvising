"""
Unit tests for ConversationService

Tests conversation persistence with mocked Firestore.
"""

import pytest
from unittest.mock import patch, MagicMock
from services.conversation import ConversationService


class TestConversationService:
    """Tests for ConversationService CRUD operations."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.conversation.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create ConversationService with mocked database"""
        with patch('services.conversation.initialize_firebase'):
            return ConversationService()

    # --- create_conversation ---

    def test_create_conversation(self, service, mock_db):
        """Should create a conversation with correct fields"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "conv_123"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.create_conversation(
            user_id="user_1",
            student_id="student_1",
            user_role="student"
        )

        assert result["studentId"] == "student_1"
        assert result["userId"] == "user_1"
        assert result["userRole"] == "student"
        assert result["status"] == "active"
        assert result["messageCount"] == 0
        assert result["title"] == ""
        assert result["id"] == "conv_123"
        mock_doc_ref.set.assert_called_once()

    def test_create_conversation_with_title(self, service, mock_db):
        """Should use provided title"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "conv_456"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.create_conversation(
            user_id="user_1",
            student_id="student_1",
            user_role="student",
            title="My Chat"
        )

        assert result["title"] == "My Chat"

    def test_create_conversation_advisor(self, service, mock_db):
        """Should allow advisor to create conversation about a student"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "conv_789"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.create_conversation(
            user_id="advisor_1",
            student_id="student_1",
            user_role="advisor"
        )

        assert result["userId"] == "advisor_1"
        assert result["studentId"] == "student_1"
        assert result["userRole"] == "advisor"

    # --- get_conversation ---

    def test_get_conversation_found(self, service, mock_db):
        """Should return conversation when it exists"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "conv_123"
        mock_doc.to_dict.return_value = {
            "studentId": "student_1",
            "userId": "user_1",
            "title": "Test Chat",
            "status": "active"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = service.get_conversation("conv_123")

        assert result is not None
        assert result["id"] == "conv_123"
        assert result["title"] == "Test Chat"

    def test_get_conversation_not_found(self, service, mock_db):
        """Should return None when conversation doesn't exist"""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = service.get_conversation("nonexistent")

        assert result is None

    # --- list_conversations ---

    def test_list_conversations(self, service, mock_db):
        """Should return conversations for a student"""
        mock_doc_1 = MagicMock()
        mock_doc_1.id = "conv_1"
        mock_doc_1.to_dict.return_value = {
            "studentId": "student_1",
            "title": "First Chat",
            "updatedAt": "2025-01-02T00:00:00"
        }
        mock_doc_2 = MagicMock()
        mock_doc_2.id = "conv_2"
        mock_doc_2.to_dict.return_value = {
            "studentId": "student_1",
            "title": "Second Chat",
            "updatedAt": "2025-01-01T00:00:00"
        }

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_doc_1, mock_doc_2]
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.list_conversations("student_1")

        assert len(result) == 2
        assert result[0]["id"] == "conv_1"
        assert result[1]["id"] == "conv_2"

    def test_list_conversations_empty(self, service, mock_db):
        """Should return empty list when no conversations"""
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.list_conversations("student_1")

        assert result == []

    def test_list_conversations_pagination(self, service, mock_db):
        """Should respect limit and offset"""
        docs = []
        for i in range(5):
            doc = MagicMock()
            doc.id = f"conv_{i}"
            doc.to_dict.return_value = {"studentId": "student_1", "title": f"Chat {i}"}
            docs.append(doc)

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = docs
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.list_conversations("student_1", limit=2, offset=2)

        assert len(result) == 2
        assert result[0]["id"] == "conv_2"
        assert result[1]["id"] == "conv_3"

    # --- add_message ---

    def test_add_message_user(self, service, mock_db):
        """Should add a user message"""
        mock_msg_ref = MagicMock()
        mock_msg_ref.id = "msg_1"
        mock_db.collection.return_value.document.return_value = mock_msg_ref

        # Mock conversation lookup for update
        mock_conv_doc = MagicMock()
        mock_conv_doc.exists = True
        mock_conv_doc.to_dict.return_value = {
            "messageCount": 0,
            "title": ""
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_conv_doc

        result = service.add_message("conv_1", "user", "What courses should I take?")

        assert result["role"] == "user"
        assert result["content"] == "What courses should I take?"
        assert result["conversationId"] == "conv_1"
        assert result["id"] == "msg_1"

    def test_add_message_assistant_with_metadata(self, service, mock_db):
        """Should add an assistant message with citations, risks, nextSteps"""
        mock_msg_ref = MagicMock()
        mock_msg_ref.id = "msg_2"
        mock_db.collection.return_value.document.return_value = mock_msg_ref

        mock_conv_doc = MagicMock()
        mock_conv_doc.exists = True
        mock_conv_doc.to_dict.return_value = {
            "messageCount": 1,
            "title": "Existing Title"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_conv_doc

        citations = [{"source": "Finance Requirements", "excerpt": "BUAD 323"}]
        risks = [{"type": "prereq", "severity": "high", "message": "Missing BUAD 203"}]
        next_steps = [{"action": "Meet advisor", "priority": "high"}]

        result = service.add_message(
            "conv_1", "assistant", "I recommend BUAD 327.",
            citations=citations,
            risks=risks,
            next_steps=next_steps
        )

        assert result["role"] == "assistant"
        assert result["citations"] == citations
        assert result["risks"] == risks
        assert result["nextSteps"] == next_steps

    def test_add_message_auto_generates_title(self, service, mock_db):
        """Should auto-generate title from first user message when title is empty"""
        mock_msg_ref = MagicMock()
        mock_msg_ref.id = "msg_1"
        mock_db.collection.return_value.document.return_value = mock_msg_ref

        mock_conv_ref = MagicMock()
        mock_conv_doc = MagicMock()
        mock_conv_doc.exists = True
        mock_conv_doc.to_dict.return_value = {
            "messageCount": 0,
            "title": ""  # Empty title
        }
        mock_conv_ref.get.return_value = mock_conv_doc

        # Make collection().document() return different refs for messages vs conversations
        def collection_side_effect(name):
            mock_coll = MagicMock()
            if name == "conversation_messages":
                mock_coll.document.return_value = mock_msg_ref
            else:
                mock_coll.document.return_value = mock_conv_ref
            return mock_coll

        mock_db.collection.side_effect = collection_side_effect

        service.add_message("conv_1", "user", "What Finance courses do I need?")

        # Verify title was set in the update call
        update_call = mock_conv_ref.update.call_args[0][0]
        assert update_call["title"] == "What Finance courses do I need?"

    def test_add_message_does_not_overwrite_title(self, service, mock_db):
        """Should not overwrite existing title"""
        mock_msg_ref = MagicMock()
        mock_msg_ref.id = "msg_2"
        mock_db.collection.return_value.document.return_value = mock_msg_ref

        mock_conv_ref = MagicMock()
        mock_conv_doc = MagicMock()
        mock_conv_doc.exists = True
        mock_conv_doc.to_dict.return_value = {
            "messageCount": 1,
            "title": "Already Has Title"
        }
        mock_conv_ref.get.return_value = mock_conv_doc

        def collection_side_effect(name):
            mock_coll = MagicMock()
            if name == "conversation_messages":
                mock_coll.document.return_value = mock_msg_ref
            else:
                mock_coll.document.return_value = mock_conv_ref
            return mock_coll

        mock_db.collection.side_effect = collection_side_effect

        service.add_message("conv_1", "user", "Follow up question")

        update_call = mock_conv_ref.update.call_args[0][0]
        assert "title" not in update_call

    def test_add_message_increments_count(self, service, mock_db):
        """Should increment messageCount"""
        mock_msg_ref = MagicMock()
        mock_msg_ref.id = "msg_1"
        mock_db.collection.return_value.document.return_value = mock_msg_ref

        mock_conv_ref = MagicMock()
        mock_conv_doc = MagicMock()
        mock_conv_doc.exists = True
        mock_conv_doc.to_dict.return_value = {
            "messageCount": 5,
            "title": "Existing"
        }
        mock_conv_ref.get.return_value = mock_conv_doc

        def collection_side_effect(name):
            mock_coll = MagicMock()
            if name == "conversation_messages":
                mock_coll.document.return_value = mock_msg_ref
            else:
                mock_coll.document.return_value = mock_conv_ref
            return mock_coll

        mock_db.collection.side_effect = collection_side_effect

        service.add_message("conv_1", "user", "Another message")

        update_call = mock_conv_ref.update.call_args[0][0]
        assert update_call["messageCount"] == 6

    # --- get_messages ---

    def test_get_messages(self, service, mock_db):
        """Should return messages in chronological order"""
        mock_msg_1 = MagicMock()
        mock_msg_1.id = "msg_1"
        mock_msg_1.to_dict.return_value = {
            "conversationId": "conv_1",
            "role": "user",
            "content": "Hello",
            "createdAt": "2025-01-01T00:00:00"
        }
        mock_msg_2 = MagicMock()
        mock_msg_2.id = "msg_2"
        mock_msg_2.to_dict.return_value = {
            "conversationId": "conv_1",
            "role": "assistant",
            "content": "Hi there!",
            "createdAt": "2025-01-01T00:00:01"
        }

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_msg_1, mock_msg_2]
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.get_messages("conv_1")

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_get_messages_empty(self, service, mock_db):
        """Should return empty list when no messages"""
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.get_messages("conv_1")

        assert result == []

    # --- update_conversation_title ---

    def test_update_title(self, service, mock_db):
        """Should update conversation title"""
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc_ref.get.return_value = mock_doc

        # After update, return updated data
        mock_updated_doc = MagicMock()
        mock_updated_doc.to_dict.return_value = {
            "title": "New Title",
            "studentId": "student_1"
        }
        mock_doc_ref.get.side_effect = [mock_doc, mock_updated_doc]

        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_conversation_title("conv_1", "New Title")

        assert result is not None
        assert result["title"] == "New Title"
        mock_doc_ref.update.assert_called_once()

    def test_update_title_not_found(self, service, mock_db):
        """Should return None when conversation not found"""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = service.update_conversation_title("nonexistent", "Title")

        assert result is None

    # --- archive_conversation ---

    def test_archive_conversation(self, service, mock_db):
        """Should set status to archived"""
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc_ref.get.return_value = mock_doc

        mock_updated_doc = MagicMock()
        mock_updated_doc.to_dict.return_value = {
            "status": "archived",
            "studentId": "student_1"
        }
        mock_doc_ref.get.side_effect = [mock_doc, mock_updated_doc]

        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.archive_conversation("conv_1")

        assert result is not None
        assert result["status"] == "archived"

    def test_archive_conversation_not_found(self, service, mock_db):
        """Should return None when conversation not found"""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = service.archive_conversation("nonexistent")

        assert result is None


class TestTitleGeneration:
    """Tests for conversation title auto-generation."""

    @pytest.fixture
    def service(self):
        with patch('services.conversation.get_firestore_client'):
            with patch('services.conversation.initialize_firebase'):
                return ConversationService()

    def test_short_message_used_as_title(self, service):
        """Messages under 60 chars should be used as-is"""
        title = service._generate_title("What courses should I take?")
        assert title == "What courses should I take?"

    def test_exactly_60_chars(self, service):
        """Messages of exactly 60 chars should be used as-is"""
        msg = "A" * 60
        title = service._generate_title(msg)
        assert title == msg
        assert len(title) == 60

    def test_long_message_truncated(self, service):
        """Messages over 60 chars should be truncated with ellipsis"""
        msg = "A" * 100
        title = service._generate_title(msg)
        assert title == "A" * 57 + "..."
        assert len(title) == 60

    def test_empty_message(self, service):
        """Empty message should return empty string"""
        title = service._generate_title("")
        assert title == ""


class TestSingleton:
    """Test singleton pattern."""

    def test_get_conversation_service_returns_instance(self):
        """Should return a ConversationService instance"""
        import services.conversation as conv_module
        conv_module._conversation_service = None

        with patch('services.conversation.initialize_firebase'):
            with patch('services.conversation.get_firestore_client'):
                from services.conversation import get_conversation_service
                svc = get_conversation_service()
                assert isinstance(svc, ConversationService)

                # Should return same instance
                svc2 = get_conversation_service()
                assert svc is svc2

        # Clean up
        conv_module._conversation_service = None
