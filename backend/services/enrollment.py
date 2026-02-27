"""
Enrollment Updater Service

Fast enrollment-only updates for Firebase.
Updates just enrollment counts (capacity, enrolled, available) without
fetching full course details - much faster than full catalog refresh.

Features:
- Rate limiting to avoid overwhelming the API
- Response caching (short TTL for enrollment data)
- Clear user-agent identification
- Validation and error reporting
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from core.config import get_firestore_client, initialize_firebase
from core.semester import SemesterManager
from core.parsers import parse_seats, parse_status
from api.client import FOSEClient, ValidationReport


class EnrollmentUpdater:
    """
    Fast enrollment updates for Firebase.

    Only fetches and updates enrollment counts, skipping course details
    like descriptions and attributes for speed.
    """

    def __init__(self, concurrency: int = 50, use_cache: bool = False):
        """
        Initialize updater.

        Args:
            concurrency: Max concurrent API requests
            use_cache: Whether to cache responses (default False for enrollment)
        """
        self.concurrency = concurrency
        self.use_cache = use_cache  # Usually False for enrollment - we want fresh data
        self.client: Optional[FOSEClient] = None
        self.db = None

    async def __aenter__(self):
        self.client = FOSEClient(
            concurrency=self.concurrency,
            use_cache=self.use_cache
        )
        await self.client.__aenter__()

        initialize_firebase()
        self.db = get_firestore_client()
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.__aexit__(*args)

    @property
    def report(self) -> Optional[ValidationReport]:
        """Get the validation report"""
        return self.client.report if self.client else None

    async def update_enrollment(self, term_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Fast enrollment update - only updates seat counts.

        This is designed to run frequently (every 5 minutes during registration).
        It only fetches enrollment data, not full course details.

        Args:
            term_code: Term to update. Defaults to current trackable term.

        Returns:
            Stats dict with update results
        """
        if term_code is None:
            term_code = SemesterManager.get_trackable_term_code()

        start_time = datetime.now()
        print(f"[{start_time}] Starting enrollment update for {term_code}...")

        self.client.report.term_code = term_code

        stats = {
            "term_code": term_code,
            "sections_checked": 0,
            "courses_updated": 0,
            "errors": 0,
            "start_time": start_time.isoformat()
        }

        # Step 1: Fetch all sections from Search API
        sections = await self.client.fetch_search(term_code)
        if not sections:
            stats["error"] = "No sections found"
            return stats

        stats["sections_checked"] = len(sections)
        print(f"[{datetime.now()}] Found {len(sections)} sections")

        # Step 2: Fetch enrollment details for all CRNs
        crns = [s.get('crn') for s in sections if s.get('crn')]

        print(f"[{datetime.now()}] Fetching enrollment data for {len(crns)} sections...")

        def progress(completed, total):
            print(f"[{datetime.now()}] Fetched {completed}/{total} details...")

        details_map = await self.client.fetch_details_batch(crns, term_code, progress)

        # Check failure rate
        failure_rate = self.client.report.failed_details / max(len(crns), 1)
        if failure_rate > 0.1:
            self.client.report.add_warning(
                f"High detail fetch failure rate: {failure_rate:.1%}"
            )

        # Step 3: Group by course code
        courses_map: Dict[str, List[Dict]] = {}
        section_info = {s.get('crn'): s for s in sections}

        for section in sections:
            code = section.get('code', '')
            if code:
                if code not in courses_map:
                    courses_map[code] = []
                courses_map[code].append(section)

        # Step 4: Update each course in Firebase
        print(f"[{datetime.now()}] Updating {len(courses_map)} courses in Firebase...")

        batch = self.db.batch()
        batch_count = 0
        updated_count = 0

        for course_code, course_sections in courses_map.items():
            try:
                doc_id = course_code.replace(" ", "_").replace("/", "-")
                doc_ref = self.db.collection("courses").document(doc_id)

                # Build updated sections array with enrollment data
                updated_sections = []
                for sec in course_sections:
                    crn = sec.get('crn', '')
                    details = details_map.get(crn, {})
                    enrollment = parse_seats(details.get('seats', ''))

                    updated_sections.append({
                        "crn": crn,
                        "section_number": sec.get('section', sec.get('no', '')),
                        "instructor": sec.get('instr', ''),
                        "status": parse_status(sec.get('stat', '')),
                        "capacity": enrollment['capacity'],
                        "enrolled": enrollment['enrolled'],
                        "available": enrollment['available'],
                        "waitlist_capacity": enrollment['waitlist_capacity'],
                        "waitlist_enrolled": enrollment['waitlist_enrolled'],
                        "meeting_times_raw": sec.get('meets', ''),
                    })

                # Update only the sections and timestamp (merge=True to handle missing docs)
                batch.set(doc_ref, {
                    "sections": updated_sections,
                    "enrollment_updated_at": datetime.utcnow().isoformat()
                }, merge=True)

                batch_count += 1
                updated_count += 1

                if batch_count >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    batch_count = 0
                    print(f"[{datetime.now()}] Committed batch of 500 updates...")

            except Exception as e:
                stats["errors"] += 1

        # Commit remaining
        if batch_count > 0:
            batch.commit()

        stats["courses_updated"] = updated_count
        stats["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        stats["end_time"] = datetime.now().isoformat()
        stats["details_fetched"] = self.client.report.successful_details
        stats["details_failed"] = self.client.report.failed_details

        print(f"[{datetime.now()}] Enrollment update complete: {updated_count} courses updated "
              f"in {stats['duration_seconds']:.1f}s")

        # Print validation report if there are issues
        if self.client.report.has_issues():
            print("\n" + self.client.report.summary())

        # Update metadata in Firebase
        self._update_metadata("enrollment_update", stats)

        return stats

    def _update_metadata(self, update_type: str, stats: Dict[str, Any]):
        """Update metadata about the last update operation"""
        try:
            # Include validation report in metadata
            report_data = self.client.report.to_dict() if self.client.report else {}

            metadata_ref = self.db.collection("metadata").document(f"last_{update_type}")
            metadata_ref.set({
                "type": update_type,
                "timestamp": datetime.utcnow().isoformat(),
                "stats": stats,
                "validation": report_data
            })
        except Exception as e:
            print(f"Warning: Could not update metadata: {e}")


async def run_enrollment_update(term_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a fast enrollment update.

    Args:
        term_code: Optional term code. Defaults to current trackable term.

    Returns:
        Stats dict with update results
    """
    async with EnrollmentUpdater(use_cache=False) as updater:
        return await updater.update_enrollment(term_code)


# For running directly
if __name__ == "__main__":
    import sys

    term = sys.argv[1] if len(sys.argv) > 1 else None
    result = asyncio.run(run_enrollment_update(term))
    print(f"\nResult: {result}")
