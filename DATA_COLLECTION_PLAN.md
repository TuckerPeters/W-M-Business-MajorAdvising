# Data Collection & Integration Plan
## W&M Business School Course Data

---

## Executive Summary

This document outlines the complete strategy for collecting, processing, and maintaining course data from William & Mary systems, specifically for the Raymond A. Mason School of Business. The plan covers data sources, scraping strategies, ETL pipelines, data validation, and ongoing maintenance.

---

## Data Sources

### 1. W&M Course Listings (Open Course List)

**URL:** `https://courselist.wm.edu/courselist/`

**Data Available:**
- Course codes and titles
- Credit hours
- Course descriptions
- Prerequisites and corequisites
- Instructors
- Meeting times and locations
- Enrollment capacity and current enrollment
- Section numbers
- Terms offered (Fall/Spring/Summer)
- General Education attributes
- Course restrictions

**Access Method:**
- Publicly accessible
- Searchable by term and department
- Results displayed in tabular format

**Update Frequency:** Real-time during registration periods

---

### 2. W&M Undergraduate Catalog

**URL:** `https://www.wm.edu/as/undergraduate/catalog/`

**Data Available:**
- Official course descriptions
- Degree requirements
- Major/minor requirements
- Academic policies
- Prerequisites (official)
- Course numbering system explanations
- Credit hour policies

**Access Method:**
- Publicly accessible HTML pages
- Academic year versioning (e.g., 2024-2025 catalog)

**Update Frequency:** Annually (published each summer)

---

### 3. Mason School of Business Website

**URL:** `https://mason.wm.edu/`

**Key Pages:**
- `/undergraduate/majors-minors/` - Program requirements
- `/undergraduate/courses/` - Business course listings
- `/undergraduate/requirements/` - Major declaration requirements
- `/faculty/` - Faculty information and research areas

**Data Available:**
- Business-specific program information
- Major concentrations (Analytics, Finance, Marketing, etc.)
- Declaration requirements and deadlines
- Suggested course sequences
- Faculty profiles and specializations

**Access Method:**
- Publicly accessible
- Mix of static pages and PDF documents

**Update Frequency:** Varies (policies annually, faculty quarterly)

---

### 4. W&M Banner/Self-Service

**URL:** `https://banner.wm.edu/`

**Data Available (if API access granted):**
- Real-time enrollment data
- Student transcripts
- Course seat availability
- Waitlist information
- Academic calendar dates
- Final exam schedules

**Access Method:**
- Requires authentication
- Potential API access with IT approval
- FERPA-protected data

**Update Frequency:** Real-time

---

### 5. Rate My Professors (Optional)

**URL:** `https://www.ratemyprofessors.com/school/1254`

**Data Available:**
- Professor ratings
- Course difficulty ratings
- Student reviews
- "Would take again" percentages

**Access Method:**
- Web scraping (check ToS)
- Unofficial data source

**Update Frequency:** Continuous user submissions

---

## Data Requirements

### Core Course Data Model

```json
{
  "course_code": "BUAD 203",
  "department": "BUAD",
  "course_number": "203",
  "title": "Financial Accounting",
  "description": "Introduction to the preparation and use of financial statements...",
  "credits": 3,
  "level": 200,
  "has_lab": false,
  "prerequisites": [
    {
      "type": "course",
      "courses": ["BUAD 101"],
      "operator": "OR",
      "min_grade": null
    }
  ],
  "corequisites": [],
  "restrictions": {
    "major_only": false,
    "class_year_min": null,
    "permission_required": false
  },
  "attributes": {
    "writing_intensive": false,
    "gen_ed_categories": [],
    "business_core": true
  },
  "typical_terms_offered": ["Fall", "Spring"],
  "catalog_year": "2024-2025"
}
```

### Course Section Data Model

```json
{
  "section_id": "BUAD-203-01-202510",
  "course_code": "BUAD 203",
  "section_number": "01",
  "term": "202510",
  "term_name": "Fall 2024",
  "crn": "12345",
  "instructor": {
    "name": "John Smith",
    "email": "jsmith@wm.edu"
  },
  "meeting_times": [
    {
      "days": ["Monday", "Wednesday", "Friday"],
      "start_time": "09:00",
      "end_time": "09:50",
      "location": "Miller Hall 101",
      "start_date": "2024-08-28",
      "end_date": "2024-12-06"
    }
  ],
  "capacity": 35,
  "enrolled": 33,
  "waitlist": 2,
  "available_seats": 0,
  "status": "Open",
  "last_updated": "2024-12-22T10:30:00Z"
}
```

