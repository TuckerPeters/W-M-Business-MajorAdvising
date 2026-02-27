"""
Integration tests for ConversationService with real Firebase.

These tests create actual conversations and messages in Firestore and clean up after.
Run with: pytest tests/integration/test_conversation_integration.py -v
"""

import pytest
import time
from datetime import datetime

pytestmark = [pytest.mark.integration, pytest.mark.firebase]

from services.conversation import ConversationService, get_conversation_service
from core.config import initialize_firebase, get_firestore_client


# Test data prefix
TEST_PREFIX = "TEST_CONV_"


@pytest.fixture(scope="module")
def firebase_db():
    """Initialize Firebase and return the Firestore client."""
    initialize_firebase()
    return get_firestore_client()


@pytest.fixture(scope="module")
def conversation_service(firebase_db):
    """Get a real ConversationService instance."""
    return get_conversation_service()


@pytest.fixture(autouse=True)
def cleanup_test_data(firebase_db):
    """Clean up any test conversations and messages after each test."""
    yield

    # Clean up conversations with test prefix in title or userId
    convs = firebase_db.collection("conversations")\
        .where("userId", ">=", TEST_PREFIX)\
        .where("userId", "<=", TEST_PREFIX + "\uf8ff")\
        .stream()

    conv_ids = []
    for doc in convs:
        conv_ids.append(doc.id)
        doc.reference.delete()

    # Clean up messages belonging to test conversations
    for conv_id in conv_ids:
        msgs = firebase_db.collection("conversation_messages")\
            .where("conversationId", "==", conv_id)\
            .stream()
        for msg in msgs:
            msg.reference.delete()


class TestConversationCRUD:
    """Integration tests for conversation CRUD with real Firestore."""

    def test_create_and_get_conversation(self, conversation_service):
        """Should create a conversation and retrieve it."""
        user_id = f"{TEST_PREFIX}student_1"

        conv = conversation_service.create_conversation(
            user_id=user_id,
            student_id=user_id,
            user_role="student"
        )

        assert conv["id"] is not None
        assert conv["studentId"] == user_id
        assert conv["status"] == "active"
        assert conv["messageCount"] == 0

        # Retrieve it
        retrieved = conversation_service.get_conversation(conv["id"])
        assert retrieved is not None
        assert retrieved["id"] == conv["id"]
        assert retrieved["studentId"] == user_id

    def test_create_conversation_with_title(self, conversation_service):
        """Should create a conversation with a custom title."""
        user_id = f"{TEST_PREFIX}student_2"

        conv = conversation_service.create_conversation(
            user_id=user_id,
            student_id=user_id,
            user_role="student",
            title="Finance Course Planning"
        )

        assert conv["title"] == "Finance Course Planning"

    def test_get_nonexistent_conversation(self, conversation_service):
        """Should return None for nonexistent conversation."""
        result = conversation_service.get_conversation("nonexistent_conv_id_xyz")
        assert result is None

    def test_list_conversations_for_student(self, conversation_service):
        """Should list conversations ordered by updatedAt descending."""
        user_id = f"{TEST_PREFIX}student_3"

        # Create two conversations
        conv1 = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student",
            title="First Chat"
        )
        time.sleep(0.1)  # Ensure different timestamps
        conv2 = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student",
            title="Second Chat"
        )

        conversations = conversation_service.list_conversations(user_id)

        assert len(conversations) >= 2
        # Most recent first
        titles = [c["title"] for c in conversations]
        assert titles.index("Second Chat") < titles.index("First Chat")

    def test_list_conversations_empty(self, conversation_service):
        """Should return empty list for student with no conversations."""
        result = conversation_service.list_conversations("nonexistent_student_xyz")
        assert result == []

    def test_update_conversation_title(self, conversation_service):
        """Should update the title of an existing conversation."""
        user_id = f"{TEST_PREFIX}student_4"

        conv = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student",
            title="Original Title"
        )

        updated = conversation_service.update_conversation_title(conv["id"], "Updated Title")

        assert updated is not None
        assert updated["title"] == "Updated Title"

    def test_archive_conversation(self, conversation_service):
        """Should set status to archived."""
        user_id = f"{TEST_PREFIX}student_5"

        conv = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student"
        )
        assert conv["status"] == "active"

        archived = conversation_service.archive_conversation(conv["id"])

        assert archived is not None
        assert archived["status"] == "archived"


