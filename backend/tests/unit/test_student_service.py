"""
Tests for services/student.py - Student profile, enrollment, and milestone operations
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from services.student import StudentService


class TestStudentProfile:
    """Tests for student profile operations"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            return StudentService()

    def test_get_student_found(self, service, mock_db):
        """Should return student data when found"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "user123"
        mock_doc.to_dict.return_value = {
            "userId": "user123",
            "name": "John Doe",
            "email": "jdoe@wm.edu",
            "classYear": 2026,
            "gpa": 3.5,
            "creditsEarned": 60,
            "declared": True,
            "intendedMajor": "Finance"
        }

        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = service.get_student("user123")

        assert result is not None
        assert result["userId"] == "user123"
        assert result["name"] == "John Doe"
        assert result["intendedMajor"] == "Finance"

    def test_get_student_not_found(self, service, mock_db):
        """Should return None when student not found"""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = service.get_student("nonexistent")

        assert result is None

    def test_create_student(self, service, mock_db):
        """Should create a new student profile"""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        data = {
            "name": "Jane Doe",
            "email": "jane@wm.edu",
            "classYear": 2027,
            "gpa": 3.8
        }

        result = service.create_student("user456", data)

        mock_doc_ref.set.assert_called_once()
        assert result["userId"] == "user456"
        assert result["name"] == "Jane Doe"
        assert "createdAt" in result

    def test_update_student_found(self, service, mock_db):
        """Should update existing student profile"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "userId": "user123",
            "name": "John Doe Updated",
            "gpa": 3.7
        }

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_student("user123", {"gpa": 3.7})

        mock_doc_ref.update.assert_called_once()
        assert result is not None

    def test_update_student_not_found(self, service, mock_db):
        """Should return None when updating non-existent student"""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_student("nonexistent", {"gpa": 3.5})

        assert result is None

    def test_declare_major(self, service, mock_db):
        """Should declare a major for student"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "userId": "user123",
            "intendedMajor": "Accounting",
            "declared": True
        }

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.declare_major("user123", "Accounting")

        assert result is not None
        mock_doc_ref.update.assert_called_once()


class TestStudentEnrollments:
    """Tests for enrollment operations"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            return StudentService()

    def test_get_student_enrollments(self, service, mock_db):
        """Should return all enrollments for a student"""
        mock_docs = [
            MagicMock(id="enroll1", to_dict=lambda: {
                "studentId": "user123",
                "courseCode": "CSCI 141",
                "term": "202510",
                "status": "completed",
                "grade": "A"
            }),
            MagicMock(id="enroll2", to_dict=lambda: {
                "studentId": "user123",
                "courseCode": "MATH 111",
                "term": "202510",
                "status": "enrolled"
            })
        ]

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.get_student_enrollments("user123")

        assert len(result) == 2
        assert result[0]["courseCode"] == "CSCI 141"

    def test_get_student_enrollments_filtered(self, service, mock_db):
        """Should filter enrollments by status"""
        mock_docs = [
            MagicMock(id="enroll1", to_dict=lambda: {
                "studentId": "user123",
                "courseCode": "CSCI 141",
                "status": "completed"
            })
        ]

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.get_student_enrollments("user123", status="completed")

        assert len(result) == 1

    def test_get_student_courses_grouped(self, service, mock_db):
        """Should group courses by status"""
        mock_docs = [
            MagicMock(id="e1", to_dict=lambda: {"status": "completed", "courseCode": "CSCI 141"}),
            MagicMock(id="e2", to_dict=lambda: {"status": "enrolled", "courseCode": "CSCI 241"}),
            MagicMock(id="e3", to_dict=lambda: {"status": "planned", "courseCode": "CSCI 301"})
        ]

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.get_student_courses("user123")

        assert "completed" in result
        assert "current" in result
        assert "planned" in result
        assert len(result["completed"]) == 1
        assert len(result["current"]) == 1
        assert len(result["planned"]) == 1

    def test_add_enrollment(self, service, mock_db):
        """Should add a new enrollment"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_enrollment_id"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Mock no existing enrollments (for time conflict check)
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_query

        # Mock course validation
        service.validate_course_section = MagicMock(return_value={"course": {}})

        data = {
            "courseCode": "BUS 201",
            "term": "Fall 2030",  # Use valid term format
            "status": "planned"
        }

        result = service.add_enrollment("user123", data)

        mock_doc_ref.set.assert_called_once()
        assert result["studentId"] == "user123"
        assert result["courseCode"] == "BUS 201"

    def test_update_enrollment_found(self, service, mock_db):
        """Should update existing enrollment"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "studentId": "user123",
            "courseCode": "CSCI 141",
            "grade": "A",
            "status": "completed"
        }

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_enrollment("enroll1", {"grade": "A", "status": "completed"})

        mock_doc_ref.update.assert_called_once()
        assert result is not None

    def test_update_enrollment_not_found(self, service, mock_db):
        """Should return None for non-existent enrollment"""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_enrollment("nonexistent", {"grade": "B"})

        assert result is None

    def test_delete_enrollment_found(self, service, mock_db):
        """Should delete existing enrollment"""
        mock_doc = MagicMock()
        mock_doc.exists = True

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.delete_enrollment("enroll1")

        mock_doc_ref.delete.assert_called_once()
        assert result is True

    def test_delete_enrollment_not_found(self, service, mock_db):
        """Should return False for non-existent enrollment"""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.delete_enrollment("nonexistent")

        assert result is False


