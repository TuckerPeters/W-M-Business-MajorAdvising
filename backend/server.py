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

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import initialize_firebase, get_firestore_client
from core.semester import SemesterManager
from services.firebase import get_course_service


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
