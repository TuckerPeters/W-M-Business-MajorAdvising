"""
FastAPI Server for W&M Course Catalog API

Provides REST endpoints for the frontend to query course data.
Runs the scheduler in the background for automatic updates.

Usage:
    python server.py                    # Run server on port 8000
    python server.py --port 3001        # Custom port
    python server.py --no-scheduler     # Disable background updates
    python server.py --debugtracking    # Enable gaze tracking for prod testing
    python server.py --debug            # Creates a demo student profile and advisor profile for testing UI
"""

import asyncio
import argparse
import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import initialize_firebase, get_firestore_client
from core.semester import SemesterManager
from core.parsers import parse_meeting_times_raw
from core.auth import (
    AuthenticatedUser,
    get_current_user,
    get_current_advisor,
    verify_user_access,
    set_debug_mode,
    is_debug_mode,
)
from services.firebase import get_course_service
from services.student import get_student_service
from services.advisor import get_advisor_service
from services.prerequisites import get_prerequisite_engine
from services.chat import get_chat_service
from services.conversation import get_conversation_service
from services.embeddings import get_embeddings_service
from services.common_questions import get_common_questions_service


# Pydantic Models (API Response Schemas)
class SectionResponse(BaseModel):
    crn: str
    section_number: str
    instructor: str
    status: str
    capacity: int
    enrolled: int
    available: int
    meeting_days: Optional[str] = ""
    meeting_time: Optional[str] = ""
    building: Optional[str] = ""
    room: Optional[str] = ""


class CourseResponse(BaseModel):
    course_code: str
    subject_code: str
    course_number: str
    title: str
    description: Optional[str] = ""
    credits: int
    attributes: List[str] = []
    prerequisites: List[str] = []
    sections: List[SectionResponse] = []


class CourseListResponse(BaseModel):
    courses: List[CourseResponse]
    total: int
    term_code: str


class SearchResponse(BaseModel):
    results: List[CourseResponse]
    total: int
    query: str


class SubjectResponse(BaseModel):
    subjects: List[str]
    total: int


class HealthResponse(BaseModel):
    status: str
    term_code: str
    semester: str
    is_registration_period: bool
    firebase: str
    redis: str


class CacheStatsResponse(BaseModel):
    connected: bool
    hits: int = 0
    misses: int = 0
    memory_used: str = "unknown"
    course_keys: int = 0
    subject_keys: int = 0
    search_keys: int = 0
    total_keys: int = 0


# Student Profile Models

class StudentProfile(BaseModel):
    id: Optional[str] = None
    userId: str
    name: str
    email: str
    classYear: int  # Required - graduation year
    gpa: Optional[float] = None  # Null allowed for first semester freshmen
    creditsEarned: int = 0
    declared: bool = False  # False until intendedMajor is declared
    intendedMajor: Optional[str] = None  # Null until declared
    apCredits: Optional[int] = None  # Null if no AP credits
    holds: List[str] = []


class StudentProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    classYear: Optional[int] = None
    gpa: Optional[float] = None
    creditsEarned: Optional[int] = None
    intendedMajor: Optional[str] = None
    apCredits: Optional[int] = None
    holds: Optional[List[str]] = None


class DeclareMajorRequest(BaseModel):
    major: str


class EnrollmentRecord(BaseModel):
    id: Optional[str] = None
    studentId: str
    courseCode: str
    courseName: Optional[str] = None
    term: str
    grade: Optional[str] = None
    status: str = "planned"
    credits: int = 3
    sectionNumber: Optional[str] = None
    crn: Optional[str] = None
    instructor: Optional[str] = None
    meeting_days: Optional[str] = None
    meeting_time: Optional[str] = None
    building: Optional[str] = None
    room: Optional[str] = None


class EnrollmentCreate(BaseModel):
    courseCode: str
    courseName: Optional[str] = None
    term: str
    grade: Optional[str] = None
    status: str = "planned"
    credits: int = 3
    sectionNumber: Optional[str] = None
    crn: Optional[str] = None
    instructor: Optional[str] = None
    meeting_days: Optional[str] = None
    meeting_time: Optional[str] = None
    building: Optional[str] = None
    room: Optional[str] = None


class EnrollmentUpdate(BaseModel):
    grade: Optional[str] = None
    status: Optional[str] = None


class StudentCoursesResponse(BaseModel):
    completed: List[EnrollmentRecord]
    current: List[EnrollmentRecord]
    planned: List[EnrollmentRecord]


class Milestone(BaseModel):
    id: str
    title: str
    description: str
    deadline: Optional[str] = None
    completionCriteria: Optional[str] = None
    completed: bool = False
    completedAt: Optional[str] = None
    notes: Optional[str] = None


class MilestoneProgressUpdate(BaseModel):
    completed: bool
    notes: Optional[str] = None


# Advisor Portal Models

class AdvisorAssignment(BaseModel):
    id: Optional[str] = None
    advisorId: str
    studentId: str
    assignedDate: str
    student: Optional[StudentProfile] = None


class AdviseeResponse(BaseModel):
    id: str
    userId: str
    name: str
    email: str
    classYear: int
    gpa: Optional[float] = None
    creditsEarned: int = 0
    declared: bool = False
    intendedMajor: Optional[str] = None
    assignmentId: Optional[str] = None
    assignedDate: Optional[str] = None


class AdvisorNote(BaseModel):
    id: Optional[str] = None
    studentId: str
    advisorId: str
    note: str
    visibility: str = "private"
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class NoteCreate(BaseModel):
    note: str
    visibility: str = "private"


class NoteUpdate(BaseModel):
    note: Optional[str] = None
    visibility: Optional[str] = None


class AdvisorAlert(BaseModel):
    type: str
    severity: str
    studentId: str
    studentName: str
    message: str
    createdAt: str


class AssignAdviseeRequest(BaseModel):
    studentId: str


# Schedule Validation Models

class ValidateScheduleRequest(BaseModel):
    studentId: str
    proposedCourses: List[str]


class RiskFlagResponse(BaseModel):
    type: str
    severity: str
    message: str
    course_code: Optional[str] = None
    details: dict = {}


class ScheduleScoreResponse(BaseModel):
    overall: int
    workload: int
    prerequisite_alignment: int
    balance: int
    recommendations: List[str] = []


class CourseValidationDetail(BaseModel):
    code: str
    name: str
    credits: float
    prerequisites: List[str] = []
    prerequisites_met: bool
    missing_prerequisites: List[str] = []


class ValidateScheduleResponse(BaseModel):
    valid: bool
    warnings: List[str] = []
    errors: List[str] = []
    missingPrereqs: dict = {}
    riskFlags: List[RiskFlagResponse] = []
    scheduleScore: ScheduleScoreResponse
    totalCredits: int
    courseDetails: List[CourseValidationDetail] = []


class PrerequisiteInfoResponse(BaseModel):
    course_code: str
    course_name: str
    credits: float
    prerequisites: List[str] = []
    semester_offered: str


class EligibleCourseResponse(BaseModel):
    code: str
    name: str
    credits: float
    semester_offered: str
    prerequisites: List[str] = []


# Chat Models

class ChatMessageRequest(BaseModel):
    studentId: str
    message: str
    chatHistory: List[dict] = []
    conversationId: Optional[str] = None


class ChatCitation(BaseModel):
    source: str
    excerpt: str
    relevance: float = 0.8


class ChatRiskFlag(BaseModel):
    type: str
    severity: str
    message: str


class ChatNextStep(BaseModel):
    action: str
    priority: str
    deadline: Optional[str] = None


