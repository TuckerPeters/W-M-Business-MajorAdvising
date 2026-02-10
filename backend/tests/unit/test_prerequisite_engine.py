"""
Tests for services/prerequisites.py - Prerequisite validation engine
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import asdict

from services.prerequisites import (
    PrerequisiteEngine,
    PrerequisiteInfo,
    RiskLevel,
    RiskFlag,
    ValidationResult,
    ScheduleScore
)


class TestPrerequisiteEngine:
    """Tests for PrerequisiteEngine core functionality"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.prerequisites.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def mock_curriculum_data(self):
        """Mock curriculum data with prerequisites"""
        return {
            "academic_year": "2025-2026",
            "core_curriculum": [
                {
                    "description": "Foundation",
                    "courses": [
                        {"code": "BUAD 300", "name": "Business Foundations", "credits": 3, "prerequisites": [], "semester": "F/S"},
                        {"code": "BUAD 311", "name": "Marketing", "credits": 3, "prerequisites": [], "semester": "F/S"},
                        {"code": "BUAD 323", "name": "Finance", "credits": 3, "prerequisites": [], "semester": "F/S"},
                        {"code": "BUAD 350", "name": "Operations", "credits": 3, "prerequisites": [], "semester": "F/S"},
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
                                {"code": "BUAD 327", "name": "Investments", "credits": 3, "prerequisites": ["BUAD 323"], "semester": "F/S"},
                                {"code": "BUAD 329", "name": "Corporate Valuation", "credits": 3, "prerequisites": ["BUAD 323"], "semester": "F/S"},
                                {"code": "BUAD 422", "name": "Applied Finance", "credits": 3, "prerequisites": ["BUAD 323", "BUAD 329"], "semester": "S"},
                            ]
                        }
                    ],
                    "elective_courses": []
                },
                {
                    "name": "Accounting",
                    "credits_required": 21,
                    "required_courses": [
                        {
                            "description": "Required",
                            "courses": [
                                {"code": "BUAD 301", "name": "Financial Reporting", "credits": 3, "prerequisites": ["BUAD 203"], "semester": "F/S"},
                                {"code": "BUAD 302", "name": "Advanced Financial Reporting", "credits": 3, "prerequisites": ["BUAD 301"], "semester": "S"},
                            ]
                        }
                    ],
                    "elective_courses": []
                }
            ],
            "concentrations": [],
            "prerequisites": None
        }

    @pytest.fixture
    def engine(self, mock_db, mock_curriculum_data):
        """Create PrerequisiteEngine with mocked data"""
        # Configure mock to return document not found (so it falls back to curriculum data)
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch('services.prerequisites.initialize_firebase'):
            with patch('services.prerequisites.load_curriculum_data', return_value=mock_curriculum_data):
                engine = PrerequisiteEngine()
                engine._ensure_loaded()
                return engine

    def test_load_prerequisite_data(self, engine):
        """Should load prerequisite data from curriculum"""
        assert len(engine._prereq_map) > 0
        assert "BUAD 323" in engine._prereq_map
        assert "BUAD 327" in engine._prereq_map

    def test_get_prerequisites_found(self, engine):
        """Should return prerequisite info for a course"""
        info = engine.get_prerequisites("BUAD 327")

        assert info is not None
        assert info.course_code == "BUAD 327"
        assert info.course_name == "Investments"
        assert "BUAD 323" in info.prerequisites

    def test_get_prerequisites_not_found(self, engine):
        """Should return None for unknown course"""
        info = engine.get_prerequisites("UNKNOWN 999")

        assert info is None

    def test_get_course_credits(self, engine):
        """Should return credits for a course"""
        credits = engine.get_course_credits("BUAD 327")

        assert credits == 3

    def test_get_course_credits_default(self, engine, mock_db):
        """Should return default 3 credits for unknown course"""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        credits = engine.get_course_credits("UNKNOWN 999")

        assert credits == 3