class TestMilestones:
    """Tests for milestone operations"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            return StudentService()

    def test_get_milestones_all(self, service, mock_db):
        """Should return all milestones"""
        mock_docs = [
            MagicMock(id="m1", to_dict=lambda: {"title": "Declare Major", "type": "degree"}),
            MagicMock(id="m2", to_dict=lambda: {"title": "Complete Core", "type": "degree"})
        ]

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value = mock_query

        result = service.get_milestones()

        assert len(result) == 2

    def test_get_milestones_for_student(self, service, mock_db):
        """Should return milestones for specific student"""
        mock_docs = [
            MagicMock(id="m1", to_dict=lambda: {"studentId": "user123", "completed": True})
        ]

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.get_milestones("user123")

        assert len(result) == 1

    def test_get_degree_milestones(self, service, mock_db):
        """Should return only degree-type milestones"""
        mock_docs = [
            MagicMock(id="m1", to_dict=lambda: {"title": "Declare Major", "type": "degree"})
        ]

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value.where.return_value = mock_query

        result = service.get_degree_milestones()

        assert len(result) == 1

    def test_update_milestone_progress_new(self, service, mock_db):
        """Should create new milestone progress record"""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "progress1"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_milestone_progress("user123", "milestone1", True, "Completed!")

        mock_doc_ref.set.assert_called_once()
        assert result["completed"] is True

    def test_update_milestone_progress_existing(self, service, mock_db):
        """Should update existing milestone progress"""
        mock_existing = MagicMock()
        mock_existing.reference = MagicMock()
        mock_existing.reference.id = "existing_progress"

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_existing]
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        result = service.update_milestone_progress("user123", "milestone1", True)

        mock_existing.reference.update.assert_called_once()


class TestNullableFields:
    """Tests for nullable field handling"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            return StudentService()

    def test_create_student_with_null_gpa_freshman(self, service, mock_db):
        """Should allow null GPA for first semester freshmen"""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        data = {
            "name": "New Freshman",
            "email": "freshman@wm.edu",
            "classYear": 2029,
            "gpa": None,  # First semester freshman has no GPA
            "creditsEarned": 0
        }

        result = service.create_student("freshman1", data)

        mock_doc_ref.set.assert_called_once()
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["gpa"] is None
        assert result["gpa"] is None

    def test_create_student_with_null_ap_credits(self, service, mock_db):
        """Should allow null AP credits when student has none"""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        data = {
            "name": "No AP Student",
            "email": "noap@wm.edu",
            "classYear": 2027,
            "gpa": 3.5,
            "apCredits": None  # No AP credits
        }

        result = service.create_student("noap1", data)

        mock_doc_ref.set.assert_called_once()
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["apCredits"] is None
        assert result["apCredits"] is None

    def test_create_student_with_null_intended_major(self, service, mock_db):
        """Should allow null intendedMajor until declared"""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        data = {
            "name": "Undeclared Student",
            "email": "undeclared@wm.edu",
            "classYear": 2027,
            "gpa": 3.2,
            "intendedMajor": None,  # Not yet declared
            "declared": False
        }

        result = service.create_student("undeclared1", data)

        mock_doc_ref.set.assert_called_once()
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["intendedMajor"] is None
        assert call_args["declared"] is False

    def test_create_student_all_nulls_freshman(self, service, mock_db):
        """Should allow all nullable fields to be null for new freshman"""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        data = {
            "name": "Brand New Freshman",
            "email": "newfreshman@wm.edu",
            "classYear": 2029,
            "gpa": None,
            "apCredits": None,
            "intendedMajor": None,
            "declared": False,
            "creditsEarned": 0
        }

        result = service.create_student("newfreshman1", data)

        mock_doc_ref.set.assert_called_once()
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["gpa"] is None
        assert call_args["apCredits"] is None
        assert call_args["intendedMajor"] is None
        assert call_args["declared"] is False

    def test_get_student_with_null_fields(self, service, mock_db):
        """Should return student with null fields intact"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "freshman123"
        mock_doc.to_dict.return_value = {
            "userId": "freshman123",
            "name": "Freshman Student",
            "email": "freshman@wm.edu",
            "classYear": 2029,
            "gpa": None,
            "creditsEarned": 0,
            "declared": False,
            "intendedMajor": None,
            "apCredits": None,
            "holds": []
        }

        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = service.get_student("freshman123")

        assert result is not None
        assert result["gpa"] is None
        assert result["intendedMajor"] is None
        assert result["apCredits"] is None
        assert result["declared"] is False

    def test_update_student_set_gpa_from_null(self, service, mock_db):
        """Should update GPA from null after first semester"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "userId": "freshman123",
            "name": "Freshman Student",
            "gpa": 3.7  # Now has GPA after first semester
        }

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.update_student("freshman123", {"gpa": 3.7})

        mock_doc_ref.update.assert_called_once()
        assert result is not None
        assert result["gpa"] == 3.7

    def test_declare_major_sets_declared_true(self, service, mock_db):
        """Should set declared to true when major is declared"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "userId": "student123",
            "intendedMajor": "Finance",
            "declared": True,
            "declaredAt": "2025-01-15T10:00:00"
        }

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = service.declare_major("student123", "Finance")

        mock_doc_ref.update.assert_called_once()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args["intendedMajor"] == "Finance"
        assert call_args["declared"] is True
        assert "declaredAt" in call_args


class TestStudentServiceSingleton:
    """Tests for service singleton pattern"""

    def test_get_student_service_returns_instance(self):
        """Should return a StudentService instance"""
        with patch('services.student.initialize_firebase'):
            with patch('services.student.get_firestore_client'):
                from services.student import get_student_service, _student_service
                import services.student as student_module

                # Reset singleton
                student_module._student_service = None

                service = get_student_service()

                assert service is not None
                assert isinstance(service, StudentService)


class TestTermValidation:
    """Tests for term/semester validation"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            return StudentService()

    def test_parse_term_valid(self, service):
        """Should parse valid term format"""
        season, year = service.parse_term("Fall 2025")
        assert season == "Fall"
        assert year == 2025

        season, year = service.parse_term("Spring 2026")
        assert season == "Spring"
        assert year == 2026

        season, year = service.parse_term("Summer 2025")
        assert season == "Summer"
        assert year == 2025

    def test_parse_term_invalid_format(self, service):
        """Should raise error for invalid term format"""
        with pytest.raises(ValueError, match="Invalid term format"):
            service.parse_term("Fall2025")

        with pytest.raises(ValueError, match="Invalid term format"):
            service.parse_term("2025")

    def test_parse_term_invalid_season(self, service):
        """Should raise error for invalid season"""
        with pytest.raises(ValueError, match="Invalid season"):
            service.parse_term("Winter 2025")

    def test_parse_term_invalid_year(self, service):
        """Should raise error for invalid year"""
        with pytest.raises(ValueError, match="Invalid year"):
            service.parse_term("Fall XXXX")

    def test_compare_terms(self, service):
        """Should compare terms chronologically"""
        # Same term
        assert service.compare_terms("Fall 2025", "Fall 2025") == 0

        # Different years
        assert service.compare_terms("Fall 2024", "Fall 2025") == -1
        assert service.compare_terms("Fall 2026", "Fall 2025") == 1

        # Same year, different seasons
        assert service.compare_terms("Spring 2025", "Fall 2025") == -1
        assert service.compare_terms("Summer 2025", "Spring 2025") == 1
        assert service.compare_terms("Fall 2025", "Summer 2025") == 1

    def test_get_current_term(self, service):
        """Should return current term based on date"""
        term = service.get_current_term()
        assert term is not None
        # Should be in format "Season YYYY"
        parts = term.split()
        assert len(parts) == 2
        assert parts[0] in ["Spring", "Summer", "Fall"]
        assert parts[1].isdigit()