class ChatMessageResponse(BaseModel):
    content: str
    citations: List[ChatCitation] = []
    risks: List[ChatRiskFlag] = []
    nextSteps: List[ChatNextStep] = []
    conversationId: Optional[str] = None


# Conversation Models

class ConversationCreateRequest(BaseModel):
    studentId: str
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    studentId: str
    userId: str
    userRole: str
    title: str
    status: str
    messageCount: int
    createdAt: str
    updatedAt: str
    lastMessagePreview: Optional[str] = None


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


class ConversationMessageResponse(BaseModel):
    id: str
    conversationId: str
    role: str
    content: str
    citations: List[ChatCitation] = []
    risks: List[ChatRiskFlag] = []
    nextSteps: List[ChatNextStep] = []
    createdAt: str


class ConversationMessagesResponse(BaseModel):
    messages: List[ConversationMessageResponse]
    total: int


class ConversationTitleUpdate(BaseModel):
    title: str


# Background Scheduler

scheduler_task = None


async def run_background_scheduler():
    """Run the scheduler in the background"""
    from tasks.scheduler import TaskScheduler

    scheduler = TaskScheduler()
    await scheduler.start()

    # Keep running
    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        scheduler.shutdown()


DEMO_STUDENT_ID = "demo-student"
DEMO_ADVISOR_ID = "demo-advisor"


DEMO_STUDENTS = [
    {"id": "demo-student",   "name": "Sarah Chen",       "email": "schen@wm.edu",       "classYear": 2027, "declared": True,  "intendedMajor": "Business Analytics",  "minor": "Computer Science",  "apCredits": 8,  "targetCredits": 42},
    {"id": "demo-student-2", "name": "Marcus Williams",   "email": "mwilliams@wm.edu",   "classYear": 2027, "declared": True,  "intendedMajor": "Finance",             "minor": None,                "apCredits": 4,  "targetCredits": 48},
    {"id": "demo-student-3", "name": "Priya Patel",       "email": "ppatel@wm.edu",       "classYear": 2028, "declared": False, "intendedMajor": "Accounting",          "minor": None,                "apCredits": 12, "targetCredits": 28},
    {"id": "demo-student-4", "name": "James O'Brien",     "email": "jobrien@wm.edu",      "classYear": 2026, "declared": True,  "intendedMajor": "Marketing",           "minor": "Psychology",        "apCredits": 6,  "targetCredits": 90},
    {"id": "demo-student-5", "name": "Sofia Martinez",    "email": "smartinez@wm.edu",    "classYear": 2028, "declared": False, "intendedMajor": None,                  "minor": None,                "apCredits": 0,  "targetCredits": 15},
    {"id": "demo-student-6", "name": "Tyler Washington",  "email": "twashington@wm.edu",  "classYear": 2027, "declared": True,  "intendedMajor": "Finance",             "minor": "Economics",         "apCredits": 8,  "targetCredits": 55},
    {"id": "demo-student-7", "name": "Emma Nguyen",       "email": "enguyen@wm.edu",      "classYear": 2026, "declared": True,  "intendedMajor": "Business Analytics",  "minor": None,                "apCredits": 10, "targetCredits": 100},
    {"id": "demo-student-8", "name": "David Kim",         "email": "dkim@wm.edu",         "classYear": 2028, "declared": False, "intendedMajor": "Accounting",          "minor": None,                "apCredits": 3,  "targetCredits": 20},
    {"id": "demo-student-9", "name": "Olivia Jackson",    "email": "ojackson@wm.edu",     "classYear": 2027, "declared": True,  "intendedMajor": "Marketing",           "minor": "Data Science",      "apCredits": 6,  "targetCredits": 60},
    {"id": "demo-student-10","name": "Aiden Thompson",    "email": "athompson@wm.edu",    "classYear": 2026, "declared": True,  "intendedMajor": "Finance",             "minor": None,                "apCredits": 4,  "targetCredits": 85},
]

# In-memory fallback data for demo mode (no Firestore writes needed)
DEMO_ADVISOR_PROFILE = {
    "userId": DEMO_ADVISOR_ID,
    "name": "Dr. Emily Rodriguez",
    "email": "erodriguez@wm.edu",
    "role": "advisor",
    "department": "Raymond A. Mason School of Business",
    "office": "Miller Hall 2040",
    "phone": "757-221-2900",
}

_DEMO_PROFILES = {s["id"]: {
    "userId": s["id"], "name": s["name"], "email": s["email"],
    "classYear": s["classYear"], "gpa": 3.72 if s["id"] == "demo-student" else round(2.5 + hash(s["id"]) % 15 / 10, 2),
    "creditsEarned": s["targetCredits"], "declared": s["declared"],
    "intendedMajor": s["intendedMajor"], "apCredits": s["apCredits"],
    "holds": [], "minor": s["minor"], "advisorId": DEMO_ADVISOR_ID,
} for s in DEMO_STUDENTS}

def _get_demo_profile(user_id: str):
    """Return in-memory demo student profile, or None if not a demo student."""
    return _DEMO_PROFILES.get(user_id)


