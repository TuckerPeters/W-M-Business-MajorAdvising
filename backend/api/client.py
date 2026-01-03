"""
API Client with Rate Limiting, Caching, and Validation

Provides a robust HTTP client for the FOSE API with:
- Rate limiting to avoid overwhelming the API
- Response caching to reduce redundant requests
- Clear user-agent identification
- Validation and error reporting
"""

import asyncio
import aiohttp
import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "admin@example.com")
USER_AGENT = f"WM-Business-MajorAdvising/1.0 (Course Catalog Sync; Contact: {CONTACT_EMAIL})"

API_BASE = "https://registration.wm.edu/api/"
SEARCH_ENDPOINT = f"{API_BASE}?page=fose&route=search"
DETAILS_ENDPOINT = f"{API_BASE}?page=fose&route=details"

# Rate limiting
DEFAULT_REQUESTS_PER_SECOND = 10  # Max requests per second
DEFAULT_CONCURRENT_REQUESTS = 50  # Max concurrent requests
BURST_LIMIT = 20  # Allow short bursts

# Caching
CACHE_DIR = Path(__file__).parent.parent / ".cache"
SEARCH_CACHE_TTL = 300  # 5 minutes for search results
DETAILS_CACHE_TTL = 60  # 1 minute for details (enrollment changes frequently)


# Validation Report

