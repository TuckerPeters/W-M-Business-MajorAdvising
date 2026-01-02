"""
Redis Cache Service for Course Data

Provides caching layer for Firebase/Firestore data to reduce database reads
and improve API response times.

Features:
- Automatic serialization/deserialization of course data
- Configurable TTL for different data types
- Graceful fallback if Redis unavailable
- Cache invalidation on updates
"""

import os
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis not installed. Run: pip install redis")

from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Cache key prefixes
CACHE_PREFIX = "wm_advising:"
COURSE_PREFIX = f"{CACHE_PREFIX}course:"
COURSES_BY_SUBJECT_PREFIX = f"{CACHE_PREFIX}subject:"
ALL_COURSES_KEY = f"{CACHE_PREFIX}all_courses"
ALL_SUBJECTS_KEY = f"{CACHE_PREFIX}all_subjects"
SEARCH_PREFIX = f"{CACHE_PREFIX}search:"
METADATA_KEY = f"{CACHE_PREFIX}metadata"

# TTL settings (in seconds)
COURSE_TTL = 300  # 5 minutes for individual courses
SUBJECT_TTL = 300  # 5 minutes for courses by subject
ALL_COURSES_TTL = 600  # 10 minutes for all courses list
SEARCH_TTL = 120  # 2 minutes for search results
METADATA_TTL = 60  # 1 minute for metadata


