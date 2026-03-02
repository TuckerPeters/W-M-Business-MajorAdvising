"""
Unit test fixtures
"""

import pytest
import sys
from pathlib import Path

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture
def sample_search_result():
    """Sample search API response"""
    return {
        'crn': '12345',
        'code': 'CSCI 141',
        'title': 'Computational Problem Solving',
        'section': '01',
        'instr': 'Smith, John',
        'meets': 'MWF 10:00-10:50am',
        'stat': 'A',
        'cart_opts': '{"credit_hrs":{"options":[{"value":"4"}]}}'
    }


@pytest.fixture
def sample_details_response():
    """Sample details API response"""
    return {
        'seats': '<b>Maximum Enrollment:</b> 30<br><b>Seats Avail</b>: 5',
        'description': '<p>Introduction to computational problem solving.</p>',
        'attr': '<ul><li>GER 1A</li><li>COLL 150</li></ul>',
        'meeting': '<span>MWF 10:00-10:50am in Morton 201</span>'
    }


@pytest.fixture
def sample_search_results():
    """Multiple search results for grouping tests"""
    return [
        {
            'crn': '12345',
            'code': 'CSCI 141',
            'title': 'Computational Problem Solving',
            'section': '01',
            'instr': 'Smith, John',
            'meets': 'MWF 10:00-10:50am',
            'stat': 'A',
        },
        {
            'crn': '12346',
            'code': 'CSCI 141',
            'title': 'Computational Problem Solving',
            'section': '02',
            'instr': 'Jones, Jane',
            'meets': 'TR 11:00-12:20pm',
            'stat': 'A',
        },
        {
            'crn': '12347',
            'code': 'CSCI 243',
            'title': 'Data Structures',
            'section': '01',
            'instr': 'Smith, John',
            'meets': 'MWF 11:00-11:50am',
            'stat': 'F',
        },
    ]
