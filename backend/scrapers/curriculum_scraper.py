"""
Curriculum Guide PDF Scraper

Downloads and parses the Business Majors Curriculum Guide PDF from
the W&M Mason School of Business website.

Features:
- Downloads PDF from official URL
- Parses prerequisites, core curriculum, majors, and concentrations
- Checks for updates based on PDF modification date
- Caches parsed data to avoid unnecessary re-processing
"""

import re
import hashlib
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    print("Warning: pdfplumber not installed. Run: pip install pdfplumber")


# Configuration

BASE_URL = "https://mason.wm.edu"
CURRICULUM_PAGE = "/undergraduate/academics/majors-concentrations/"
PDF_PATH = "/undergraduate/documents/business-majors-curriculum-guide-2025-2026.pdf"
PDF_URL = urljoin(BASE_URL, PDF_PATH)

CACHE_DIR = Path(__file__).parent.parent / ".cache" / "curriculum"
PDF_CACHE_FILE = CACHE_DIR / "curriculum_guide.pdf"
DATA_CACHE_FILE = CACHE_DIR / "curriculum_data.json"
METADATA_FILE = CACHE_DIR / "metadata.json"

# Check for updates once per year (can be adjusted)
UPDATE_CHECK_INTERVAL_DAYS = 30  # Check monthly, update when PDF changes


# Data Models

@dataclass
class Course:
    """A single course requirement"""
    code: str  # e.g., "BUAD 301"
    name: str  # e.g., "Financial Reporting & Analysis"
    credits: float
    semester: str = ""  # F, S, F/S
    prerequisites: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CourseGroup:
    """A group of courses (e.g., 'Choose 2 from the following')"""
    description: str
    required_count: Optional[int] = None  # None means all required
    courses: List[Course] = field(default_factory=list)


@dataclass
class Major:
    """A business major with its requirements"""
    name: str
    credits_required: int
    description: str = ""
    required_courses: List[CourseGroup] = field(default_factory=list)
    elective_courses: List[CourseGroup] = field(default_factory=list)


@dataclass
class Concentration:
    """A business concentration"""
    name: str
    credits_required: int = 6
    description: str = ""
    course_groups: List[CourseGroup] = field(default_factory=list)


@dataclass
class CurriculumData:
    """Complete curriculum data from the PDF"""
    academic_year: str
    revision_date: str
    prerequisites: CourseGroup = None
    core_curriculum: List[CourseGroup] = field(default_factory=list)
    majors: List[Major] = field(default_factory=list)
    concentrations: List[Concentration] = field(default_factory=list)
    international_emphasis: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    pdf_hash: str = ""
    parsed_at: str = ""
    source_url: str = ""


# PDF Downloader