### Business Program Requirements Model

```json
{
  "program_type": "major",
  "program_name": "Business Analytics",
  "catalog_year": "2024-2025",
  "total_credits_required": 120,
  "major_credits_required": 45,
  "declaration_requirements": {
    "min_credits": 39,
    "max_credits": 54,
    "required_courses": ["BUAD 101", "BUAD 203"],
    "min_gpa": 2.0,
    "holds_allowed": false
  },
  "core_requirements": [
    {
      "category": "Business Foundation",
      "credits_required": 18,
      "courses": [
        {"code": "BUAD 101", "title": "Introduction to Business", "credits": 3, "required": true},
        {"code": "BUAD 203", "title": "Financial Accounting", "credits": 3, "required": true},
        {"code": "BUAD 204", "title": "Managerial Accounting", "credits": 3, "required": true},
        {"code": "BUAD 301", "title": "Marketing Principles", "credits": 3, "required": true},
        {"code": "BUAD 302", "title": "Corporate Finance", "credits": 3, "required": true},
        {"code": "BUAD 304", "title": "Operations Management", "credits": 3, "required": true}
      ]
    },
    {
      "category": "Quantitative Foundation",
      "credits_required": 10,
      "courses": [
        {"code": "MATH 112", "title": "Calculus I", "credits": 4, "required": true},
        {"code": "ECON 101", "title": "Principles of Microeconomics", "credits": 3, "required": true},
        {"code": "ECON 102", "title": "Principles of Macroeconomics", "credits": 3, "required": true}
      ]
    }
  ],
  "concentration_requirements": {
    "Analytics": {
      "credits_required": 15,
      "required_courses": ["BUAD 320", "BUAD 420", "BUAD 425"],
      "elective_courses": ["BUAD 321", "BUAD 421", "BUAD 422"],
      "electives_required": 2
    }
  }
}
```

---

## Data Collection Strategy

### Phase 1: Initial Data Scraping

#### Tool Selection

**Option A: Python-based Web Scraping**
```python
# Recommended stack
- requests / httpx - HTTP requests
- BeautifulSoup4 - HTML parsing
- Selenium - For JavaScript-heavy pages
- Scrapy - Full scraping framework (if extensive)
- pandas - Data manipulation
- pydantic - Data validation
```

**Option B: Pre-built Scrapers**
```bash
# Research existing tools
- Check if W&M provides any data feeds/APIs
- Look for existing open-source W&M scrapers
- Consider Apify or similar scraping services
```

---

### Phase 2: Scraper Implementation

#### A. Course Listings Scraper

**Target:** `https://courselist.wm.edu/courselist/`

**Implementation Strategy:**