class TestPrerequisiteChecking:
    """Tests for prerequisite validation"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.prerequisites.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def mock_curriculum_data(self):
        """Mock curriculum data with prerequisites"""
        return {
            "academic_year": "2025-2026",
            "core_curriculum": [],
            "majors": [
                {
                    "name": "Finance",
                    "credits_required": 21,
                    "required_courses": [
                        {
                            "description": "Required",
                            "courses": [
                                {"code": "BUAD 323", "name": "Finance", "credits": 3, "prerequisites": [], "semester": "F/S"},
                                {"code": "BUAD 327", "name": "Investments", "credits": 3, "prerequisites": ["BUAD 323"], "semester": "F/S"},
                                {"code": "BUAD 422", "name": "Applied Finance", "credits": 3, "prerequisites": ["BUAD 323", "BUAD 329"], "semester": "S"},
                            ]
                        }
                    ],
                    "elective_courses": []
                }
            ],
            "concentrations": [],
            "prerequisites": None
        }

    @pytest.fixture
    def engine(self, mock_db, mock_curriculum_data):
        """Create PrerequisiteEngine with mocked data"""
        # Mock Firebase document lookup to return prerequisites based on course code
        # check_prerequisites_met uses Firebase as the source for prerequisites
        firebase_prereqs = {
            "BUAD_323": [],  # No prerequisites
            "BUAD_327": ["BUAD 323"],  # Requires BUAD 323
            "BUAD_422": ["BUAD 323", "BUAD 329"],  # Requires both
        }

        def mock_get_doc():
            doc_id = mock_db.collection.return_value.document.call_args[0][0]
            mock_doc = MagicMock()
            if doc_id in firebase_prereqs:
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {"prerequisites": firebase_prereqs[doc_id]}
            else:
                mock_doc.exists = False
            return mock_doc

        mock_db.collection.return_value.document.return_value.get.side_effect = mock_get_doc

        with patch('services.prerequisites.initialize_firebase'):
            with patch('services.prerequisites.load_curriculum_data', return_value=mock_curriculum_data):
                engine = PrerequisiteEngine()
                engine._ensure_loaded()
                return engine

    def test_check_prerequisites_met_no_prereqs(self, engine):
        """Should pass when course has no prerequisites"""
        met, missing = engine.check_prerequisites_met("BUAD 323", set())

        assert met is True
        assert len(missing) == 0

    def test_check_prerequisites_met_with_completed(self, engine):
        """Should pass when prerequisites are completed"""
        met, missing = engine.check_prerequisites_met("BUAD 327", {"BUAD 323"})

        assert met is True
        assert len(missing) == 0

    def test_check_prerequisites_not_met(self, engine):
        """Should fail when prerequisites are missing"""
        met, missing = engine.check_prerequisites_met("BUAD 327", set())

        assert met is False
        assert "BUAD 323" in missing

    def test_check_prerequisites_multiple_missing(self, engine):
        """Should detect multiple missing prerequisites"""
        met, missing = engine.check_prerequisites_met("BUAD 422", set())

        assert met is False
        assert "BUAD 323" in missing
        assert "BUAD 329" in missing

    def test_check_prerequisites_partial(self, engine):
        """Should detect partially met prerequisites"""
        met, missing = engine.check_prerequisites_met("BUAD 422", {"BUAD 323"})

        assert met is False
        assert "BUAD 329" in missing
        assert "BUAD 323" not in missing

    def test_check_prerequisites_concurrent(self, engine):
        """Should consider concurrent courses"""
        met, missing = engine.check_prerequisites_met(
            "BUAD 327",
            set(),  # No completed
            {"BUAD 323"}  # Taking concurrently
        )

        assert met is True
        assert len(missing) == 0


class TestCreditLimits:
    """Tests for credit limit validation"""

    @pytest.fixture
    def engine(self):
        """Create PrerequisiteEngine for credit testing"""
        with patch('services.prerequisites.get_firestore_client'):
            with patch('services.prerequisites.initialize_firebase'):
                with patch('services.prerequisites.load_curriculum_data', return_value=None):
                    engine = PrerequisiteEngine()
                    engine._loaded = True  # Skip loading
                    return engine

    def test_credit_normal_range(self, engine):
        """Should not flag credits in normal range (12-15)"""
        flag = engine._check_credit_limits(15)

        assert flag is None

    def test_credit_underload(self, engine):
        """Should flag underload (below 12 credits)"""
        flag = engine._check_credit_limits(9)

        assert flag is not None
        assert flag.type == "underload"
        assert flag.severity == RiskLevel.MEDIUM

    def test_credit_heavy_workload(self, engine):
        """Should flag heavy workload (16-18 credits)"""
        flag = engine._check_credit_limits(17)

        assert flag is not None
        assert flag.type == "heavy_workload"
        assert flag.severity == RiskLevel.MEDIUM

    def test_credit_at_max(self, engine):
        """Should flag heavy workload at max credits (18)"""
        flag = engine._check_credit_limits(18)

        assert flag is not None
        assert flag.type == "heavy_workload"
        assert flag.severity == RiskLevel.MEDIUM

    def test_credit_overload_invalid(self, engine):
        """Should flag overload (>18 credits) as CRITICAL and invalid"""
        flag = engine._check_credit_limits(19)

        assert flag is not None
        assert flag.type == "credit_overload"
        assert flag.severity == RiskLevel.CRITICAL
        assert flag.details.get("invalid") is True

    def test_credit_high_overload(self, engine):
        """Should flag high overload (>21 credits) as CRITICAL"""
        flag = engine._check_credit_limits(22)

        assert flag is not None
        assert flag.type == "credit_overload"
        assert flag.severity == RiskLevel.CRITICAL
        assert flag.details.get("invalid") is True


class TestScheduleValidation:
    """Tests for full schedule validation"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.prerequisites.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def mock_curriculum_data(self):
        """Mock curriculum data"""
        return {
            "academic_year": "2025-2026",
            "core_curriculum": [
                {
                    "description": "Foundation",
                    "courses": [
                        {"code": "BUAD 300", "name": "Business Foundations", "credits": 3, "prerequisites": [], "semester": "F/S"},
                        {"code": "BUAD 311", "name": "Marketing", "credits": 3, "prerequisites": [], "semester": "F/S"},
                        {"code": "BUAD 350", "name": "Operations", "credits": 3, "prerequisites": [], "semester": "F/S"},
                        {"code": "BUAD 317", "name": "Management", "credits": 3, "prerequisites": [], "semester": "F/S"},
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
                                {"code": "BUAD 323", "name": "Finance", "credits": 3, "prerequisites": [], "semester": "F/S"},
                                {"code": "BUAD 327", "name": "Investments", "credits": 3, "prerequisites": ["BUAD 323"], "semester": "F/S"},
                                {"code": "BUAD 329", "name": "Corporate Valuation", "credits": 3, "prerequisites": ["BUAD 323"], "semester": "F/S"},
                            ]
                        }
                    ],
                    "elective_courses": []
                }
            ],
            "concentrations": [],
            "prerequisites": None
        }

    @pytest.fixture
    def engine(self, mock_db, mock_curriculum_data):
        """Create PrerequisiteEngine with mocked data"""
        # Mock Firebase document lookup to return prerequisites based on course code
        firebase_prereqs = {
            "BUAD_323": [],
            "BUAD_327": ["BUAD 323"],
            "BUAD_329": ["BUAD 323"],
            "BUAD_300": [],
            "BUAD_311": [],
            "BUAD_350": [],
            "BUAD_317": [],
        }

        def mock_get_doc():
            doc_id = mock_db.collection.return_value.document.call_args[0][0]
            mock_doc = MagicMock()
            if doc_id in firebase_prereqs:
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {"prerequisites": firebase_prereqs[doc_id]}
            else:
                mock_doc.exists = False
            return mock_doc

        mock_db.collection.return_value.document.return_value.get.side_effect = mock_get_doc

        with patch('services.prerequisites.initialize_firebase'):
            with patch('services.prerequisites.load_curriculum_data', return_value=mock_curriculum_data):
                engine = PrerequisiteEngine()
                engine._ensure_loaded()
                return engine

    def test_validate_schedule_valid(self, engine, mock_db):
        """Should validate a valid schedule"""
        # Mock completed courses query
        mock_completed = MagicMock()
        mock_completed.stream.return_value = [
            MagicMock(to_dict=lambda: {"courseCode": "BUAD 323", "status": "completed"})
        ]

        # Mock current courses query
        mock_current = MagicMock()
        mock_current.stream.return_value = []

        mock_db.collection.return_value.where.return_value.where.return_value = mock_completed
        mock_db.collection.return_value.where.return_value.where.side_effect = [mock_completed, mock_current]

        result = engine.validate_schedule("student1", ["BUAD 327", "BUAD 329"])

        assert result.valid is True
        assert len(result.missing_prereqs) == 0

    def test_validate_schedule_missing_prereqs(self, engine, mock_db):
        """Should detect missing prerequisites"""
        # Mock empty completed courses
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value = mock_query

        result = engine.validate_schedule("student1", ["BUAD 327"])

        assert result.valid is False
        assert "BUAD 327" in result.missing_prereqs
        assert "BUAD 323" in result.missing_prereqs["BUAD 327"]

    def test_validate_schedule_credit_overload(self, engine, mock_db):
        """Should flag credit overload"""
        # Mock completed courses
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value = mock_query

        # Add enough courses to trigger overload (7 x 3 = 21 credits)
        courses = ["BUAD 323", "BUAD 327", "BUAD 329", "BUAD 300", "BUAD 311", "BUAD 350", "BUAD 317"]
        result = engine.validate_schedule("student1", courses)

        # Should have credit overload flag
        overload_flags = [f for f in result.risk_flags if f.get("type") == "credit_overload"]
        assert len(overload_flags) > 0