class CurriculumPDFDownloader:
    """Downloads curriculum PDF from W&M website"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WM-Business-MajorAdvising/1.0 (Curriculum Sync)'
        })
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def get_pdf_url_from_page(self) -> Optional[str]:
        """
        Scrape the curriculum page to find the current PDF URL.
        This handles cases where the PDF filename changes year to year.
        """
        try:
            page_url = urljoin(BASE_URL, CURRICULUM_PAGE)
            response = self.session.get(page_url, timeout=30)
            response.raise_for_status()

            # Look for the curriculum guide PDF link
            # Pattern: href="...business-majors-curriculum-guide...pdf"
            pattern = r'href="([^"]*business-majors-curriculum-guide[^"]*\.pdf)"'
            match = re.search(pattern, response.text, re.IGNORECASE)

            if match:
                pdf_path = match.group(1)
                # Handle relative URLs
                if pdf_path.startswith('/'):
                    return urljoin(BASE_URL, pdf_path)
                elif not pdf_path.startswith('http'):
                    return urljoin(page_url, pdf_path)
                return pdf_path

            print("Warning: Could not find curriculum PDF link on page")
            return PDF_URL  # Fall back to known URL

        except Exception as e:
            print(f"Error fetching curriculum page: {e}")
            return PDF_URL  # Fall back to known URL

    def download_pdf(self, force: bool = False) -> Optional[Path]:
        """
        Download the curriculum PDF if needed.

        Args:
            force: Force download even if cached

        Returns:
            Path to downloaded PDF or None if failed
        """
        # Check if we need to download
        if not force and self._is_cache_valid():
            print("Using cached PDF (still valid)")
            return PDF_CACHE_FILE

        # Get current PDF URL (may change year to year)
        pdf_url = self.get_pdf_url_from_page()
        print(f"Downloading curriculum PDF from: {pdf_url}")

        try:
            response = self.session.get(pdf_url, timeout=60)
            response.raise_for_status()

            # Save PDF
            PDF_CACHE_FILE.write_bytes(response.content)

            # Calculate hash for change detection
            pdf_hash = hashlib.md5(response.content).hexdigest()

            # Save metadata
            metadata = {
                'downloaded_at': datetime.now().isoformat(),
                'source_url': pdf_url,
                'pdf_hash': pdf_hash,
                'content_length': len(response.content),
                'last_check': datetime.now().isoformat()
            }
            METADATA_FILE.write_text(json.dumps(metadata, indent=2))

            print(f"Downloaded PDF ({len(response.content)} bytes)")
            return PDF_CACHE_FILE

        except Exception as e:
            print(f"Error downloading PDF: {e}")
            # Return cached version if available
            if PDF_CACHE_FILE.exists():
                print("Using previously cached PDF")
                return PDF_CACHE_FILE
            return None

    def _is_cache_valid(self) -> bool:
        """Check if cached PDF is still valid"""
        if not PDF_CACHE_FILE.exists() or not METADATA_FILE.exists():
            return False

        try:
            metadata = json.loads(METADATA_FILE.read_text())
            last_check = datetime.fromisoformat(metadata.get('last_check', '2000-01-01'))
            age_days = (datetime.now() - last_check).days

            return age_days < UPDATE_CHECK_INTERVAL_DAYS
        except Exception:
            return False

    def check_for_updates(self) -> bool:
        """
        Check if the PDF has been updated on the server.

        Returns:
            True if PDF has changed, False otherwise
        """
        if not METADATA_FILE.exists():
            return True

        try:
            metadata = json.loads(METADATA_FILE.read_text())
            old_hash = metadata.get('pdf_hash', '')

            # Download and check hash
            pdf_url = self.get_pdf_url_from_page()
            response = self.session.get(pdf_url, timeout=60)
            response.raise_for_status()

            new_hash = hashlib.md5(response.content).hexdigest()

            # Update last check time
            metadata['last_check'] = datetime.now().isoformat()
            METADATA_FILE.write_text(json.dumps(metadata, indent=2))

            if new_hash != old_hash:
                print(f"PDF has been updated! Old: {old_hash[:8]}, New: {new_hash[:8]}")
                # Save new PDF
                PDF_CACHE_FILE.write_bytes(response.content)
                metadata['pdf_hash'] = new_hash
                metadata['downloaded_at'] = datetime.now().isoformat()
                METADATA_FILE.write_text(json.dumps(metadata, indent=2))
                return True

            print("PDF unchanged")
            return False

        except Exception as e:
            print(f"Error checking for updates: {e}")
            return False


# PDF Parser

class CurriculumPDFParser:
    """Parses the curriculum PDF into structured data"""

    def __init__(self, pdf_path: Path):
        if pdfplumber is None:
            raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")
        self.pdf_path = pdf_path
        self.text_pages: List[str] = []
        self.full_text: str = ""

    def parse(self) -> CurriculumData:
        """Parse the PDF and return structured curriculum data"""
        print(f"Parsing PDF: {self.pdf_path}")

        # Extract text from PDF
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                self.text_pages.append(text)
            self.full_text = "\n\n".join(self.text_pages)

        # Parse sections
        data = CurriculumData(
            academic_year=self._extract_academic_year(),
            revision_date=self._extract_revision_date(),
            prerequisites=self._parse_prerequisites(),
            core_curriculum=self._parse_core_curriculum(),
            majors=self._parse_majors(),
            concentrations=self._parse_concentrations(),
            international_emphasis=self._parse_international_emphasis(),
            pdf_hash=hashlib.md5(self.pdf_path.read_bytes()).hexdigest(),
            parsed_at=datetime.now().isoformat(),
            source_url=PDF_URL
        )

        return data

    def _extract_academic_year(self) -> str:
        """Extract academic year from PDF"""
        match = re.search(r'Curriculum Guide (\d{4}-\d{4})', self.full_text)
        return match.group(1) if match else "Unknown"

    def _extract_revision_date(self) -> str:
        """Extract revision date from PDF"""
        match = re.search(r'\(Revised ([^)]+)\)', self.full_text)
        return match.group(1) if match else "Unknown"

    def _parse_course_line(self, line: str) -> Optional[Course]:
        """Parse a single course line into a Course object"""
        # Pattern: CODE NAME CREDITS SEMESTER (PREREQS)
        # Example: "301 Financial Reporting & Analysis 3 cr F/S (BUAD 203)"
        # Example: "ECON 101 Microeconomics 3 cr"

        patterns = [
            # BUAD courses (just number)
            r'^(\d{3})\s+(.+?)\s+(\d+(?:\.\d+)?)\s*cr\s*([FS/]*)\s*(?:\(([^)]+)\))?',
            # Full course codes
            r'^([A-Z]{2,4}\s*\d{3}[A-Z]?)\s+(.+?)\s+(\d+(?:\.\d+)?)\s*cr\s*([FS/]*)\s*(?:\(([^)]+)\))?',
        ]

        for pattern in patterns:
            match = re.match(pattern, line.strip())
            if match:
                code = match.group(1).strip()
                name = match.group(2).strip()
                credits = float(match.group(3))
                semester = match.group(4).strip() if match.group(4) else ""
                prereqs_str = match.group(5) if match.group(5) else ""

                # Parse prerequisites
                prereqs = []
                if prereqs_str:
                    prereqs = [p.strip() for p in re.split(r'[,&]', prereqs_str)]

                # Add BUAD prefix if just a number
                if code.isdigit():
                    code = f"BUAD {code}"

                return Course(
                    code=code,
                    name=name,
                    credits=credits,
                    semester=semester,
                    prerequisites=prereqs
                )

        return None

    def _parse_prerequisites(self) -> CourseGroup:
        """Parse prerequisites for admission section"""
        courses = []

        # Known prerequisites
        prereq_data = [
            ("ECON 101", "Microeconomics", 3),
            ("ECON 102", "Macroeconomics", 3),
            ("MATH 108, 111, or 131", "Calculus", 3),
            ("BUAD 203", "Accounting (Financial & Managerial)", 3),
            ("BUAD 231", "Statistics", 3),
        ]

        for code, name, credits in prereq_data:
            courses.append(Course(
                code=code,
                name=name,
                credits=credits,
                notes="OR any of: MATH 351, ECON 307, PSYC 301, SOCL 353, KINE 394" if "231" in code else ""
            ))

        return CourseGroup(
            description="Prerequisites for Admission to Business Major",
            required_count=5,
            courses=courses
        )

    def _parse_core_curriculum(self) -> List[CourseGroup]:
        """Parse core curriculum section"""
        groups = []

        # Foundation semester courses
        foundation = CourseGroup(
            description="Required Integrated Foundation Semester",
            courses=[
                Course(code="BUAD 300", name="Business Perspectives and Applications", credits=1),
                Course(code="BUAD 311", name="Principles of Marketing", credits=3),
                Course(code="BUAD 323", name="Financial Management", credits=3),
                Course(code="BUAD 330", name="Computer Skills for Business", credits=1),
                Course(code="BUAD 350", name="Introduction to Business Analytics", credits=3),
            ]
        )
        groups.append(foundation)

        # Upper level core
        upper_level = CourseGroup(
            description="Required Upper Level Core Courses",
            courses=[
                Course(code="BUAD 317", name="Organizational Behavior & Management", credits=3, semester="F/S"),
                Course(code="BUAD 343", name="Legal Environment of Business", credits=2, semester="F/S"),
                Course(code="BUAD 351", name="Operations Management", credits=1.5, semester="F/S", prerequisites=["BUAD 350"]),
                Course(code="BUAD 352", name="Data Visualization & Simulation", credits=1.5, semester="F/S", prerequisites=["BUAD 350"]),
                Course(code="BUAD 414", name="Global Strategic Management", credits=3, semester="F/S", notes="Seniors only"),
            ]
        )
        groups.append(upper_level)

        return groups

    def _parse_majors(self) -> List[Major]:
        """Parse major requirements"""
        majors = []

        # Accounting Major
        accounting = Major(
            name="Accounting",
            credits_required=15,
            description="15 credits in addition to the core curriculum",
            required_courses=[
                CourseGroup(
                    description="Accounting Required Courses",
                    courses=[
                        Course(code="BUAD 301", name="Financial Reporting & Analysis", credits=3, semester="F/S", prerequisites=["BUAD 203"]),
                        Course(code="BUAD 302", name="Advanced Financial Reporting & Analysis", credits=3, semester="F/S", prerequisites=["BUAD 301"]),
                        Course(code="BUAD 303", name="Strategic Cost Management", credits=3, semester="F", prerequisites=["BUAD 203"]),
                        Course(code="BUAD 404", name="Auditing & Internal Controls", credits=3, semester="S", prerequisites=["BUAD 301"]),
                        Course(code="BUAD 405", name="Federal Taxation", credits=3, semester="F", prerequisites=["BUAD 203"]),
                    ]
                )
            ],
            elective_courses=[
                CourseGroup(
                    description="Accounting Elective Course (choose 1)",
                    required_count=1,
                    courses=[
                        Course(code="BUAD 304", name="Not-for-Profit Accounting & Analysis", credits=3, semester="S"),
                        Course(code="BUAD 305", name="Accounting Info Systems", credits=3, semester="F"),
                        Course(code="BUAD 306", name="Financial Transparency and Global Markets", credits=3, semester="S"),
                        Course(code="BUAD 492", name="Audit & Innovation Challenge", credits=1, semester="F"),
                    ]
                )
            ]
        )
        majors.append(accounting)

        # Business Analytics - Data Science
        ba_data_science = Major(
            name="Business Analytics (Data Science Emphasis)",
            credits_required=12,
            description="12 credits in addition to the core curriculum",
            required_courses=[
                CourseGroup(
                    description="Business Analytics w/ Data Science Required Courses",
                    courses=[
                        Course(code="BUAD 466", name="Developing Business Intelligence", credits=3, semester="F/S", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 467", name="Predictive Analytics", credits=3, semester="S", prerequisites=["BUAD 330"]),
                        Course(code="BUAD 468", name="Prescriptive Analytics", credits=3, semester="F", prerequisites=["BUAD 352"]),
                    ]
                )
            ],
            elective_courses=[
                CourseGroup(
                    description="Choose one Business Analytics w/ Data Science Elective",
                    required_count=1,
                    courses=[
                        Course(code="BUAD 460", name="Big Data Analytics w/ Machine Learning", credits=3, semester="F", prerequisites=["BUAD 467"]),
                        Course(code="BUAD 461", name="Lean Six Sigma Toolkit", credits=3, semester="F", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 462", name="Healthcare Informatics", credits=3, semester="S"),
                        Course(code="BUAD 463", name="Supply Chain Analytics", credits=3, semester="S", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 465", name="Supply Chain Management", credits=3, semester="S", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 469", name="Advanced Modeling Techniques", credits=3, semester="S", prerequisites=["BUAD 352"]),
                        Course(code="BUAD 482", name="Project Management", credits=3, semester="S"),
                    ]
                )
            ]
        )
        majors.append(ba_data_science)

        # Business Analytics - Supply Chain
        ba_supply_chain = Major(
            name="Business Analytics (Supply Chain Emphasis)",
            credits_required=12,
            description="12 credits in addition to the core curriculum",
            required_courses=[
                CourseGroup(
                    description="Business Analytics w/ Supply Chain Required Courses",
                    courses=[
                        Course(code="BUAD 461", name="Lean Six Sigma Toolkit", credits=3, semester="F", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 463", name="Supply Chain Analytics", credits=3, semester="S", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 465", name="Supply Chain Management", credits=3, semester="S", prerequisites=["BUAD 350"]),
                    ]
                )
            ],
            elective_courses=[
                CourseGroup(
                    description="Choose one Business Analytics w/ Supply Chain Elective",
                    required_count=1,
                    courses=[
                        Course(code="BUAD 460", name="Big Data Analytics w/ Machine Learning", credits=3, semester="F", prerequisites=["BUAD 467"]),
                        Course(code="BUAD 462", name="Healthcare Informatics", credits=3, semester="S"),
                        Course(code="BUAD 466", name="Developing Business Intelligence", credits=3, semester="F/S", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 467", name="Predictive Analytics", credits=3, semester="S", prerequisites=["BUAD 330"]),
                        Course(code="BUAD 468", name="Prescriptive Analytics", credits=3, semester="F/S", prerequisites=["BUAD 352"]),
                        Course(code="BUAD 469", name="Advanced Modeling Techniques", credits=3, semester="S", prerequisites=["BUAD 330"]),
                        Course(code="BUAD 482", name="Project Management", credits=3, semester="S"),
                    ]
                )
            ]
        )
        majors.append(ba_supply_chain)

        # Finance Major
        finance = Major(
            name="Finance",
            credits_required=13,
            description="13 credits in addition to the core curriculum",
            required_courses=[
                CourseGroup(
                    description="Finance Required Courses",
                    courses=[
                        Course(code="BUAD 327", name="Investments", credits=3, semester="F/S", prerequisites=["BUAD 323"]),
                        Course(code="BUAD 329", name="Corporate Valuation & Credit Analysis", credits=3, semester="F/S", prerequisites=["BUAD 323"]),
                    ]
                ),
                CourseGroup(
                    description="Choose two courses from the following",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 422", name="Applied Financial Concepts", credits=3, semester="S", prerequisites=["BUAD 323", "BUAD 329"], notes="Boehly Center Application Required"),
                        Course(code="BUAD 423", name="Corporate Financial Strategy", credits=3, semester="F/S", prerequisites=["BUAD 323"]),
                        Course(code="BUAD 424", name="Derivatives & Risk Management", credits=3, semester="F/S", prerequisites=["BUAD 323", "BUAD 327"]),
                        Course(code="BUAD 427", name="Advanced Investments", credits=3, semester="F/S", prerequisites=["BUAD 323", "BUAD 327"]),
                    ]
                )
            ],
            elective_courses=[
                CourseGroup(
                    description="Choose one experiential elective (1-3 credits)",
                    required_count=1,
                    courses=[
                        Course(code="BUAD 421", name="Student Managed Investment Fund", credits=3, semester="F/S", prerequisites=["BUAD 323"], notes="Boehly Center Application Required"),
                        Course(code="BUAD 426", name="Hedge Fund Management", credits=1, semester="S", prerequisites=["BUAD 323"], notes="Boehly Center Application Required"),
                        Course(code="BUAD 492", name="CFA Challenge", credits=2, semester="F/S", prerequisites=["BUAD 323"], notes="1 cr F + 1 cr S"),
                        Course(code="BUAD 492", name="Experiential Finance Topic", credits=1, semester="F/S"),
                    ]
                )
            ]
        )
        majors.append(finance)

        # Marketing Major
        marketing = Major(
            name="Marketing",
            credits_required=12,
            description="12 credits in addition to the core curriculum",
            required_courses=[
                CourseGroup(
                    description="Marketing Required Courses",
                    courses=[
                        Course(code="BUAD 452", name="Marketing Research", credits=3, semester="F/S", prerequisites=["BUAD 311"]),
                        Course(code="BUAD 446", name="Consumer Behavior", credits=3, semester="F", prerequisites=["BUAD 311"]),
                    ]
                ),
                CourseGroup(
                    description="Choose two courses from the following",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 445", name="Product and Brand Management", credits=3, semester="S", prerequisites=["BUAD 311"]),
                        Course(code="BUAD 448", name="Marketing Strategy", credits=3, semester="S", prerequisites=["BUAD 311"]),
                        Course(code="BUAD 450", name="Global Marketing", credits=3, semester="S", prerequisites=["BUAD 311"]),
                        Course(code="BUAD 451", name="Customer Insights for Innovation", credits=3, semester="F", prerequisites=["BUAD 311", "BUAD 340"]),
                        Course(code="BUAD 453", name="Sustainability Inspired Design", credits=3, semester="S", prerequisites=["BUAD 311", "BUAD 340"]),
                        Course(code="BUAD 456", name="Advertising and Digital Marketing", credits=3, semester="F", prerequisites=["BUAD 311"]),
                    ]
                )
            ]
        )
        majors.append(marketing)

        return majors

    def _parse_concentrations(self) -> List[Concentration]:
        """Parse concentration requirements"""
        concentrations = []

        # Accounting Concentration
        concentrations.append(Concentration(
            name="Accounting",
            description="Choose 2 courses including BUAD 301 (3 credits each)",
            course_groups=[
                CourseGroup(
                    description="Choose 2 courses including 301",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 301", name="Financial Reporting & Analysis", credits=3, semester="F/S", prerequisites=["BUAD 203"]),
                        Course(code="BUAD 302", name="Advanced Financial Reporting & Analysis", credits=3, semester="S", prerequisites=["BUAD 301"]),
                        Course(code="BUAD 303", name="Strategic Cost Management", credits=3, semester="F", prerequisites=["BUAD 203"]),
                        Course(code="BUAD 404", name="Auditing & Internal Controls", credits=3, semester="S", prerequisites=["BUAD 301"]),
                        Course(code="BUAD 405", name="Federal Taxation", credits=3, semester="F", prerequisites=["BUAD 203"]),
                    ]
                )
            ]
        ))

        # Business Analytics Concentration
        concentrations.append(Concentration(
            name="Business Analytics",
            description="Choose 2 courses (3 credits each)",
            course_groups=[
                CourseGroup(
                    description="Choose 2 courses",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 460", name="Big Data Analytics w/ Machine Learning", credits=3, semester="F", prerequisites=["BUAD 467"]),
                        Course(code="BUAD 466", name="Developing Business Intelligence", credits=3, semester="F/S", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 467", name="Predictive Analytics", credits=3, semester="S", prerequisites=["BUAD 330", "Statistics"]),
                        Course(code="BUAD 468", name="Prescriptive Analytics", credits=3, semester="F/S", prerequisites=["BUAD 352"]),
                    ]
                )
            ]
        ))

        # Consulting Concentration
        concentrations.append(Concentration(
            name="Consulting",
            description="Choose 2 courses (3 credits each)",
            course_groups=[
                CourseGroup(
                    description="Choose 2 courses",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 431", name="Management Consulting", credits=3, semester="F", prerequisites=["BUAD 317"]),
                        Course(code="BUAD 437", name="Change Management & Org Transformation", credits=3, semester="S", prerequisites=["BUAD 317"]),
                        Course(code="BUAD 466", name="Developing Business Intelligence", credits=3, semester="F/S", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 482", name="Project Management", credits=3, semester="S"),
                    ]
                )
            ]
        ))

        # Finance Concentration
        concentrations.append(Concentration(
            name="Finance",
            description="Choose 2 courses including 327 or 329 (3 credits each)",
            course_groups=[
                CourseGroup(
                    description="Choose 2 courses including 327 or 329",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 327", name="Investments", credits=3, semester="F/S", prerequisites=["BUAD 323"]),
                        Course(code="BUAD 329", name="Corporate Valuation", credits=3, semester="F/S", prerequisites=["BUAD 323"]),
                        Course(code="BUAD 421", name="Student Managed Investment Fund", credits=3, semester="F/S", prerequisites=["BUAD 323"], notes="Boehly Center Application Required"),
                        Course(code="BUAD 422", name="Applied Financial Concepts", credits=3, semester="S", prerequisites=["BUAD 323", "BUAD 329"], notes="Boehly Center Application Required"),
                        Course(code="BUAD 423", name="Corporate Financial Strategy", credits=3, semester="S", prerequisites=["BUAD 323"]),
                        Course(code="BUAD 424", name="Derivatives and Risk Management", credits=3, semester="F/S", prerequisites=["BUAD 323", "BUAD 327"]),
                        Course(code="BUAD 427", name="Advanced Investments", credits=3, semester="F/S", prerequisites=["BUAD 323", "BUAD 327"]),
                        Course(code="BUAD 428", name="Behavioral Finance", credits=3, semester="F", prerequisites=["ECON 101", "Statistics"]),
                    ]
                )
            ]
        ))

        # Management & Organizational Leadership Concentration
        concentrations.append(Concentration(
            name="Management & Organizational Leadership",
            description="Choose 2 courses (3 credits each)",
            course_groups=[
                CourseGroup(
                    description="Choose 2 courses",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 435", name="Teams: Design, Selection, & Development", credits=3, semester="S", prerequisites=["BUAD 317"]),
                        Course(code="BUAD 436", name="Business & Society", credits=3, semester="F", prerequisites=["BUAD 317"]),
                        Course(code="BUAD 437", name="Change Management & Org Transformation", credits=3, semester="S", prerequisites=["BUAD 317"]),
                        Course(code="BUAD 438", name="Leadership", credits=3, semester="S", prerequisites=["BUAD 317"]),
                        Course(code="BUAD 442", name="Psychology of Decision Making", credits=3, semester="F", prerequisites=["Statistics"]),
                    ]
                )
            ]
        ))

        # Innovation & Entrepreneurship Concentration
        concentrations.append(Concentration(
            name="Innovation & Entrepreneurship",
            description="Required course + choose 2 courses (3 credits each)",
            course_groups=[
                CourseGroup(
                    description="Required Course",
                    courses=[
                        Course(code="BUAD 340", name="Introduction to Innovation and Entrepreneurship", credits=3),
                    ]
                ),
                CourseGroup(
                    description="Choose 2 courses",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 451", name="Customer Insights for Innovation", credits=3, semester="F", prerequisites=["BUAD 311", "BUAD 340"]),
                        Course(code="BUAD 443", name="Entrepreneurial Ventures", credits=3, semester="F/S", prerequisites=["BUAD 311"]),
                        Course(code="BUAD 453", name="Sustainability Inspired Innovation & Design", credits=3, semester="S", prerequisites=["BUAD 311", "BUAD 340"]),
                        Course(code="BUAD 457", name="Creative Problem Solving", credits=3, semester="S"),
                        Course(code="BUAD 492", name="Product Management", credits=3, semester="S"),
                    ]
                )
            ]
        ))

        # Supply Chain Analytics Concentration
        concentrations.append(Concentration(
            name="Supply Chain Analytics",
            description="Choose 2 courses (3 credits each)",
            course_groups=[
                CourseGroup(
                    description="Choose 2 courses",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 461", name="Lean Six Sigma", credits=3, semester="F", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 463", name="Supply Chain Analytics", credits=3, semester="S", prerequisites=["BUAD 350"]),
                        Course(code="BUAD 465", name="Supply Chain Management", credits=3, semester="S", prerequisites=["BUAD 350"]),
                    ]
                )
            ]
        ))

        # Marketing Concentration
        concentrations.append(Concentration(
            name="Marketing",
            description="Choose 2 courses (3 credits each)",
            course_groups=[
                CourseGroup(
                    description="Choose 2 courses",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 446", name="Consumer Behavior", credits=3, semester="S", prerequisites=["BUAD 311"]),
                        Course(code="BUAD 448", name="Marketing Strategy", credits=3, semester="S", prerequisites=["BUAD 311"]),
                        Course(code="BUAD 451", name="Customer Insights for Innovation", credits=3, semester="F", prerequisites=["BUAD 311", "BUAD 340"]),
                        Course(code="BUAD 452", name="Marketing Research", credits=3, semester="F/S", prerequisites=["BUAD 311"]),
                        Course(code="BUAD 453", name="Sustainability Inspired Innovation & Design", credits=3, semester="S", prerequisites=["BUAD 311", "BUAD 340"]),
                        Course(code="BUAD 456", name="Advertising & Digital Marketing", credits=3, semester="F", prerequisites=["BUAD 311"]),
                        Course(code="BUAD 445", name="Product and Brand Management", credits=3, semester="S", prerequisites=["BUAD 311"]),
                    ]
                )
            ]
        ))

        # Sustainability Concentration
        concentrations.append(Concentration(
            name="Sustainability",
            description="Choose 2 courses (3 credits each)",
            course_groups=[
                CourseGroup(
                    description="Choose 2 courses",
                    required_count=2,
                    courses=[
                        Course(code="BUAD 436", name="Business & Society", credits=3, semester="F"),
                        Course(code="BUAD 453", name="Sustainability Inspired Innovation & Design", credits=3, semester="S", prerequisites=["BUAD 311", "BUAD 340"]),
                        Course(code="ENSP 101", name="Intro to Environment & Sustainability", credits=3, semester="F"),
                    ]
                )
            ]
        ))

        return concentrations

    def _parse_international_emphasis(self) -> Dict[str, Any]:
        """Parse international emphasis requirements"""
        return {
            "description": "Recognition for students who incorporate international experiences in their Individual Program of Study (IPS)",
            "requirements": [
                {
                    "number": 1,
                    "description": "Course in international business",
                    "options": ["BUAD 410 International Business Management (should be completed abroad)", "BUAD 412", "BUAD 413", "Three credits equivalent"]
                },
                {
                    "number": 2,
                    "description": "Elective with international emphasis related to major or concentration",
                    "example": "BUAD 417 International Finance for Finance Major"
                },
                {
                    "number": 3,
                    "description": "Language and/or culture course(s)",
                    "note": "To be approved by Business Program"
                },
                {
                    "number": 4,
                    "description": "Study abroad experience",
                    "minimum_credits": 12,
                    "note": "May be earned over one semester or separate experiences"
                }
            ]
        }


# Data Serialization

def dataclass_to_dict(obj) -> Any:
    """Recursively convert dataclass to dict"""
    if hasattr(obj, '__dataclass_fields__'):
        return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def save_curriculum_data(data: CurriculumData) -> Path:
    """Save parsed curriculum data to JSON"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    data_dict = dataclass_to_dict(data)
    DATA_CACHE_FILE.write_text(json.dumps(data_dict, indent=2))

    print(f"Saved curriculum data to {DATA_CACHE_FILE}")
    return DATA_CACHE_FILE


