"""
Tests for services/cache.py - Redis cache service
"""

import pytest
import json
from unittest.mock import MagicMock, patch


class TestRedisCacheKeyGeneration:
    """Tests for key generation and sanitization - tests REAL logic"""

    def test_sanitize_key_replaces_spaces(self):
        """Should replace spaces with underscores"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()

            result = cache._sanitize_key("CSCI 141")
            assert result == "CSCI_141"

    def test_sanitize_key_replaces_slashes(self):
        """Should replace slashes with dashes"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()

            result = cache._sanitize_key("BUS/ACCT")
            assert result == "BUS-ACCT"

    def test_sanitize_key_handles_multiple_replacements(self):
        """Should handle both spaces and slashes"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()

            result = cache._sanitize_key("BUS/ACCT 301")
            assert result == "BUS-ACCT_301"

    def test_hash_query_produces_consistent_hash(self):
        """Should produce same hash for same query"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()

            hash1 = cache._hash_query("CSCI", 20)
            hash2 = cache._hash_query("CSCI", 20)
            assert hash1 == hash2

    def test_hash_query_different_for_different_queries(self):
        """Should produce different hash for different queries"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()

            hash1 = cache._hash_query("CSCI", 20)
            hash2 = cache._hash_query("MATH", 20)
            assert hash1 != hash2

    def test_hash_query_different_for_different_limits(self):
        """Should produce different hash for different limits"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()

            hash1 = cache._hash_query("CSCI", 20)
            hash2 = cache._hash_query("CSCI", 50)
            assert hash1 != hash2

    def test_hash_query_case_insensitive(self):
        """Should produce same hash regardless of case"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()

            hash1 = cache._hash_query("CSCI", 20)
            hash2 = cache._hash_query("csci", 20)
            assert hash1 == hash2

    def test_hash_query_length(self):
        """Should produce 16-character hash"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()

            result = cache._hash_query("test query", 100)
            assert len(result) == 16


class TestRedisCacheConnection:
    """Tests for Redis connection handling"""

    def test_connect_returns_false_when_redis_unavailable(self):
        """Should return False when redis library not installed"""
        with patch('services.cache.REDIS_AVAILABLE', False):
            from services.cache import RedisCache
            cache = RedisCache()

            result = cache.connect()

            assert result is False
            assert cache._connected is False

    def test_connect_returns_false_when_connection_fails(self):
        """Should return False and set _connected=False when connection fails"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            mock_redis = MagicMock()
            mock_redis.ping.side_effect = Exception("Connection refused")

            with patch('services.cache.redis.Redis', return_value=mock_redis):
                from services.cache import RedisCache
                cache = RedisCache()

                result = cache.connect()

                assert result is False
                assert cache._connected is False
                assert cache._client is None

    def test_connect_returns_true_when_successful(self):
        """Should return True and set _connected=True when connection succeeds"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch('services.cache.redis.Redis', return_value=mock_redis):
                from services.cache import RedisCache
                cache = RedisCache()

                result = cache.connect()

                assert result is True
                assert cache._connected is True
                assert cache._client is mock_redis

    def test_is_connected_returns_false_when_not_connected(self):
        """Should return False when _connected is False"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()
            cache._connected = False
            cache._client = None

            assert cache.is_connected is False

    def test_is_connected_pings_redis(self):
        """Should ping Redis to verify connection is still alive"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            cache._client = mock_client
            cache._connected = True

            result = cache.is_connected

            assert result is True
            mock_client.ping.assert_called_once()

    def test_is_connected_returns_false_when_ping_fails(self):
        """Should return False and set _connected=False when ping fails"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Connection lost")
            cache._client = mock_client
            cache._connected = True

            result = cache.is_connected

            assert result is False
            assert cache._connected is False


class TestRedisCacheGetSet:
    """Tests for get/set operations - testing REAL serialization logic"""

    @pytest.fixture
    def connected_cache(self):
        """Create a cache with mocked but connected Redis client"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            cache._client = mock_client
            cache._connected = True
            return cache, mock_client

    def test_get_deserializes_json(self, connected_cache):
        """Should deserialize JSON data from Redis"""
        cache, mock_client = connected_cache
        test_data = {"course_code": "CSCI 141", "title": "Test", "credits": 3}
        mock_client.get.return_value = json.dumps(test_data)

        result = cache.get("test_key")

        assert result == test_data
        assert isinstance(result, dict)
        assert result["credits"] == 3

    def test_get_returns_none_for_missing_key(self, connected_cache):
        """Should return None when key doesn't exist"""
        cache, mock_client = connected_cache
        mock_client.get.return_value = None

        result = cache.get("nonexistent")

        assert result is None

    def test_get_returns_none_on_invalid_json(self, connected_cache):
        """Should return None when stored data is not valid JSON"""
        cache, mock_client = connected_cache
        mock_client.get.return_value = "not valid json {"

        result = cache.get("bad_key")

        assert result is None

    def test_set_serializes_to_json(self, connected_cache):
        """Should serialize data as JSON when storing"""
        cache, mock_client = connected_cache
        test_data = {"course_code": "CSCI 141", "credits": 3}

        cache.set("test_key", test_data, ttl=300)

        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args[0]
        assert call_args[0] == "test_key"
        assert call_args[1] == 300
        # Verify the stored value is valid JSON that matches our data
        stored_json = call_args[2]
        assert json.loads(stored_json) == test_data

    def test_set_uses_default_ttl(self, connected_cache):
        """Should use COURSE_TTL as default TTL"""
        cache, mock_client = connected_cache
        from services.cache import COURSE_TTL

        cache.set("test_key", {"data": "test"})

        call_args = mock_client.setex.call_args[0]
        assert call_args[1] == COURSE_TTL

    def test_set_returns_false_on_error(self, connected_cache):
        """Should return False when Redis operation fails"""
        cache, mock_client = connected_cache
        mock_client.setex.side_effect = Exception("Redis error")

        result = cache.set("test_key", {"data": "test"})

        assert result is False