class TestEnrollmentTermValidation:
    """Tests for enrollment term validation errors"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            svc = StudentService()
            # Mock to avoid course validation
            svc.validate_course_section = MagicMock(return_value={"course": {}})
            # Mock to avoid time conflict checks
            svc.check_time_conflict = MagicMock(return_value=None)
            return svc

    def test_add_enrollment_missing_term(self, service, mock_db):
        """Should raise InvalidTermError when term is missing"""
        from services.student import InvalidTermError

        with pytest.raises(InvalidTermError, match="Term is required"):
            service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "status": "planned"
                # No term provided
            })

    def test_add_enrollment_invalid_term_format(self, service, mock_db):
        """Should raise InvalidTermError for invalid term format"""
        from services.student import InvalidTermError

        with pytest.raises(InvalidTermError, match="Invalid term format"):
            service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall2025",  # Missing space
                "status": "planned"
            })

    def test_add_enrollment_enrolled_wrong_term(self, service, mock_db):
        """Should raise InvalidTermError when enrolled course is not current semester"""
        from services.student import InvalidTermError

        # Use a past term
        with pytest.raises(InvalidTermError, match="current semester"):
            service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2020",  # Past term
                "status": "enrolled"
            })

    def test_add_enrollment_planned_past_term(self, service, mock_db):
        """Should raise InvalidTermError when planned course is in the past"""
        from services.student import InvalidTermError

        with pytest.raises(InvalidTermError, match="current or future"):
            service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2020",  # Past term
                "status": "planned"
            })

    def test_add_enrollment_planned_future_term_succeeds(self, service, mock_db):
        """Should allow planned courses in future terms"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_enrollment_id"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Mock no time conflicts
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_query

        # Mock course service
        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course_svc.return_value.get_course.return_value = {
                "course_code": "BUAD 327",
                "sections": []
            }

            # Mock prerequisite engine
            with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
                mock_prereq.return_value.get_student_completed_courses.return_value = set()
                mock_prereq.return_value.get_student_current_courses.return_value = set()
                mock_prereq.return_value.check_prerequisites_met.return_value = (True, [])

                # Use a future term
                result = service.add_enrollment("user123", {
                    "courseCode": "BUAD 327",
                    "term": "Fall 2030",  # Future term
                    "status": "planned"
                })

                mock_doc_ref.set.assert_called_once()
                assert result["term"] == "Fall 2030"