```python
# scraper/course_listings.py

import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import time

class WMCourseListingScraper:
    """
    Scrapes course data from W&M Course Listings
    """

    BASE_URL = "https://courselist.wm.edu/courselist/"

    # W&M department codes for business
    BUSINESS_DEPTS = [
        "BUAD",  # Business Administration
        "ACCT",  # Accounting (if separate)
        "FIN",   # Finance (if separate)
        "MGMT",  # Management (if separate)
        "MKTG",  # Marketing (if separate)
    ]

    # Term codes (format: YYYYTT where TT = 10 Fall, 20 Spring, 30 Summer)
    TERMS = [
        "202410",  # Fall 2024
        "202420",  # Spring 2025
        "202510",  # Fall 2025
    ]

    def __init__(self, rate_limit: float = 1.0):
        """
        Args:
            rate_limit: Seconds to wait between requests (be respectful)
        """
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WM Business Advising Tool - Data Collection Bot (contact: advising@wm.edu)'
        })

    def scrape_term_department(self, term: str, dept: str) -> List[Dict]:
        """
        Scrape all courses for a specific term and department
        """
        courses = []

        # Build search URL (adjust based on actual site structure)
        url = f"{self.BASE_URL}?term={term}&dept={dept}"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find course rows (inspect HTML to determine correct selector)
            course_rows = soup.find_all('tr', class_='course-row')  # Example selector

            for row in course_rows:
                course = self._parse_course_row(row, term)
                if course:
                    courses.append(course)

            # Respectful rate limiting
            time.sleep(self.rate_limit)

        except Exception as e:
            print(f"Error scraping {dept} for {term}: {e}")

        return courses

    def _parse_course_row(self, row, term: str) -> Dict:
        """
        Extract course data from HTML row
        """
        try:
            # Example parsing (adjust to actual HTML structure)
            course_code = row.find('td', class_='course-code').text.strip()
            title = row.find('td', class_='course-title').text.strip()
            credits = int(row.find('td', class_='credits').text.strip())
            instructor = row.find('td', class_='instructor').text.strip()

            # Parse meeting times
            meeting_pattern = row.find('td', class_='meeting-pattern').text.strip()
            times = self._parse_meeting_times(meeting_pattern)

            # Parse capacity/enrollment
            enrollment = row.find('td', class_='enrollment').text.strip()
            capacity, enrolled = self._parse_enrollment(enrollment)

            return {
                'course_code': course_code,
                'title': title,
                'credits': credits,
                'instructor': instructor,
                'term': term,
                'meeting_times': times,
                'capacity': capacity,
                'enrolled': enrolled,
                'available': capacity - enrolled,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error parsing row: {e}")
            return None

    def _parse_meeting_times(self, meeting_str: str) -> List[Dict]:
        """
        Parse meeting time string like "MWF 09:00AM-09:50AM Miller 101"
        """
        # Implementation depends on actual format
        # Return structured meeting time data
        pass

    def _parse_enrollment(self, enrollment_str: str) -> tuple:
        """
        Parse enrollment string like "33/35" to get enrolled and capacity
        """
        # Example: "33/35" -> (35, 33)
        parts = enrollment_str.split('/')
        return int(parts[1]), int(parts[0])

    def scrape_all_business_courses(self) -> List[Dict]:
        """
        Scrape all business courses across all terms
        """
        all_courses = []

        for term in self.TERMS:
            for dept in self.BUSINESS_DEPTS:
                print(f"Scraping {dept} for term {term}...")
                courses = self.scrape_term_department(term, dept)
                all_courses.extend(courses)

        return all_courses

    def save_to_json(self, courses: List[Dict], filename: str):
        """
        Save scraped data to JSON file
        """
        with open(filename, 'w') as f:
            json.dump(courses, f, indent=2)
        print(f"Saved {len(courses)} courses to {filename}")


# Usage
if __name__ == "__main__":
    scraper = WMCourseListingScraper(rate_limit=2.0)  # 2 seconds between requests
    courses = scraper.scrape_all_business_courses()
    scraper.save_to_json(courses, 'data/raw/course_listings.json')
```

---

#### B. Catalog Scraper

**Target:** W&M Undergraduate Catalog

**Implementation:**

```python
# scraper/catalog_scraper.py

import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List

class CatalogScraper:
    """
    Scrapes course descriptions and prerequisites from official catalog
    """

    BASE_URL = "https://www.wm.edu/as/undergraduate/catalog/"

    def scrape_course_catalog(self, catalog_year: str = "2024-2025") -> List[Dict]:
        """
        Scrape full course catalog for business courses
        """
        # URL might be like: .../catalog/courses/buad.php
        url = f"{self.BASE_URL}courses/buad.php"

        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        courses = []

        # Find course entries (adjust selector based on actual HTML)
        course_sections = soup.find_all('div', class_='course')

        for section in course_sections:
            course = self._parse_catalog_entry(section, catalog_year)
            if course:
                courses.append(course)

        return courses

    def _parse_catalog_entry(self, section, catalog_year: str) -> Dict:
        """
        Parse individual course entry from catalog
        """
        try:
            # Example structure (adjust to actual HTML)
            header = section.find('h3', class_='course-header').text

            # Parse header like "BUAD 203. Financial Accounting. 3 credits."
            match = re.match(r'(\w+\s+\d+)\.\s+(.+?)\.\s+(\d+)\s+credits?', header)
            if not match:
                return None

            course_code, title, credits = match.groups()

            # Get description
            description = section.find('p', class_='description').text.strip()

            # Parse prerequisites
            prereq_text = section.find('p', class_='prerequisites')
            prerequisites = self._parse_prerequisites(prereq_text.text if prereq_text else "")

            # Parse attributes
            attributes = self._extract_attributes(description)

            return {
                'course_code': course_code,
                'title': title,
                'credits': int(credits),
                'description': description,
                'prerequisites': prerequisites,
                'attributes': attributes,
                'catalog_year': catalog_year,
                'department': course_code.split()[0],
                'level': int(course_code.split()[1][0]) * 100
            }
        except Exception as e:
            print(f"Error parsing catalog entry: {e}")
            return None

    def _parse_prerequisites(self, prereq_text: str) -> List[Dict]:
        """
        Parse prerequisite text into structured format

        Examples:
        - "Prerequisite: BUAD 101"
        - "Prerequisites: BUAD 101 and ECON 101"
        - "Prerequisite: BUAD 101 or permission of instructor"
        - "Prerequisites: BUAD 203 with a minimum grade of C"
        """
        if not prereq_text or 'none' in prereq_text.lower():
            return []

        prerequisites = []

        # Remove "Prerequisite:" or "Prerequisites:" prefix
        text = re.sub(r'^Prerequisites?:\s*', '', prereq_text, flags=re.IGNORECASE)

        # Find all course codes (e.g., BUAD 203, ECON 101)
        course_codes = re.findall(r'[A-Z]{3,4}\s+\d{3}', text)

        # Determine operator (AND/OR)
        if ' or ' in text.lower():
            operator = 'OR'
        elif ' and ' in text.lower():
            operator = 'AND'
        else:
            operator = 'AND' if len(course_codes) > 1 else None

        # Check for minimum grade requirement
        min_grade = None
        grade_match = re.search(r'minimum grade of ([A-DF][+-]?)', text)
        if grade_match:
            min_grade = grade_match.group(1)

        # Check for permission requirement
        permission_required = 'permission' in text.lower()

        if course_codes:
            prerequisites.append({
                'type': 'course',
                'courses': course_codes,
                'operator': operator,
                'min_grade': min_grade
            })

        if permission_required:
            prerequisites.append({
                'type': 'permission',
                'note': 'Permission of instructor required'
            })

        return prerequisites

    def _extract_attributes(self, description: str) -> Dict:
        """
        Extract course attributes from description
        """
        attributes = {
            'writing_intensive': False,
            'quantitative_intensive': False,
            'gen_ed_categories': [],
            'business_core': False
        }

        # Check for writing intensive
        if 'writing intensive' in description.lower():
            attributes['writing_intensive'] = True

        # Check for business core
        if 'core requirement' in description.lower() or 'business core' in description.lower():
            attributes['business_core'] = True

        return attributes
```

