"""
Firebase Service for Course Catalog Storage

Handles all Firestore database operations for storing and retrieving course data.
Includes Redis caching for improved read performance.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from core.config import get_firestore_client, initialize_firebase
from api.fetcher import CourseData
from services.cache import get_cache, is_cache_available


class FirebaseCourseService:
    """Service for managing courses in Firebase Firestore with Redis caching."""

    def __init__(self, use_cache: bool = True):
        """Initialize the Firebase course service."""
        self.db = get_firestore_client()
        self.courses_collection = "courses"
        self.metadata_collection = "metadata"
        self._use_cache = use_cache and is_cache_available()
        self._cache = get_cache() if self._use_cache else None

    def store_courses(self, courses: List[CourseData], term_code: str) -> Dict[str, Any]:
        """
        Store courses in Firestore.

        Args:
            courses: List of CourseData objects to store
            term_code: Term code for the courses

        Returns:
            Dictionary with statistics about the operation
        """
        stats = {
            "total_courses": len(courses),
            "created": 0,
            "updated": 0,
            "errors": 0,
            "term_code": term_code
        }

        batch = self.db.batch()
        batch_count = 0
        max_batch_size = 500  # Firestore limit

        for course in courses:
            try:
                # Use course_code as document ID (sanitized)
                doc_id = self._sanitize_doc_id(course.course_code)
                doc_ref = self.db.collection(self.courses_collection).document(doc_id)

                # Check if document exists
                existing_doc = doc_ref.get()

                # Prepare course data
                course_data = course.to_dict()
                course_data["term_code"] = term_code

                if existing_doc.exists:
                    batch.update(doc_ref, course_data)
                    stats["updated"] += 1
                else:
                    course_data["created_at"] = datetime.utcnow().isoformat()
                    batch.set(doc_ref, course_data)
                    stats["created"] += 1

                batch_count += 1

                # Commit batch if limit reached
                if batch_count >= max_batch_size:
                    batch.commit()
                    batch = self.db.batch()
                    batch_count = 0
                    print(f"Committed batch of {max_batch_size} courses...")

            except Exception as e:
                print(f"Error storing course {course.course_code}: {e}")
                stats["errors"] += 1

        # Commit remaining
        if batch_count > 0:
            batch.commit()
            print(f"Committed final batch of {batch_count} courses")

        # Update metadata
        self._update_metadata(term_code, stats)

        # Invalidate and warm cache
        if self._use_cache and self._cache:
            self._cache.invalidate_all_courses()
            # Warm cache with new data
            course_dicts = [c.to_dict() for c in courses]
            for cd in course_dicts:
                cd["term_code"] = term_code
            self._cache.warm_cache(course_dicts)

        return stats

    def store_courses_by_subject(self, courses: List[CourseData], term_code: str) -> Dict[str, Any]:
        """
        Store courses organized by subject code in Firestore.

        This creates a hierarchical structure:
        - subjects/{subject_code}/courses/{course_number}

        Args:
            courses: List of CourseData objects to store
            term_code: Term code for the courses

        Returns:
            Dictionary with statistics about the operation
        """
        stats = {
            "total_courses": len(courses),
            "subjects": set(),
            "created": 0,
            "updated": 0,
            "errors": 0,
            "term_code": term_code
        }

        # Group courses by subject
        subjects: Dict[str, List[CourseData]] = {}
        for course in courses:
            if course.subject_code not in subjects:
                subjects[course.subject_code] = []
            subjects[course.subject_code].append(course)

        for subject_code, subject_courses in subjects.items():
            stats["subjects"].add(subject_code)

            # Create/update subject document
            subject_ref = self.db.collection("subjects").document(subject_code)
            subject_ref.set({
                "subject_code": subject_code,
                "course_count": len(subject_courses),
                "term_code": term_code,
                "updated_at": datetime.utcnow().isoformat()
            }, merge=True)

            # Store each course under the subject
            batch = self.db.batch()
            batch_count = 0

            for course in subject_courses:
                try:
                    doc_id = course.course_number
                    doc_ref = subject_ref.collection("courses").document(doc_id)

                    existing = doc_ref.get()
                    course_data = course.to_dict()
                    course_data["term_code"] = term_code

                    if existing.exists:
                        batch.update(doc_ref, course_data)
                        stats["updated"] += 1
                    else:
                        course_data["created_at"] = datetime.utcnow().isoformat()
                        batch.set(doc_ref, course_data)
                        stats["created"] += 1

                    batch_count += 1

                    if batch_count >= 500:
                        batch.commit()
                        batch = self.db.batch()
                        batch_count = 0

                except Exception as e:
                    print(f"Error storing course {course.course_code}: {e}")
                    stats["errors"] += 1

            if batch_count > 0:
                batch.commit()

            print(f"Stored {len(subject_courses)} courses for subject {subject_code}")

        stats["subjects"] = list(stats["subjects"])
        self._update_metadata(term_code, stats)

        return stats

    def get_course(self, course_code: str) -> Optional[Dict[str, Any]]:
        """
        Get a single course by course code.

        Args:
            course_code: The course code (e.g., "CSCI 141")

        Returns:
            Course data dictionary or None if not found
        """
        # Try cache first
        if self._use_cache and self._cache:
            cached = self._cache.get_course(course_code)
            if cached:
                return cached

        # Fetch from Firestore
        doc_id = self._sanitize_doc_id(course_code)
        doc = self.db.collection(self.courses_collection).document(doc_id).get()

        if doc.exists:
            data = doc.to_dict()
            # Cache the result
            if self._use_cache and self._cache:
                self._cache.set_course(course_code, data)
            return data
        return None

    def get_courses_by_subject(self, subject_code: str) -> List[Dict[str, Any]]:
        """
        Get all courses for a subject.

        Args:
            subject_code: The subject code (e.g., "CSCI")

        Returns:
            List of course data dictionaries
        """
        # Try cache first
        if self._use_cache and self._cache:
            cached = self._cache.get_courses_by_subject(subject_code)
            if cached:
                return cached

        # Fetch from Firestore
        courses = []
        query = self.db.collection(self.courses_collection).where(
            "subject_code", "==", subject_code
        )

        for doc in query.stream():
            courses.append(doc.to_dict())

        # Cache the results
        if self._use_cache and self._cache and courses:
            self._cache.set_courses_by_subject(subject_code, courses)

        return courses

    def get_all_subjects(self) -> List[str]:
        """Get a list of all subject codes."""
        # Try cache first
        if self._use_cache and self._cache:
            cached = self._cache.get_all_subjects()
            if cached:
                return cached

        # Fetch from Firestore
        subjects = set()
        docs = self.db.collection(self.courses_collection).select(["subject_code"]).stream()

        for doc in docs:
            data = doc.to_dict()
            if "subject_code" in data:
                subjects.add(data["subject_code"])

        result = sorted(list(subjects))

        # Cache the results
        if self._use_cache and self._cache and result:
            self._cache.set_all_subjects(result)

        return result

    def search_courses(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search courses by title or course code.

        Note: Firestore doesn't support full-text search natively.
        For production, consider using Algolia or Elasticsearch.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching course data dictionaries
        """
        # Try cache first
        if self._use_cache and self._cache:
            cached = self._cache.get_search_results(query, limit)
            if cached:
                return cached

        # Search Firestore
        results = []
        query_upper = query.upper()

        # Search by course code prefix
        docs = self.db.collection(self.courses_collection)\
            .where("course_code", ">=", query_upper)\
            .where("course_code", "<=", query_upper + "\uf8ff")\
            .limit(limit)\
            .stream()

        for doc in docs:
            results.append(doc.to_dict())

        # Cache the results
        if self._use_cache and self._cache and results:
            self._cache.set_search_results(query, limit, results)

        return results

    def delete_all_courses(self) -> int:
        """
        Delete all courses from the database.

        Returns:
            Number of deleted documents
        """
        deleted = 0
        docs = self.db.collection(self.courses_collection).stream()

        batch = self.db.batch()
        batch_count = 0

        for doc in docs:
            batch.delete(doc.reference)
            batch_count += 1
            deleted += 1

            if batch_count >= 500:
                batch.commit()
                batch = self.db.batch()
                batch_count = 0

        if batch_count > 0:
            batch.commit()

        # Clear cache
        if self._use_cache and self._cache:
            self._cache.invalidate_all_courses()

        return deleted

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        if self._use_cache and self._cache:
            return self._cache.get_stats()
        return {"enabled": False}

    def clear_cache(self) -> bool:
        """Manually clear all cached data."""
        if self._use_cache and self._cache:
            return self._cache.clear_all()
        return False

    def _sanitize_doc_id(self, doc_id: str) -> str:
        """
        Sanitize a string to be used as a Firestore document ID.

        Firestore document IDs cannot contain:
        - Forward slashes (/)
        - Null characters
        - Cannot be . or ..
        """
        # Replace spaces with underscores
        sanitized = doc_id.replace(" ", "_")
        # Replace slashes
        sanitized = sanitized.replace("/", "-")
        return sanitized

    def _update_metadata(self, term_code: str, stats: Dict[str, Any]):
        """Update metadata about the last update operation."""
        metadata_ref = self.db.collection(self.metadata_collection).document("last_update")
        metadata_ref.set({
            "term_code": term_code,
            "timestamp": datetime.utcnow().isoformat(),
            "stats": stats
        })


def get_course_service() -> FirebaseCourseService:
    """Get an instance of the Firebase course service."""
    initialize_firebase()
    return FirebaseCourseService()