class TestTimeConflictValidation:
    """Tests for time conflict detection"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            return StudentService()

    def test_days_overlap_mwf_mwf(self, service):
        """MWF should overlap with MWF"""
        assert service._days_overlap("MWF", "MWF") is True

    def test_days_overlap_mwf_tr(self, service):
        """MWF should not overlap with TR"""
        assert service._days_overlap("MWF", "TR") is False

    def test_days_overlap_partial(self, service):
        """Should detect partial day overlap"""
        assert service._days_overlap("MW", "MWF") is True
        assert service._days_overlap("TR", "T") is True

    def test_times_overlap_same(self, service):
        """Same time slots should overlap"""
        assert service._times_overlap("09:00", "09:50", "09:00", "09:50") is True

    def test_times_overlap_partial(self, service):
        """Partially overlapping times should be detected"""
        assert service._times_overlap("09:00", "10:00", "09:30", "10:30") is True
        assert service._times_overlap("09:30", "10:30", "09:00", "10:00") is True

    def test_times_no_overlap(self, service):
        """Non-overlapping times should not conflict"""
        assert service._times_overlap("09:00", "09:50", "10:00", "10:50") is False
        assert service._times_overlap("14:00", "15:00", "09:00", "10:00") is False

    def test_check_time_conflict_found(self, service, mock_db):
        """Should detect time conflict with existing enrollment"""
        # Mock existing enrollments
        existing_enrollment = {
            "courseCode": "BUAD 323",
            "term": "Fall 2025",
            "meetingDays": "MWF",
            "startTime": "09:00",
            "endTime": "09:50"
        }

        mock_docs = [MagicMock(id="e1", to_dict=lambda: existing_enrollment)]
        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value.where.return_value = mock_query

        # Try to add conflicting course
        new_course = {
            "courseCode": "BUAD 327",
            "meetingDays": "MWF",
            "startTime": "09:00",
            "endTime": "09:50"
        }

        conflict = service.check_time_conflict("user123", new_course, "Fall 2025")

        assert conflict is not None
        assert conflict["courseCode"] == "BUAD 323"

    def test_check_time_conflict_different_term(self, service, mock_db):
        """Should not conflict with courses in different terms"""
        existing_enrollment = {
            "courseCode": "BUAD 323",
            "term": "Spring 2025",  # Different term
            "meetingDays": "MWF",
            "startTime": "09:00",
            "endTime": "09:50"
        }

        mock_docs = [MagicMock(id="e1", to_dict=lambda: existing_enrollment)]
        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value.where.return_value = mock_query

        new_course = {
            "courseCode": "BUAD 327",
            "meetingDays": "MWF",
            "startTime": "09:00",
            "endTime": "09:50"
        }

        conflict = service.check_time_conflict("user123", new_course, "Fall 2025")

        assert conflict is None

    def test_add_enrollment_with_time_conflict(self, service, mock_db):
        """Should raise ScheduleConflictError when time conflicts"""
        from services.student import ScheduleConflictError

        # Mock course validation to pass
        service.validate_course_section = MagicMock(return_value={"course": {}})

        # Mock existing enrollment with conflict
        existing = {
            "courseCode": "BUAD 323",
            "term": "Fall 2030",
            "meetingDays": "MWF",
            "startTime": "09:00",
            "endTime": "09:50"
        }
        mock_docs = [MagicMock(id="e1", to_dict=lambda: existing)]
        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value.where.return_value = mock_query

        with pytest.raises(ScheduleConflictError, match="Time conflict"):
            service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2030",
                "status": "planned",
                "meetingDays": "MWF",
                "startTime": "09:00",
                "endTime": "09:50"
            })


class TestCourseValidation:
    """Tests for course/section validation"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            return StudentService()

    def test_validate_course_not_found(self, service):
        """Should raise CourseNotFoundError when course doesn't exist"""
        from services.student import CourseNotFoundError

        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course_svc.return_value.get_course.return_value = None

            with pytest.raises(CourseNotFoundError, match="not found in catalog"):
                service.validate_course_section("FAKE 999")

    def test_validate_course_exists(self, service):
        """Should return course when it exists"""
        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course = {"course_code": "BUAD 327", "title": "Investments"}
            mock_course_svc.return_value.get_course.return_value = mock_course

            result = service.validate_course_section("BUAD 327")

            assert result["course_code"] == "BUAD 327"

    def test_validate_section_not_found(self, service):
        """Should raise SectionNotFoundError when section doesn't exist"""
        from services.student import SectionNotFoundError

        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course = {
                "course_code": "BUAD 327",
                "sections": [
                    {"section_number": "01", "available": 10},
                    {"section_number": "02", "available": 5}
                ]
            }
            mock_course_svc.return_value.get_course.return_value = mock_course

            with pytest.raises(SectionNotFoundError, match="Section '99' not found"):
                service.validate_course_section("BUAD 327", section_number="99")

    def test_validate_section_exists(self, service):
        """Should return section when it exists"""
        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course = {
                "course_code": "BUAD 327",
                "sections": [
                    {"section_number": "01", "available": 10},
                    {"section_number": "02", "available": 5}
                ]
            }
            mock_course_svc.return_value.get_course.return_value = mock_course

            result = service.validate_course_section("BUAD 327", section_number="01")

            assert result["section"]["section_number"] == "01"

    def test_validate_no_available(self, service):
        """Should raise NoSeatsAvailableError when section is full"""
        from services.student import NoSeatsAvailableError

        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course = {
                "course_code": "BUAD 327",
                "sections": [
                    {"section_number": "01", "available": 0}  # Full
                ]
            }
            mock_course_svc.return_value.get_course.return_value = mock_course

            with pytest.raises(NoSeatsAvailableError, match="No seats available"):
                service.validate_course_section("BUAD 327", section_number="01", check_seats=True)

    def test_validate_available(self, service):
        """Should pass when seats are available"""
        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course = {
                "course_code": "BUAD 327",
                "sections": [
                    {"section_number": "01", "available": 5}
                ]
            }
            mock_course_svc.return_value.get_course.return_value = mock_course

            result = service.validate_course_section("BUAD 327", section_number="01", check_seats=True)

            assert result["section"]["available"] == 5

    def test_validate_skip_seat_check(self, service):
        """Should skip seat check when check_seats=False"""
        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course = {
                "course_code": "BUAD 327",
                "sections": [
                    {"section_number": "01", "available": 0}  # Full but should pass
                ]
            }
            mock_course_svc.return_value.get_course.return_value = mock_course

            # Should not raise even though no seats
            result = service.validate_course_section("BUAD 327", section_number="01", check_seats=False)

            assert result["section"]["section_number"] == "01"


