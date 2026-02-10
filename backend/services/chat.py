"""
AI Chat Service for Academic Advising

Provides RAG-powered chat for student advising questions.
Integrates with policy documents and curriculum data.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .embeddings import get_embeddings_service, SearchResult
from .student import get_student_service
from .advisor import get_advisor_service
from .prerequisites import get_prerequisite_engine
from scrapers.curriculum_scraper import load_curriculum_data


# User roles for authorization
USER_ROLE_STUDENT = "student"
USER_ROLE_ADVISOR = "advisor"
USER_ROLE_ADMIN = "admin"


@dataclass
class Citation:
    """A citation from a source document."""
    source: str
    excerpt: str
    relevance: float


@dataclass
class RiskFlag:
    """A risk or concern identified in the conversation."""
    type: str  # academic, deadline, prerequisite, workload, etc.
    severity: str  # low, medium, high
    message: str


@dataclass
class NextStep:
    """A recommended next step for the student."""
    action: str
    priority: str  # low, medium, high
    deadline: Optional[str] = None


@dataclass
class ChatMessage:
    """A message in the chat history."""
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[str] = None


@dataclass
class ChatResponse:
    """Response from the chat service."""
    content: str
    citations: List[Citation] = field(default_factory=list)
    risks: List[RiskFlag] = field(default_factory=list)
    nextSteps: List[NextStep] = field(default_factory=list)


SYSTEM_PROMPT = """You are an AI academic advisor for the William & Mary Mason School of Business.
Your role is to help students with questions about:
- Major requirements and course selection
- Prerequisites and course sequencing
- Academic policies and procedures
- Career planning related to their major
- Registration and enrollment questions

CRITICAL RULES FOR COURSE RECOMMENDATIONS:
1. NEVER recommend a course the student has already COMPLETED (check the COMPLETED COURSES section)
2. NEVER recommend a course the student is CURRENTLY ENROLLED in (check CURRENT ENROLLMENT section)
3. ALWAYS check prerequisites before recommending - only recommend courses where the student has completed ALL prerequisites
4. When building a semester schedule, recommend 12-18 credits (typically 4-6 courses)
5. Prioritize required courses for the student's major before electives
6. Consider course sequencing - some courses should be taken before others

SCHEDULING & SECTION RECOMMENDATIONS:
7. When the student has current courses with schedule info (days/times), CHECK FOR TIME CONFLICTS before recommending new sections
8. If recommending a specific section, include: section number, meeting days (MWF, TR, etc.), time slot, location, and instructor when available
9. Avoid recommending sections that overlap with the student's current schedule
10. When multiple sections exist, recommend ones that fit the student's existing schedule
11. Consider back-to-back classes - allow reasonable travel time between buildings
12. If the student has early morning classes, avoid recommending additional 8am sections unless necessary

Guidelines:
1. Be helpful, accurate, and supportive
2. When citing policies or requirements, reference the specific source
3. If you're unsure about something, say so and recommend the student speak with a human advisor
4. Identify any risks or concerns (academic probation, missed deadlines, prerequisite issues)
5. Suggest concrete next steps when appropriate
6. Keep responses concise but complete

You have access to curriculum data and policy documents. Use this context to provide accurate answers.
Always prioritize official W&M Business School policies over general knowledge.

