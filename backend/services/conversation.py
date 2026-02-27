"""
Conversation Persistence Service

Handles all Firestore operations for storing and retrieving chat conversations
and messages. Enables students to reference prior chats and advisors to view
advisee conversation history.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from core.config import get_firestore_client, initialize_firebase


class ConversationService:
    """Service for managing chat conversations in Firebase Firestore."""

    CONVERSATIONS_COLLECTION = "conversations"
    MESSAGES_COLLECTION = "conversation_messages"

    def __init__(self):
        self.db = get_firestore_client()

    # --- Conversation Operations ---

    def create_conversation(
        self, user_id: str, student_id: str, user_role: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new conversation."""
        now = datetime.utcnow().isoformat()

        conversation_data = {
            "studentId": student_id,
            "userId": user_id,
            "userRole": user_role,
            "title": title or "",
            "status": "active",
            "messageCount": 0,
            "createdAt": now,
            "updatedAt": now,
            "lastMessagePreview": ""
        }

        doc_ref = self.db.collection(self.CONVERSATIONS_COLLECTION).document()
        doc_ref.set(conversation_data)
        conversation_data["id"] = doc_ref.id

        return conversation_data

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a single conversation by ID."""
        doc = self.db.collection(self.CONVERSATIONS_COLLECTION).document(conversation_id).get()
        if not doc.exists:
            return None

        data = doc.to_dict()
        data["id"] = doc.id
        return data

    def list_conversations(
        self, student_id: str, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversations for a student, most recent first."""
        query = self.db.collection(self.CONVERSATIONS_COLLECTION)\
            .where("studentId", "==", student_id)\
            .order_by("updatedAt", direction="DESCENDING")

        # Firestore doesn't support offset natively, so we fetch limit+offset and skip
        docs = list(query.limit(limit + offset).stream())

        conversations = []
        for doc in docs[offset:offset + limit]:
            data = doc.to_dict()
            data["id"] = doc.id
            conversations.append(data)

        return conversations

    # --- Message Operations ---

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: Optional[List[Dict]] = None,
        risks: Optional[List[Dict]] = None,
        next_steps: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation.

        Also updates the parent conversation's updatedAt, messageCount,
        lastMessagePreview, and auto-generates title from first user message.
        """
        now = datetime.utcnow().isoformat()

        message_data = {
            "conversationId": conversation_id,
            "role": role,
            "content": content,
            "citations": citations or [],
            "risks": risks or [],
            "nextSteps": next_steps or [],
            "createdAt": now
        }

        doc_ref = self.db.collection(self.MESSAGES_COLLECTION).document()
        doc_ref.set(message_data)
        message_data["id"] = doc_ref.id

        # Update parent conversation
        conv_ref = self.db.collection(self.CONVERSATIONS_COLLECTION).document(conversation_id)
        conv_doc = conv_ref.get()

        if conv_doc.exists:
            conv_data = conv_doc.to_dict()
            update_data = {
                "updatedAt": now,
                "messageCount": conv_data.get("messageCount", 0) + 1,
                "lastMessagePreview": content[:100] if content else ""
            }

            # Auto-generate title from first user message
            if role == "user" and not conv_data.get("title"):
                update_data["title"] = self._generate_title(content)

            conv_ref.update(update_data)

        return message_data

    def get_messages(
        self, conversation_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation in chronological order."""
        query = self.db.collection(self.MESSAGES_COLLECTION)\
            .where("conversationId", "==", conversation_id)\
            .order_by("createdAt")

        docs = list(query.limit(limit + offset).stream())

        messages = []
        for doc in docs[offset:offset + limit]:
            data = doc.to_dict()
            data["id"] = doc.id
            messages.append(data)

        return messages

    # --- Conversation Management ---

    def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> Optional[Dict[str, Any]]:
        """Update a conversation's title."""
        doc_ref = self.db.collection(self.CONVERSATIONS_COLLECTION).document(conversation_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        doc_ref.update({
            "title": title,
            "updatedAt": datetime.utcnow().isoformat()
        })

        updated = doc_ref.get()
        result = updated.to_dict()
        result["id"] = conversation_id
        return result

    def archive_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Archive a conversation."""
        doc_ref = self.db.collection(self.CONVERSATIONS_COLLECTION).document(conversation_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        doc_ref.update({
            "status": "archived",
            "updatedAt": datetime.utcnow().isoformat()
        })

        updated = doc_ref.get()
        result = updated.to_dict()
        result["id"] = conversation_id
        return result

    # --- Helpers ---

    def _generate_title(self, first_message: str) -> str:
        """Generate a conversation title from the first user message."""
        if len(first_message) <= 60:
            return first_message
        return first_message[:57] + "..."


_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get singleton instance of ConversationService."""
    global _conversation_service
    if _conversation_service is None:
        initialize_firebase()
        _conversation_service = ConversationService()
    return _conversation_service