class TestMessageCRUD:
    """Integration tests for message persistence with real Firestore."""

    def test_add_and_get_messages(self, conversation_service):
        """Should add messages and retrieve them in chronological order."""
        user_id = f"{TEST_PREFIX}student_msg_1"

        conv = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student"
        )

        # Add user message
        msg1 = conversation_service.add_message(
            conv["id"], "user", "What courses should I take?"
        )
        assert msg1["role"] == "user"
        assert msg1["content"] == "What courses should I take?"

        # Add assistant message
        msg2 = conversation_service.add_message(
            conv["id"], "assistant", "I recommend BUAD 327.",
            citations=[{"source": "Finance Req", "excerpt": "BUAD 327", "relevance": 0.9}],
            risks=[{"type": "prereq", "severity": "medium", "message": "Check BUAD 323"}],
            next_steps=[{"action": "Meet advisor", "priority": "high"}]
        )
        assert msg2["role"] == "assistant"
        assert len(msg2["citations"]) == 1
        assert len(msg2["risks"]) == 1
        assert len(msg2["nextSteps"]) == 1

        # Retrieve messages
        messages = conversation_service.get_messages(conv["id"])
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_add_message_updates_conversation_metadata(self, conversation_service):
        """Should update messageCount, updatedAt, and lastMessagePreview."""
        user_id = f"{TEST_PREFIX}student_msg_2"

        conv = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student"
        )
        original_updated = conv["updatedAt"]

        conversation_service.add_message(conv["id"], "user", "Hello there!")

        # Check conversation was updated
        updated_conv = conversation_service.get_conversation(conv["id"])
        assert updated_conv["messageCount"] == 1
        assert updated_conv["lastMessagePreview"] == "Hello there!"
        assert updated_conv["updatedAt"] >= original_updated

    def test_add_message_auto_generates_title(self, conversation_service):
        """Should auto-generate title from first user message."""
        user_id = f"{TEST_PREFIX}student_msg_3"

        conv = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student"
        )
        assert conv["title"] == ""

        conversation_service.add_message(conv["id"], "user", "What Finance courses do I need?")

        updated_conv = conversation_service.get_conversation(conv["id"])
        assert updated_conv["title"] == "What Finance courses do I need?"

    def test_title_not_overwritten_on_second_message(self, conversation_service):
        """Title should only be set once from the first message."""
        user_id = f"{TEST_PREFIX}student_msg_4"

        conv = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student"
        )

        conversation_service.add_message(conv["id"], "user", "First question")
        conversation_service.add_message(conv["id"], "assistant", "Answer")
        conversation_service.add_message(conv["id"], "user", "Second question")

        updated_conv = conversation_service.get_conversation(conv["id"])
        assert updated_conv["title"] == "First question"

    def test_long_message_title_truncation(self, conversation_service):
        """Should truncate long messages to 60 chars for title."""
        user_id = f"{TEST_PREFIX}student_msg_5"

        conv = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student"
        )

        long_message = "A" * 100
        conversation_service.add_message(conv["id"], "user", long_message)

        updated_conv = conversation_service.get_conversation(conv["id"])
        assert len(updated_conv["title"]) == 60
        assert updated_conv["title"].endswith("...")

    def test_get_messages_empty(self, conversation_service):
        """Should return empty list for conversation with no messages."""
        user_id = f"{TEST_PREFIX}student_msg_6"

        conv = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student"
        )

        messages = conversation_service.get_messages(conv["id"])
        assert messages == []


class TestConversationWorkflow:
    """Integration tests for full conversation workflows."""

    def test_complete_conversation_flow(self, conversation_service):
        """Test a complete conversation: create -> messages -> rename -> archive."""
        user_id = f"{TEST_PREFIX}student_flow"

        # 1. Create conversation
        conv = conversation_service.create_conversation(
            user_id=user_id, student_id=user_id, user_role="student"
        )
        assert conv["status"] == "active"
        assert conv["messageCount"] == 0

        # 2. Add messages
        conversation_service.add_message(conv["id"], "user", "What should I take next?")
        conversation_service.add_message(
            conv["id"], "assistant", "Based on your profile, I recommend BUAD 327.",
            citations=[{"source": "Finance Major", "excerpt": "...", "relevance": 0.85}]
        )
        conversation_service.add_message(conv["id"], "user", "What about prerequisites?")
        conversation_service.add_message(conv["id"], "assistant", "You need BUAD 323 first.")

        # 3. Verify state
        updated = conversation_service.get_conversation(conv["id"])
        assert updated["messageCount"] == 4
        assert updated["title"] == "What should I take next?"

        messages = conversation_service.get_messages(conv["id"])
        assert len(messages) == 4
        assert messages[0]["role"] == "user"
        assert messages[3]["role"] == "assistant"

        # 4. Rename
        renamed = conversation_service.update_conversation_title(conv["id"], "Course Planning Session")
        assert renamed["title"] == "Course Planning Session"

        # 5. Archive
        archived = conversation_service.archive_conversation(conv["id"])
        assert archived["status"] == "archived"

        # 6. Still retrievable
        final = conversation_service.get_conversation(conv["id"])
        assert final["status"] == "archived"
        assert final["messageCount"] == 4

    def test_advisor_conversation_about_student(self, conversation_service):
        """Advisor creates conversation about a student (different userId and studentId)."""
        advisor_id = f"{TEST_PREFIX}advisor_1"
        student_id = f"{TEST_PREFIX}advisee_1"

        conv = conversation_service.create_conversation(
            user_id=advisor_id,
            student_id=student_id,
            user_role="advisor"
        )

        assert conv["userId"] == advisor_id
        assert conv["studentId"] == student_id
        assert conv["userRole"] == "advisor"

        # Listing by studentId should find it
        convs = conversation_service.list_conversations(student_id)
        assert any(c["id"] == conv["id"] for c in convs)