IMPORTANT: Format your response as JSON with the following structure:
{
    "content": "Your main response text here",
    "citations": [{"source": "source name", "excerpt": "relevant quote"}],
    "risks": [{"type": "risk type", "severity": "low|medium|high", "message": "description"}],
    "nextSteps": [{"action": "what to do", "priority": "low|medium|high", "deadline": "optional date"}]
}
"""


class ChatService:
    """
    AI Chat Service with RAG for academic advising.

    Features:
    - Context-aware responses using RAG
    - Citation extraction from source documents
    - Risk identification
    - Next step recommendations
    """

    MODEL = "gpt-4o-mini"  # Cost-effective for chat
    MAX_CONTEXT_RESULTS = 5
    MAX_HISTORY_MESSAGES = 10

    def __init__(self):
        self._openai_client = None
        self._embeddings = None
        self._curriculum_loaded = False
        self._initialized = False

    def _ensure_initialized(self):
        """Initialize services on first use."""
        if self._initialized:
            return

        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI package not installed. Run: pip install openai")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")

        self._openai_client = OpenAI(api_key=api_key)
        self._embeddings = get_embeddings_service()
        self._initialized = True

        # Load curriculum data into vector store if not already done
        self._load_curriculum_if_needed()

    def _load_curriculum_if_needed(self):
        """Load curriculum data into vector store."""
        if self._curriculum_loaded:
            return

        # Check if we already have documents
        if self._embeddings.get_document_count() > 0:
            self._curriculum_loaded = True
            return

        curriculum = load_curriculum_data()
        if not curriculum:
            print("Warning: No curriculum data available for chat context")
            self._curriculum_loaded = True
            return

        documents = []

        # Add core curriculum
        for group in curriculum.get("core_curriculum", []):
            desc = group.get("description", "Core Curriculum")
            courses = group.get("courses", [])
            if courses:
                content = f"Core Curriculum - {desc}:\n"
                for c in courses:
                    prereqs = ", ".join(c.get("prerequisites", [])) or "None"
                    content += f"- {c['code']}: {c['name']} ({c.get('credits', 3)} credits, Prerequisites: {prereqs})\n"
                documents.append({
                    "content": content,
                    "source": f"Core Curriculum - {desc}",
                    "metadata": {"type": "curriculum", "section": "core"}
                })

        # Add majors
        for major in curriculum.get("majors", []):
            major_name = major.get("name", "Unknown Major")
            credits = major.get("credits_required", 0)

            # Required courses
            for group in major.get("required_courses", []):
                desc = group.get("description", "Required")
                courses = group.get("courses", [])
                if courses:
                    content = f"{major_name} Major - {desc} (Total: {credits} credits required):\n"
                    for c in courses:
                        prereqs = ", ".join(c.get("prerequisites", [])) or "None"
                        content += f"- {c['code']}: {c['name']} ({c.get('credits', 3)} credits, Prerequisites: {prereqs})\n"
                    documents.append({
                        "content": content,
                        "source": f"{major_name} Major Requirements",
                        "metadata": {"type": "curriculum", "section": "major", "major": major_name}
                    })

            # Electives
            for group in major.get("elective_courses", []):
                desc = group.get("description", "Electives")
                courses = group.get("courses", [])
                if courses:
                    content = f"{major_name} Major - {desc}:\n"
                    for c in courses:
                        prereqs = ", ".join(c.get("prerequisites", [])) or "None"
                        content += f"- {c['code']}: {c['name']} ({c.get('credits', 3)} credits, Prerequisites: {prereqs})\n"
                    documents.append({
                        "content": content,
                        "source": f"{major_name} Major Electives",
                        "metadata": {"type": "curriculum", "section": "electives", "major": major_name}
                    })

        # Add concentrations
        for conc in curriculum.get("concentrations", []):
            conc_name = conc.get("name", "Unknown Concentration")
            for group in conc.get("course_groups", []):
                desc = group.get("description", "Courses")
                courses = group.get("courses", [])
                if courses:
                    content = f"{conc_name} Concentration - {desc}:\n"
                    for c in courses:
                        prereqs = ", ".join(c.get("prerequisites", [])) or "None"
                        content += f"- {c['code']}: {c['name']} ({c.get('credits', 3)} credits, Prerequisites: {prereqs})\n"
                    documents.append({
                        "content": content,
                        "source": f"{conc_name} Concentration",
                        "metadata": {"type": "curriculum", "section": "concentration", "concentration": conc_name}
                    })

        # Add general policies
        documents.append({
            "content": """W&M Business School Academic Policies:
- Full-time enrollment: 12-18 credits per semester
- Credit overload (>18 credits) requires advisor approval
- Students must maintain a 2.0 GPA minimum
- Prerequisites must be completed with a C- or better
- Major declaration typically occurs sophomore year
- All business majors must complete the core curriculum
- Senior capstone course required for graduation""",
            "source": "Academic Policies",
            "metadata": {"type": "policy", "section": "general"}
        })

        documents.append({
            "content": """Important Deadlines and Procedures:
- Add/Drop deadline: First two weeks of semester
- Withdrawal deadline: Before 60% of semester completed
- Major declaration: Submit form to Business School advising office
- Graduation application: Due one semester before intended graduation
- Course substitution requests: Require advisor and department approval""",
            "source": "Deadlines and Procedures",
            "metadata": {"type": "policy", "section": "deadlines"}
        })

        if documents:
            self._embeddings.add_documents(documents)
            print(f"Loaded {len(documents)} documents into vector store")

        self._curriculum_loaded = True

    def _get_context(self, query: str) -> str:
        """Retrieve relevant context for the query."""
        results = self._embeddings.search(query, n_results=self.MAX_CONTEXT_RESULTS)

        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results):
            context_parts.append(f"[Source: {result.source}]\n{result.content}")

        return "\n\n---\n\n".join(context_parts)

    def _format_validation_flags(self, student_id: str) -> str:
        """
        Format validation flags for a student as context.

        Returns saved validation flags that were acknowledged by the student,
        including credit load warnings, workload issues, and schedule scores.
        """
        try:
            prereq_engine = get_prerequisite_engine()
            flags = prereq_engine.get_saved_validation_flags(student_id)

            if not flags:
                return ""

            context_parts = []
            context_parts.append("\n=== SCHEDULE VALIDATION ALERTS ===")

            # Show warnings
            warnings = flags.get("warnings", [])
            if warnings:
                for warning in warnings:
                    context_parts.append(f"WARNING: {warning}")

            # Show specific flags
            flag_list = flags.get("flags", [])
            for flag in flag_list:
                severity = flag.get("severity", "low")
                flag_type = flag.get("type", "unknown")
                message = flag.get("message", "")
                term = flag.get("term", "")

                if severity == "critical":
                    context_parts.append(f"CRITICAL ({term}): {message}")
                elif severity == "high":
                    context_parts.append(f"HIGH ({term}): {message}")
                elif severity == "medium":
                    context_parts.append(f"{flag_type} ({term}): {message}")

            # Show credits by term
            credits_by_term = flags.get("total_credits_by_term", {})
            if credits_by_term:
                context_parts.append("\nCredits by Term:")
                for term, credits in credits_by_term.items():
                    context_parts.append(f"  - {term}: {credits} credits")

            # Show schedule score
            schedule_score = flags.get("schedule_score")
            if schedule_score:
                overall = schedule_score.get("overall", 0)
                context_parts.append(f"\nSchedule Quality Score: {overall}/100")
                recommendations = schedule_score.get("recommendations", [])
                if recommendations:
                    context_parts.append("Recommendations:")
                    for rec in recommendations[:3]:  # Limit to top 3
                        context_parts.append(f"  - {rec}")

            return "\n".join(context_parts)

        except Exception as e:
            print(f"Warning: Could not fetch validation flags: {e}")
            return ""

    def _get_student_context(self, student_id: str) -> str:
        """Fetch and format student-specific data as context."""
        try:
            student_service = get_student_service()

            # Get student profile
            profile = student_service.get_student(student_id)
            if not profile:
                return ""

            context_parts = []

            # Basic info
            context_parts.append("=== STUDENT PROFILE ===")
            context_parts.append(f"Name: {profile.get('firstName', '')} {profile.get('lastName', '')}")
            context_parts.append(f"Class Year: {profile.get('classYear', 'Unknown')}")

            if profile.get('gpa') is not None:
                context_parts.append(f"GPA: {profile.get('gpa')}")

            if profile.get('majorDeclared') and profile.get('major'):
                context_parts.append(f"Declared Major: {profile.get('major')}")
            elif profile.get('intendedMajor'):
                context_parts.append(f"Intended Major: {profile.get('intendedMajor')} (not yet declared)")

            if profile.get('concentration'):
                context_parts.append(f"Concentration: {profile.get('concentration')}")

            if profile.get('apCredits'):
                context_parts.append(f"AP Credits: {profile.get('apCredits')}")

            if profile.get('holds'):
                context_parts.append(f"ALERT - Active Holds: {', '.join(profile.get('holds', []))}")

            # Get enrollments
            enrollments = student_service.get_student_courses(student_id)

            # Completed courses
            completed = enrollments.get('completed', [])
            if completed:
                context_parts.append("\n=== COMPLETED COURSES ===")
                for course in completed:
                    grade = course.get('grade', 'N/A')
                    context_parts.append(f"- {course.get('courseCode')}: {course.get('courseName', '')} (Grade: {grade})")

            # Current courses with schedule info
            current = enrollments.get('current', [])
            if current:
                context_parts.append("\n=== CURRENT ENROLLMENT & SCHEDULE ===")
                total_credits = 0
                for course in current:
                    credits = course.get('credits', 3)
                    total_credits += credits

                    # Build course line with scheduling details
                    course_line = f"- {course.get('courseCode')}"
                    if course.get('sectionNumber'):
                        course_line += f" (Section {course.get('sectionNumber')})"
                    course_line += f": {course.get('courseName', '')} ({credits} credits)"
                    context_parts.append(course_line)

                    # Add schedule details if available
                    schedule_parts = []
                    if course.get('meetingDays'):
                        schedule_parts.append(f"Days: {course.get('meetingDays')}")
                    if course.get('startTime') and course.get('endTime'):
                        schedule_parts.append(f"Time: {course.get('startTime')}-{course.get('endTime')}")
                    if course.get('location'):
                        schedule_parts.append(f"Room: {course.get('location')}")
                    if course.get('instructor'):
                        schedule_parts.append(f"Instructor: {course.get('instructor')}")

                    if schedule_parts:
                        context_parts.append(f"  Schedule: {', '.join(schedule_parts)}")

                context_parts.append(f"Total Current Credits: {total_credits}")

            # Planned courses with schedule info
            planned = enrollments.get('planned', [])
            if planned:
                context_parts.append("\n=== PLANNED COURSES ===")
                for course in planned:
                    term = course.get('term', 'TBD')
                    course_line = f"- {course.get('courseCode')}"
                    if course.get('sectionNumber'):
                        course_line += f" (Section {course.get('sectionNumber')})"
                    course_line += f": {course.get('courseName', '')} (Planned: {term})"
                    context_parts.append(course_line)

                    # Add schedule details if available
                    schedule_parts = []
                    if course.get('meetingDays'):
                        schedule_parts.append(f"Days: {course.get('meetingDays')}")
                    if course.get('startTime') and course.get('endTime'):
                        schedule_parts.append(f"Time: {course.get('startTime')}-{course.get('endTime')}")
                    if course.get('location'):
                        schedule_parts.append(f"Room: {course.get('location')}")
                    if course.get('instructor'):
                        schedule_parts.append(f"Instructor: {course.get('instructor')}")

                    if schedule_parts:
                        context_parts.append(f"  Schedule: {', '.join(schedule_parts)}")

            # Include validation flags (credit warnings, workload issues, etc.)
            validation_context = self._format_validation_flags(student_id)
            if validation_context:
                context_parts.append(validation_context)

            return "\n".join(context_parts)

        except Exception as e:
            print(f"Warning: Could not fetch student data: {e}")
            return ""

    def _get_advisor_context(self, advisor_id: str, target_student_id: str = None) -> str:
        """
        Fetch and format advisor's advisees data as context.

        Args:
            advisor_id: The advisor's user ID
            target_student_id: Optional specific student to focus on

        Returns:
            Formatted string with advisee information
        """
        try:
            advisor_service = get_advisor_service()
            student_service = get_student_service()

            # Get all advisees
            advisees = advisor_service.get_advisees(advisor_id)
            if not advisees:
                return ""

            context_parts = []
            context_parts.append("=== ADVISOR VIEW ===")
            context_parts.append(f"You are viewing data as an advisor with {len(advisees)} advisees.\n")

            # If targeting a specific student, show their full details
            if target_student_id:
                student_context = self._get_student_context(target_student_id)
                if student_context:
                    context_parts.append(student_context)

                # Also add summary of other advisees for reference
                other_advisees = [a for a in advisees if a.get('studentId') != target_student_id]
                if other_advisees:
                    context_parts.append("\n=== OTHER ADVISEES (Summary) ===")
                    for advisee in other_advisees[:5]:  # Limit to 5 for context size
                        sid = advisee.get('studentId')
                        profile = student_service.get_student(sid)
                        if profile:
                            name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}"
                            major = profile.get('major') or profile.get('intendedMajor', 'Undeclared')
                            context_parts.append(f"- {name}: {profile.get('classYear', 'N/A')}, {major}")
            else:
                # No specific student - show overview of all advisees
                context_parts.append("=== ALL ADVISEES ===")
                for advisee in advisees:
                    sid = advisee.get('studentId')
                    profile = student_service.get_student(sid)
                    if profile:
                        name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}"
                        class_year = profile.get('classYear', 'N/A')
                        gpa = profile.get('gpa')
                        major = profile.get('major') or profile.get('intendedMajor', 'Undeclared')
                        holds = profile.get('holds', [])

                        line = f"\n**{name}** (ID: {sid})"
                        line += f"\n  Class: {class_year}, Major: {major}"
                        if gpa is not None:
                            line += f", GPA: {gpa}"
                        if holds:
                            line += f"\n  HOLDS: {', '.join(holds)}"

                        # Get brief enrollment info
                        enrollments = student_service.get_student_courses(sid)
                        current = enrollments.get('current', [])
                        if current:
                            credits = sum(c.get('credits', 3) for c in current)
                            line += f"\n  Current: {len(current)} courses ({credits} credits)"

                        # Include validation alerts for each advisee
                        prereq_engine = get_prerequisite_engine()
                        flags = prereq_engine.get_saved_validation_flags(sid)
                        if flags:
                            warnings = flags.get("warnings", [])
                            if warnings:
                                line += f"\n  ALERTS: {len(warnings)} schedule warning(s)"
                                for w in warnings[:2]:  # Show first 2 warnings
                                    line += f"\n    - {w}"

                        context_parts.append(line)

            return "\n".join(context_parts)

        except Exception as e:
            print(f"Warning: Could not fetch advisor data: {e}")
            return ""

    def _parse_response(self, response_text: str) -> ChatResponse:
        """Parse the LLM response into structured format."""
        # Try to extract JSON from response
        try:
            # Look for JSON block
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())

                citations = [
                    Citation(
                        source=c.get("source", ""),
                        excerpt=c.get("excerpt", ""),
                        relevance=c.get("relevance", 0.8)
                    )
                    for c in data.get("citations", [])
                ]

                risks = [
                    RiskFlag(
                        type=r.get("type", "general"),
                        severity=r.get("severity", "low"),
                        message=r.get("message", "")
                    )
                    for r in data.get("risks", [])
                ]

                next_steps = [
                    NextStep(
                        action=n.get("action", ""),
                        priority=n.get("priority", "medium"),
                        deadline=n.get("deadline")
                    )
                    for n in data.get("nextSteps", [])
                ]

                return ChatResponse(
                    content=data.get("content", response_text),
                    citations=citations,
                    risks=risks,
                    nextSteps=next_steps
                )
        except (json.JSONDecodeError, KeyError):
            pass

        # Fallback: return raw text
        return ChatResponse(content=response_text)

    def chat(
        self,
        student_id: str,
        message: str,
        chat_history: List[Dict[str, str]] = None,
        user_id: str = None,
        user_role: str = None
    ) -> ChatResponse:
        """
        Process a chat message and return a response.

        Args:
            student_id: The student's ID being queried (for context)
            message: The user's message
            chat_history: Previous messages in the conversation
            user_id: The authenticated user's ID
            user_role: The authenticated user's role (student/advisor/admin)

        Returns:
            ChatResponse with content, citations, risks, and next steps
        """
        self._ensure_initialized()

        # Get relevant context via RAG
        context = self._get_context(message)

        # Get user-specific context based on role
        user_context = ""

        if user_role == USER_ROLE_ADVISOR or user_role == USER_ROLE_ADMIN:
            # Advisors/admins can see advisee data
            # If student_id is provided, focus on that student but include advisee list
            user_context = self._get_advisor_context(user_id, student_id)
        elif user_role == USER_ROLE_STUDENT:
            # Students can only see their own data
            # Ensure they're only querying about themselves
            if user_id and user_id == student_id:
                user_context = self._get_student_context(student_id)
            # If student tries to query another student, don't include any student data
        else:
            # No role or unknown role - use student_id if provided (legacy support)
            if student_id:
                user_context = self._get_student_context(student_id)

        # Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add user context as system message
        if user_context:
            messages.append({
                "role": "system",
                "content": f"Current user information:\n\n{user_context}"
            })

        # Add curriculum context as system message
        if context:
            messages.append({
                "role": "system",
                "content": f"Relevant context from W&M Business School documents:\n\n{context}"
            })

        # Add chat history (limited)
        if chat_history:
            for msg in chat_history[-self.MAX_HISTORY_MESSAGES:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # Add current message
        messages.append({"role": "user", "content": message})

        # Call OpenAI
        response = self._openai_client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        response_text = response.choices[0].message.content

        return self._parse_response(response_text)

    def add_policy_document(self, content: str, source: str, metadata: Dict[str, Any] = None):
        """Add a policy document to the knowledge base."""
        self._ensure_initialized()
        self._embeddings.add_document(content, source, metadata or {"type": "policy"})

    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        self._ensure_initialized()
        return {
            "document_count": self._embeddings.get_document_count(),
            "curriculum_loaded": self._curriculum_loaded
        }


# Singleton instance
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get singleton instance of ChatService."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