class TestScheduleScore:
    """Tests for schedule scoring"""

    @pytest.fixture
    def engine(self):
        """Create PrerequisiteEngine for score testing"""
        with patch('services.prerequisites.get_firestore_client'):
            with patch('services.prerequisites.initialize_firebase'):
                with patch('services.prerequisites.load_curriculum_data', return_value=None):
                    engine = PrerequisiteEngine()
                    engine._loaded = True
                    return engine

    def test_score_perfect_schedule(self, engine):
        """Should score perfect schedule highly"""
        score = engine._calculate_schedule_score(
            courses=["BUAD 323", "BUAD 311", "MATH 111", "ECON 101", "ENGL 101"],
            missing_prereqs={},
            total_credits=15,
            course_details=[
                {"code": "BUAD 323", "prerequisites": []},
                {"code": "BUAD 311", "prerequisites": []},
                {"code": "MATH 111", "prerequisites": []},
                {"code": "ECON 101", "prerequisites": []},
                {"code": "ENGL 101", "prerequisites": []},
            ]
        )

        assert score.overall >= 90
        assert score.prerequisite_alignment == 100
        assert score.workload == 100

    def test_score_missing_prereqs(self, engine):
        """Should penalize missing prerequisites"""
        score = engine._calculate_schedule_score(
            courses=["BUAD 327", "BUAD 329"],
            missing_prereqs={"BUAD 327": ["BUAD 323"], "BUAD 329": ["BUAD 323"]},
            total_credits=6,
            course_details=[]
        )

        assert score.prerequisite_alignment == 0  # All courses missing prereqs

    def test_score_heavy_workload(self, engine):
        """Should penalize heavy workload (16-18 credits)"""
        score = engine._calculate_schedule_score(
            courses=["C1", "C2", "C3", "C4", "C5", "C6"],
            missing_prereqs={},
            total_credits=17,
            course_details=[]
        )

        # 17 credits = 100 - 10*(17-15) = 80
        assert score.workload == 80

    def test_score_overload_invalid(self, engine):
        """Should give zero workload score for invalid credit load (>18)"""
        score = engine._calculate_schedule_score(
            courses=["C1", "C2", "C3", "C4", "C5", "C6", "C7"],
            missing_prereqs={},
            total_credits=21,
            course_details=[]
        )

        assert score.workload == 0  # Invalid schedule