def _seed_debug_data():
    """Create demo student and advisor profiles for debug mode.
    Skips seeding if demo data already exists in Firestore.
    Uses Firestore batch writes (max 500 ops each) to stay within quota."""
    import random
    import time as _time
    from datetime import datetime

    db = get_firestore_client()

    # Check if demo data already exists — skip seeding if so
    try:
        existing = db.collection("students").document(DEMO_STUDENT_ID).get()
        if existing.exists:
            print("[Debug] Demo data already exists in Firestore — skipping seed")
            return
    except Exception as e:
        print(f"[Debug] Firestore check failed ({e}), skipping seed — in-memory fallbacks will be used")
        return

    # Pull real courses from the database (limit to keep reads low)
    all_courses = []
    course_docs = db.collection("courses").limit(200).stream()
    for doc in course_docs:
        data = doc.to_dict()
        if data.get("course_code") and data.get("title"):
            all_courses.append(data)

    if all_courses:
        print(f"[Debug] Found {len(all_courses)} courses in database")
    else:
        print("[Debug] No courses in database, demo students will have no enrollments")

    grade_points = {
        "A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7, "D+": 1.3, "D": 1.0, "F": 0.0,
    }
    now = datetime.utcnow().isoformat()

    # Collect all writes, then flush in batches of 450 (under 500 limit)
    pending_writes = []  # list of (doc_ref, data_dict)

    def flush_writes():
        """Commit pending writes in Firestore batches of 450."""
        for i in range(0, len(pending_writes), 450):
            batch = db.batch()
            for ref, data in pending_writes[i:i + 450]:
                batch.set(ref, data, merge=True)
            batch.commit()
            if i + 450 < len(pending_writes):
                _time.sleep(0.5)  # brief pause between batches
        pending_writes.clear()

    # --- Demo advisor (create first so assignments reference it) ---
    pending_writes.append((db.collection("students").document(DEMO_ADVISOR_ID), {
        "userId": DEMO_ADVISOR_ID,
        "name": "Dr. Emily Rodriguez",
        "email": "erodriguez@wm.edu",
        "role": "advisor",
        "department": "Raymond A. Mason School of Business",
        "office": "Miller Hall 2040",
        "phone": "757-221-2900",
        "createdAt": now,
        "updatedAt": now,
    }))

    # --- Create each demo student ---
    for student_info in DEMO_STUDENTS:
        sid = student_info["id"]
        target_credits = student_info["targetCredits"]

        # Grade pool varies by student to create GPA diversity
        if target_credits >= 85:
            grade_pool = ["A", "A-", "A", "B+", "A-", "B+"]
        elif target_credits >= 50:
            grade_pool = ["A-", "B+", "B", "B+", "A-", "B"]
        elif target_credits >= 30:
            grade_pool = ["B+", "B", "B-", "A-", "B", "C+"]
        else:
            grade_pool = ["A", "B+", "B", "A-", "B+", "A"]

        # Risk-triggering GPAs for some students
        if sid == "demo-student-5":
            grade_pool = ["C+", "C", "C-", "B-", "C", "D+"]
        elif sid == "demo-student-8":
            grade_pool = ["B-", "C+", "C", "B", "C+", "C"]

        # Build enrollments from shuffled courses
        enrollments = []
        if all_courses:
            shuffled = list(all_courses)
            random.shuffle(shuffled)

            completed, completed_credits, idx = [], 0, 0
            while idx < len(shuffled) and completed_credits < target_credits:
                c = shuffled[idx]
                cr = c.get("credits", 3)
                if completed_credits + cr <= target_credits + 3:
                    completed.append(c)
                    completed_credits += cr
                idx += 1

            enrolled, enrolled_credits = [], 0
            while idx < len(shuffled) and enrolled_credits < 15:
                c = shuffled[idx]
                cr = c.get("credits", 3)
                if enrolled_credits + cr <= 18:
                    enrolled.append(c)
                    enrolled_credits += cr
                idx += 1

            planned = shuffled[idx:idx + 2] if idx < len(shuffled) else []

            for c in completed:
                enrollments.append({"courseCode": c["course_code"], "courseName": c["title"], "term": "202501", "status": "completed", "grade": random.choice(grade_pool), "credits": c.get("credits", 3)})
            for c in enrolled:
                sections = c.get("sections", [])
                section = random.choice(sections) if sections else {}
                meeting = parse_meeting_times_raw(section.get("meeting_times_raw", ""))
                enrollments.append({"courseCode": c["course_code"], "courseName": c["title"], "term": "202602", "status": "enrolled", "grade": None, "credits": c.get("credits", 3), "sectionNumber": section.get("section_number", ""), "crn": section.get("crn", ""), "instructor": section.get("instructor", ""), "meeting_days": meeting["days"], "meeting_time": meeting["time"], "building": section.get("building", ""), "room": section.get("room", "")})
            for c in planned:
                enrollments.append({"courseCode": c["course_code"], "courseName": c["title"], "term": "202609", "status": "planned", "grade": None, "credits": c.get("credits", 3)})

        # Calculate GPA
        completed_enrollments = [e for e in enrollments if e["status"] == "completed" and e.get("grade")]
        credits_earned = sum(e["credits"] for e in completed_enrollments)
        total_qp = sum(grade_points.get(e["grade"], 0.0) * e["credits"] for e in completed_enrollments)
        gpa = round(total_qp / credits_earned, 2) if credits_earned > 0 else 0.0

        # Student profile
        pending_writes.append((db.collection("students").document(sid), {
            "userId": sid,
            "name": student_info["name"],
            "email": student_info["email"],
            "classYear": student_info["classYear"],
            "gpa": gpa,
            "creditsEarned": credits_earned,
            "declared": student_info["declared"],
            "intendedMajor": student_info["intendedMajor"],
            "apCredits": student_info["apCredits"],
            "holds": [],
            "minor": student_info["minor"],
            "phone": f"757-555-{random.randint(1000, 9999)}",
            "advisorId": DEMO_ADVISOR_ID,
            "createdAt": now,
            "updatedAt": now,
        }))

        # Enrollments
        for enrollment in enrollments:
            pending_writes.append((db.collection("enrollments").document(), {
                "studentId": sid, **enrollment, "createdAt": now, "updatedAt": now,
            }))

        # Milestones
        completed_codes = {e["courseCode"] for e in enrollments if e["status"] == "completed"}
        core_courses = {"BUAD 201", "BUAD 202", "BUAD 231", "BUAD 310", "BUAD 302", "ECON 101", "ECON 102"}
        core_done = core_courses.issubset(completed_codes)
        has_39 = credits_earned >= 39
        for milestone in [
            {"title": "Complete Business Core", "description": "BUAD 201, 202, 231, 310, 302, and ECON 101, 102", "completed": core_done, "order": 0, **({"completedAt": "2025-12-15"} if core_done else {})},
            {"title": "Complete 39 Credits", "description": "Minimum credits to declare major", "completed": has_39, "order": 1, **({"completedAt": "2025-12-15"} if has_39 else {})},
            {"title": "Declare Major", "description": "Must declare before earning 54 credits", "completed": student_info["declared"], "order": 2, **({"completedAt": "2026-01-20"} if student_info["declared"] else {})},
            {"title": "Complete 120 Credits", "description": "Total credits required for graduation", "completed": False, "order": 3, "credits": {"current": credits_earned, "required": 120}},
        ]:
            pending_writes.append((db.collection("milestones").document(), {
                "studentId": sid, "type": "degree", **milestone, "createdAt": now,
            }))

        # Advisor assignment
        pending_writes.append((db.collection("advisor_assignments").document(f"{DEMO_ADVISOR_ID}_{sid}"), {
            "advisorId": DEMO_ADVISOR_ID, "studentId": sid, "assignedDate": now,
        }))

        print(f"[Debug] Prepared {student_info['name']} ({sid}) — {credits_earned}cr, {gpa} GPA, {len(enrollments)} enrollments")

    # Flush all writes in batches
    print(f"[Debug] Flushing {len(pending_writes)} writes to Firestore...")
    flush_writes()
    print(f"[Debug] Done — created demo advisor + {len(DEMO_STUDENTS)} demo students")


def _cleanup_debug_data():
    """Remove all demo students, advisor, enrollments, milestones, and assignments on shutdown."""
    db = get_firestore_client()

    for student_info in DEMO_STUDENTS:
        sid = student_info["id"]

        for doc in db.collection("enrollments").where("studentId", "==", sid).stream():
            doc.reference.delete()
        for doc in db.collection("milestones").where("studentId", "==", sid).stream():
            doc.reference.delete()
        for conv in db.collection("conversations").where("studentId", "==", sid).stream():
            for msg in db.collection("conversation_messages").where("conversationId", "==", conv.id).stream():
                msg.reference.delete()
            conv.reference.delete()
        db.collection("students").document(sid).delete()
        db.collection("advisor_assignments").document(f"{DEMO_ADVISOR_ID}_{sid}").delete()

    db.collection("students").document(DEMO_ADVISOR_ID).delete()
    print(f"[Debug] Cleaned up all demo data ({len(DEMO_STUDENTS)} students + advisor)")


# App Lifespan (startup/shutdown)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown"""
    global scheduler_task

    # Startup
    print("[Server] Initializing Firebase...")
    initialize_firebase()

    # Seed demo data in debug mode
    if getattr(app.state, 'debug_mode', False):
        set_debug_mode(True)
        print("[Server] Debug mode: seeding demo student and advisor...")
        _seed_debug_data()

    # Start scheduler if enabled (skip in debug mode)
    if app.state.enable_scheduler and not getattr(app.state, 'debug_mode', False):
        print("[Server] Starting background scheduler...")
        scheduler_task = asyncio.create_task(run_background_scheduler())
    elif getattr(app.state, 'debug_mode', False):
        print("[Server] Debug mode: skipping background scheduler")

    print("[Server] Ready!")

    yield

    # Shutdown — skip cleanup so demo data persists across restarts
    # _cleanup_debug_data() is available but disabled to avoid quota issues

    if scheduler_task:
        print("[Server] Stopping scheduler...")
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

    print("[Server] Shutdown complete")


# FastAPI App