---

#### C. Mason School Website Scraper

**Target:** Program requirements and policies

```python
# scraper/mason_scraper.py

class MasonWebsiteScraper:
    """
    Scrapes business program requirements from Mason School website
    """

    BASE_URL = "https://mason.wm.edu"

    def scrape_major_requirements(self, major_name: str) -> Dict:
        """
        Scrape major requirements page
        """
        # Example URL: /undergraduate/majors-minors/business-analytics/
        url = f"{self.BASE_URL}/undergraduate/majors-minors/{major_name}/"

        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        requirements = {
            'program_name': major_name.replace('-', ' ').title(),
            'program_type': 'major',
            'requirements': self._extract_requirements(soup),
            'declaration_info': self._extract_declaration_info(soup)
        }

        return requirements

    def _extract_requirements(self, soup) -> Dict:
        """
        Extract course requirements from page
        """
        # Look for tables or lists of required courses
        requirements = {
            'core_courses': [],
            'concentration_courses': [],
            'electives': []
        }

        # Implementation depends on actual HTML structure
        # Look for sections like "Core Requirements", "Concentration Courses"

        return requirements

    def scrape_declaration_requirements(self) -> Dict:
        """
        Scrape major declaration requirements page
        """
        url = f"{self.BASE_URL}/undergraduate/requirements/"

        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract declaration requirements
        # - Credit thresholds
        # - Required courses
        # - GPA requirements
        # - Deadlines

        return self._parse_declaration_page(soup)
```

---

### Phase 3: Data Processing & ETL

#### A. Data Cleaning Pipeline