class TestEligibleCourses:
    """Tests for eligible courses lookup"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.prerequisites.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def mock_curriculum_data(self):
        """Mock curriculum data"""
        return {
            "academic_year": "2025-2026",
            "core_curriculum": [],
            "majors": [
                {
                    "name": "Finance",
                    "credits_required": 21,
                    "required_courses": [
                        {
                            "description": "Required",
                            "courses": [
                                {"code": "BUAD 323", "name": "Finance", "credits": 3, "prerequisites": [], "semester": "F/S"},
                                {"code": "BUAD 327", "name": "Investments", "credits": 3, "prerequisites": ["BUAD 323"], "semester": "F/S"},
                            ]
                        }
                    ],
                    "elective_courses": []
                }
            ],
            "concentrations": [],
            "prerequisites": None
        }

    @pytest.fixture
    def engine(self, mock_db, mock_curriculum_data):
        """Create PrerequisiteEngine with mocked data"""
        # Mock Firebase document lookup to return prerequisites based on course code
        firebase_prereqs = {
            "BUAD_323": [],
            "BUAD_327": ["BUAD 323"],
        }

        def mock_get_doc():
            doc_id = mock_db.collection.return_value.document.call_args[0][0]
            mock_doc = MagicMock()
            if doc_id in firebase_prereqs:
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {"prerequisites": firebase_prereqs[doc_id]}
            else:
                mock_doc.exists = False
            return mock_doc

        mock_db.collection.return_value.document.return_value.get.side_effect = mock_get_doc

        with patch('services.prerequisites.initialize_firebase'):
            with patch('services.prerequisites.load_curriculum_data', return_value=mock_curriculum_data):
                engine = PrerequisiteEngine()
                engine._ensure_loaded()
                return engine

    def test_eligible_courses_none_completed(self, engine, mock_db):
        """Should return courses with no prerequisites when nothing completed"""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value = mock_query

        eligible = engine.get_eligible_courses("student1")

        # Should include BUAD 323 (no prereqs) but not BUAD 327
        codes = [c["code"] for c in eligible]
        assert "BUAD 323" in codes
        assert "BUAD 327" not in codes

    def test_eligible_courses_with_completed(self, engine, mock_db):
        """Should include courses with met prerequisites"""
        # Mock completed courses
        mock_completed = MagicMock()
        mock_completed.stream.return_value = [
            MagicMock(to_dict=lambda: {"courseCode": "BUAD 323", "status": "completed"})
        ]
        mock_current = MagicMock()
        mock_current.stream.return_value = []

        mock_db.collection.return_value.where.return_value.where.side_effect = [mock_completed, mock_current]

        eligible = engine.get_eligible_courses("student1")

        # Should include BUAD 327 since BUAD 323 is completed
        codes = [c["code"] for c in eligible]
        assert "BUAD 327" in codes
        # Should not include BUAD 323 since already completed
        assert "BUAD 323" not in codes


class TestPrerequisiteChain:
    """Tests for prerequisite chain lookup"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.prerequisites.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def mock_curriculum_data(self):
        """Mock curriculum data with chain"""
        return {
            "academic_year": "2025-2026",
            "core_curriculum": [],
            "majors": [
                {
                    "name": "Accounting",
                    "credits_required": 21,
                    "required_courses": [
                        {
                            "description": "Required",
                            "courses": [
                                {"code": "BUAD 203", "name": "Intro Accounting", "credits": 3, "prerequisites": [], "semester": "F/S"},
                                {"code": "BUAD 301", "name": "Financial Reporting", "credits": 3, "prerequisites": ["BUAD 203"], "semester": "F/S"},
                                {"code": "BUAD 302", "name": "Advanced Reporting", "credits": 3, "prerequisites": ["BUAD 301"], "semester": "S"},
                            ]
                        }
                    ],
                    "elective_courses": []
                }
            ],
            "concentrations": [],
            "prerequisites": None
        }

    @pytest.fixture
    def engine(self, mock_db, mock_curriculum_data):
        """Create PrerequisiteEngine with mocked data"""
        # Configure mock to return document not found (so it falls back to curriculum data)
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch('services.prerequisites.initialize_firebase'):
            with patch('services.prerequisites.load_curriculum_data', return_value=mock_curriculum_data):
                engine = PrerequisiteEngine()
                engine._ensure_loaded()
                return engine

    def test_prerequisite_chain(self, engine):
        """Should build full prerequisite chain"""
        chain = engine.get_prerequisite_chain("BUAD 302")

        assert chain["code"] == "BUAD 302"
        assert len(chain["prerequisites"]) == 1

        # First level prereq
        prereq1 = chain["prerequisites"][0]
        assert prereq1["code"] == "BUAD 301"
        assert len(prereq1["prerequisites"]) == 1

        # Second level prereq
        prereq2 = prereq1["prerequisites"][0]
        assert prereq2["code"] == "BUAD 203"
        assert len(prereq2["prerequisites"]) == 0

    def test_prerequisite_chain_no_prereqs(self, engine):
        """Should handle course with no prerequisites"""
        chain = engine.get_prerequisite_chain("BUAD 203")

        assert chain["code"] == "BUAD 203"
        assert len(chain["prerequisites"]) == 0