@dataclass
class ValidationReport:
    """Tracks data quality issues and API changes"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    term_code: str = ""

    # Counts
    total_sections: int = 0
    total_courses: int = 0
    successful_details: int = 0
    failed_details: int = 0

    # Issues
    missing_fields: Dict[str, int] = field(default_factory=dict)
    invalid_values: Dict[str, List[str]] = field(default_factory=dict)
    api_errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Response shape tracking (detect API changes)
    expected_search_fields: set = field(default_factory=lambda: {
        'crn', 'code', 'title', 'instr', 'meets', 'stat', 'cart_opts', 'section'
    })
    expected_details_fields: set = field(default_factory=lambda: {
        'seats', 'description', 'attr', 'meeting'
    })
    unexpected_fields: Dict[str, set] = field(default_factory=dict)
    missing_expected_fields: Dict[str, set] = field(default_factory=dict)

    def add_missing_field(self, field_name: str):
        """Track a missing required field"""
        self.missing_fields[field_name] = self.missing_fields.get(field_name, 0) + 1

    def add_invalid_value(self, field_name: str, value: str, reason: str = ""):
        """Track an invalid field value"""
        if field_name not in self.invalid_values:
            self.invalid_values[field_name] = []
        if len(self.invalid_values[field_name]) < 10:  # Limit examples
            self.invalid_values[field_name].append(f"{value} ({reason})" if reason else value)

    def add_api_error(self, endpoint: str, status: int, message: str):
        """Track an API error"""
        if len(self.api_errors) < 100:  # Limit stored errors
            self.api_errors.append({
                "endpoint": endpoint,
                "status": status,
                "message": message,
                "time": datetime.now().isoformat()
            })

    def add_warning(self, message: str):
        """Add a warning message"""
        if len(self.warnings) < 50:
            self.warnings.append(message)

    def check_response_shape(self, response_type: str, fields: set):
        """Check if response has expected fields, track changes"""
        if response_type == "search":
            expected = self.expected_search_fields
        elif response_type == "details":
            expected = self.expected_details_fields
        else:
            return

        # Track unexpected new fields
        unexpected = fields - expected
        if unexpected:
            if response_type not in self.unexpected_fields:
                self.unexpected_fields[response_type] = set()
            self.unexpected_fields[response_type].update(unexpected)

        # Track missing expected fields
        missing = expected - fields
        if missing:
            if response_type not in self.missing_expected_fields:
                self.missing_expected_fields[response_type] = set()
            self.missing_expected_fields[response_type].update(missing)

    def has_issues(self) -> bool:
        """Check if any issues were found"""
        return bool(
            self.missing_fields or
            self.invalid_values or
            self.api_errors or
            self.unexpected_fields or
            self.missing_expected_fields
        )

    def summary(self) -> str:
        """Generate a summary report"""
        lines = [
            "=" * 60,
            "VALIDATION REPORT",
            "=" * 60,
            f"Timestamp: {self.timestamp}",
            f"Term: {self.term_code}",
            f"Sections: {self.total_sections}",
            f"Courses: {self.total_courses}",
            f"Details fetched: {self.successful_details}/{self.successful_details + self.failed_details}",
            ""
        ]

        if not self.has_issues():
            lines.append("[OK] No issues detected")
        else:
            if self.api_errors:
                lines.append(f"[ERROR] API Errors: {len(self.api_errors)}")
                for err in self.api_errors[:5]:
                    lines.append(f"  - {err['endpoint']}: {err['status']} - {err['message']}")

            if self.missing_fields:
                lines.append(f"[WARNING] Missing Fields:")
                for field, count in sorted(self.missing_fields.items(), key=lambda x: -x[1])[:10]:
                    lines.append(f"  - {field}: {count} occurrences")

            if self.invalid_values:
                lines.append(f"[WARNING] Invalid Values:")
                for field, examples in list(self.invalid_values.items())[:5]:
                    lines.append(f"  - {field}: {examples[:3]}")

            if self.unexpected_fields:
                lines.append(f"[NOTICE] New API fields detected (possible API change):")
                for resp_type, fields in self.unexpected_fields.items():
                    lines.append(f"  - {resp_type}: {fields}")

            if self.missing_expected_fields:
                lines.append(f"[WARNING] Expected fields missing (possible API change):")
                for resp_type, fields in self.missing_expected_fields.items():
                    lines.append(f"  - {resp_type}: {fields}")

        if self.warnings:
            lines.append(f"\nWarnings:")
            for w in self.warnings[:10]:
                lines.append(f"  - {w}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "timestamp": self.timestamp,
            "term_code": self.term_code,
            "total_sections": self.total_sections,
            "total_courses": self.total_courses,
            "successful_details": self.successful_details,
            "failed_details": self.failed_details,
            "missing_fields": self.missing_fields,
            "invalid_values": self.invalid_values,
            "api_errors": self.api_errors,
            "warnings": self.warnings,
            "unexpected_fields": {k: list(v) for k, v in self.unexpected_fields.items()},
            "missing_expected_fields": {k: list(v) for k, v in self.missing_expected_fields.items()},
            "has_issues": self.has_issues()
        }


# Rate Limiter

class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, rate: float = DEFAULT_REQUESTS_PER_SECOND, burst: int = BURST_LIMIT):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire a token, waiting if necessary"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


# Response Cache

class ResponseCache:
    """Simple file-based cache for API responses"""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self._memory_cache: Dict[str, tuple] = {}  # key -> (data, expiry)

    def _cache_key(self, endpoint: str, payload: Dict) -> str:
        """Generate cache key from endpoint and payload"""
        content = f"{endpoint}:{json.dumps(payload, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, endpoint: str, payload: Dict, ttl: int) -> Optional[Dict]:
        """Get cached response if valid"""
        key = self._cache_key(endpoint, payload)

        # Check memory cache first
        if key in self._memory_cache:
            data, expiry = self._memory_cache[key]
            if time.time() < expiry:
                return data
            else:
                del self._memory_cache[key]

        # Check file cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                if time.time() < cached.get('expiry', 0):
                    data = cached['data']
                    self._memory_cache[key] = (data, cached['expiry'])
                    return data
                else:
                    cache_file.unlink()  # Remove expired
            except (json.JSONDecodeError, KeyError):
                cache_file.unlink()

        return None

    def set(self, endpoint: str, payload: Dict, data: Dict, ttl: int):
        """Cache a response"""
        key = self._cache_key(endpoint, payload)
        expiry = time.time() + ttl

        # Memory cache
        self._memory_cache[key] = (data, expiry)

        # File cache
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({'data': data, 'expiry': expiry}, f)
        except Exception:
            pass  # Ignore cache write errors

    def clear(self):
        """Clear all caches"""
        self._memory_cache.clear()
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
            except Exception:
                pass


# API Client

class FOSEClient:
    """
    FOSE API client with rate limiting, caching, and validation.
    """

    def __init__(
        self,
        concurrency: int = DEFAULT_CONCURRENT_REQUESTS,
        rate_limit: float = DEFAULT_REQUESTS_PER_SECOND,
        use_cache: bool = True
    ):
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        self.rate_limiter = RateLimiter(rate=rate_limit)
        self.cache = ResponseCache() if use_cache else None
        self.session: Optional[aiohttp.ClientSession] = None
        self.report: Optional[ValidationReport] = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30, connect=5, sock_read=15)
        connector = aiohttp.TCPConnector(
            limit=self.concurrency * 2,
            limit_per_host=self.concurrency,
            keepalive_timeout=30,
        )
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': USER_AGENT,
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
            }
        )
        self.report = ValidationReport()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def fetch_search(self, term_code: str) -> List[Dict]:
        """
        Fetch all sections from search API.

        Returns list of section dictionaries.
        """
        payload = {
            "other": {"srcdb": term_code},
            "criteria": []
        }

        # Check cache
        if self.cache:
            cached = self.cache.get(SEARCH_ENDPOINT, payload, SEARCH_CACHE_TTL)
            if cached:
                print(f"[CACHE HIT] Search results for {term_code}")
                return cached.get('results', [])

        # Rate limit and fetch
        await self.rate_limiter.acquire()

        try:
            async with self.session.post(SEARCH_ENDPOINT, json=payload) as resp:
                if resp.status != 200:
                    self.report.add_api_error(SEARCH_ENDPOINT, resp.status, await resp.text())
                    return []

                data = await resp.json()
                results = data.get('results', [])

                # Validate response shape
                if results:
                    sample_fields = set(results[0].keys())
                    self.report.check_response_shape("search", sample_fields)

                # Cache results
                if self.cache:
                    self.cache.set(SEARCH_ENDPOINT, payload, data, SEARCH_CACHE_TTL)

                self.report.total_sections = len(results)
                return results

        except aiohttp.ClientError as e:
            self.report.add_api_error(SEARCH_ENDPOINT, 0, str(e))
            return []
        except Exception as e:
            self.report.add_api_error(SEARCH_ENDPOINT, 0, f"Unexpected: {e}")
            return []

    async def fetch_details(self, crn: str, term_code: str) -> Optional[Dict]:
        """Fetch details for a single CRN"""
        payload = {
            "key": f"crn:{crn}",
            "srcdb": term_code,
            "matched": f"crn:{crn}"
        }

        # Check cache
        if self.cache:
            cached = self.cache.get(DETAILS_ENDPOINT, payload, DETAILS_CACHE_TTL)
            if cached:
                return cached

        # Rate limit and fetch
        await self.rate_limiter.acquire()

        async with self.semaphore:
            try:
                async with self.session.post(DETAILS_ENDPOINT, json=payload) as resp:
                    if resp.status != 200:
                        self.report.failed_details += 1
                        return None

                    data = await resp.json()

                    # Validate response shape (first successful response)
                    if self.report.successful_details == 0:
                        self.report.check_response_shape("details", set(data.keys()))

                    # Cache result
                    if self.cache:
                        self.cache.set(DETAILS_ENDPOINT, payload, data, DETAILS_CACHE_TTL)

                    self.report.successful_details += 1
                    return data

            except Exception:
                self.report.failed_details += 1
                return None

    async def fetch_details_batch(
        self,
        crns: List[str],
        term_code: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Dict]:
        """Fetch details for multiple CRNs concurrently"""
        results = {}
        completed = 0
        total = len(crns)

        async def fetch_one(crn: str):
            nonlocal completed
            details = await self.fetch_details(crn, term_code)
            if details:
                results[crn] = details
            completed += 1
            if progress_callback and completed % 500 == 0:
                progress_callback(completed, total)

        # Process in batches to avoid memory issues
        batch_size = 500
        for i in range(0, len(crns), batch_size):
            batch = crns[i:i + batch_size]
            tasks = [asyncio.create_task(fetch_one(crn)) for crn in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            if progress_callback:
                progress_callback(min(i + batch_size, total), total)

        return results

    def validate_section(self, section: Dict) -> bool:
        """Validate a section has required fields"""
        required = ['crn', 'code', 'title']
        valid = True

        for field in required:
            if not section.get(field):
                self.report.add_missing_field(field)
                valid = False

        # Validate CRN format (should be 5 digits)
        crn = section.get('crn', '')
        if crn and not crn.isdigit():
            self.report.add_invalid_value('crn', crn, 'not numeric')
            valid = False

        # Validate status
        status = section.get('stat', '')
        if status and status not in ('A', 'F', 'C', 'X'):
            self.report.add_invalid_value('stat', status, 'unknown status code')

        return valid

    def validate_course_code(self, code: str) -> bool:
        """Validate course code format (e.g., 'CSCI 141')"""
        import re
        if not re.match(r'^[A-Z]{2,4}\s+\d{3}[A-Z]?$', code):
            self.report.add_invalid_value('code', code, 'invalid format')
            return False
        return True

    def get_report(self) -> ValidationReport:
        """Get the validation report"""
        return self.report

    def clear_cache(self):
        """Clear the response cache"""
        if self.cache:
            self.cache.clear()