class TestRedisCacheCourseOperations:
    """Tests for course-specific operations - verifying correct key prefixes"""

    @pytest.fixture
    def connected_cache(self):
        """Create a cache with mocked but connected Redis client"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache, COURSE_PREFIX, COURSES_BY_SUBJECT_PREFIX
            cache = RedisCache()
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            cache._client = mock_client
            cache._connected = True
            return cache, mock_client, COURSE_PREFIX, COURSES_BY_SUBJECT_PREFIX

    def test_get_course_uses_correct_key_prefix(self, connected_cache):
        """Should use COURSE_PREFIX with sanitized course code"""
        cache, mock_client, COURSE_PREFIX, _ = connected_cache
        mock_client.get.return_value = None

        cache.get_course("CSCI 141")

        # Verify the key was constructed correctly
        expected_key = f"{COURSE_PREFIX}CSCI_141"
        mock_client.get.assert_called_with(expected_key)

    def test_set_course_uses_correct_key_prefix(self, connected_cache):
        """Should use COURSE_PREFIX when caching course"""
        cache, mock_client, COURSE_PREFIX, _ = connected_cache
        course_data = {"course_code": "CSCI 141"}

        cache.set_course("CSCI 141", course_data)

        call_args = mock_client.setex.call_args[0]
        expected_key = f"{COURSE_PREFIX}CSCI_141"
        assert call_args[0] == expected_key

    def test_get_courses_by_subject_uses_correct_key_prefix(self, connected_cache):
        """Should use COURSES_BY_SUBJECT_PREFIX"""
        cache, mock_client, _, SUBJECT_PREFIX = connected_cache
        mock_client.get.return_value = None

        cache.get_courses_by_subject("CSCI")

        expected_key = f"{SUBJECT_PREFIX}CSCI"
        mock_client.get.assert_called_with(expected_key)

    def test_search_results_uses_hashed_key(self, connected_cache):
        """Should use hash-based key for search results"""
        cache, mock_client, _, _ = connected_cache
        from services.cache import SEARCH_PREFIX
        mock_client.get.return_value = None

        cache.get_search_results("CSCI", 20)

        # Verify search prefix is used
        call_args = mock_client.get.call_args[0][0]
        assert call_args.startswith(SEARCH_PREFIX)


class TestRedisCacheInvalidation:
    """Tests for cache invalidation"""

    @pytest.fixture
    def connected_cache(self):
        """Create a cache with mocked but connected Redis client"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.keys.return_value = ["key1", "key2"]
            mock_client.delete.return_value = 2
            cache._client = mock_client
            cache._connected = True
            return cache, mock_client

    def test_invalidate_all_courses_deletes_multiple_patterns(self, connected_cache):
        """Should delete courses, subjects, and search caches"""
        cache, mock_client = connected_cache
        from services.cache import COURSE_PREFIX, COURSES_BY_SUBJECT_PREFIX, SEARCH_PREFIX

        cache.invalidate_all_courses()

        # Should have called keys() for each pattern
        key_calls = [call[0][0] for call in mock_client.keys.call_args_list]
        assert any(COURSE_PREFIX in k for k in key_calls)
        assert any(COURSES_BY_SUBJECT_PREFIX in k for k in key_calls)
        assert any(SEARCH_PREFIX in k for k in key_calls)

    def test_clear_all_uses_app_prefix(self, connected_cache):
        """Should only clear keys with our app prefix"""
        cache, mock_client = connected_cache
        from services.cache import CACHE_PREFIX

        cache.clear_all()

        mock_client.keys.assert_called_with(f"{CACHE_PREFIX}*")