```python
# etl/data_cleaner.py

import pandas as pd
from typing import List, Dict
import re

class CourseDataCleaner:
    """
    Clean and normalize scraped course data
    """

    def clean_course_code(self, code: str) -> str:
        """
        Normalize course codes
        Examples: "BUAD203" -> "BUAD 203", "buad 203" -> "BUAD 203"
        """
        code = code.strip().upper()
        match = re.match(r'([A-Z]+)[\s-]?(\d+)', code)
        if match:
            dept, num = match.groups()
            return f"{dept} {num}"
        return code

    def normalize_instructor_name(self, name: str) -> str:
        """
        Normalize instructor names
        Handle cases like "Smith, John", "John Smith", "TBA", "STAFF"
        """
        if not name or name.upper() in ['TBA', 'STAFF', 'TO BE ANNOUNCED']:
            return None

        name = name.strip()

        # Convert "Last, First" to "First Last"
        if ',' in name:
            parts = name.split(',')
            return f"{parts[1].strip()} {parts[0].strip()}"

        return name

    def parse_credits(self, credits_str: str) -> int:
        """
        Parse credit values
        Handle cases like "3", "3-4", "1 TO 4"
        """
        # Extract first number
        match = re.search(r'(\d+)', str(credits_str))
        return int(match.group(1)) if match else 3  # Default to 3 if unclear

    def deduplicate_courses(self, courses: List[Dict]) -> List[Dict]:
        """
        Remove duplicate courses, keeping most recent data
        """
        df = pd.DataFrame(courses)

        # Sort by scraped_at (most recent first)
        df['scraped_at'] = pd.to_datetime(df['scraped_at'])
        df = df.sort_values('scraped_at', ascending=False)

        # Drop duplicates keeping first (most recent)
        df = df.drop_duplicates(subset=['course_code', 'term'], keep='first')

        return df.to_dict('records')

    def validate_course_data(self, course: Dict) -> tuple[bool, List[str]]:
        """
        Validate course data and return (is_valid, errors)
        """
        errors = []

        # Required fields
        required = ['course_code', 'title', 'credits']
        for field in required:
            if not course.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate course code format
        if not re.match(r'^[A-Z]{3,4}\s+\d{3}$', course.get('course_code', '')):
            errors.append(f"Invalid course code format: {course.get('course_code')}")

        # Validate credits
        credits = course.get('credits')
        if credits and (credits < 0 or credits > 6):
            errors.append(f"Invalid credit value: {credits}")

        # Validate term format (if present)
        term = course.get('term')
        if term and not re.match(r'^\d{6}$', term):
            errors.append(f"Invalid term format: {term}")

        return len(errors) == 0, errors
```

---

#### B. Data Merging

```python
# etl/data_merger.py

class CourseDataMerger:
    """
    Merge data from multiple sources into unified course records
    """

    def merge_catalog_and_listings(
        self,
        catalog_data: List[Dict],
        listing_data: List[Dict]
    ) -> List[Dict]:
        """
        Merge catalog descriptions with live course listings
        """
        # Convert to DataFrames for easier merging
        catalog_df = pd.DataFrame(catalog_data)
        listing_df = pd.DataFrame(listing_data)

        # Merge on course_code
        merged = listing_df.merge(
            catalog_df[['course_code', 'description', 'prerequisites', 'catalog_year']],
            on='course_code',
            how='left'
        )

        return merged.to_dict('records')

    def enrich_with_difficulty_index(self, courses: List[Dict]) -> List[Dict]:
        """
        Calculate difficulty index based on:
        - Course level (100-400)
        - Prerequisites count
        - Average GPA (if available)
        - Student ratings (if available)
        """
        for course in courses:
            level = course.get('level', 100)
            prereq_count = len(course.get('prerequisites', []))

            # Simple difficulty calculation (0.0 to 1.0)
            level_factor = (level - 100) / 300  # 0.0 for 100-level, 1.0 for 400-level
            prereq_factor = min(prereq_count / 5, 0.3)  # Cap at 0.3

            difficulty = min(level_factor + prereq_factor, 1.0)
            course['difficulty_index'] = round(difficulty, 2)

        return courses
```

---

#### C. Database Import

```python
# etl/database_import.py

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict
import asyncio

class CourseDataImporter:
    """
    Import cleaned data into PostgreSQL database
    """

    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def import_courses(self, courses: List[Dict]):
        """
        Import course catalog data
        """
        for course_data in courses:
            # Check if course exists
            existing = await self._get_course_by_code(course_data['course_code'])

            if existing:
                # Update existing
                await self._update_course(existing.id, course_data)
            else:
                # Create new
                await self._create_course(course_data)

        await self.session.commit()

    async def import_sections(self, sections: List[Dict]):
        """
        Import course sections for specific term
        """
        for section_data in sections:
            # Upsert section data
            await self._upsert_section(section_data)

        await self.session.commit()

    async def _create_course(self, data: Dict):
        """Create new course record"""
        course = Course(
            code=data['course_code'],
            title=data['title'],
            description=data.get('description'),
            credits=data['credits'],
            department=data['course_code'].split()[0],
            level=int(data['course_code'].split()[1][0]) * 100,
            has_lab=data.get('has_lab', False),
            difficulty_index=data.get('difficulty_index', 0.5),
            prerequisite_ids=await self._resolve_prerequisite_ids(data.get('prerequisites', [])),
            attributes=data.get('attributes', {}),
            active=True
        )
        self.session.add(course)
```

---

### Phase 4: Automation & Scheduling

#### A. Scheduled Updates