class TestAddEnrollmentFullValidation:
    """Tests for full add_enrollment validation chain"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            return StudentService()

    def test_add_enrollment_success_with_all_validations(self, service, mock_db):
        """Should successfully add enrollment when all validations pass"""
        # Mock course validation
        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course = {
                "course_code": "BUAD 327",
                "sections": [{"section_number": "01", "available": 10}]
            }
            mock_course_svc.return_value.get_course.return_value = mock_course

            # Mock no existing enrollments (no time conflicts)
            mock_query = MagicMock()
            mock_query.stream.return_value = []
            mock_db.collection.return_value.where.return_value = mock_query

            # Mock document creation
            mock_doc_ref = MagicMock()
            mock_doc_ref.id = "new_enrollment"
            mock_db.collection.return_value.document.return_value = mock_doc_ref

            # Mock prerequisite engine
            with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
                mock_prereq.return_value.get_student_completed_courses.return_value = {"BUAD 323"}
                mock_prereq.return_value.get_student_current_courses.return_value = set()
                mock_prereq.return_value.check_prerequisites_met.return_value = (True, [])

                result = service.add_enrollment("user123", {
                    "courseCode": "BUAD 327",
                    "courseName": "Investments",
                    "term": "Fall 2030",
                    "status": "planned",
                    "sectionNumber": "01",
                    "meetingDays": "MWF",
                    "startTime": "10:00",
                    "endTime": "10:50"
                })

                assert result["courseCode"] == "BUAD 327"
                assert result["sectionNumber"] == "01"
                mock_doc_ref.set.assert_called_once()

    def test_add_enrollment_completed_skips_course_validation(self, service, mock_db):
        """Should skip course validation for completed (historical) courses"""
        # No course service mock - validation should be skipped

        # Mock no existing enrollments
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_query

        # Mock document creation
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "completed_enrollment"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Completed courses shouldn't validate against current catalog
        result = service.add_enrollment("user123", {
            "courseCode": "OLD 101",  # Might not exist anymore
            "term": "Fall 2020",
            "status": "completed",
            "grade": "A"
        })

        assert result["status"] == "completed"
        mock_doc_ref.set.assert_called_once()

    def test_add_enrollment_full_section_sets_waitlist_flag(self, service, mock_db):
        """Should set waitlistRequired=True when section is full"""
        # Mock course with full section
        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course = {
                "course_code": "BUAD 327",
                "sections": [{"section_number": "01", "available": 0}]  # Full!
            }
            mock_course_svc.return_value.get_course.return_value = mock_course

            # Mock no existing enrollments (no time conflicts)
            mock_query = MagicMock()
            mock_query.stream.return_value = []
            mock_db.collection.return_value.where.return_value = mock_query

            # Mock document creation
            mock_doc_ref = MagicMock()
            mock_doc_ref.id = "waitlist_enrollment"
            mock_db.collection.return_value.document.return_value = mock_doc_ref

            # Mock prerequisite engine
            with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
                mock_prereq.return_value.get_student_completed_courses.return_value = {"BUAD 323"}
                mock_prereq.return_value.get_student_current_courses.return_value = set()
                mock_prereq.return_value.check_prerequisites_met.return_value = (True, [])

                result = service.add_enrollment("user123", {
                    "courseCode": "BUAD 327",
                    "term": "Fall 2030",
                    "status": "planned",
                    "sectionNumber": "01"
                })

                # Should succeed but with waitlist flag
                assert result["courseCode"] == "BUAD 327"
                assert result["waitlistRequired"] is True
                mock_doc_ref.set.assert_called_once()

    def test_add_enrollment_available_section_no_waitlist(self, service, mock_db):
        """Should set waitlistRequired=False when seats are available"""
        # Mock course with available seats
        with patch('services.firebase.get_course_service') as mock_course_svc:
            mock_course = {
                "course_code": "BUAD 327",
                "sections": [{"section_number": "01", "available": 5}]
            }
            mock_course_svc.return_value.get_course.return_value = mock_course

            # Mock no existing enrollments
            mock_query = MagicMock()
            mock_query.stream.return_value = []
            mock_db.collection.return_value.where.return_value = mock_query

            # Mock document creation
            mock_doc_ref = MagicMock()
            mock_doc_ref.id = "available_enrollment"
            mock_db.collection.return_value.document.return_value = mock_doc_ref

            # Mock prerequisite engine
            with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
                mock_prereq.return_value.get_student_completed_courses.return_value = {"BUAD 323"}
                mock_prereq.return_value.get_student_current_courses.return_value = set()
                mock_prereq.return_value.check_prerequisites_met.return_value = (True, [])

                result = service.add_enrollment("user123", {
                    "courseCode": "BUAD 327",
                    "term": "Fall 2030",
                    "status": "planned",
                    "sectionNumber": "01"
                })

                assert result["waitlistRequired"] is False
                mock_doc_ref.set.assert_called_once()


class TestPrerequisiteValidation:
    """Tests for prerequisite validation in enrollment"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            svc = StudentService()
            # Mock course validation to pass
            svc.validate_course_section = MagicMock(return_value={"course": {}})
            # Mock time conflict check to pass
            svc.check_time_conflict = MagicMock(return_value=None)
            return svc

    def test_add_enrollment_prereqs_not_met(self, service, mock_db):
        """Should raise PrerequisitesNotMetError when prerequisites not met"""
        from services.student import PrerequisitesNotMetError

        # Mock the prerequisite engine
        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            mock_engine = MagicMock()
            mock_engine.get_student_completed_courses.return_value = set()
            mock_engine.get_student_current_courses.return_value = set()
            mock_engine.check_prerequisites_met.return_value = (False, ["BUAD 201", "ACCT 203"])
            mock_prereq.return_value = mock_engine

            with pytest.raises(PrerequisitesNotMetError) as exc_info:
                service.add_enrollment("user123", {
                    "courseCode": "BUAD 327",
                    "term": "Fall 2030",
                    "status": "planned"
                })

            assert "BUAD 201" in str(exc_info.value)
            assert "ACCT 203" in str(exc_info.value)
            assert exc_info.value.missing_prerequisites == ["BUAD 201", "ACCT 203"]

    def test_add_enrollment_prereqs_met(self, service, mock_db):
        """Should succeed when prerequisites are met"""
        # Mock document creation
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_enrollment"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Mock the prerequisite engine to return prereqs met
        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            mock_engine = MagicMock()
            mock_engine.get_student_completed_courses.return_value = {"BUAD 201", "ACCT 203"}
            mock_engine.get_student_current_courses.return_value = set()
            mock_engine.check_prerequisites_met.return_value = (True, [])
            mock_prereq.return_value = mock_engine

            result = service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2030",
                "status": "planned"
            })

            assert result["courseCode"] == "BUAD 327"
            mock_doc_ref.set.assert_called_once()

    def test_add_enrollment_completed_skips_prereq_check(self, service, mock_db):
        """Should skip prerequisite check for completed courses"""
        # Mock document creation
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "completed_enrollment"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Mock no existing enrollments for time conflict check
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_query

        # Don't mock prereq engine - it should not be called for completed courses
        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            result = service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2020",
                "status": "completed",
                "grade": "A"
            })

            # Prereq engine should not have been called
            mock_prereq.assert_not_called()
            assert result["status"] == "completed"

    def test_add_enrollment_current_courses_count_for_prereqs(self, service, mock_db):
        """Should include current courses when checking prerequisites"""
        # Mock document creation
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_enrollment"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            mock_engine = MagicMock()
            # Student has BUAD 201 completed, ACCT 203 currently enrolled
            mock_engine.get_student_completed_courses.return_value = {"BUAD 201"}
            mock_engine.get_student_current_courses.return_value = {"ACCT 203"}
            mock_engine.check_prerequisites_met.return_value = (True, [])
            mock_prereq.return_value = mock_engine

            result = service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2030",
                "status": "planned"
            })

            # Verify check_prerequisites_met was called with combined courses
            call_args = mock_engine.check_prerequisites_met.call_args
            available_courses = call_args[0][1]
            assert "BUAD 201" in available_courses
            assert "ACCT 203" in available_courses
            assert result["courseCode"] == "BUAD 327"

    def test_prereqs_not_met_error_has_missing_list(self, service, mock_db):
        """PrerequisitesNotMetError should contain the list of missing prereqs"""
        from services.student import PrerequisitesNotMetError

        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            mock_engine = MagicMock()
            mock_engine.get_student_completed_courses.return_value = set()
            mock_engine.get_student_current_courses.return_value = set()
            missing_list = ["BUAD 201", "ACCT 203", "FINA 301"]
            mock_engine.check_prerequisites_met.return_value = (False, missing_list)
            mock_prereq.return_value = mock_engine

            with pytest.raises(PrerequisitesNotMetError) as exc_info:
                service.add_enrollment("user123", {
                    "courseCode": "BUAD 499",
                    "term": "Fall 2030",
                    "status": "planned"  # Use planned to bypass current term restriction
                })

            # Verify the error contains the missing prerequisites
            assert exc_info.value.missing_prerequisites == missing_list
            assert len(exc_info.value.missing_prerequisites) == 3