def load_curriculum_data() -> Optional[CurriculumData]:
    """Load cached curriculum data"""
    if not DATA_CACHE_FILE.exists():
        return None

    try:
        data_dict = json.loads(DATA_CACHE_FILE.read_text())
        # Note: This returns a dict, not CurriculumData object
        # For full reconstruction, you'd need a from_dict method
        return data_dict
    except Exception as e:
        print(f"Error loading cached data: {e}")
        return None


# Main Functions

def fetch_and_parse_curriculum(force_download: bool = False) -> Optional[CurriculumData]:
    """
    Main function to fetch and parse the curriculum guide.

    Args:
        force_download: Force download even if cached

    Returns:
        Parsed CurriculumData or None if failed
    """
    # Download PDF
    downloader = CurriculumPDFDownloader()
    pdf_path = downloader.download_pdf(force=force_download)

    if not pdf_path:
        print("Failed to download PDF")
        return None

    # Check if we need to re-parse
    if not force_download and DATA_CACHE_FILE.exists():
        cached_data = load_curriculum_data()
        if cached_data:
            # Check if PDF hash matches
            current_hash = hashlib.md5(pdf_path.read_bytes()).hexdigest()
            if cached_data.get('pdf_hash') == current_hash:
                print("Using cached parsed data")
                return cached_data

    # Parse PDF
    parser = CurriculumPDFParser(pdf_path)
    data = parser.parse()

    # Save parsed data
    save_curriculum_data(data)

    return data


