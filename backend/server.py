"""
FastAPI Server for W&M Course Catalog API

Provides REST endpoints for the frontend to query course data.
Runs the scheduler in the background for automatic updates.

Usage:
    python server.py                    # Run server on port 8000
    python server.py --port 3001        # Custom port
    python server.py --no-scheduler     # Disable background updates
"""

import asyncio
import argparse
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import initialize_firebase, get_firestore_client
from core.semester import SemesterManager
from core.auth import (
    AuthenticatedUser,
    get_current_user,
    get_current_advisor,
    verify_user_access
)
from services.firebase import get_course_service
from services.student import get_student_service
from services.advisor import get_advisor_service
from services.prerequisites import get_prerequisite_engine
from services.chat import get_chat_service
from services.conversation import get_conversation_service


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
    term: str
    grade: Optional[str] = None
    status: str = "planned"
    credits: int = 3


class EnrollmentCreate(BaseModel):
    courseCode: str
    term: str
    grade: Optional[str] = None
    status: str = "planned"
    credits: int = 3


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


# App Lifespan (startup/shutdown)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown"""
    global scheduler_task

    # Startup
    print("[Server] Initializing Firebase...")
    initialize_firebase()

    # Start scheduler if enabled
    if app.state.enable_scheduler:
        print("[Server] Starting background scheduler...")
        scheduler_task = asyncio.create_task(run_background_scheduler())

    print("[Server] Ready!")

    yield

    # Shutdown
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # Add your production frontend URL here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default: enable scheduler
app.state.enable_scheduler = True


# API Endpoints

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        term_code=SemesterManager.get_trackable_term_code(),
        semester=SemesterManager.get_trackable_display_name(),
        is_registration_period=SemesterManager.is_registration_period()
    )


@app.get("/api/health", response_model=HealthResponse)
async def api_health():
    """API health check"""
    return await health_check()


@app.get("/api/courses", response_model=CourseListResponse)
async def list_courses(
    subject: Optional[str] = Query(None, description="Filter by subject code (e.g., CSCI)"),
    limit: int = Query(100, ge=1, le=500, description="Max courses to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List all courses, optionally filtered by subject.
    """
    db = get_firestore_client()
    term_code = SemesterManager.get_trackable_term_code()

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
        raise HTTPException(status_code=404, detail="Student not found")

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
        raise HTTPException(status_code=404, detail="Student not found")

    courses = service.get_student_courses(user_id)

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
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    milestones = service.get_student_milestone_progress(user_id)

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
        response = chat_service.chat(
            student_id=request.studentId,
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
        sections.append(SectionResponse(
            crn=s.get("crn", ""),
            section_number=s.get("section_number", ""),
            instructor=s.get("instructor", ""),
            status=s.get("status", "UNKNOWN"),
            capacity=s.get("capacity", 0),
            enrolled=s.get("enrolled", 0),
            available=s.get("available", 0),
            meeting_days=s.get("meeting_days", ""),
            meeting_time=s.get("meeting_time", ""),
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
        sections=sections
    )


# Main

def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="W&M Course Catalog API Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--no-scheduler", action="store_true", help="Disable background scheduler")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    app.state.enable_scheduler = not args.no_scheduler

    print(f"[Server] Starting on http://{args.host}:{args.port}")
    print(f"[Server] Scheduler: {'enabled' if app.state.enable_scheduler else 'disabled'}")

    uvicorn.run(
        "server:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
