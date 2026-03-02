"""
Background Task Scheduler for Course Catalog Updates

UPDATE SCHEDULE:
- Enrollment Update: Every 5 minutes during registration, 15 minutes otherwise
- Full Catalog Update: Twice daily at 6 AM and 11 PM
- Semester Transition Check: Daily at midnight
- Curriculum PDF Check: Monthly on the 1st at 3 AM

SEMESTER TRANSITIONS:
- November 1: Fall -> Spring (next year)
- June 1: Spring -> Summer (same year)
- August 1: Summer -> Fall (same year)

Usage:
    python -m tasks.scheduler                    # Run scheduler (foreground)
    python -m tasks.scheduler --once enrollment  # Run enrollment update once
    python -m tasks.scheduler --once catalog     # Run full catalog update once
    python -m tasks.scheduler --once curriculum  # Check curriculum PDF once
"""

import asyncio
import argparse
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from core.semester import SemesterManager
from api.fetcher import fetch_courses
from services.firebase import get_course_service
from services.enrollment import run_enrollment_update
from scrapers.curriculum_scraper import check_and_update_curriculum, fetch_and_parse_curriculum


class TaskScheduler:
    """Manages background update tasks"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._last_term_code: Optional[str] = None

    async def start(self):
        """Start the scheduler with configured tasks"""
        print("=" * 60)
        print("W&M Course Catalog Scheduler")
        print("=" * 60)
        print(f"Started: {datetime.now()}")
        print(f"Trackable Term: {SemesterManager.get_trackable_display_name()}")
        print(f"Registration Period: {SemesterManager.is_registration_period()}")
        print("=" * 60)

        # Store current term for transition detection
        self._last_term_code = SemesterManager.get_trackable_term_code()

        # Semester transition check (daily at midnight)
        self.scheduler.add_job(
            self.check_semester_transition,
            CronTrigger(hour=0, minute=0),
            id='check_semester_transition',
            name='Check Semester Transition',
            replace_existing=True,
            max_instances=1
        )

        # Enrollment update (dynamic interval based on registration period)
        interval = SemesterManager.get_update_interval_minutes()
        self.scheduler.add_job(
            self.update_enrollment,
            IntervalTrigger(minutes=interval),
            id='update_enrollment',
            name=f'Update Enrollment (every {interval} min)',
            replace_existing=True,
            max_instances=1
        )

        # Full catalog update (6 AM daily)
        self.scheduler.add_job(
            self.update_full_catalog,
            CronTrigger(hour=6, minute=0),
            id='update_catalog_morning',
            name='Full Catalog Update (Morning)',
            replace_existing=True,
            max_instances=1
        )

        # Full catalog update (11 PM daily)
        self.scheduler.add_job(
            self.update_full_catalog,
            CronTrigger(hour=23, minute=0),
            id='update_catalog_evening',
            name='Full Catalog Update (Evening)',
            replace_existing=True,
            max_instances=1
        )

        # Adjust enrollment interval check (hourly)
        # Updates the enrollment job interval during registration periods
        self.scheduler.add_job(
            self.adjust_enrollment_interval,
            IntervalTrigger(hours=1),
            id='adjust_interval',
            name='Adjust Update Interval',
            replace_existing=True
        )

        # Curriculum PDF check (monthly on 1st at 3 AM)
        # Checks for updated curriculum guide PDF and re-parses if changed
        self.scheduler.add_job(
            self.update_curriculum,
            CronTrigger(day=1, hour=3, minute=0),
            id='update_curriculum',
            name='Curriculum PDF Update (Monthly)',
            replace_existing=True,
            max_instances=1
        )

        self.scheduler.start()
        print("\n[SUCCESS] Scheduler started with the following jobs:")
        for job in self.scheduler.get_jobs():
            print(f"  - {job.name}: {job.trigger}")
        print("\nPress Ctrl+C to stop\n")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            print("[INFO] Scheduler stopped")

    # SEMESTER TRANSITION CHECK

    async def check_semester_transition(self):
        """Check if semester has changed and trigger full catalog refresh"""
        current_term = SemesterManager.get_trackable_term_code()

        if self._last_term_code and current_term != self._last_term_code:
            print(f"\n[TRANSITION] Semester changed: {self._last_term_code} -> {current_term}")
            print(f"[TRANSITION] Running full catalog update for new semester...")

            # Run full catalog update for new semester
            await self.update_full_catalog()

            self._last_term_code = current_term
            print(f"[TRANSITION] Complete!")
        else:
            print(f"[{datetime.now()}] Semester check: No transition needed ({current_term})")

    # ENROLLMENT UPDATE (Fast, frequent)

    async def update_enrollment(self):
        """Fast enrollment-only update"""
        term_code = SemesterManager.get_trackable_term_code()

        try:
            result = await run_enrollment_update(term_code)
            print(f"[{datetime.now()}] Enrollment update ({term_code}): "
                  f"{result.get('sections_updated', 0)} courses updated "
                  f"in {result.get('duration_seconds', 0):.1f}s")
        except Exception as e:
            print(f"[ERROR] Enrollment update failed: {e}")

    # FULL CATALOG UPDATE (Slow, twice daily)

    async def update_full_catalog(self):
        """Full catalog update with descriptions, attributes, etc."""
        term_code = SemesterManager.get_trackable_term_code()

        try:
            print(f"\n[{datetime.now()}] Starting full catalog update for {term_code}...")

            # Fetch all courses
            courses = await fetch_courses(term_code)

            if not courses:
                print(f"[WARNING] No courses found for {term_code}")
                return

            # Store in Firebase
            service = get_course_service()
            stats = service.store_courses(courses, term_code)

            print(f"[{datetime.now()}] Full catalog update complete:")
            print(f"  - Total courses: {stats['total_courses']}")
            print(f"  - Created: {stats['created']}")
            print(f"  - Updated: {stats['updated']}")
            print(f"  - Errors: {stats['errors']}")

        except Exception as e:
            print(f"[ERROR] Full catalog update failed: {e}")
            import traceback
            traceback.print_exc()

    # CURRICULUM PDF UPDATE (Monthly)

    async def update_curriculum(self):
        """Check for curriculum PDF updates and re-parse if needed"""
        try:
            print(f"\n[{datetime.now()}] Checking for curriculum PDF updates...")

            # Run in thread pool since it's sync I/O
            loop = asyncio.get_event_loop()
            updated = await loop.run_in_executor(None, check_and_update_curriculum)

            if updated:
                print(f"[{datetime.now()}] Curriculum PDF updated and re-parsed!")
            else:
                print(f"[{datetime.now()}] Curriculum PDF unchanged")

        except Exception as e:
            print(f"[ERROR] Curriculum update failed: {e}")
            import traceback
            traceback.print_exc()

    # DYNAMIC INTERVAL ADJUSTMENT

    async def adjust_enrollment_interval(self):
        """Adjust enrollment update interval based on registration period"""
        new_interval = SemesterManager.get_update_interval_minutes()

        # Get current job
        job = self.scheduler.get_job('update_enrollment')
        if job:
            current_interval = job.trigger.interval.total_seconds() / 60

            if current_interval != new_interval:
                print(f"[{datetime.now()}] Adjusting enrollment interval: "
                      f"{int(current_interval)} min -> {new_interval} min")

                # Reschedule with new interval
                self.scheduler.reschedule_job(
                    'update_enrollment',
                    trigger=IntervalTrigger(minutes=new_interval)
                )


async def run_scheduler():
    """Run the scheduler indefinitely"""
    scheduler = TaskScheduler()
    await scheduler.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


async def run_once(task: str, term_code: Optional[str] = None):
    """Run a single task once"""
    if term_code is None:
        term_code = SemesterManager.get_trackable_term_code()

    if task == "enrollment":
        print(f"Running {task} for term {term_code}...")
        result = await run_enrollment_update(term_code)
        print(f"Result: {result}")

    elif task == "catalog":
        print(f"Running {task} for term {term_code}...")
        courses = await fetch_courses(term_code)
        if courses:
            service = get_course_service()
            stats = service.store_courses(courses, term_code)
            print(f"Result: {stats}")
        else:
            print("No courses found")

    elif task == "curriculum":
        print("Checking curriculum PDF for updates...")
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, fetch_and_parse_curriculum, True)
        if data:
            if isinstance(data, dict):
                print(f"Parsed curriculum for {data.get('academic_year', 'Unknown')}")
                print(f"  Majors: {len(data.get('majors', []))}")
                print(f"  Concentrations: {len(data.get('concentrations', []))}")
            else:
                print(f"Parsed curriculum for {data.academic_year}")
                print(f"  Majors: {len(data.majors)}")
                print(f"  Concentrations: {len(data.concentrations)}")
        else:
            print("Failed to parse curriculum")

    else:
        print(f"Unknown task: {task}")


def main():
    parser = argparse.ArgumentParser(
        description="W&M Course Catalog Scheduler"
    )
    parser.add_argument(
        "--once",
        type=str,
        choices=["enrollment", "catalog", "curriculum"],
        help="Run a single task once and exit"
    )
    parser.add_argument(
        "--term",
        type=str,
        default=None,
        help="Term code (e.g., 202610). Defaults to current trackable term."
    )

    args = parser.parse_args()

    if args.once:
        asyncio.run(run_once(args.once, args.term))
    else:
        asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