class TestRedisCacheWarmUp:
    """Tests for cache warm-up functionality"""

    @pytest.fixture
    def connected_cache(self):
        """Create a cache with mocked but connected Redis client"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            cache._client = mock_client
            cache._connected = True
            return cache, mock_client

    def test_warm_cache_returns_count_of_cached_courses(self, connected_cache):
        """Should return number of courses cached"""
        cache, mock_client = connected_cache
        courses = [
            {"course_code": "CSCI 141", "subject_code": "CSCI"},
            {"course_code": "CSCI 241", "subject_code": "CSCI"},
            {"course_code": "MATH 111", "subject_code": "MATH"}
        ]

        result = cache.warm_cache(courses)

        assert result == 3

    def test_warm_cache_caches_each_course(self, connected_cache):
        """Should cache each course individually"""
        cache, mock_client = connected_cache
        courses = [
            {"course_code": "CSCI 141", "subject_code": "CSCI"},
            {"course_code": "MATH 111", "subject_code": "MATH"}
        ]

        cache.warm_cache(courses)

        # Should have called setex at least once per course + subjects list
        assert mock_client.setex.call_count >= 2

    def test_warm_cache_skips_courses_without_code(self, connected_cache):
        """Should skip courses without course_code"""
        cache, mock_client = connected_cache
        courses = [
            {"course_code": "CSCI 141", "subject_code": "CSCI"},
            {"subject_code": "MATH"},  # No course_code
            {"course_code": "", "subject_code": "BUAD"}  # Empty course_code
        ]

        result = cache.warm_cache(courses)

        assert result == 1  # Only the first course should be cached


class TestRedisCacheStats:
    """Tests for cache statistics"""

    def test_get_stats_returns_disconnected_when_not_connected(self):
        """Should return connected=False when not connected"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()
            cache._connected = False

            with patch.object(cache, 'connect', return_value=False):
                result = cache.get_stats()

            assert result == {"connected": False}

    def test_get_stats_includes_hit_miss_info(self):
        """Should include hits and misses from Redis info"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            from services.cache import RedisCache
            cache = RedisCache()
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.info.return_value = {
                "keyspace_hits": 150,
                "keyspace_misses": 25,
                "used_memory_human": "2.5M"
            }
            mock_client.keys.return_value = []
            cache._client = mock_client
            cache._connected = True

            result = cache.get_stats()

            assert result["connected"] is True
            assert result["hits"] == 150
            assert result["misses"] == 25
            assert result["memory_used"] == "2.5M"


class TestCacheHelperFunctions:
    """Tests for module-level helper functions"""

    def test_get_cache_returns_singleton(self):
        """Should return the same instance on multiple calls"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            import services.cache as cache_module

            # Reset singleton
            cache_module._cache_instance = None

            with patch.object(cache_module.RedisCache, 'connect', return_value=False):
                cache1 = cache_module.get_cache()
                cache2 = cache_module.get_cache()

                assert cache1 is cache2

            # Clean up
            cache_module._cache_instance = None

    def test_is_cache_available_returns_connection_status(self):
        """Should return True when cache is connected"""
        with patch('services.cache.REDIS_AVAILABLE', True):
            import services.cache as cache_module

            mock_cache = MagicMock()
            mock_cache.is_connected = True

            with patch.object(cache_module, 'get_cache', return_value=mock_cache):
                result = cache_module.is_cache_available()

            assert result is True
