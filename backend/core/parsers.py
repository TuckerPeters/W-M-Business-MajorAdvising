"""
Shared parsing utilities for course data.

These parsers are used by both the FOSE Fetcher and Enrollment Updater
to parse API responses consistently.
"""

import re
from typing import Dict


def parse_seats(seats_html: str) -> Dict[str, int]:
    """
    Parse enrollment from seats HTML.

    Args:
        seats_html: HTML string containing enrollment data from FOSE API

    Returns:
        Dict with capacity, enrolled, available, waitlist_capacity,
        waitlist_enrolled, waitlist_available
    """
    result = {
        'capacity': 0,
        'available': 0,
        'enrolled': 0,
        'waitlist_capacity': 0,
        'waitlist_enrolled': 0,
        'waitlist_available': 0
    }

    if not seats_html:
        return result

    cap = re.search(r'Maximum Enrollment:</b>\s*(\d+)', seats_html)
    if cap:
        result['capacity'] = int(cap.group(1))

    avail = re.search(r'Seats Avail</b>:\s*(\d+)', seats_html)
    if avail:
        result['available'] = int(avail.group(1))

    result['enrolled'] = result['capacity'] - result['available']

    wait = re.search(r'Waitlist Total:</b>\s*(\d+)\s*of\s*(\d+)', seats_html)
    if wait:
        result['waitlist_enrolled'] = int(wait.group(1))
        result['waitlist_capacity'] = int(wait.group(2))
        result['waitlist_available'] = result['waitlist_capacity'] - result['waitlist_enrolled']

    return result


def parse_status(stat: str) -> str:
    """
    Convert status code to readable string.

    Args:
        stat: Status code from FOSE API (A, F, C, X)

    Returns:
        Human-readable status string
    """
    status_map = {
        'A': 'OPEN',
        'F': 'CLOSED',
        'C': 'CANCELLED',
        'X': 'CANCELLED'
    }
    return status_map.get(stat, 'UNKNOWN')