class TestValidationWarningsWorkflow:
    """Tests for the two-step enrollment validation workflow.

    Workflow:
    1. add_enrollment saves enrollment and returns validation warnings
    2. User reviews warnings
    3. acknowledge_enrollment_warnings saves flags if user accepts
    """

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.student.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def service(self, mock_db):
        """Create StudentService with mocked database"""
        with patch('services.student.initialize_firebase'):
            svc = StudentService()
            svc.validate_course_section = MagicMock(return_value={"course": {}})
            svc.check_time_conflict = MagicMock(return_value=None)
            return svc

    def test_add_enrollment_returns_validation_warnings(self, service, mock_db):
        """add_enrollment should return validationWarnings after successful save"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_enrollment"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        mock_validation_flags = {
            "flags": [{"type": "heavy_workload", "severity": "medium", "message": "16 credits"}],
            "warnings": ["Fall 2030: Heavy course load (16 credits)"],
            "total_credits_by_term": {"Fall 2030": 16},
            "schedule_score": {"overall": 85}
        }

        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            mock_engine = MagicMock()
            mock_engine.get_student_completed_courses.return_value = {"BUAD 201"}
            mock_engine.get_student_current_courses.return_value = set()
            mock_engine.check_prerequisites_met.return_value = (True, [])
            mock_engine.compute_student_validation_flags.return_value = mock_validation_flags
            mock_prereq.return_value = mock_engine

            result = service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2030",
                "status": "planned"
            })

            # Should have validationWarnings in result
            assert "validationWarnings" in result
            assert result["validationWarnings"] == mock_validation_flags
            assert result["validationWarnings"]["warnings"] == ["Fall 2030: Heavy course load (16 credits)"]

    def test_add_enrollment_calls_compute_validation_flags_after_save(self, service, mock_db):
        """compute_student_validation_flags should be called AFTER enrollment is saved"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_enrollment"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        call_order = []

        def track_set(*args, **kwargs):
            call_order.append("save")

        def track_compute(*args, **kwargs):
            call_order.append("compute")
            return {"flags": [], "warnings": []}

        mock_doc_ref.set.side_effect = track_set

        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            mock_engine = MagicMock()
            mock_engine.get_student_completed_courses.return_value = set()
            mock_engine.get_student_current_courses.return_value = set()
            mock_engine.check_prerequisites_met.return_value = (True, [])
            mock_engine.compute_student_validation_flags.side_effect = track_compute
            mock_prereq.return_value = mock_engine

            service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2030",
                "status": "planned"
            })

            # Verify save happens before compute
            assert call_order == ["save", "compute"]

    def test_add_enrollment_no_validation_warnings_for_completed(self, service, mock_db):
        """Completed courses should not trigger validation warnings"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "completed_enrollment"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_query

        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            result = service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2020",
                "status": "completed",
                "grade": "A"
            })

            # Should have None for validationWarnings
            assert result["validationWarnings"] is None
            # compute_student_validation_flags should not be called
            mock_prereq.return_value.compute_student_validation_flags.assert_not_called()

    def test_acknowledge_enrollment_warnings_saves_flags(self, service, mock_db):
        """acknowledge_enrollment_warnings should call save_validation_flags"""
        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            mock_engine = MagicMock()
            saved_flags = {
                "flags": [{"type": "heavy_workload"}],
                "warnings": ["Heavy course load"]
            }
            mock_engine.save_validation_flags.return_value = saved_flags
            mock_prereq.return_value = mock_engine

            result = service.acknowledge_enrollment_warnings("user123")

            mock_engine.save_validation_flags.assert_called_once_with("user123")
            assert result == saved_flags

    def test_prereq_check_happens_only_once(self, service, mock_db):
        """Prerequisite check should happen only once in add_enrollment, not in compute_validation_flags"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_enrollment"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            mock_engine = MagicMock()
            mock_engine.get_student_completed_courses.return_value = {"BUAD 201"}
            mock_engine.get_student_current_courses.return_value = set()
            mock_engine.check_prerequisites_met.return_value = (True, [])
            mock_engine.compute_student_validation_flags.return_value = {"flags": [], "warnings": []}
            mock_prereq.return_value = mock_engine

            service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Fall 2030",
                "status": "planned"
            })

            # check_prerequisites_met should be called exactly once (before save)
            assert mock_engine.check_prerequisites_met.call_count == 1

            # compute_student_validation_flags should NOT call check_prerequisites_met again
            # (it only checks credit limits and workload balance)
            # This is verified by the call count remaining at 1

    def test_validation_warnings_include_term_filter(self, service, mock_db):
        """compute_student_validation_flags should be called with the specific term"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_enrollment"
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        with patch('services.prerequisites.get_prerequisite_engine') as mock_prereq:
            mock_engine = MagicMock()
            mock_engine.get_student_completed_courses.return_value = set()
            mock_engine.get_student_current_courses.return_value = set()
            mock_engine.check_prerequisites_met.return_value = (True, [])
            mock_engine.compute_student_validation_flags.return_value = {"flags": [], "warnings": []}
            mock_prereq.return_value = mock_engine

            service.add_enrollment("user123", {
                "courseCode": "BUAD 327",
                "term": "Spring 2031",
                "status": "planned"
            })

            # Should be called with specific term
            mock_engine.compute_student_validation_flags.assert_called_once_with(
                "user123", term="Spring 2031"
            )