class RedisCache:
    """Redis caching service for course data"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connected = False

    def connect(self) -> bool:
        """
        Connect to Redis server.

        Returns:
            True if connected successfully, False otherwise
        """
        if not REDIS_AVAILABLE:
            print("[CACHE] Redis library not available")
            return False

        try:
            # Try URL first, then host/port
            if REDIS_URL and REDIS_URL != "redis://localhost:6379/0":
                self._client = redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
            else:
                self._client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )

            # Test connection
            self._client.ping()
            self._connected = True
            print(f"[CACHE] Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return True

        except Exception as e:
            print(f"[CACHE] Failed to connect to Redis: {e}")
            self._client = None
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self._connected or not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False

    def _ensure_connected(self) -> bool:
        """Ensure Redis is connected, attempt reconnect if not"""
        if self.is_connected:
            return True
        return self.connect()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._ensure_connected():
            return None

        try:
            data = self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"[CACHE] Get error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = COURSE_TTL) -> bool:
        """Set value in cache with TTL"""
        if not self._ensure_connected():
            return False

        try:
            self._client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            print(f"[CACHE] Set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self._ensure_connected():
            return False

        try:
            self._client.delete(key)
            return True
        except Exception as e:
            print(f"[CACHE] Delete error for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self._ensure_connected():
            return 0

        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            print(f"[CACHE] Delete pattern error for {pattern}: {e}")
            return 0

    def clear_all(self) -> bool:
        """Clear all cache keys for this application"""
        if not self._ensure_connected():
            return False

        try:
            deleted = self.delete_pattern(f"{CACHE_PREFIX}*")
            print(f"[CACHE] Cleared {deleted} keys")
            return True
        except Exception as e:
            print(f"[CACHE] Clear error: {e}")
            return False

    def get_course(self, course_code: str) -> Optional[Dict[str, Any]]:
        """Get a single course from cache"""
        key = f"{COURSE_PREFIX}{self._sanitize_key(course_code)}"
        return self.get(key)

    def set_course(self, course_code: str, course_data: Dict[str, Any]) -> bool:
        """Cache a single course"""
        key = f"{COURSE_PREFIX}{self._sanitize_key(course_code)}"
        return self.set(key, course_data, COURSE_TTL)

    def invalidate_course(self, course_code: str) -> bool:
        """Invalidate cache for a single course"""
        key = f"{COURSE_PREFIX}{self._sanitize_key(course_code)}"
        return self.delete(key)

    def get_courses_by_subject(self, subject_code: str) -> Optional[List[Dict[str, Any]]]:
        """Get all courses for a subject from cache"""
        key = f"{COURSES_BY_SUBJECT_PREFIX}{subject_code}"
        return self.get(key)

    def set_courses_by_subject(self, subject_code: str, courses: List[Dict[str, Any]]) -> bool:
        """Cache courses for a subject"""
        key = f"{COURSES_BY_SUBJECT_PREFIX}{subject_code}"
        return self.set(key, courses, SUBJECT_TTL)

    def invalidate_subject(self, subject_code: str) -> bool:
        """Invalidate cache for a subject"""
        key = f"{COURSES_BY_SUBJECT_PREFIX}{subject_code}"
        return self.delete(key)

    def get_all_subjects(self) -> Optional[List[str]]:
        """Get all subject codes from cache"""
        return self.get(ALL_SUBJECTS_KEY)

    def set_all_subjects(self, subjects: List[str]) -> bool:
        """Cache all subject codes"""
        return self.set(ALL_SUBJECTS_KEY, subjects, ALL_COURSES_TTL)

    def get_search_results(self, query: str, limit: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results"""
        key = f"{SEARCH_PREFIX}{self._hash_query(query, limit)}"
        return self.get(key)

    def set_search_results(self, query: str, limit: int, results: List[Dict[str, Any]]) -> bool:
        """Cache search results"""
        key = f"{SEARCH_PREFIX}{self._hash_query(query, limit)}"
        return self.set(key, results, SEARCH_TTL)

    def invalidate_all_courses(self) -> int:
        """Invalidate all course caches (after bulk update)"""
        count = 0
        count += self.delete_pattern(f"{COURSE_PREFIX}*")
        count += self.delete_pattern(f"{COURSES_BY_SUBJECT_PREFIX}*")
        count += self.delete_pattern(f"{SEARCH_PREFIX}*")
        self.delete(ALL_COURSES_KEY)
        self.delete(ALL_SUBJECTS_KEY)
        print(f"[CACHE] Invalidated {count} course cache entries")
        return count

    def warm_cache(self, courses: List[Dict[str, Any]]) -> int:
        """
        Pre-populate cache with course data.
        Call after bulk updates to Firebase.
        """
        if not self._ensure_connected():
            return 0

        cached = 0
        subjects = set()

        for course in courses:
            code = course.get('course_code', '')
            subject = course.get('subject_code', '')

            if code:
                if self.set_course(code, course):
                    cached += 1

            if subject:
                subjects.add(subject)

        # Cache subjects list
        if subjects:
            self.set_all_subjects(sorted(list(subjects)))

        print(f"[CACHE] Warmed cache with {cached} courses")
        return cached

    def _sanitize_key(self, key: str) -> str:
        """Sanitize a string for use as Redis key"""
        return key.replace(" ", "_").replace("/", "-")

    def _hash_query(self, query: str, limit: int) -> str:
        """Create hash for search query cache key"""
        content = f"{query.lower()}:{limit}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._ensure_connected():
            return {"connected": False}

        try:
            info = self._client.info("stats")
            memory = self._client.info("memory")

            # Count our keys
            course_keys = len(self._client.keys(f"{COURSE_PREFIX}*"))
            subject_keys = len(self._client.keys(f"{COURSES_BY_SUBJECT_PREFIX}*"))
            search_keys = len(self._client.keys(f"{SEARCH_PREFIX}*"))

            return {
                "connected": True,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "memory_used": memory.get("used_memory_human", "unknown"),
                "course_keys": course_keys,
                "subject_keys": subject_keys,
                "search_keys": search_keys,
                "total_keys": course_keys + subject_keys + search_keys
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}


_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get the singleton cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
        _cache_instance.connect()
    return _cache_instance


def is_cache_available() -> bool:
    """Check if cache is available and connected"""
    cache = get_cache()
    return cache.is_connected
