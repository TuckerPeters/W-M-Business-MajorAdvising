"""
Tests for services/advisor.py - Advisor portal operations
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from services.advisor import AdvisorService


class TestAdviseeAssignments:
    """Tests for advisee assignment operations"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.advisor.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create AdvisorService with mocked database"""
        with patch('services.advisor.initialize_firebase'):
            return AdvisorService()

    def test_get_advisees(self, service, mock_db):
        """Should return all advisees for an advisor"""
        mock_assignment = MagicMock()
        mock_assignment.id = "assign1"
        mock_assignment.to_dict.return_value = {
            "advisorId": "advisor1",
            "studentId": "student1",
            "assignedDate": "2025-01-15T10:00:00"
        }

        mock_student = MagicMock()
        mock_student.exists = True
        mock_student.id = "student1"
        mock_student.to_dict.return_value = {
            "userId": "student1",
            "name": "John Doe",
            "email": "jdoe@wm.edu"
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_assignment]
        mock_db.collection.return_value.where.return_value = mock_query
        mock_db.collection.return_value.document.return_value.get.return_value = mock_student

        result = service.get_advisees("advisor1")

        assert len(result) == 1
        assert result[0]["studentId"] == "student1"
        assert "student" in result[0]

    def test_get_advisees_empty(self, service, mock_db):
        """Should return empty list when no advisees"""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.get_advisees("advisor1")

        assert len(result) == 0

    def test_get_advisee_found(self, service, mock_db):
        """Should return advisee details when found"""
        mock_assignment = MagicMock()
        mock_assignment.id = "assign1"
        mock_assignment.to_dict.return_value = {
            "advisorId": "advisor1",
            "studentId": "student1",
            "assignedDate": "2025-01-15T10:00:00"
        }

        mock_student = MagicMock()
        mock_student.exists = True
        mock_student.id = "student1"
        mock_student.to_dict.return_value = {
            "userId": "student1",
            "name": "John Doe",
            "email": "jdoe@wm.edu",
            "classYear": 2026
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_assignment]
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query
        mock_db.collection.return_value.document.return_value.get.return_value = mock_student

        result = service.get_advisee("advisor1", "student1")

        assert result is not None
        assert result["userId"] == "student1"
        assert result["assignmentId"] == "assign1"

    def test_get_advisee_not_assigned(self, service, mock_db):
        """Should return None when student not assigned to advisor"""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        result = service.get_advisee("advisor1", "student1")

        assert result is None

    def test_assign_advisee_new(self, service, mock_db):
        """Should create new assignment"""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_assign"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.assign_advisee("advisor1", "student1")

        mock_doc_ref.set.assert_called_once()
        assert result["advisorId"] == "advisor1"
        assert result["studentId"] == "student1"

    def test_assign_advisee_existing(self, service, mock_db):
        """Should return existing assignment if already assigned"""
        mock_existing = MagicMock()
        mock_existing.id = "existing_assign"
        mock_existing.to_dict.return_value = {
            "advisorId": "advisor1",
            "studentId": "student1",
            "assignedDate": "2025-01-15T10:00:00"
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_existing]
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        result = service.assign_advisee("advisor1", "student1")

        assert result["id"] == "existing_assign"

    def test_remove_advisee_found(self, service, mock_db):
        """Should remove existing assignment"""
        mock_existing = MagicMock()
        mock_existing.reference = MagicMock()

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_existing]
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        result = service.remove_advisee("advisor1", "student1")

        mock_existing.reference.delete.assert_called_once()
        assert result is True

    def test_remove_advisee_not_found(self, service, mock_db):
        """Should return False when assignment not found"""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        result = service.remove_advisee("advisor1", "student1")

        assert result is False