def check_and_update_curriculum() -> bool:
    """
    Check for curriculum updates and re-parse if needed.
    Called by scheduler (e.g., once per month).

    Returns:
        True if updated, False otherwise
    """
    downloader = CurriculumPDFDownloader()

    if downloader.check_for_updates():
        print("Curriculum PDF updated, re-parsing...")
        fetch_and_parse_curriculum(force_download=True)
        return True

    return False


# CLI Entry Point

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Curriculum Guide PDF Scraper")
    parser.add_argument("--force", action="store_true", help="Force download and re-parse")
    parser.add_argument("--check", action="store_true", help="Check for updates only")
    parser.add_argument("--print", action="store_true", help="Print parsed data")

    args = parser.parse_args()

    if args.check:
        updated = check_and_update_curriculum()
        print(f"Updated: {updated}")
    else:
        data = fetch_and_parse_curriculum(force_download=args.force)

        if data and args.print:
            if isinstance(data, dict):
                print(json.dumps(data, indent=2))
            else:
                print(json.dumps(dataclass_to_dict(data), indent=2))
        elif data:
            if isinstance(data, dict):
                print(f"\nParsed curriculum for {data.get('academic_year', 'Unknown')}")
                print(f"Majors: {len(data.get('majors', []))}")
                print(f"Concentrations: {len(data.get('concentrations', []))}")
            else:
                print(f"\nParsed curriculum for {data.academic_year}")
                print(f"Majors: {len(data.majors)}")
                print(f"Concentrations: {len(data.concentrations)}")