class TestComputeValidationFlags:
    """Tests for compute_student_validation_flags - the non-blocking validation method.

    IMPORTANT: compute_student_validation_flags should ONLY check:
    - Credit limits (_check_credit_limits)
    - Workload balance (_check_workload_balance)
    - Schedule score (_calculate_schedule_score)

    It should NOT re-check prerequisites - that happens at enrollment time.
    """

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.prerequisites.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def mock_curriculum_data(self):
        """Mock curriculum data"""
        return {
            "academic_year": "2025-2026",
            "core_curriculum": [],
            "majors": [
                {
                    "name": "Finance",
                    "credits_required": 21,
                    "required_courses": [
                        {
                            "description": "Required",
                            "courses": [
                                {"code": "BUAD 323", "name": "Finance", "credits": 3, "prerequisites": [], "semester": "F/S"},
                                {"code": "BUAD 327", "name": "Investments", "credits": 3, "prerequisites": ["BUAD 323"], "semester": "F/S"},
                                {"code": "BUAD 329", "name": "Corporate Valuation", "credits": 3, "prerequisites": ["BUAD 323"], "semester": "F/S"},
                            ]
                        }
                    ],
                    "elective_courses": []
                }
            ],
            "concentrations": [],
            "prerequisites": None
        }

    @pytest.fixture
    def engine(self, mock_db, mock_curriculum_data):
        """Create PrerequisiteEngine with mocked data"""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch('services.prerequisites.initialize_firebase'):
            with patch('services.prerequisites.load_curriculum_data', return_value=mock_curriculum_data):
                engine = PrerequisiteEngine()
                engine._ensure_loaded()
                return engine

    def test_compute_validation_flags_does_not_check_prerequisites(self, engine, mock_db):
        """compute_student_validation_flags should NOT call check_prerequisites_met"""
        # Mock enrollments
        mock_enrollment = MagicMock()
        mock_enrollment.to_dict.return_value = {
            "studentId": "student1",
            "courseCode": "BUAD 327",
            "term": "Fall 2030",
            "status": "planned",
            "credits": 3
        }
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_enrollment]
        mock_db.collection.return_value.where.return_value = mock_query

        # Spy on check_prerequisites_met
        original_check = engine.check_prerequisites_met
        engine.check_prerequisites_met = MagicMock(wraps=original_check)

        result = engine.compute_student_validation_flags("student1")

        # check_prerequisites_met should NOT be called
        engine.check_prerequisites_met.assert_not_called()

        # But the result should still have validation data
        assert "flags" in result
        assert "warnings" in result

    def test_compute_validation_flags_checks_credit_limits(self, engine, mock_db):
        """compute_student_validation_flags should call _check_credit_limits"""
        # Mock 6 enrollments (18 credits = heavy workload)
        enrollments = []
        for i, code in enumerate(["BUAD 323", "BUAD 327", "BUAD 329", "BUAD 300", "BUAD 311", "BUAD 350"]):
            mock_enrollment = MagicMock()
            mock_enrollment.to_dict.return_value = {
                "studentId": "student1",
                "courseCode": code,
                "term": "Fall 2030",
                "status": "planned",
                "credits": 3
            }
            enrollments.append(mock_enrollment)

        mock_query = MagicMock()
        mock_query.stream.return_value = enrollments
        mock_db.collection.return_value.where.return_value = mock_query

        result = engine.compute_student_validation_flags("student1")

        # Should have a heavy_workload flag
        flag_types = [f.get("type") for f in result["flags"]]
        assert "heavy_workload" in flag_types

    def test_compute_validation_flags_checks_workload_balance(self, engine, mock_db):
        """compute_student_validation_flags should call _check_workload_balance"""
        # Mock 4 upper-level courses (courses ending with 4,5,6,7,8,9 trigger workload_imbalance)
        enrollments = []
        for code in ["BUAD 424", "BUAD 425", "BUAD 426", "BUAD 427"]:
            mock_enrollment = MagicMock()
            mock_enrollment.to_dict.return_value = {
                "studentId": "student1",
                "courseCode": code,
                "term": "Fall 2030",
                "status": "planned",
                "credits": 3
            }
            enrollments.append(mock_enrollment)

        mock_query = MagicMock()
        mock_query.stream.return_value = enrollments
        mock_db.collection.return_value.where.return_value = mock_query

        result = engine.compute_student_validation_flags("student1")

        # Should have a workload_imbalance flag
        flag_types = [f.get("type") for f in result["flags"]]
        assert "workload_imbalance" in flag_types

    def test_compute_validation_flags_returns_credits_by_term(self, engine, mock_db):
        """compute_student_validation_flags should return credits grouped by term"""
        enrollments = []
        # 2 courses in Fall 2030
        for code in ["BUAD 323", "BUAD 327"]:
            mock_enrollment = MagicMock()
            mock_enrollment.to_dict.return_value = {
                "studentId": "student1",
                "courseCode": code,
                "term": "Fall 2030",
                "status": "planned",
                "credits": 3
            }
            enrollments.append(mock_enrollment)

        # 1 course in Spring 2031
        mock_enrollment = MagicMock()
        mock_enrollment.to_dict.return_value = {
            "studentId": "student1",
            "courseCode": "BUAD 329",
            "term": "Spring 2031",
            "status": "planned",
            "credits": 3
        }
        enrollments.append(mock_enrollment)

        mock_query = MagicMock()
        mock_query.stream.return_value = enrollments
        mock_db.collection.return_value.where.return_value = mock_query

        result = engine.compute_student_validation_flags("student1")

        assert "total_credits_by_term" in result
        assert result["total_credits_by_term"]["Fall 2030"] == 6
        assert result["total_credits_by_term"]["Spring 2031"] == 3

    def test_compute_validation_flags_filters_by_term(self, engine, mock_db):
        """compute_student_validation_flags should filter by term when specified"""
        enrollments = []
        # Mix of terms
        for code, term in [("BUAD 323", "Fall 2030"), ("BUAD 327", "Fall 2030"), ("BUAD 329", "Spring 2031")]:
            mock_enrollment = MagicMock()
            mock_enrollment.to_dict.return_value = {
                "studentId": "student1",
                "courseCode": code,
                "term": term,
                "status": "planned",
                "credits": 3
            }
            enrollments.append(mock_enrollment)

        mock_query = MagicMock()
        mock_query.stream.return_value = enrollments
        mock_db.collection.return_value.where.return_value = mock_query

        result = engine.compute_student_validation_flags("student1", term="Fall 2030")

        # Should only include Fall 2030
        assert "Fall 2030" in result["total_credits_by_term"]
        assert "Spring 2031" not in result["total_credits_by_term"]

    def test_compute_validation_flags_empty_enrollments(self, engine, mock_db):
        """compute_student_validation_flags should handle no enrollments"""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_query

        result = engine.compute_student_validation_flags("student1")

        assert result["flags"] == []
        assert result["warnings"] == []
        assert result["total_credits"] == 0
        assert result["schedule_score"] is None