```python
# scheduler/update_scheduler.py

from celery import Celery
from celery.schedules import crontab

app = Celery('course_updater')

@app.task
def update_course_listings():
    """
    Daily update of course listings to track enrollment
    """
    scraper = WMCourseListingScraper()
    courses = scraper.scrape_all_business_courses()

    # Process and import
    cleaner = CourseDataCleaner()
    cleaned = cleaner.clean_data(courses)

    importer = CourseDataImporter()
    asyncio.run(importer.import_sections(cleaned))

@app.task
def update_course_catalog():
    """
    Weekly update of course catalog (in case of changes)
    """
    scraper = CatalogScraper()
    courses = scraper.scrape_course_catalog()

    # Process and import
    importer = CourseDataImporter()
    asyncio.run(importer.import_courses(courses))

@app.task
def full_resync():
    """
    Full resync at start of each semester
    """
    # Run all scrapers
    # Validate all data
    # Generate report of changes
    pass

# Schedule
app.conf.beat_schedule = {
    'update-listings-daily': {
        'task': 'update_course_listings',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    'update-catalog-weekly': {
        'task': 'update_course_catalog',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),  # Monday 2 AM
    },
    'full-resync-semester': {
        'task': 'full_resync',
        'schedule': crontab(day_of_month=1, hour=1, minute=0),  # 1st of month
    }
}
```

---

## Special Data Collection Tasks

### 1. Historical Grade Data

**Source:** Request from W&M Institutional Research

**Data Needed:**
- Course-level grade distributions by semester
- Average GPA per course per instructor
- Drop/withdraw rates

**Use Case:** Improve difficulty index calculation, identify challenging courses

**Access:** Requires data request form and IRB approval

---

### 2. Prerequisite Validation Data

**Challenge:** Prerequisites are sometimes listed as text, not structured

**Solution:**
```python
# Create prerequisite resolution system

def resolve_prerequisite_text(prereq_text: str) -> List[Dict]:
    """
    Convert text prerequisites to structured format

    Examples:
    "BUAD 101" -> [{"course": "BUAD 101"}]
    "BUAD 101 and ECON 101" -> [{"course": "BUAD 101"}, {"course": "ECON 101"}]
    "BUAD 101 or permission" -> [{"course": "BUAD 101", "or_permission": True}]
    "Sophomore standing" -> [{"type": "class_year", "min": 2}]
    """
    # Implement NLP-based prerequisite parser
    pass
```

---

### 3. Faculty Research Areas

**Source:** Mason School faculty directory

**Data Collection:**
```python
# Scrape faculty profiles
- Name and title
- Department/discipline
- Research interests
- Courses taught
- Office hours
- Contact information

# Use case: Match students with advisors based on interests
```

---

## Data Validation Strategy

### Automated Validation Rules

```python
# validation/rules.py

class DataValidationRules:
    """
    Validation rules for course data
    """

    RULES = [
        {
            'name': 'valid_course_code',
            'check': lambda c: bool(re.match(r'^[A-Z]{3,4}\s+\d{3}$', c['course_code'])),
            'severity': 'error'
        },
        {
            'name': 'valid_credits',
            'check': lambda c: 0 < c['credits'] <= 6,
            'severity': 'error'
        },
        {
            'name': 'valid_level',
            'check': lambda c: c['level'] in [100, 200, 300, 400],
            'severity': 'error'
        },
        {
            'name': 'has_description',
            'check': lambda c: bool(c.get('description')),
            'severity': 'warning'
        },
        {
            'name': 'enrollment_within_capacity',
            'check': lambda c: c.get('enrolled', 0) <= c.get('capacity', 999),
            'severity': 'warning'
        },
        {
            'name': 'prereqs_exist',
            'check': lambda c: all_prerequisite_courses_exist(c.get('prerequisites', [])),
            'severity': 'error'
        }
    ]

    def validate_course(self, course: Dict) -> List[Dict]:
        """
        Run all validation rules on a course
        Returns list of validation errors/warnings
        """
        issues = []

        for rule in self.RULES:
            try:
                if not rule['check'](course):
                    issues.append({
                        'rule': rule['name'],
                        'severity': rule['severity'],
                        'course': course['course_code'],
                        'message': f"Failed validation: {rule['name']}"
                    })
            except Exception as e:
                issues.append({
                    'rule': rule['name'],
                    'severity': 'error',
                    'course': course.get('course_code', 'unknown'),
                    'message': f"Validation error: {str(e)}"
                })

        return issues
```

### Manual Review Process