app = FastAPI(
    title="W&M Course Catalog API",
    description="API for William & Mary course catalog data",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - Allow frontend origins
_cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
]
# Add production frontend URL from environment variable
_frontend_url = os.getenv("FRONTEND_URL", "").strip()
if _frontend_url:
    _cors_origins.append(_frontend_url)
    # Also allow without trailing slash
    _cors_origins.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Defaults — also honor env vars for deployments using uvicorn directly (Heroku)
app.state.enable_scheduler = True
app.state.debug_mode = os.getenv("DEMO_MODE", "").lower() in ("true", "1")
app.state.debug_tracking = os.getenv("DEBUG_TRACKING", "").lower() in ("true", "1")


# API Endpoints

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    # Check Firebase connectivity
    firebase_status = "connected"
    try:
        db = get_firestore_client()
        # Try a simple operation
        db.collection("metadata").document("health_check").get()
    except Exception as e:
        firebase_status = f"error: {str(e)[:50]}"

    # Check Redis connectivity
    redis_status = "unavailable"
    try:
        from services.cache import get_cache
        cache = get_cache()
        if cache.is_connected:
            redis_status = "connected"
    except Exception:
        redis_status = "unavailable"

    return HealthResponse(
        status="ok" if firebase_status == "connected" else "degraded",
        term_code=SemesterManager.get_trackable_term_code(),
        semester=SemesterManager.get_trackable_display_name(),
        is_registration_period=SemesterManager.is_registration_period(),
        firebase=firebase_status,
        redis=redis_status
    )


@app.get("/api/health", response_model=HealthResponse)
async def api_health():
    """API health check"""
    return await health_check()