class TestAdvisorNotes:
    """Tests for advisor note operations"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.advisor.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create AdvisorService with mocked database"""
        with patch('services.advisor.initialize_firebase'):
            return AdvisorService()

    def test_get_notes(self, service, mock_db):
        """Should return all notes for a student"""
        mock_notes = [
            MagicMock(id="note1", to_dict=lambda: {
                "advisorId": "advisor1",
                "studentId": "student1",
                "note": "Great progress",
                "visibility": "private",
                "createdAt": "2025-01-15T10:00:00"
            }),
            MagicMock(id="note2", to_dict=lambda: {
                "advisorId": "advisor1",
                "studentId": "student1",
                "note": "Needs to declare major",
                "visibility": "private",
                "createdAt": "2025-01-14T10:00:00"
            })
        ]

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_notes
        mock_db.collection.return_value.where.return_value.where.return_value = mock_query

        result = service.get_notes("advisor1", "student1")

        assert len(result) == 2

    def test_create_note(self, service, mock_db):
        """Should create a new note"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_note"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.create_note("advisor1", "student1", "Test note", "private")

        mock_doc_ref.set.assert_called_once()
        assert result["note"] == "Test note"
        assert result["visibility"] == "private"
        assert result["id"] == "new_note"

    def test_update_note_found(self, service, mock_db):
        """Should update existing note"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "advisorId": "advisor1",
            "studentId": "student1",
            "note": "Original note",
            "visibility": "private"
        }

        mock_updated = MagicMock()
        mock_updated.to_dict.return_value = {
            "advisorId": "advisor1",
            "studentId": "student1",
            "note": "Updated note",
            "visibility": "private"
        }

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.side_effect = [mock_doc, mock_updated]
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_note("advisor1", "note1", note="Updated note")

        mock_doc_ref.update.assert_called_once()
        assert result is not None

    def test_update_note_wrong_advisor(self, service, mock_db):
        """Should return None when note belongs to different advisor"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "advisorId": "other_advisor",
            "studentId": "student1",
            "note": "Original note"
        }

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_note("advisor1", "note1", note="Updated note")

        assert result is None

    def test_update_note_not_found(self, service, mock_db):
        """Should return None when note not found"""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_note("advisor1", "nonexistent", note="Updated")

        assert result is None

    def test_delete_note_found(self, service, mock_db):
        """Should delete existing note"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"advisorId": "advisor1"}

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.delete_note("advisor1", "note1")

        mock_doc_ref.delete.assert_called_once()
        assert result is True

    def test_delete_note_wrong_advisor(self, service, mock_db):
        """Should return False when note belongs to different advisor"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"advisorId": "other_advisor"}

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.delete_note("advisor1", "note1")

        assert result is False


class TestAdvisorAlerts:
    """Tests for advisor alert operations"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.advisor.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create AdvisorService with mocked database"""
        with patch('services.advisor.initialize_firebase'):
            return AdvisorService()

    def test_get_alerts_with_holds(self, service, mock_db):
        """Should return alerts for students with holds"""
        mock_assignment = MagicMock()
        mock_assignment.id = "assign1"
        mock_assignment.to_dict.return_value = {
            "advisorId": "advisor1",
            "studentId": "student1"
        }

        mock_student = MagicMock()
        mock_student.exists = True
        mock_student.to_dict.return_value = {
            "name": "John Doe",
            "holds": ["Academic Hold"],
            "gpa": 3.5,
            "declared": True,
            "classYear": 2026
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_assignment]
        mock_db.collection.return_value.where.return_value = mock_query
        mock_db.collection.return_value.document.return_value.get.return_value = mock_student

        result = service.get_alerts("advisor1")

        assert len(result) == 1
        assert result[0]["type"] == "hold"
        assert result[0]["severity"] == "high"

    def test_get_alerts_low_gpa(self, service, mock_db):
        """Should return alerts for students with low GPA"""
        mock_assignment = MagicMock()
        mock_assignment.id = "assign1"
        mock_assignment.to_dict.return_value = {
            "advisorId": "advisor1",
            "studentId": "student1"
        }

        mock_student = MagicMock()
        mock_student.exists = True
        mock_student.to_dict.return_value = {
            "name": "Jane Doe",
            "holds": [],
            "gpa": 1.8,
            "declared": True,
            "classYear": 2026
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_assignment]
        mock_db.collection.return_value.where.return_value = mock_query
        mock_db.collection.return_value.document.return_value.get.return_value = mock_student

        result = service.get_alerts("advisor1")

        gpa_alerts = [a for a in result if a["type"] == "gpa"]
        assert len(gpa_alerts) == 1
        assert gpa_alerts[0]["severity"] == "high"

    def test_get_alerts_undeclared_upperclassman(self, service, mock_db):
        """Should return alerts for undeclared juniors/seniors"""
        mock_assignment = MagicMock()
        mock_assignment.id = "assign1"
        mock_assignment.to_dict.return_value = {
            "advisorId": "advisor1",
            "studentId": "student1"
        }

        current_year = datetime.utcnow().year
        mock_student = MagicMock()
        mock_student.exists = True
        mock_student.to_dict.return_value = {
            "name": "Undeclared Junior",
            "holds": [],
            "gpa": 3.0,
            "declared": False,
            "classYear": current_year + 1  # Junior (1 year until graduation)
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_assignment]
        mock_db.collection.return_value.where.return_value = mock_query
        mock_db.collection.return_value.document.return_value.get.return_value = mock_student

        result = service.get_alerts("advisor1")

        declaration_alerts = [a for a in result if a["type"] == "declaration"]
        assert len(declaration_alerts) == 1

    def test_get_alerts_no_issues(self, service, mock_db):
        """Should return empty list when no issues"""
        mock_assignment = MagicMock()
        mock_assignment.id = "assign1"
        mock_assignment.to_dict.return_value = {
            "advisorId": "advisor1",
            "studentId": "student1"
        }

        current_year = datetime.utcnow().year
        mock_student = MagicMock()
        mock_student.exists = True
        mock_student.to_dict.return_value = {
            "name": "Good Student",
            "holds": [],
            "gpa": 3.5,
            "declared": True,
            "classYear": current_year + 3  # Freshman
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_assignment]
        mock_db.collection.return_value.where.return_value = mock_query
        mock_db.collection.return_value.document.return_value.get.return_value = mock_student

        result = service.get_alerts("advisor1")

        assert len(result) == 0


class TestAdvisorServiceSingleton:
    """Tests for service singleton pattern"""

    def test_get_advisor_service_returns_instance(self):
        """Should return an AdvisorService instance"""
        with patch('services.advisor.initialize_firebase'):
            with patch('services.advisor.get_firestore_client'):
                from services.advisor import get_advisor_service, _advisor_service
                import services.advisor as advisor_module

                # Reset singleton
                advisor_module._advisor_service = None

                service = get_advisor_service()

                assert service is not None
                assert isinstance(service, AdvisorService)