```python
# Generate daily validation report

def generate_validation_report(validation_results: List[Dict]) -> str:
    """
    Create human-readable report of validation issues
    """
    report = "# Course Data Validation Report\n\n"
    report += f"Generated: {datetime.now()}\n\n"

    # Group by severity
    errors = [r for r in validation_results if r['severity'] == 'error']
    warnings = [r for r in validation_results if r['severity'] == 'warning']

    report += f"## Errors: {len(errors)}\n\n"
    for error in errors:
        report += f"- [{error['course']}] {error['message']}\n"

    report += f"\n## Warnings: {len(warnings)}\n\n"
    for warning in warnings:
        report += f"- [{warning['course']}] {warning['message']}\n"

    return report

# Email report to data team daily
```

---

## Data Update Frequency

| Data Type | Source | Update Frequency | Method |
|-----------|--------|-----------------|--------|
| Course sections (enrollment) | Course Listings | Every 6 hours during registration | Automated scraper |
| Course catalog | Undergraduate Catalog | Weekly | Automated scraper |
| Program requirements | Mason website | Monthly | Automated scraper + manual review |
| Prerequisites | Catalog | Weekly | Automated scraper |
| Faculty information | Mason website | Monthly | Automated scraper |
| Historical grades | Institutional Research | Semester | Manual data request |
| Academic calendar | Registrar | Semester | Manual entry |

---

## Legal & Compliance Considerations

### 1. Web Scraping Ethics

**Best Practices:**
- Respect robots.txt directives
- Implement rate limiting (2-5 seconds between requests)
- Use descriptive User-Agent header
- Cache data to minimize requests
- Consider contacting W&M IT for official API access

**Check robots.txt:**
```bash
curl https://courselist.wm.edu/robots.txt
curl https://www.wm.edu/robots.txt
```

### 2. Terms of Service

- Review W&M website Terms of Service
- Ensure scraping is for educational/institutional purposes
- Do not redistribute scraped data publicly
- Use data only for advising platform

### 3. FERPA Compliance

- **DO NOT scrape student-specific data** without proper authorization
- Only collect publicly available course information
- Any student transcript data must come through official SIS integration
- Implement access controls for any sensitive data

### 4. Copyright

- Course descriptions are copyrighted by W&M
- Internal use for advising is likely covered under educational use
- Do not republish descriptions externally without permission

---

## Implementation Timeline

### Week 1-2: Setup & Reconnaissance
- [ ] Set up Python scraping environment
- [ ] Manually inspect all data source websites
- [ ] Document HTML structure and patterns
- [ ] Create data models and schemas
- [ ] Set up development database

### Week 3-4: Initial Scrapers
- [ ] Build course listings scraper
- [ ] Build catalog scraper
- [ ] Build Mason website scraper
- [ ] Implement data cleaning pipeline
- [ ] Create validation rules

### Week 5-6: Testing & Refinement
- [ ] Test scrapers on sample data
- [ ] Validate data quality
- [ ] Handle edge cases (TBA instructors, special formats)
- [ ] Implement error handling
- [ ] Create data quality reports

### Week 7-8: Integration
- [ ] Build ETL pipeline
- [ ] Import data into production database
- [ ] Set up automated scheduling
- [ ] Create monitoring dashboards
- [ ] Document data refresh process

### Week 9-10: Historical Data
- [ ] Request historical grade data
- [ ] Import past semester course offerings
- [ ] Build historical trend analysis
- [ ] Backfill prerequisite relationships

### Ongoing: Maintenance
- [ ] Monitor scraper health daily
- [ ] Review validation reports weekly
- [ ] Update scrapers when websites change
- [ ] Quarterly data quality audits

---

## Data Quality Metrics

Track the following metrics to ensure data quality:

```python
# metrics/quality_metrics.py

class DataQualityMetrics:
    """
    Track data quality KPIs
    """

    def calculate_completeness(self, courses: List[Dict]) -> float:
        """
        Percentage of courses with all required fields populated
        """
        required_fields = ['course_code', 'title', 'description', 'credits', 'prerequisites']

        complete_count = 0
        for course in courses:
            if all(course.get(field) for field in required_fields):
                complete_count += 1

        return complete_count / len(courses) if courses else 0

    def calculate_accuracy(self) -> float:
        """
        Percentage of courses that pass validation rules
        """
        # Run validation on all courses
        # Return % that pass
        pass

    def calculate_freshness(self) -> Dict:
        """
        Time since last update for each data type
        """
        return {
            'course_listings': self._time_since_last_update('course_sections'),
            'catalog': self._time_since_last_update('courses'),
            'requirements': self._time_since_last_update('programs')
        }

    def generate_dashboard(self):
        """
        Create Grafana-compatible metrics
        """
        return {
            'completeness': self.calculate_completeness(),
            'accuracy': self.calculate_accuracy(),
            'freshness': self.calculate_freshness(),
            'total_courses': self.count_total_courses(),
            'total_sections': self.count_total_sections()
        }
```

