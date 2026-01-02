"""
Course Catalog Population Script

Fetches the W&M course catalog from the FOSE API and stores it in Firebase.

Usage:
    python -m tasks.populate                      # Use current trackable term
    python -m tasks.populate --term 202510        # Specify term code
    python -m tasks.populate --by-subject         # Store organized by subject
    python -m tasks.populate --delete-first       # Clear existing data first
"""

import asyncio
import argparse
from datetime import datetime

from api.fetcher import fetch_courses, get_current_term_code
from services.firebase import get_course_service


async def populate_database(
    term_code: str = None,
    by_subject: bool = False,
    delete_first: bool = False
):
    """
    Populate the Firebase database with course catalog data.

    Args:
        term_code: Term code to fetch (e.g., "202510"). If None, uses current.
        by_subject: If True, organizes courses by subject in Firestore.
        delete_first: If True, deletes all existing courses before populating.
    """
    if term_code is None:
        term_code = get_current_term_code()

    print("=" * 60)
    print("W&M Course Catalog Population Script")
    print("=" * 60)
    print(f"Term Code: {term_code}")
    print(f"Organization: {'By Subject' if by_subject else 'Flat Collection'}")
    print(f"Delete First: {delete_first}")
    print(f"Started: {datetime.now()}")
    print("=" * 60)

    # Initialize Firebase service
    print("\n[1/4] Initializing Firebase...")
    try:
        service = get_course_service()
        print("Firebase initialized successfully!")
    except Exception as e:
        print(f"ERROR: Failed to initialize Firebase: {e}")
        print("\nMake sure you have:")
        print("1. Downloaded your service account key from Firebase Console")
        print("2. Saved it as 'serviceAccountKey.json' in the backend folder")
        return

    # Delete existing data if requested
    if delete_first:
        print("\n[2/4] Deleting existing courses...")
        deleted = service.delete_all_courses()
        print(f"Deleted {deleted} existing courses")
    else:
        print("\n[2/4] Skipping deletion (will upsert)")

    # Fetch courses from FOSE API
    print(f"\n[3/4] Fetching courses from W&M FOSE API...")
    try:
        courses = await fetch_courses(term_code)
        print(f"Fetched {len(courses)} courses")
    except Exception as e:
        print(f"ERROR: Failed to fetch courses: {e}")
        return

    if not courses:
        print("No courses found for this term. Exiting.")
        return

    # Store courses in Firebase
    print(f"\n[4/4] Storing courses in Firebase...")
    try:
        if by_subject:
            stats = service.store_courses_by_subject(courses, term_code)
        else:
            stats = service.store_courses(courses, term_code)

        print("\n" + "=" * 60)
        print("POPULATION COMPLETE")
        print("=" * 60)
        print(f"Total Courses: {stats['total_courses']}")
        print(f"Created: {stats['created']}")
        print(f"Updated: {stats['updated']}")
        print(f"Errors: {stats['errors']}")
        if 'subjects' in stats:
            print(f"Subjects: {len(stats['subjects'])}")
        print(f"Completed: {datetime.now()}")
        print("=" * 60)

    except Exception as e:
        print(f"ERROR: Failed to store courses: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Populate Firebase with W&M course catalog data"
    )
    parser.add_argument(
        "--term",
        type=str,
        default=None,
        help="Term code (e.g., 202510 for Spring 2025). Defaults to current trackable term."
    )
    parser.add_argument(
        "--by-subject",
        action="store_true",
        help="Organize courses by subject code in Firestore"
    )
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete all existing courses before populating"
    )

    args = parser.parse_args()

    # Run the async population
    asyncio.run(populate_database(
        term_code=args.term,
        by_subject=args.by_subject,
        delete_first=args.delete_first
    ))


if __name__ == "__main__":
    main()