class TestSaveValidationFlags:
    """Tests for save_validation_flags - persisting flags to student document"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.prerequisites.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def engine(self, mock_db):
        """Create PrerequisiteEngine with mocked data"""
        with patch('services.prerequisites.initialize_firebase'):
            with patch('services.prerequisites.load_curriculum_data', return_value=None):
                engine = PrerequisiteEngine()
                engine._loaded = True
                return engine

    def test_save_validation_flags_updates_student_document(self, engine, mock_db):
        """save_validation_flags should update student document with flags"""
        # Mock compute to return specific flags
        mock_flags = {
            "flags": [{"type": "heavy_workload"}],
            "warnings": ["Heavy course load"],
            "total_credits_by_term": {"Fall 2030": 16}
        }
        engine.compute_student_validation_flags = MagicMock(return_value=mock_flags)

        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = engine.save_validation_flags("student1")

        # Should update student document
        mock_doc_ref.update.assert_called_once()
        update_call = mock_doc_ref.update.call_args[0][0]
        assert update_call["validationFlags"] == mock_flags
        assert "validationFlagsUpdatedAt" in update_call

        assert result == mock_flags


class TestGetSavedValidationFlags:
    """Tests for get_saved_validation_flags - retrieving persisted flags"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client"""
        with patch('services.prerequisites.get_firestore_client') as mock:
            db = MagicMock()
            mock.return_value = db
            yield db

    @pytest.fixture
    def engine(self, mock_db):
        """Create PrerequisiteEngine with mocked data"""
        with patch('services.prerequisites.initialize_firebase'):
            with patch('services.prerequisites.load_curriculum_data', return_value=None):
                engine = PrerequisiteEngine()
                engine._loaded = True
                return engine

    def test_get_saved_validation_flags_returns_flags(self, engine, mock_db):
        """get_saved_validation_flags should return saved flags from student document"""
        saved_flags = {
            "flags": [{"type": "heavy_workload"}],
            "warnings": ["Heavy course load"]
        }

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"validationFlags": saved_flags}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = engine.get_saved_validation_flags("student1")

        assert result == saved_flags

    def test_get_saved_validation_flags_returns_none_when_no_flags(self, engine, mock_db):
        """get_saved_validation_flags should return None if no flags saved"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "John"}  # No validationFlags
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = engine.get_saved_validation_flags("student1")

        assert result is None

    def test_get_saved_validation_flags_returns_none_when_student_not_found(self, engine, mock_db):
        """get_saved_validation_flags should return None if student not found"""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = engine.get_saved_validation_flags("nonexistent")

        assert result is None


class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_prerequisite_engine_returns_instance(self):
        """Should return a PrerequisiteEngine instance"""
        with patch('services.prerequisites.initialize_firebase'):
            with patch('services.prerequisites.get_firestore_client'):
                with patch('services.prerequisites.load_curriculum_data', return_value=None):
                    from services.prerequisites import get_prerequisite_engine, _prerequisite_engine
                    import services.prerequisites as prereq_module

                    # Reset singleton
                    prereq_module._prerequisite_engine = None

                    engine = get_prerequisite_engine()

                    assert engine is not None
                    assert isinstance(engine, PrerequisiteEngine)