**Target Metrics:**
- Completeness: >95%
- Accuracy: >98%
- Freshness: <24 hours for enrollment data, <7 days for catalog

---

## Backup & Recovery

### Data Backup Strategy

```bash
# Daily backups of raw scraped data
/data/
  backups/
    2024-12-22/
      course_listings.json
      catalog.json
      mason_programs.json
      metadata.json

# Retention: 90 days
```

### Recovery Plan

If scraper breaks or data is corrupted:

1. **Immediate:** Revert to last known good data backup
2. **Short-term:** Fix scraper and re-run
3. **Long-term:** Manual data entry from website if scraper unfixable

---

## Alternative: Official API Request

### Best Case Scenario

**Request from W&M IT:**
- Official API access to Banner/Self-Service
- Real-time course data feed
- Authenticated endpoint with API key
- Structured JSON responses

**Benefits:**
- More reliable than scraping
- Real-time data
- Official support
- No ToS concerns

**Process:**
1. Submit formal request to W&M IT
2. Describe use case and data needs
3. Sign data use agreement
4. Receive API documentation and credentials
5. Build official integration

**Recommended contact:** W&M IT Services or Registrar's Office

---

## Sample Data Output

### Final Unified Course JSON

```json
{
  "course_id": "uuid-here",
  "course_code": "BUAD 203",
  "department": "BUAD",
  "course_number": "203",
  "title": "Financial Accounting",
  "description": "Introduction to the preparation and use of financial statements...",
  "credits": 3,
  "level": 200,
  "has_lab": false,
  "difficulty_index": 0.60,
  "prerequisites": [
    {
      "type": "course",
      "courses": ["BUAD 101"],
      "operator": null,
      "min_grade": null
    }
  ],
  "corequisites": [],
  "restrictions": {
    "major_only": false,
    "class_year_min": null,
    "permission_required": false
  },
  "attributes": {
    "writing_intensive": false,
    "gen_ed_categories": [],
    "business_core": true
  },
  "typical_terms_offered": ["Fall", "Spring"],
  "catalog_year": "2024-2025",
  "sections": [
    {
      "section_id": "BUAD-203-01-202510",
      "section_number": "01",
      "term": "202510",
      "term_name": "Fall 2024",
      "crn": "12345",
      "instructor": {
        "name": "John Smith",
        "email": "jsmith@wm.edu",
        "rating": 4.2
      },
      "meeting_times": [
        {
          "days": ["Monday", "Wednesday", "Friday"],
          "start_time": "09:00",
          "end_time": "09:50",
          "location": "Miller Hall 101",
          "start_date": "2024-08-28",
          "end_date": "2024-12-06"
        }
      ],
      "capacity": 35,
      "enrolled": 33,
      "waitlist": 2,
      "available_seats": 0,
      "status": "Open",
      "last_updated": "2024-12-22T10:30:00Z"
    }
  ],
  "historical_data": {
    "avg_gpa": 3.2,
    "avg_enrollment": 32,
    "drop_rate": 0.05
  },
  "data_sources": {
    "catalog": "https://www.wm.edu/as/undergraduate/catalog/courses/buad.php",
    "listings": "https://courselist.wm.edu/courselist/",
    "scraped_at": "2024-12-22T10:00:00Z"
  }
}
```

---

## Next Steps

### Immediate Actions

1. **Manual reconnaissance** - Inspect all W&M websites, take screenshots, document structure
2. **Contact W&M IT** - Ask about official API access
3. **Set up scraping environment** - Install Python, create virtual environment
4. **Build first prototype scraper** - Start with course listings scraper
5. **Validate sample data** - Scrape 10-20 courses and manually verify accuracy

### Questions to Answer

- Does W&M provide an official course data API?
- What are the peak registration times (when to scrape most frequently)?
- Are there any W&M-specific data formats or codes to be aware of?
- Who owns the course data at W&M? (Registrar, IT, Business School)
- Is there existing documentation on W&M's course catalog structure?

---

**Document Version:** 1.0
**Last Updated:** 2024-12-22
**Status:** Ready for Implementation
