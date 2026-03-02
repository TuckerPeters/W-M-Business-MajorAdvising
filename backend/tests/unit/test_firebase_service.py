"""
Tests for services/firebase.py - Firebase operations with Redis caching
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from api.fetcher import CourseData, SectionData


class TestFirebaseCourseService:
    """Tests for FirebaseCourseService"""

    @pytest.fixture
    def mock_firestore(self):
        """Create mock Firestore client"""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_batch = MagicMock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        mock_doc.get.return_value.exists = False
        mock_db.batch.return_value = mock_batch

        return mock_db

    @pytest.fixture
    def mock_cache(self):
        """Create mock Redis cache"""
        mock = MagicMock()
        mock.get_course.return_value = None
        mock.set_course.return_value = True
        mock.get_courses_by_subject.return_value = None
        mock.set_courses_by_subject.return_value = True
        mock.get_all_subjects.return_value = None
        mock.set_all_subjects.return_value = True
        mock.get_search_results.return_value = None
        mock.set_search_results.return_value = True
        mock.invalidate_all_courses.return_value = 0
        mock.warm_cache.return_value = 0
        mock.get_stats.return_value = {"connected": True}
        mock.clear_all.return_value = True
        return mock

    @pytest.fixture
    def sample_course(self):
        """Create sample course for testing"""
        section = SectionData(
            crn="12345",
            section_number="01",
            instructor="Smith",
            meeting_days="MWF",
            meeting_time="10:00",
            meeting_times_raw="MWF 10:00am",
            building="Morton",
            room="201",
            status="OPEN",
            capacity=30,
            enrolled=25,
            available=5
        )

        return CourseData(
            course_code="CSCI 141",
            subject_code="CSCI",
            course_number="141",
            title="Computational Problem Solving",
            description="Intro to CS",
            credits=4,
            attributes=["GER 1A"],
            sections=[section]
        )

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_store_courses_creates_new(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache, sample_course):
        """Should create new course documents"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        stats = service.store_courses([sample_course], "202610")

        assert stats['total_courses'] == 1
        assert stats['created'] == 1
        assert stats['errors'] == 0

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_store_courses_invalidates_cache(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache, sample_course):
        """Should invalidate and warm cache after storing courses"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        service.store_courses([sample_course], "202610")

        mock_cache.invalidate_all_courses.assert_called_once()
        mock_cache.warm_cache.assert_called_once()

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_store_courses_updates_existing(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache, sample_course):
        """Should update existing course documents"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        # Simulate existing document
        mock_doc = mock_firestore.collection.return_value.document.return_value
        mock_doc.get.return_value.exists = True

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        stats = service.store_courses([sample_course], "202610")

        assert stats['updated'] == 1

    def test_sanitize_doc_id(self):
        """Should sanitize document IDs"""
        from services.firebase import FirebaseCourseService

        # Create minimal instance for testing
        service = FirebaseCourseService.__new__(FirebaseCourseService)

        assert service._sanitize_doc_id("CSCI 141") == "CSCI_141"
        assert service._sanitize_doc_id("BUS/ACCT 301") == "BUS-ACCT_301"

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_get_course_cache_hit(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should return course from cache when cached"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        cached_course = {"course_code": "CSCI 141", "title": "From Cache"}
        mock_cache.get_course.return_value = cached_course

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        result = service.get_course("CSCI 141")

        assert result == cached_course
        mock_cache.get_course.assert_called_with("CSCI 141")

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_get_course_cache_miss(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should query Firestore and cache result when not in cache"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        mock_cache.get_course.return_value = None

        mock_doc = mock_firestore.collection.return_value.document.return_value
        mock_doc.get.return_value.exists = True
        mock_doc.get.return_value.to_dict.return_value = {
            "course_code": "CSCI 141",
            "title": "From Firestore"
        }

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        result = service.get_course("CSCI 141")

        assert result["title"] == "From Firestore"
        mock_cache.set_course.assert_called_once()

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_get_course_not_found(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should return None for non-existent course"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        mock_cache.get_course.return_value = None

        mock_doc = mock_firestore.collection.return_value.document.return_value
        mock_doc.get.return_value.exists = False

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        result = service.get_course("CSCI 999")
        assert result is None

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_get_course_found_no_cache(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should return course data when found without caching"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = False
        mock_get_cache.return_value = mock_cache

        mock_doc = mock_firestore.collection.return_value.document.return_value
        mock_doc.get.return_value.exists = True
        mock_doc.get.return_value.to_dict.return_value = {
            "course_code": "CSCI 141",
            "title": "Test Course"
        }

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=False)
        service.db = mock_firestore

        result = service.get_course("CSCI 141")
        assert result is not None
        assert result["course_code"] == "CSCI 141"


class TestFirebaseServiceCacheOperations:
    """Tests for cache-specific operations"""

    @pytest.fixture
    def mock_firestore(self):
        """Create mock Firestore client"""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        return mock_db

    @pytest.fixture
    def mock_cache(self):
        """Create mock Redis cache"""
        mock = MagicMock()
        mock.get_course.return_value = None
        mock.get_courses_by_subject.return_value = None
        mock.set_courses_by_subject.return_value = True
        mock.get_all_subjects.return_value = None
        mock.set_all_subjects.return_value = True
        mock.get_search_results.return_value = None
        mock.set_search_results.return_value = True
        mock.get_stats.return_value = {"connected": True, "hits": 100}
        mock.clear_all.return_value = True
        return mock

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_get_courses_by_subject_cache_hit(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should return courses from cache when cached"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        cached_courses = [{"course_code": "CSCI 141"}, {"course_code": "CSCI 241"}]
        mock_cache.get_courses_by_subject.return_value = cached_courses

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        result = service.get_courses_by_subject("CSCI")

        assert result == cached_courses
        mock_cache.get_courses_by_subject.assert_called_with("CSCI")

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_get_all_subjects_cache_hit(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should return subjects from cache when cached"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        cached_subjects = ["CSCI", "MATH", "BUAD"]
        mock_cache.get_all_subjects.return_value = cached_subjects

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        result = service.get_all_subjects()

        assert result == cached_subjects

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_search_courses_cache_hit(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should return search results from cache when cached"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        cached_results = [{"course_code": "CSCI 141"}]
        mock_cache.get_search_results.return_value = cached_results

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        result = service.search_courses("CSCI", limit=20)

        assert result == cached_results
        mock_cache.get_search_results.assert_called_with("CSCI", 20)

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_get_cache_stats(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should return cache statistics"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        mock_cache.get_stats.return_value = {"connected": True, "hits": 100, "misses": 10}

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        result = service.get_cache_stats()

        assert result["connected"] is True
        assert result["hits"] == 100

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_get_cache_stats_no_cache(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should return disabled status when cache not used"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = False

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=False)
        service.db = mock_firestore
        service._use_cache = False

        result = service.get_cache_stats()

        assert result["enabled"] is False

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.get_firestore_client')
    def test_clear_cache(self, mock_get_client, mock_get_cache, mock_cache_available, mock_firestore, mock_cache):
        """Should clear cache"""
        mock_get_client.return_value = mock_firestore
        mock_cache_available.return_value = True
        mock_get_cache.return_value = mock_cache

        from services.firebase import FirebaseCourseService
        service = FirebaseCourseService(use_cache=True)
        service.db = mock_firestore
        service._cache = mock_cache
        service._use_cache = True

        result = service.clear_cache()

        assert result is True
        mock_cache.clear_all.assert_called_once()


class TestFirebaseServiceHelpers:
    """Tests for helper functions"""

    @patch('services.firebase.is_cache_available')
    @patch('services.firebase.get_cache')
    @patch('services.firebase.initialize_firebase')
    @patch('services.firebase.get_firestore_client')
    def test_get_course_service(self, mock_get_client, mock_init, mock_get_cache, mock_cache_available):
        """Should return service instance"""
        mock_get_client.return_value = MagicMock()
        mock_cache_available.return_value = False

        from services.firebase import get_course_service
        service = get_course_service()

        assert service is not None
        mock_init.assert_called_once()