@app.get("/api/courses", response_model=CourseListResponse)
async def list_courses(
    subject: Optional[str] = Query(None, description="Filter by subject code (e.g., CSCI)"),
    term: Optional[str] = Query(None, description="Term code (e.g., 202620). Defaults to current trackable term."),
    limit: int = Query(500, ge=1, le=2000, description="Max courses to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List all courses, optionally filtered by subject.
    """
    db = get_firestore_client()
    term_code = term or SemesterManager.get_trackable_term_code()

    query = db.collection("courses")

    if subject:
        query = query.where("subject_code", "==", subject.upper())

    # Get total count (for pagination)
    all_docs = list(query.stream())
    total = len(all_docs)

    # Apply pagination
    courses = []
    for doc in all_docs[offset:offset + limit]:
        data = doc.to_dict()
        courses.append(_format_course(data))

    return CourseListResponse(
        courses=courses,
        total=total,
        term_code=term_code
    )


@app.get("/api/courses/search", response_model=SearchResponse)
async def search_courses(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results")
):
    """
    Search courses by title, code, or instructor.
    Note: This route must be defined BEFORE /api/courses/{course_code}
    """
    db = get_firestore_client()
    query_upper = q.upper()
    query_lower = q.lower()

    results = []

    # Search by course code prefix
    docs = db.collection("courses") \
        .where("course_code", ">=", query_upper) \
        .where("course_code", "<=", query_upper + "\uf8ff") \
        .limit(limit) \
        .stream()

    for doc in docs:
        results.append(_format_course(doc.to_dict()))

    # If not enough results, search by title (basic)
    if len(results) < limit:
        all_docs = db.collection("courses").stream()
        for doc in all_docs:
            if len(results) >= limit:
                break
            data = doc.to_dict()
            title = data.get("title", "").lower()
            if query_lower in title and data not in [r.dict() for r in results]:
                results.append(_format_course(data))

    return SearchResponse(
        results=results[:limit],
        total=len(results),
        query=q
    )


@app.get("/api/courses/{course_code}", response_model=CourseResponse)
async def get_course(course_code: str):
    """
    Get a single course by course code.

    Example: /api/courses/CSCI%20141
    """
    service = get_course_service()

    # Try with original code
    course = service.get_course(course_code)

    # Try with underscore replacement
    if not course:
        course = service.get_course(course_code.replace("_", " "))

    if not course:
        raise HTTPException(status_code=404, detail=f"Course not found: {course_code}")

    return _format_course(course)


@app.get("/api/subjects", response_model=SubjectResponse)
async def list_subjects():
    """
    List all available subject codes.
    """
    db = get_firestore_client()

    subjects = set()
    docs = db.collection("courses").select(["subject_code"]).stream()

    for doc in docs:
        data = doc.to_dict()
        if "subject_code" in data:
            subjects.add(data["subject_code"])

    sorted_subjects = sorted(list(subjects))

    return SubjectResponse(
        subjects=sorted_subjects,
        total=len(sorted_subjects)
    )


@app.get("/api/term")
async def get_current_term():
    """
    Get current term information.
    """
    info = SemesterManager.get_trackable_semester_info()
    next_transition = SemesterManager.get_next_transition_info()

    return {
        "current": info,
        "next_transition": {
            "date": next_transition["transition_date"].isoformat(),
            "next_term": next_transition["next_trackable"],
            "next_semester": next_transition["next_semester"]
        },
        "is_registration_period": SemesterManager.is_registration_period()
    }


@app.get("/api/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get Redis cache statistics.
    """
    service = get_course_service()
    stats = service.get_cache_stats()
    return CacheStatsResponse(**stats)


@app.post("/api/cache/clear")
async def clear_cache():
    """
    Clear all cached data.
    """
    service = get_course_service()
    success = service.clear_cache()
    return {"success": success, "message": "Cache cleared" if success else "Cache not available"}


# --- Student Profile Endpoints ---

@app.get("/api/student/{user_id}/profile", response_model=StudentProfile)
async def get_student_profile(
    user_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get a student's profile."""
    # Verify access (user can view their own profile, or advisor/admin can view any)
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_student_service()
    student = service.get_student(user_id)

    if not student:
        # In demo mode, serve from in-memory fallback
        if is_debug_mode():
            student = _get_demo_profile(user_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

    # In demo mode, show a strong GPA for the demo student
    if is_debug_mode() and user_id == DEMO_STUDENT_ID:
        student["gpa"] = 3.72

    return StudentProfile(**student)


@app.post("/api/student/{user_id}/profile", response_model=StudentProfile)
async def create_student_profile(
    user_id: str,
    profile: StudentProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new student profile."""
    # Users can only create their own profile
    if current_user.uid != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Can only create your own profile")

    service = get_student_service()

    existing = service.get_student(user_id)
    if existing:
        raise HTTPException(status_code=409, detail="Student profile already exists")

    data = profile.model_dump(exclude_none=True)
    data["userId"] = user_id

    student = service.create_student(user_id, data)
    return StudentProfile(**student)


@app.put("/api/student/{user_id}/profile", response_model=StudentProfile)
async def update_student_profile(
    user_id: str,
    profile: StudentProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update an existing student profile."""
    # Verify access
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_student_service()

    updated = service.update_student(user_id, profile.model_dump(exclude_none=True))

    if not updated:
        raise HTTPException(status_code=404, detail="Student not found")

    return StudentProfile(**updated)


@app.post("/api/student/{user_id}/declare-major", response_model=StudentProfile)
async def declare_major(
    user_id: str,
    request: DeclareMajorRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Declare or update a student's major."""
    # Verify access
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_student_service()

    updated = service.declare_major(user_id, request.major)

    if not updated:
        raise HTTPException(status_code=404, detail="Student not found")

    return StudentProfile(**updated)


# --- Student Courses/Enrollments Endpoints ---

@app.get("/api/student/{user_id}/courses", response_model=StudentCoursesResponse)
async def get_student_courses(
    user_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get a student's courses (completed, current, planned)."""
    # Verify access
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_student_service()

    student = service.get_student(user_id)
    if not student:
        if is_debug_mode() and _get_demo_profile(user_id):
            student = _get_demo_profile(user_id)
        else:
            raise HTTPException(status_code=404, detail="Student not found")

    courses = service.get_student_courses(user_id)

    # In demo mode, boost the demo student's grades for a better demo presentation
    if is_debug_mode() and user_id == DEMO_STUDENT_ID:
        import random as _rng
        _good = ["A", "A", "A-", "A-", "A", "B+", "A-", "A"]
        _rng.seed(42)  # deterministic so grades don't change on refresh
        for e in courses["completed"]:
            if e.get("grade"):
                e["grade"] = _rng.choice(_good)

    return StudentCoursesResponse(
        completed=[EnrollmentRecord(**e) for e in courses["completed"]],
        current=[EnrollmentRecord(**e) for e in courses["current"]],
        planned=[EnrollmentRecord(**e) for e in courses["planned"]]
    )


@app.post("/api/student/{user_id}/courses", response_model=EnrollmentRecord)
async def add_student_enrollment(
    user_id: str,
    enrollment: EnrollmentCreate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Add a course enrollment for a student."""
    # Verify access
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_student_service()

    student = service.get_student(user_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    data = enrollment.model_dump()
    result = service.add_enrollment(user_id, data)

    return EnrollmentRecord(**result)


@app.put("/api/student/{user_id}/courses/{enrollment_id}", response_model=EnrollmentRecord)
async def update_student_enrollment(
    user_id: str,
    enrollment_id: str,
    enrollment: EnrollmentUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a course enrollment."""
    # Verify access
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_student_service()

    updated = service.update_enrollment(enrollment_id, enrollment.model_dump(exclude_none=True))

    if not updated:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    return EnrollmentRecord(**updated)


@app.delete("/api/student/{user_id}/courses/{enrollment_id}")
async def delete_student_enrollment(
    user_id: str,
    enrollment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a course enrollment."""
    # Verify access
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_student_service()

    success = service.delete_enrollment(enrollment_id)

    if not success:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    return {"success": True, "message": "Enrollment deleted"}


# --- Milestone Endpoints ---

@app.get("/api/student/{user_id}/milestones", response_model=List[Milestone])
async def get_student_milestones(
    user_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get degree progress milestones for a student."""
    # Verify access
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_student_service()

    student = service.get_student(user_id)
    if not student and is_debug_mode():
        student = _get_demo_profile(user_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    milestones = service.get_milestones(user_id)

    # In demo mode, return default milestones if Firestore is empty
    if not milestones and is_debug_mode() and _get_demo_profile(user_id):
        cr = _get_demo_profile(user_id).get("creditsEarned", 0)
        declared = _get_demo_profile(user_id).get("declared", False)
        milestones = [
            {"id": f"{user_id}-m0", "studentId": user_id, "type": "degree", "title": "Complete Business Core", "description": "BUAD 201, 202, 231, 310, 302, and ECON 101, 102", "completed": cr >= 39, "order": 0},
            {"id": f"{user_id}-m1", "studentId": user_id, "type": "degree", "title": "Complete 39 Credits", "description": "Minimum credits to declare major", "completed": cr >= 39, "order": 1},
            {"id": f"{user_id}-m2", "studentId": user_id, "type": "degree", "title": "Declare Major", "description": "Must declare before earning 54 credits", "completed": declared, "order": 2},
            {"id": f"{user_id}-m3", "studentId": user_id, "type": "degree", "title": "Complete 120 Credits", "description": "Total credits required for graduation", "completed": False, "order": 3, "credits": {"current": cr, "required": 120}},
        ]

    return [Milestone(**m) for m in milestones]


@app.put("/api/student/{user_id}/milestones/{milestone_id}", response_model=Milestone)
async def update_milestone_progress(
    user_id: str,
    milestone_id: str,
    progress: MilestoneProgressUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a student's progress on a milestone."""
    # Verify access
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_student_service()

    student = service.get_student(user_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    result = service.update_milestone_progress(
        user_id, milestone_id, progress.completed, progress.notes
    )

    return {"id": milestone_id, "completed": progress.completed, "notes": progress.notes, **result}


@app.get("/api/milestones", response_model=List[Milestone])
async def get_degree_milestones():
    """Get all standard degree milestones."""
    service = get_student_service()
    milestones = service.get_degree_milestones()

    return [Milestone(**m) for m in milestones]


# --- Advisor Portal Endpoints ---

@app.get("/api/advisor/{advisor_id}/profile")
async def get_advisor_profile(
    advisor_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get an advisor's profile."""
    if not verify_user_access(current_user, advisor_id):
        raise HTTPException(status_code=403, detail="Access denied")

    db = get_firestore_client()
    doc = db.collection("students").document(advisor_id).get()
    if not doc.exists:
        # In debug mode, return in-memory fallback for the demo advisor
        if is_debug_mode() and advisor_id == DEMO_ADVISOR_ID:
            return {"id": advisor_id, **{k: v for k, v in DEMO_ADVISOR_PROFILE.items() if k != "userId"}}
        raise HTTPException(status_code=404, detail="Advisor not found")

    data = doc.to_dict()
    return {
        "id": advisor_id,
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "department": data.get("department", ""),
        "office": data.get("office", ""),
        "phone": data.get("phone", ""),
    }


@app.get("/api/advisor/{advisor_id}/advisees", response_model=List[AdvisorAssignment])
async def get_advisees(
    advisor_id: str,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """Get all students assigned to an advisor."""
    # Advisors can only view their own advisees
    if current_user.uid != advisor_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_advisor_service()
    advisees = service.get_advisees(advisor_id)

    # In demo mode, if Firestore has no assignments, serve all demo students
    if not advisees and is_debug_mode() and advisor_id == DEMO_ADVISOR_ID:
        from datetime import datetime
        advisees = []
        for s in DEMO_STUDENTS:
            profile = _DEMO_PROFILES[s["id"]]
            advisees.append(AdvisorAssignment(
                id=f"{DEMO_ADVISOR_ID}_{s['id']}",
                advisorId=DEMO_ADVISOR_ID,
                studentId=s["id"],
                assignedDate=datetime.utcnow().isoformat(),
                student=StudentProfile(
                    id=s["id"], userId=s["id"], name=s["name"], email=s["email"],
                    classYear=s["classYear"], gpa=profile["gpa"],
                    creditsEarned=profile["creditsEarned"], declared=s["declared"],
                    intendedMajor=s["intendedMajor"], apCredits=s["apCredits"],
                    holds=[],
                ),
            ))

    return advisees


@app.post("/api/advisor/{advisor_id}/advisees", response_model=AdvisorAssignment)
async def assign_advisee(
    advisor_id: str,
    request: AssignAdviseeRequest,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """Assign a student to an advisor."""
    # Advisors can only assign to themselves
    if current_user.uid != advisor_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_advisor_service()

    # Verify student exists
    student_service = get_student_service()
    student = student_service.get_student(request.studentId)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    assignment = service.assign_advisee(advisor_id, request.studentId)
    return assignment


@app.delete("/api/advisor/{advisor_id}/advisees/{student_id}")
async def remove_advisee(
    advisor_id: str,
    student_id: str,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """Remove a student from an advisor's list."""
    # Advisors can only remove from their own list
    if current_user.uid != advisor_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_advisor_service()

    success = service.remove_advisee(advisor_id, student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Assignment not found")

    return {"success": True, "message": "Advisee removed"}


@app.get("/api/advisor/{advisor_id}/advisees/{student_id}", response_model=AdviseeResponse)
async def get_advisee(
    advisor_id: str,
    student_id: str,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """Get a specific advisee's details."""
    # Advisors can only view their own advisees
    if current_user.uid != advisor_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_advisor_service()

    advisee = service.get_advisee(advisor_id, student_id)
    if not advisee:
        raise HTTPException(status_code=404, detail="Advisee not found or not assigned to this advisor")

    return AdviseeResponse(**advisee)


@app.get("/api/advisor/{advisor_id}/advisees/{student_id}/notes", response_model=List[AdvisorNote])
async def get_advisee_notes(
    advisor_id: str,
    student_id: str,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """Get all notes for an advisee."""
    # Advisors can only view their own notes
    if current_user.uid != advisor_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_advisor_service()

    # Verify assignment exists
    advisee = service.get_advisee(advisor_id, student_id)
    if not advisee:
        raise HTTPException(status_code=404, detail="Advisee not found or not assigned to this advisor")

    notes = service.get_notes(advisor_id, student_id)
    return [AdvisorNote(**n) for n in notes]


@app.post("/api/advisor/{advisor_id}/advisees/{student_id}/notes", response_model=AdvisorNote)
async def create_advisee_note(
    advisor_id: str,
    student_id: str,
    note_data: NoteCreate,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """Create a new note for an advisee."""
    # Advisors can only create notes for their own advisees
    if current_user.uid != advisor_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_advisor_service()

    # Verify assignment exists
    advisee = service.get_advisee(advisor_id, student_id)
    if not advisee:
        raise HTTPException(status_code=404, detail="Advisee not found or not assigned to this advisor")

    note = service.create_note(advisor_id, student_id, note_data.note, note_data.visibility)
    return AdvisorNote(**note)


@app.put("/api/advisor/{advisor_id}/advisees/{student_id}/notes/{note_id}", response_model=AdvisorNote)
async def update_advisee_note(
    advisor_id: str,
    student_id: str,
    note_id: str,
    note_data: NoteUpdate,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """Update a note for an advisee."""
    # Advisors can only update their own notes
    if current_user.uid != advisor_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_advisor_service()

    updated = service.update_note(advisor_id, note_id, note_data.note, note_data.visibility)
    if not updated:
        raise HTTPException(status_code=404, detail="Note not found or not owned by this advisor")

    return AdvisorNote(**updated)


@app.delete("/api/advisor/{advisor_id}/advisees/{student_id}/notes/{note_id}")
async def delete_advisee_note(
    advisor_id: str,
    student_id: str,
    note_id: str,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """Delete a note for an advisee."""
    # Advisors can only delete their own notes
    if current_user.uid != advisor_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_advisor_service()

    success = service.delete_note(advisor_id, note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found or not owned by this advisor")

    return {"success": True, "message": "Note deleted"}


@app.get("/api/advisor/{advisor_id}/alerts", response_model=List[AdvisorAlert])
async def get_advisor_alerts(
    advisor_id: str,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """Get alerts for an advisor's advisees."""
    # Advisors can only view their own alerts
    if current_user.uid != advisor_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    service = get_advisor_service()
    alerts = service.get_alerts(advisor_id)

    return [AdvisorAlert(**a) for a in alerts]


@app.get("/api/advisor/common-questions")
async def get_common_questions(
    limit: int = 5,
    current_user: AuthenticatedUser = Depends(get_current_advisor)
):
    """
    Get the most commonly asked student questions, clustered by similarity.

    Uses stored question embeddings to find groups of similar questions
    and returns a representative question for each cluster with a count.
    """
    service = get_common_questions_service()
    questions = service.get_common_questions(limit=limit)
    return {"questions": questions}


# --- Schedule Validation & Prerequisite Endpoints ---

@app.post("/api/student/validate-schedule", response_model=ValidateScheduleResponse)
async def validate_schedule(
    request: ValidateScheduleRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Validate a proposed course schedule for a student.

    Checks:
    - Prerequisites are met
    - Credit limits (12-18 normal, 18+ overload)
    - Workload balance
    - Risk flags

    Returns validation result with score and recommendations.
    """
    # Verify access
    if not verify_user_access(current_user, request.studentId):
        raise HTTPException(status_code=403, detail="Access denied")

    engine = get_prerequisite_engine()

    # Verify student exists
    student_service = get_student_service()
    student = student_service.get_student(request.studentId)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Validate schedule
    result = engine.validate_schedule(request.studentId, request.proposedCourses)

    # Convert risk flags to proper format
    risk_flags = []
    for flag in result.risk_flags:
        # Handle severity which may be a RiskLevel enum, string, or dict
        severity_raw = flag.get("severity", "low")
        if hasattr(severity_raw, 'value'):  # It's an Enum
            severity = severity_raw.value
        elif isinstance(severity_raw, str):
            severity = severity_raw
        else:
            severity = "low"

        risk_flags.append(RiskFlagResponse(
            type=flag.get("type", ""),
            severity=severity,
            message=flag.get("message", ""),
            course_code=flag.get("course_code"),
            details=flag.get("details", {})
        ))

    # Convert course details
    course_details = []
    for detail in result.course_details:
        course_details.append(CourseValidationDetail(
            code=detail.get("code", ""),
            name=detail.get("name", ""),
            credits=detail.get("credits", 3),
            prerequisites=detail.get("prerequisites", []),
            prerequisites_met=detail.get("prerequisites_met", True),
            missing_prerequisites=detail.get("missing_prerequisites", [])
        ))

    return ValidateScheduleResponse(
        valid=result.valid,
        warnings=result.warnings,
        errors=result.errors,
        missingPrereqs=result.missing_prereqs,
        riskFlags=risk_flags,
        scheduleScore=ScheduleScoreResponse(**result.schedule_score),
        totalCredits=result.total_credits,
        courseDetails=course_details
    )


@app.get("/api/student/{user_id}/eligible-courses", response_model=List[EligibleCourseResponse])
async def get_eligible_courses(
    user_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get all courses a student is eligible to take based on completed prerequisites.
    """
    # Verify access
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    engine = get_prerequisite_engine()

    # Verify student exists
    student_service = get_student_service()
    student = student_service.get_student(user_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    eligible = engine.get_eligible_courses(user_id)

    return [EligibleCourseResponse(**course) for course in eligible]


@app.get("/api/degree-requirements")
async def get_degree_requirements():
    """Return structured degree requirements for the Mason School of Business."""
    from scrapers.curriculum_scraper import load_curriculum_data
    data = load_curriculum_data()
    if data:
        return data
    # Fallback: return hardcoded structure from prerequisite engine
    engine = get_prerequisite_engine()
    return {
        "prerequisites": {
            "name": "Prerequisites for Admission to Business Major",
            "courses": [
                {"code": "ECON 101", "title": "Principles of Microeconomics", "credits": 3},
                {"code": "ECON 102", "title": "Principles of Macroeconomics", "credits": 3},
                {"code": "MATH 108", "title": "Calculus for the Social Sciences (or MATH 111/131)", "credits": 3},
                {"code": "BUAD 203", "title": "Introduction to Accounting", "credits": 3},
                {"code": "BUAD 231", "title": "Business Statistics", "credits": 3},
            ],
        },
        "core_curriculum": [
            {
                "name": "Foundation Semester — Integrated Core",
                "courses": [
                    {"code": "BUAD 300", "title": "Business Communication I", "credits": 1},
                    {"code": "BUAD 311", "title": "Financial Management", "credits": 3},
                    {"code": "BUAD 323", "title": "Management of Organizations", "credits": 3},
                    {"code": "BUAD 330", "title": "Business Communication II", "credits": 1},
                    {"code": "BUAD 350", "title": "Marketing Management", "credits": 3},
                ],
            },
            {
                "name": "Upper Level Core",
                "courses": [
                    {"code": "BUAD 317", "title": "Operations Management", "credits": 3},
                    {"code": "BUAD 343", "title": "Business Law", "credits": 2},
                    {"code": "BUAD 351", "title": "Marketing Analytics", "credits": 1.5},
                    {"code": "BUAD 352", "title": "Marketing Communication", "credits": 1.5},
                    {"code": "BUAD 414", "title": "Strategic Management", "credits": 3},
                ],
            },
        ],
        "majors": [
            {
                "name": "Accounting", "credits_required": 15,
                "required_courses": [
                    {"code": "BUAD 301", "title": "Intermediate Financial Accounting I", "credits": 3},
                    {"code": "BUAD 302", "title": "Intermediate Financial Accounting II", "credits": 3},
                    {"code": "BUAD 303", "title": "Cost Accounting", "credits": 3},
                    {"code": "BUAD 404", "title": "Auditing", "credits": 3},
                    {"code": "BUAD 405", "title": "Federal Tax", "credits": 3},
                ],
                "elective_courses": [
                    {"code": "BUAD 304", "title": "Accounting Information Systems", "credits": 3},
                    {"code": "BUAD 305", "title": "Advanced Accounting", "credits": 3},
                    {"code": "BUAD 306", "title": "Forensic Accounting", "credits": 3},
                ],
                "electives_required": 1,
            },
            {
                "name": "Business Analytics — Data Science", "credits_required": 12,
                "required_courses": [
                    {"code": "BUAD 466", "title": "Business Analytics I", "credits": 3},
                    {"code": "BUAD 467", "title": "Business Analytics II", "credits": 3},
                    {"code": "BUAD 468", "title": "Business Analytics III", "credits": 3},
                ],
                "elective_courses": [
                    {"code": "BUAD 461", "title": "Supply Chain Analytics", "credits": 3},
                    {"code": "BUAD 463", "title": "Operations Analytics", "credits": 3},
                ],
                "electives_required": 1,
            },
            {
                "name": "Finance", "credits_required": 13,
                "required_courses": [
                    {"code": "BUAD 327", "title": "Investments", "credits": 3},
                    {"code": "BUAD 329", "title": "Corporate Finance", "credits": 4},
                ],
                "elective_courses": [
                    {"code": "BUAD 422", "title": "Financial Modeling", "credits": 3},
                    {"code": "BUAD 423", "title": "Derivatives", "credits": 3},
                    {"code": "BUAD 424", "title": "Fixed Income", "credits": 3},
                    {"code": "BUAD 427", "title": "Advanced Corporate Finance", "credits": 3},
                ],
                "electives_required": 2,
            },
            {
                "name": "Marketing", "credits_required": 12,
                "required_courses": [
                    {"code": "BUAD 452", "title": "Consumer Behavior", "credits": 3},
                    {"code": "BUAD 446", "title": "Marketing Research", "credits": 3},
                ],
                "elective_courses": [
                    {"code": "BUAD 445", "title": "Digital Marketing", "credits": 3},
                    {"code": "BUAD 448", "title": "Brand Management", "credits": 3},
                    {"code": "BUAD 450", "title": "Sales Management", "credits": 3},
                    {"code": "BUAD 451", "title": "Product Management", "credits": 3},
                    {"code": "BUAD 453", "title": "Retail Management", "credits": 3},
                    {"code": "BUAD 456", "title": "International Marketing", "credits": 3},
                ],
                "electives_required": 2,
            },
        ],
        "total_credits_required": 120,
    }


@app.get("/api/courses/{course_code}/prerequisites", response_model=PrerequisiteInfoResponse)
async def get_course_prerequisites(course_code: str):
    """
    Get prerequisite information for a specific course.
    """
    engine = get_prerequisite_engine()

    # Handle URL-encoded course codes
    course_code = course_code.replace("_", " ")

    prereq_info = engine.get_prerequisites(course_code)

    if not prereq_info:
        raise HTTPException(
            status_code=404,
            detail=f"Prerequisite information not found for {course_code}"
        )

    return PrerequisiteInfoResponse(
        course_code=prereq_info.course_code,
        course_name=prereq_info.course_name,
        credits=prereq_info.credits,
        prerequisites=prereq_info.prerequisites,
        semester_offered=prereq_info.semester_offered
    )


@app.get("/api/courses/{course_code}/prerequisite-chain")
async def get_prerequisite_chain(course_code: str):
    """
    Get the full prerequisite chain for a course (prerequisites of prerequisites).
    """
    engine = get_prerequisite_engine()

    # Handle URL-encoded course codes
    course_code = course_code.replace("_", " ")

    chain = engine.get_prerequisite_chain(course_code)

    return chain


# --- Conversation Endpoints ---

@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new conversation for a student."""
    if not verify_user_access(current_user, request.studentId):
        raise HTTPException(status_code=403, detail="Access denied")

    conversation_service = get_conversation_service()
    conversation = conversation_service.create_conversation(
        user_id=current_user.uid,
        student_id=request.studentId,
        user_role=current_user.role.value,
        title=request.title
    )

    return ConversationResponse(**conversation)


@app.get("/api/student/{user_id}/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """List conversations for a student, most recent first."""
    if not verify_user_access(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    conversation_service = get_conversation_service()
    conversations = conversation_service.list_conversations(user_id, limit, offset)

    return ConversationListResponse(
        conversations=[ConversationResponse(**c) for c in conversations],
        total=len(conversations)
    )


@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get a single conversation by ID."""
    conversation_service = get_conversation_service()
    conversation = conversation_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not verify_user_access(current_user, conversation["studentId"]):
        raise HTTPException(status_code=403, detail="Access denied")

    return ConversationResponse(**conversation)


@app.get("/api/conversations/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get messages for a conversation in chronological order."""
    conversation_service = get_conversation_service()
    conversation = conversation_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not verify_user_access(current_user, conversation["studentId"]):
        raise HTTPException(status_code=403, detail="Access denied")

    messages = conversation_service.get_messages(conversation_id, limit, offset)

    return ConversationMessagesResponse(
        messages=[ConversationMessageResponse(**m) for m in messages],
        total=len(messages)
    )


@app.put("/api/conversations/{conversation_id}/title", response_model=ConversationResponse)
async def update_conversation_title(
    conversation_id: str,
    request: ConversationTitleUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a conversation's title."""
    conversation_service = get_conversation_service()
    conversation = conversation_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not verify_user_access(current_user, conversation["studentId"]):
        raise HTTPException(status_code=403, detail="Access denied")

    updated = conversation_service.update_conversation_title(conversation_id, request.title)
    return ConversationResponse(**updated)


@app.put("/api/conversations/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Archive a conversation."""
    conversation_service = get_conversation_service()
    conversation = conversation_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not verify_user_access(current_user, conversation["studentId"]):
        raise HTTPException(status_code=403, detail="Access denied")

    updated = conversation_service.archive_conversation(conversation_id)
    return ConversationResponse(**updated)


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a conversation and all its messages permanently."""
    conversation_service = get_conversation_service()
    conversation = conversation_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not verify_user_access(current_user, conversation["studentId"]):
        raise HTTPException(status_code=403, detail="Access denied")

    conversation_service.delete_conversation(conversation_id)
    return {"success": True, "message": "Conversation deleted"}


# --- AI Chat Endpoints ---

@app.post("/api/chat/message", response_model=ChatMessageResponse)
async def chat_message(
    request: ChatMessageRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Send a message to the AI academic advisor.

    Features:
    - RAG-powered responses using curriculum and policy documents
    - Citation extraction from source materials
    - Risk identification (academic, deadline, prerequisite issues)
    - Recommended next steps

    Requires authentication and access to the student's profile.
    """
    # Verify access
    if not verify_user_access(current_user, request.studentId):
        raise HTTPException(status_code=403, detail="Access denied")

    # Advisors chatting with their own ID don't need a student record
    is_advisor_self = current_user.is_advisor and current_user.uid == request.studentId

    if not is_advisor_self:
        # Verify student exists
        student_service = get_student_service()
        student = student_service.get_student(request.studentId)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

    try:
        conversation_service = get_conversation_service()
        conversation_id = request.conversationId

        # Resolve conversation and chat history
        if conversation_id:
            # Persistent mode: load history from DB
            conversation = conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if not verify_user_access(current_user, conversation["studentId"]):
                raise HTTPException(status_code=403, detail="Access denied to conversation")

            stored_messages = conversation_service.get_messages(conversation_id, limit=20)
            chat_history = [
                {"role": m["role"], "content": m["content"]}
                for m in stored_messages
            ]
        else:
            # Auto-create a new conversation
            conversation = conversation_service.create_conversation(
                user_id=current_user.uid,
                student_id=request.studentId,
                user_role=current_user.role.value
            )
            conversation_id = conversation["id"]
            chat_history = request.chatHistory

        chat_service = get_chat_service()
        # When an advisor chats with their own ID (general advising mode),
        # pass None as student_id so _get_advisor_context returns the full
        # advisee overview instead of trying to look up the advisor as a student.
        chat_student_id = None if is_advisor_self else request.studentId
        response = chat_service.chat(
            student_id=chat_student_id,
            message=request.message,
            chat_history=chat_history,
            user_id=current_user.uid,
            user_role=current_user.role.value
        )

        # Persist both messages
        conversation_service.add_message(conversation_id, "user", request.message)
        conversation_service.add_message(
            conversation_id, "assistant", response.content,
            citations=[
                {"source": c.source, "excerpt": c.excerpt, "relevance": c.relevance}
                for c in response.citations
            ],
            risks=[
                {"type": r.type, "severity": r.severity, "message": r.message}
                for r in response.risks
            ],
            next_steps=[
                {"action": n.action, "priority": n.priority, "deadline": n.deadline}
                for n in response.nextSteps
            ]
        )

        # Store question embedding for common-questions clustering
        try:
            from google.cloud.firestore_v1.vector import Vector
            from datetime import datetime as dt
            emb_service = get_embeddings_service()
            embedding = emb_service.generate_embedding(request.message)
            db = get_firestore_client()
            db.collection("question_embeddings").add({
                "text": request.message,
                "embedding": Vector(embedding),
                "conversationId": conversation_id,
                "studentId": request.studentId,
                "createdAt": dt.utcnow().isoformat()
            })
        except Exception:
            pass  # Don't fail the chat if embedding storage fails

        return ChatMessageResponse(
            content=response.content,
            citations=[
                ChatCitation(
                    source=c.source,
                    excerpt=c.excerpt,
                    relevance=c.relevance
                )
                for c in response.citations
            ],
            risks=[
                ChatRiskFlag(
                    type=r.type,
                    severity=r.severity,
                    message=r.message
                )
                for r in response.risks
            ],
            nextSteps=[
                ChatNextStep(
                    action=n.action,
                    priority=n.priority,
                    deadline=n.deadline
                )
                for n in response.nextSteps
            ],
            conversationId=conversation_id
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Chat service unavailable: {str(e)}"
        )


# Helpers
def _format_course(data: dict) -> CourseResponse:
    """Format course data for API response"""
    sections = []
    for s in data.get("sections", []):
        meeting = parse_meeting_times_raw(s.get("meeting_times_raw", ""))
        sections.append(SectionResponse(
            crn=s.get("crn", ""),
            section_number=s.get("section_number", ""),
            instructor=s.get("instructor", ""),
            status=s.get("status", "UNKNOWN"),
            capacity=s.get("capacity", 0),
            enrolled=s.get("enrolled", 0),
            available=s.get("available", 0),
            meeting_days=meeting["days"] or s.get("meeting_days", ""),
            meeting_time=meeting["time"] or s.get("meeting_time", ""),
            building=s.get("building", ""),
            room=s.get("room", ""),
        ))

    return CourseResponse(
        course_code=data.get("course_code", ""),
        subject_code=data.get("subject_code", ""),
        course_number=data.get("course_number", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        credits=data.get("credits", 0),
        attributes=data.get("attributes", []),
        prerequisites=data.get("prerequisites", []),
        sections=sections
    )


# --- Gaze/Mouse Tracking Endpoints (debug mode only) ---

class TrackingSessionRequest(BaseModel):
    userId: str = "anonymous"
    viewportWidth: int = 1920
    viewportHeight: int = 1080

class TrackingEvent(BaseModel):
    x: int
    y: int
    timestamp: float
    type: str = "mouse"
    confidence: float = 1.0

class TrackingSnapshotRequest(BaseModel):
    sessionId: str
    pageUrl: str
    screenshot: str  # base64 PNG
    events: List[TrackingEvent]


def _require_debug_tracking():
    if not getattr(app.state, "debug_tracking", False):
        raise HTTPException(status_code=404, detail="Not found")


@app.post("/api/tracking/sessions")
async def create_tracking_session(request: TrackingSessionRequest):
    """Create a new tracking session."""
    _require_debug_tracking()
    from services.tracking import get_tracking_service
    service = get_tracking_service()
    session = service.create_session(
        user_id=request.userId,
        viewport_width=request.viewportWidth,
        viewport_height=request.viewportHeight,
    )
    return session


@app.post("/api/tracking/snapshot")
async def save_tracking_snapshot(request: TrackingSnapshotRequest):
    """Save a page snapshot: composite heatmap onto screenshot and save as PNG."""
    _require_debug_tracking()
    from services.tracking import get_tracking_service
    service = get_tracking_service()
    filename = service.save_snapshot(
        session_id=request.sessionId,
        page_url=request.pageUrl,
        screenshot_b64=request.screenshot,
        events=[e.model_dump() for e in request.events],
    )
    if not filename:
        return {"saved": False, "filename": None}
    return {"saved": True, "filename": filename}


@app.get("/api/tracking/sessions")
async def list_tracking_sessions(user_id: str = None):
    """List tracking sessions."""
    _require_debug_tracking()
    from services.tracking import get_tracking_service
    service = get_tracking_service()
    return service.get_sessions(user_id=user_id)


@app.post("/api/tracking/sessions/{session_id}/end")
async def end_tracking_session(session_id: str):
    """End a tracking session."""
    _require_debug_tracking()
    from services.tracking import get_tracking_service
    service = get_tracking_service()
    service.end_session(session_id)
    return {"status": "ended"}


# Main

def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="W&M Course Catalog API Server")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--no-scheduler", action="store_true", help="Disable background scheduler")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (bypasses auth, creates demo data)")
    parser.add_argument("--debugtracking", action="store_true", help="Enable gaze/mouse tracking endpoints")

    args = parser.parse_args()

    app.state.enable_scheduler = not args.no_scheduler
    app.state.debug_mode = args.debug
    app.state.debug_tracking = args.debugtracking

    print(f"[Server] Starting on http://{args.host}:{args.port}")
    print(f"[Server] Scheduler: {'enabled' if app.state.enable_scheduler else 'disabled'}")
    if args.debug:
        print(f"[Server] *** DEBUG MODE ENABLED - Auth bypassed, demo data created ***")
    if args.debugtracking:
        print(f"[Server] *** TRACKING ENABLED - Gaze/mouse tracking endpoints active ***")

    uvicorn.run(
        "server:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
