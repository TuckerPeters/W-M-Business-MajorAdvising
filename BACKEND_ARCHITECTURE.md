# Backend Architecture Plan
## W&M Business Advising Platform

---

## Executive Summary

This document outlines the complete backend architecture for the W&M Business Advising Platform. The system is designed to support AI-powered academic advising with dual portals for students and advisors, integrating with university systems while maintaining FERPA compliance and high availability.

---

## Technology Stack

### Core Framework
- **Python 3.11+** with **FastAPI** - High-performance async framework with automatic API documentation
- **Pydantic v2** - Data validation and serialization
- **SQLAlchemy 2.0** - ORM with async support
- **Alembic** - Database migrations

### Database Layer
- **PostgreSQL 15+** - Primary relational database
  - ACID compliance for transactional data
  - Full-text search capabilities
  - JSON/JSONB support for flexible data
- **Redis 7+** - Caching and session management
  - Session storage
  - Rate limiting
  - Real-time features (WebSocket pub/sub)

### AI/ML Services
- **OpenAI API (GPT-4)** or **Anthropic Claude 3.5** - Primary LLM for chat interface
- **LangChain** - LLM orchestration framework
- **Pinecone** or **Weaviate** - Vector database for RAG (Retrieval-Augmented Generation)
- **Sentence-Transformers** - Document embedding generation
- **spaCy** - NLP preprocessing and entity extraction

### Message Queue & Background Jobs
- **Celery** - Distributed task queue
- **RabbitMQ** or **Redis** - Message broker
- Use cases:
  - Async AI response generation
  - Batch risk analysis
  - Email notifications
  - Scheduled report generation

### Authentication & Security
- **Auth0** or **Okta** - SSO/SAML integration with university identity system
- **Python-JOSE** - JWT token handling
- **Argon2** - Password hashing (for admin accounts)
- **Python-Passlib** - Password utilities

### Monitoring & Observability
- **Prometheus** - Metrics collection
- **Grafana** - Dashboards and visualization
- **Sentry** - Error tracking and performance monitoring
- **ELK Stack** (Elasticsearch, Logstash, Kibana) - Centralized logging
- **OpenTelemetry** - Distributed tracing

### Development Tools
- **Poetry** - Dependency management
- **pytest** - Testing framework
- **Black** - Code formatting
- **Ruff** - Linting
- **mypy** - Static type checking
- **pre-commit** - Git hooks for code quality

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend (Next.js)                      │
│                     Student Portal | Advisor Portal              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS/WSS
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      API Gateway / Load Balancer                 │
│                     (nginx or AWS ALB)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐ ┌──────▼──────┐ ┌────────▼────────┐
│   FastAPI      │ │   FastAPI   │ │    FastAPI      │
│   Instance 1   │ │  Instance 2 │ │   Instance N    │
│                │ │              │ │                 │
│ - REST API     │ │ - REST API  │ │  - REST API     │
│ - WebSockets   │ │ - WebSockets│ │  - WebSockets   │
└───────┬────────┘ └──────┬──────┘ └────────┬────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────────────┐
        │                  │                          │
┌───────▼────────┐ ┌──────▼──────────┐ ┌────────────▼─────────┐
│   PostgreSQL   │ │     Redis       │ │   Celery Workers     │
│   - User data  │ │  - Sessions     │ │  - AI processing     │
│   - Courses    │ │  - Cache        │ │  - Batch jobs        │
│   - Transcripts│ │  - Rate limit   │ │  - Notifications     │
└───────┬────────┘ └─────────────────┘ └──────────────────────┘
        │
        │
┌───────▼─────────────────────────────────────────────────────────┐
│                    External Integrations                         │
├──────────────────┬──────────────────┬──────────────────────────┤
│  University SIS  │   Auth Provider  │   Email Service          │
│  (Banner/PeopleSoft)│  (SSO/SAML)   │   (SendGrid/SES)         │
└──────────────────┴──────────────────┴──────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        AI/ML Pipeline                            │
├──────────────────┬──────────────────┬──────────────────────────┤
│  Vector DB       │   OpenAI/Claude  │   Document Store         │
│  (Pinecone)      │   API            │   (S3/MinIO)             │
└──────────────────┴──────────────────┴──────────────────────────┘
```

### Microservices Architecture (Optional - for scale)

For larger deployments, consider splitting into services:

1. **User Service** - Authentication, user profiles, authorization
2. **Course Service** - Course catalog, prerequisites, scheduling
3. **Advising Service** - AI chat, schedule evaluation, recommendations
4. **Analytics Service** - Risk detection, reporting, metrics
5. **Notification Service** - Email, push notifications, alerts
6. **Document Service** - Policy documents, RAG document management

---

## Database Schema

### Core Tables

```sql
-- Users and Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id VARCHAR(20) UNIQUE NOT NULL, -- Banner ID
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'advisor', 'admin')),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_university_id ON users(university_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Students
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    class_year INTEGER NOT NULL,
    entry_semester VARCHAR(20) NOT NULL, -- 'Fall 2023'
    gpa NUMERIC(3,2),
    credits_earned INTEGER DEFAULT 0,
    ap_credits INTEGER DEFAULT 0,
    transfer_credits INTEGER DEFAULT 0,
    declared BOOLEAN DEFAULT FALSE,
    intended_major VARCHAR(100),
    declared_major VARCHAR(100),
    major_declared_date DATE,
    minor VARCHAR(100),
    academic_standing VARCHAR(50), -- 'Good Standing', 'Academic Probation', etc.
    holds JSONB DEFAULT '[]', -- Array of hold types
    advisor_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_students_user_id ON students(user_id);
CREATE INDEX idx_students_advisor_id ON students(advisor_id);
CREATE INDEX idx_students_class_year ON students(class_year);
CREATE INDEX idx_students_declared ON students(declared);

-- Advisors
CREATE TABLE advisors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    department VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    max_advisees INTEGER DEFAULT 50,
    specializations JSONB, -- Array of specialization areas
    office_location VARCHAR(100),
    office_hours TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Courses
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) UNIQUE NOT NULL, -- 'BUS 203'
    title VARCHAR(255) NOT NULL,
    description TEXT,
    credits INTEGER NOT NULL,
    department VARCHAR(10) NOT NULL,
    level INTEGER NOT NULL, -- 100, 200, 300, 400
    has_lab BOOLEAN DEFAULT FALSE,
    difficulty_index NUMERIC(3,2), -- 0.0 to 1.0
    prerequisite_ids UUID[] DEFAULT '{}', -- Array of course UUIDs
    corequisite_ids UUID[] DEFAULT '{}',
    attributes JSONB, -- Gen ed categories, etc.
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_courses_code ON courses(code);
CREATE INDEX idx_courses_department ON courses(department);
CREATE INDEX idx_courses_level ON courses(level);

-- Course Sections (actual offerings)
CREATE TABLE course_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    section_number VARCHAR(10) NOT NULL,
    term VARCHAR(20) NOT NULL, -- 'Fall 2024'
    instructor_name VARCHAR(255),
    capacity INTEGER,
    enrolled_count INTEGER DEFAULT 0,
    waitlist_count INTEGER DEFAULT 0,
    meeting_times JSONB, -- [{day: 'MWF', start: '09:00', end: '09:50', location: 'Miller 101'}]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(course_id, section_number, term)
);

CREATE INDEX idx_course_sections_term ON course_sections(term);
CREATE INDEX idx_course_sections_course_id ON course_sections(course_id);

-- Student Course History
CREATE TABLE student_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id),
    section_id UUID REFERENCES course_sections(id),
    term VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('enrolled', 'completed', 'dropped', 'withdrawn', 'planned')),
    grade VARCHAR(5), -- 'A', 'A-', 'B+', 'W', 'IP', etc.
    grade_points NUMERIC(3,2),
    enrolled_date DATE,
    completed_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_student_courses_student_id ON student_courses(student_id);
CREATE INDEX idx_student_courses_status ON student_courses(status);
CREATE INDEX idx_student_courses_term ON student_courses(term);

-- Academic Milestones
CREATE TABLE milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    milestone_type VARCHAR(50) NOT NULL, -- 'credit_threshold', 'major_declaration', 'prerequisite_completion'
    criteria JSONB NOT NULL, -- {credits_required: 39, courses_required: ['BUS 101', 'BUS 203']}
    deadline_offset_days INTEGER, -- Days from entry semester
    required BOOLEAN DEFAULT TRUE,
    applies_to_years INTEGER[], -- [2024, 2025, 2026, 2027]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Student Milestone Tracking
CREATE TABLE student_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES milestones(id),
    completed BOOLEAN DEFAULT FALSE,
    completed_date DATE,
    deadline DATE,
    status VARCHAR(50), -- 'completed', 'on_track', 'at_risk', 'overdue'
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(student_id, milestone_id)
);

CREATE INDEX idx_student_milestones_student_id ON student_milestones(student_id);
CREATE INDEX idx_student_milestones_status ON student_milestones(status);

-- Chat Conversations
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    title VARCHAR(255), -- Auto-generated from first message
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    archived BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_chat_sessions_student_id ON chat_sessions(student_id);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB, -- Array of citation objects
    risks JSONB, -- Array of detected risks
    next_steps JSONB, -- Array of suggested next steps
    metadata JSONB, -- Token count, model used, latency, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);

-- Schedule Evaluations
CREATE TABLE schedule_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    term VARCHAR(20) NOT NULL,
    courses JSONB NOT NULL, -- Array of course codes
    score NUMERIC(3,2), -- 0.0 to 1.0
    rationale TEXT,
    warnings JSONB, -- Array of warning messages
    suggested_swaps JSONB, -- Array of swap suggestions
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_schedule_evaluations_student_id ON schedule_evaluations(student_id);

-- Risk Assessments
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL,
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('none', 'low', 'medium', 'high', 'critical')),
    overload_risk BOOLEAN DEFAULT FALSE,
    missing_prereqs BOOLEAN DEFAULT FALSE,
    gpa_dip BOOLEAN DEFAULT FALSE,
    credit_pace_risk BOOLEAN DEFAULT FALSE,
    milestone_risk BOOLEAN DEFAULT FALSE,
    risk_factors JSONB, -- Detailed breakdown
    recommendations JSONB, -- Action items
    reviewed_by_advisor BOOLEAN DEFAULT FALSE,
    advisor_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_risk_assessments_student_id ON risk_assessments(student_id);
CREATE INDEX idx_risk_assessments_risk_level ON risk_assessments(risk_level);
CREATE INDEX idx_risk_assessments_date ON risk_assessments(assessment_date);

-- Advisor Notes
CREATE TABLE advisor_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    advisor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    note TEXT NOT NULL,
    visibility VARCHAR(20) NOT NULL CHECK (visibility IN ('private', 'shared_advisors', 'student_visible')),
    tags JSONB, -- Array of tags for categorization
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_advisor_notes_student_id ON advisor_notes(student_id);
CREATE INDEX idx_advisor_notes_advisor_id ON advisor_notes(advisor_id);
CREATE INDEX idx_advisor_notes_visibility ON advisor_notes(visibility);

-- Advisor-Student Communication Log
CREATE TABLE advisor_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    advisor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    contact_type VARCHAR(50) NOT NULL, -- 'email', 'meeting', 'phone', 'chat'
    subject VARCHAR(255),
    summary TEXT,
    contacted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_advisor_contacts_student_id ON advisor_contacts(student_id);
CREATE INDEX idx_advisor_contacts_advisor_id ON advisor_contacts(advisor_id);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL, -- 'milestone_approaching', 'advisor_message', 'risk_alert'
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    link VARCHAR(500), -- Deep link to relevant page
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    sent_via JSONB, -- ['email', 'push', 'in_app']
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- Audit Log (FERPA compliance)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL, -- 'view_student_record', 'update_grades', 'delete_note'
    resource_type VARCHAR(50) NOT NULL, -- 'student', 'course', 'chat_message'
    resource_id UUID NOT NULL,
    student_id UUID REFERENCES students(id), -- If action involves student data
    ip_address INET,
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    changes JSONB, -- Before/after for updates
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_student_id ON audit_logs(student_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Document Store (for RAG)
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- 'policy', 'course_catalog', 'handbook', 'faq'
    source_url VARCHAR(1000),
    content TEXT NOT NULL,
    summary TEXT,
    academic_year VARCHAR(20), -- '2024-2025'
    version VARCHAR(50),
    department VARCHAR(100),
    metadata JSONB, -- Additional structured data
    embedding_id VARCHAR(255), -- Reference to vector DB
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_knowledge_documents_type ON knowledge_documents(document_type);
CREATE INDEX idx_knowledge_documents_active ON knowledge_documents(active);
CREATE INDEX idx_knowledge_documents_year ON knowledge_documents(academic_year);
```

---

## API Design

### REST API Structure

Base URL: `https://api.advising.wm.edu/v1`

#### Authentication Endpoints

```
POST   /auth/login              # SSO callback
POST   /auth/logout             # Invalidate session
POST   /auth/refresh            # Refresh access token
GET    /auth/me                 # Current user info
```

#### Student Endpoints

```
# Profile
GET    /students/me                           # Current student profile
GET    /students/{id}                         # Student profile (advisor only)
PATCH  /students/me                           # Update preferences
GET    /students/me/transcript                # Full course history
GET    /students/me/progress                  # Progress toward degree

# Courses
GET    /students/me/courses                   # Current/planned courses
GET    /students/me/courses/history           # Completed courses
POST   /students/me/courses/evaluate          # Evaluate schedule
GET    /students/me/courses/recommendations   # AI course recommendations

# Milestones
GET    /students/me/milestones                # Milestone tracking
GET    /students/me/milestones/{id}           # Specific milestone

# Chat
GET    /students/me/chat/sessions             # Chat history
POST   /students/me/chat/sessions             # New chat session
GET    /students/me/chat/sessions/{id}        # Chat session messages
POST   /students/me/chat/sessions/{id}/messages # Send message
WS     /ws/chat/{session_id}                  # WebSocket for streaming

# Notifications
GET    /students/me/notifications             # User notifications
PATCH  /students/me/notifications/{id}        # Mark as read
```

#### Advisor Endpoints

```
# Advisees
GET    /advisors/me/advisees                  # List all advisees
GET    /advisors/me/advisees/{id}             # Advisee details
GET    /advisors/me/advisees/{id}/transcript  # Advisee transcript
GET    /advisors/me/advisees/{id}/chat-history # View student's chat history
GET    /advisors/me/advisees/at-risk          # Filter at-risk students

# Risk Management
GET    /advisors/me/risk-assessments          # Recent risk assessments
GET    /advisors/me/advisees/{id}/risks       # Student risk details
POST   /advisors/me/advisees/{id}/risks/review # Mark risk as reviewed

# Notes & Communication
GET    /advisors/me/advisees/{id}/notes       # Advisor notes
POST   /advisors/me/advisees/{id}/notes       # Create note
PATCH  /advisors/me/notes/{id}                # Update note
DELETE /advisors/me/notes/{id}                # Delete note
POST   /advisors/me/advisees/{id}/contact     # Log contact
GET    /advisors/me/advisees/{id}/contacts    # Contact history

# Analytics
GET    /advisors/me/analytics/overview        # Advisee cohort metrics
GET    /advisors/me/analytics/graduation-pace # Graduation timeline analytics
```

#### Course Catalog Endpoints

```
GET    /courses                               # Search courses
GET    /courses/{id}                          # Course details
GET    /courses/{id}/sections                 # Available sections
GET    /courses/{id}/prerequisites            # Prerequisite tree
GET    /courses/search                        # Advanced search
```

#### Admin Endpoints

```
POST   /admin/courses                         # Create course
PATCH  /admin/courses/{id}                    # Update course
POST   /admin/documents                       # Upload policy document
POST   /admin/documents/{id}/reindex          # Trigger vector embedding
GET    /admin/analytics                       # System-wide analytics
GET    /admin/audit-logs                      # FERPA audit logs
```

### WebSocket API

```
# Real-time chat with AI
WS /ws/chat/{session_id}

Client → Server:
{
  "type": "message",
  "content": "What courses should I take next semester?"
}

Server → Client (streaming):
{
  "type": "chunk",
  "content": "Based on your progress..."
}

Server → Client (final):
{
  "type": "complete",
  "message_id": "uuid",
  "content": "...",
  "citations": [...],
  "nextSteps": [...]
}
```

### API Response Format

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2024-12-22T10:30:00Z",
    "request_id": "uuid"
  }
}
```

Error format:
```json
{
  "success": false,
  "error": {
    "code": "MISSING_PREREQUISITES",
    "message": "Cannot enroll in BUS 305 without STAT 250",
    "details": {
      "course": "BUS 305",
      "missing_prereqs": ["STAT 250"]
    }
  },
  "meta": {
    "timestamp": "2024-12-22T10:30:00Z",
    "request_id": "uuid"
  }
}
```

---

## Authentication & Authorization

### Authentication Flow

1. **SSO Integration (SAML 2.0)**
   - Integrate with university identity provider (CAS, Shibboleth, etc.)
   - Use Auth0 or Okta as intermediary for protocol translation
   - Map university ID to internal user record

2. **Token-based Auth**
   - Access token (JWT): 15-minute expiry
   - Refresh token: 7-day expiry (stored in Redis)
   - Token payload:
     ```json
     {
       "sub": "user_uuid",
       "role": "student",
       "university_id": "W12345678",
       "exp": 1703260800,
       "iat": 1703260000
     }
     ```

3. **Session Management**
   - Store active sessions in Redis
   - Support session revocation
   - Track session metadata (IP, user agent, login time)

### Authorization Model

**Role-Based Access Control (RBAC)**

Roles:
- `student` - Can access own data only
- `advisor` - Can access assigned advisees' data
- `admin` - Full system access
- `super_admin` - System configuration

Permissions Matrix:

| Resource | Student | Advisor | Admin |
|----------|---------|---------|-------|
| Own profile | Read/Write | - | Read/Write |
| Own courses | Read/Write | - | Read/Write |
| Own chat | Read/Write | - | Read/Write |
| Advisee profiles | - | Read (assigned) | Read (all) |
| Advisee chat history | - | Read (assigned) | Read (all) |
| Risk assessments | - | Read/Write (assigned) | Read/Write (all) |
| Course catalog | Read | Read | Read/Write |
| Policy documents | Read | Read | Read/Write |
| Audit logs | - | - | Read |

**Row-Level Security**
- Implement in application layer
- Students: `WHERE student.user_id = current_user.id`
- Advisors: `WHERE student.advisor_id = current_user.id`
- Admin: No filters

---

## AI/ML Architecture

### RAG (Retrieval-Augmented Generation) Pipeline

#### 1. Document Ingestion

```python
# Pipeline flow
Document (PDF/HTML/Markdown)
  ↓
Preprocessing (clean, parse)
  ↓
Chunking (semantic chunking, 500-1000 tokens)
  ↓
Embedding (sentence-transformers)
  ↓
Vector Storage (Pinecone/Weaviate)
  ↓
Metadata Index (PostgreSQL)
```

**Document Types:**
- Academic policies
- Course catalog
- Degree requirements
- Major/minor guidelines
- Academic calendar
- FAQ documents

#### 2. Query Processing

```python
# User query flow
User Question
  ↓
Query Enhancement (expand, rephrase)
  ↓
Embedding Generation
  ↓
Vector Search (top-k similar chunks)
  ↓
Reranking (cross-encoder)
  ↓
Context Assembly
  ↓
LLM Prompt Construction
  ↓
LLM Response Generation
  ↓
Citation Extraction
  ↓
Response Formatting
```

#### 3. Prompt Engineering

**System Prompt Template:**
```
You are an academic advisor assistant for William & Mary Business School.
You help students with course planning, degree requirements, and major declaration.

IMPORTANT RULES:
1. Only provide information grounded in the provided context documents
2. Include citations for all factual claims
3. Flag high-stakes decisions (e.g., major declaration deadlines) for human advisor review
4. If information is not in the context, say "I don't have that information"
5. Be encouraging but realistic about academic challenges
6. Consider FERPA privacy - never discuss other students

STUDENT CONTEXT:
- Name: {student_name}
- Class Year: {class_year}
- GPA: {gpa}
- Credits Earned: {credits_earned}
- Declared: {declared}
- Intended Major: {intended_major}

RETRIEVED CONTEXT:
{context_chunks}

CONVERSATION HISTORY:
{chat_history}

USER QUESTION:
{user_question}

Provide a helpful, accurate response with citations.
```

#### 4. Response Validation

```python
def validate_response(response, context_docs, student_data):
    """Post-processing validation"""
    # Check for hallucinations
    - Verify all course codes exist in catalog
    - Verify all policy references exist in documents
    - Check for date inconsistencies

    # Risk detection
    - Flag advice about dropping courses
    - Flag advice about changing majors
    - Flag financial aid implications

    # Citation extraction
    - Parse document references
    - Generate citation objects with title, URL, version

    return validated_response
```

### Schedule Optimization

**Algorithm: Multi-Objective Optimization**

Objectives:
1. Maximize progress toward degree
2. Minimize course difficulty variance
3. Balance workload across semester
4. Satisfy prerequisite chains
5. Consider student preferences

```python
def evaluate_schedule(courses, student_history, constraints):
    """
    Returns score 0.0-1.0 with rationale
    """
    score = 0.0
    warnings = []

    # Credit load (12-18 optimal, penalize extremes)
    total_credits = sum(c.credits for c in courses)
    if total_credits < 12:
        warnings.append("Below full-time status")
        score -= 0.2
    elif total_credits > 18:
        warnings.append("Overload risk")
        score -= 0.3
    else:
        score += 0.3

    # Difficulty distribution
    difficulties = [c.difficulty_index for c in courses]
    difficulty_variance = variance(difficulties)
    if difficulty_variance > 0.2:
        warnings.append("Unbalanced difficulty")
        score -= 0.1
    else:
        score += 0.2

    # Prerequisite validation
    for course in courses:
        missing_prereqs = check_prerequisites(course, student_history)
        if missing_prereqs:
            warnings.append(f"Missing prereqs for {course.code}")
            score -= 0.5

    # Level distribution (avoid all 400-level)
    levels = [c.level for c in courses]
    if all(l >= 400 for l in levels):
        warnings.append("All upper-level courses")
        score -= 0.2

    # Progress toward degree
    major_courses = [c for c in courses if c.dept == student.intended_major_dept]
    if len(major_courses) > 0:
        score += 0.2

    return max(0.0, min(1.0, score)), warnings
```

### Risk Detection

**ML Model: Gradient Boosting Classifier**

Features:
- Current GPA
- GPA trend (last 3 semesters)
- Credits earned vs expected
- Course difficulty of current schedule
- Number of W/F grades
- Advisor contact frequency
- Chat engagement level

Target:
- `at_risk` (binary classification)

```python
def calculate_risk_score(student_data, course_history, schedule):
    """
    Real-time risk assessment
    """
    features = extract_features(student_data, course_history, schedule)
    risk_probability = model.predict_proba(features)[1]

    risk_factors = []

    # GPA dip detection
    recent_gpa = calculate_gpa(course_history[-2:])
    if recent_gpa < student_data.gpa - 0.3:
        risk_factors.append({
            'type': 'gpa_dip',
            'severity': 'medium',
            'message': 'Recent GPA decline detected'
        })

    # Course overload
    if schedule_credits > 18 and avg_difficulty > 0.6:
        risk_factors.append({
            'type': 'overload',
            'severity': 'high',
            'message': 'Heavy course load with difficult courses'
        })

    # Missing prerequisites
    prereq_issues = check_all_prerequisites(schedule, course_history)
    if prereq_issues:
        risk_factors.append({
            'type': 'prerequisites',
            'severity': 'critical',
            'message': 'Enrolled in courses without prerequisites'
        })

    return {
        'risk_level': calculate_risk_level(risk_probability),
        'probability': risk_probability,
        'factors': risk_factors,
        'recommendations': generate_recommendations(risk_factors)
    }
```

---

## External Integrations

### University Student Information System (SIS)

**Integration Pattern: ETL + API Hybrid**

1. **Batch Sync (ETL)**
   - Nightly full sync of course catalog
   - Weekly sync of student transcripts
   - Semester sync of enrollment data

2. **Real-time API**
   - Check enrollment availability
   - Verify student enrollment status
   - Fetch prerequisite checks

**API Endpoints (from SIS):**
```
GET /api/students/{id}/transcript
GET /api/courses/catalog/{term}
GET /api/courses/{course_id}/sections/{term}
POST /api/enrollment/validate
```

**Data Mapping:**
```python
# SIS → Internal mapping
sis_course_code = "BUS 203-01"  # SIS format
internal_code = "BUS 203"       # Internal format
section = "01"

# Handle SIS-specific fields
sis_grade_scale = {"A": 4.0, "A-": 3.7, "B+": 3.3, ...}
```

### Email Service

**Provider: SendGrid or AWS SES**

Email types:
- Milestone reminders
- Risk alerts to advisors
- Advisor meeting confirmations
- Weekly digest for advisors

**Template System:**
```python
# Email templates with variables
templates = {
    'milestone_reminder': {
        'subject': 'Reminder: {milestone_name} deadline approaching',
        'body_template': 'milestone_reminder.html',
        'variables': ['student_name', 'milestone_name', 'deadline_date']
    },
    'risk_alert': {
        'subject': 'Student Alert: {student_name} flagged for {risk_type}',
        'body_template': 'advisor_risk_alert.html',
        'variables': ['advisor_name', 'student_name', 'risk_level', 'risk_factors']
    }
}
```

### Document Storage

**Provider: AWS S3 or MinIO**

Storage structure:
```
s3://advising-docs/
  policies/
    2024-2025/
      undergraduate-handbook.pdf
      major-declaration-policy.pdf
  course-catalogs/
    2024-2025/
      business-courses.pdf
  student-uploads/
    {student_id}/
      ap-scores.pdf
```

---

## Security Implementation

### Data Protection

1. **Encryption**
   - At rest: PostgreSQL encryption, encrypted S3 buckets
   - In transit: TLS 1.3 only
   - Database fields: Encrypt SSN, student ID with AES-256

2. **FERPA Compliance**
   - Audit all student data access
   - Log every view, update, delete operation
   - 7-year audit log retention
   - Role-based access enforcement
   - Student consent for data sharing

3. **API Security**
   - Rate limiting: 100 requests/minute per user, 10 requests/minute for AI endpoints
   - Request size limits: 10MB max
   - DDoS protection via Cloudflare or AWS Shield
   - Input validation and sanitization

4. **Sensitive Data Handling**
   ```python
   # Never log sensitive data
   SENSITIVE_FIELDS = ['ssn', 'student_id', 'date_of_birth', 'financial_aid']

   def sanitize_log_data(data):
       for field in SENSITIVE_FIELDS:
           if field in data:
               data[field] = '***REDACTED***'
       return data
   ```

### Vulnerability Protection

1. **SQL Injection**: Use SQLAlchemy ORM with parameterized queries
2. **XSS**: Sanitize all user input, CSP headers
3. **CSRF**: SameSite cookies, CSRF tokens for state-changing operations
4. **LLM Prompt Injection**: Input filtering, output validation
5. **Mass Assignment**: Explicit field allowlists in Pydantic models

### Authentication Security

```python
# Multi-factor authentication for advisors
# Session security
- HTTPOnly cookies
- Secure flag (HTTPS only)
- SameSite=Strict
- Session binding to IP + User-Agent (optional)

# Password requirements (for admin accounts)
- Minimum 12 characters
- Complexity requirements
- Password history (prevent reuse)
- Argon2 hashing
```

---

## Deployment Architecture

### Infrastructure (AWS Example)

```
┌─────────────────────────────────────────────────────────────────┐
│                          Route 53                                │
│                      (DNS Management)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      CloudFront                                  │
│              (CDN for static assets)                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   Application Load Balancer                      │
│                     (SSL Termination)                            │
└──────────┬──────────────────────────────────┬───────────────────┘
           │                                   │
┌──────────▼──────────┐            ┌──────────▼──────────┐
│   ECS Fargate       │            │   ECS Fargate       │
│   (API Cluster)     │            │   (Worker Cluster)  │
│                     │            │                     │
│ - FastAPI pods      │            │ - Celery workers    │
│ - Auto-scaling      │            │ - Scheduled jobs    │
│ - 2-10 instances    │            │ - AI processing     │
└──────────┬──────────┘            └─────────────────────┘
           │
           ├───────────────┬────────────────┬─────────────────┐
           │               │                │                 │
┌──────────▼───────┐ ┌────▼────────┐ ┌─────▼──────┐ ┌───────▼──────┐
│   RDS PostgreSQL │ │   ElastiCache│ │    S3      │ │   Pinecone   │
│   Multi-AZ       │ │   (Redis)    │ │  (Docs)    │ │  (Vectors)   │
└──────────────────┘ └──────────────┘ └────────────┘ └──────────────┘
```

### Container Strategy

**Docker Compose for Development:**
```yaml
version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    depends_on:
      - db
      - redis

  worker:
    build: ./backend
    command: celery -A app.worker worker --loglevel=info
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
```

**Kubernetes for Production (optional):**
- API deployment: 3-10 replicas with HPA
- Worker deployment: 2-5 replicas
- Ingress: NGINX ingress controller
- Secrets: AWS Secrets Manager or HashiCorp Vault

### Environment Configuration

```bash
# .env.production
DATABASE_URL=postgresql://user:pass@db-host:5432/advising
REDIS_URL=redis://cache-host:6379/0
SECRET_KEY=<generated-secret>
OPENAI_API_KEY=<api-key>
PINECONE_API_KEY=<api-key>
PINECONE_ENVIRONMENT=us-west1-gcp
SENDGRID_API_KEY=<api-key>
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
S3_BUCKET=advising-documents
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://advising.wm.edu
SIS_API_URL=https://sis.wm.edu/api
SIS_API_KEY=<key>
AUTH0_DOMAIN=wm.auth0.com
AUTH0_CLIENT_ID=<client-id>
AUTH0_CLIENT_SECRET=<secret>
```

### CI/CD Pipeline

**GitHub Actions Example:**

```yaml
name: Deploy Backend

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          poetry install
          poetry run pytest --cov=app tests/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t advising-api:${{ github.sha }} .
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker push advising-api:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster advising-production \
            --service api \
            --force-new-deployment
```

---

## Monitoring & Observability

### Metrics to Track

**Application Metrics:**
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Active WebSocket connections
- AI token usage and cost
- Database query performance

**Business Metrics:**
- Active chat sessions
- Average messages per session
- Schedule evaluations performed
- Risk alerts generated
- Advisor response time

**Infrastructure Metrics:**
- CPU/Memory utilization
- Database connections
- Cache hit ratio
- Queue depth (Celery)

### Logging Strategy

```python
# Structured logging
import structlog

logger = structlog.get_logger()

logger.info(
    "schedule_evaluation_completed",
    student_id=student_id,
    term="Fall 2024",
    score=0.85,
    duration_ms=1230,
    request_id=request_id
)
```

**Log Levels:**
- DEBUG: Development only
- INFO: Normal operations
- WARNING: Recoverable issues (rate limit hit, cache miss)
- ERROR: Application errors
- CRITICAL: System failures

### Alerting Rules

1. **Error Rate > 5%** → Page on-call engineer
2. **P95 latency > 3s** → Slack alert
3. **Database connections > 80%** → Slack alert
4. **AI API errors > 10/minute** → Page on-call
5. **Disk space > 85%** → Email alert

---

## Scalability Considerations

### Database Optimization

1. **Read Replicas**
   - Route read-heavy queries to replicas
   - Master for writes only
   - Advisor dashboard queries → replica

2. **Connection Pooling**
   ```python
   # SQLAlchemy configuration
   engine = create_async_engine(
       DATABASE_URL,
       pool_size=20,
       max_overflow=10,
       pool_pre_ping=True
   )
   ```

3. **Indexing Strategy**
   - Index all foreign keys
   - Composite indexes for common query patterns
   - Partial indexes for filtered queries

4. **Partitioning**
   - Partition `chat_messages` by month
   - Partition `audit_logs` by month
   - Archive old data to S3

### Caching Strategy

```python
# Cache layers
L1: Application cache (in-memory, per instance)
L2: Redis cache (shared across instances)
L3: Database

# Cache TTLs
- Course catalog: 24 hours
- Student profile: 15 minutes
- Chat session: 5 minutes
- Schedule evaluation: No cache (always fresh)

# Cache invalidation
- On student data update → invalidate student cache
- On course catalog update → invalidate course cache
```

### Rate Limiting

```python
# Redis-based rate limiting
from slowapi import Limiter

limiter = Limiter(key_func=get_user_id)

@app.post("/chat/message")
@limiter.limit("10/minute")  # 10 AI requests per minute
async def send_message():
    ...

@app.get("/students/me")
@limiter.limit("100/minute")  # 100 reads per minute
async def get_profile():
    ...
```

---

## Cost Optimization

### AI API Costs

**Estimated Monthly Costs (1000 active students):**

| Service | Usage | Cost |
|---------|-------|------|
| OpenAI GPT-4 | 50K requests × 1K tokens avg | $1,500 |
| Embeddings | 10K documents × 500 tokens | $20 |
| Pinecone | Vector storage + queries | $70 |

**Optimization Strategies:**
1. Use GPT-3.5 for simple queries, GPT-4 for complex
2. Cache common questions
3. Implement semantic deduplication
4. Rate limit per student

### Infrastructure Costs

**AWS Monthly Estimate:**
- RDS PostgreSQL (db.t3.large): $150
- ElastiCache Redis (cache.t3.medium): $75
- ECS Fargate (2 vCPU, 4GB × 3 instances): $200
- S3 storage (100GB): $3
- Data transfer: $50
- **Total: ~$478/month** (before AI costs)

---

## Testing Strategy

### Unit Tests

```python
# pytest example
def test_schedule_evaluation():
    student = create_mock_student(credits=42, gpa=3.5)
    courses = [
        Course(code="BUS 301", credits=3, difficulty=0.5),
        Course(code="BUS 305", credits=3, difficulty=0.6),
        Course(code="MATH 211", credits=4, difficulty=0.7),
    ]

    score, warnings = evaluate_schedule(courses, student)

    assert 0.7 <= score <= 0.9
    assert len(warnings) == 0
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_chat_api_flow(client, mock_student):
    # Create session
    response = await client.post("/chat/sessions")
    session_id = response.json()["data"]["id"]

    # Send message
    response = await client.post(
        f"/chat/sessions/{session_id}/messages",
        json={"content": "What courses should I take?"}
    )

    assert response.status_code == 200
    message = response.json()["data"]
    assert "citations" in message
```

### Load Testing

```python
# locust load test
from locust import HttpUser, task, between

class StudentUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        # Login
        self.client.post("/auth/login", json={"token": "..."})

    @task(3)
    def view_profile(self):
        self.client.get("/students/me")

    @task(1)
    def send_chat_message(self):
        self.client.post("/chat/sessions/xyz/messages", json={
            "content": "What GPA do I need for Business Analytics?"
        })
```

**Load Test Scenarios:**
- 100 concurrent users (normal)
- 500 concurrent users (peak registration period)
- 1000 concurrent users (stress test)

---

## Migration & Rollout Plan

### Phase 1: MVP (Months 1-3)

**Core Features:**
- User authentication (SSO)
- Student profile viewing
- Basic chat interface (GPT-3.5)
- Course catalog integration
- Simple schedule evaluation

**Infrastructure:**
- Single region deployment
- Basic monitoring
- Development + Staging + Production environments

### Phase 2: Enhanced Features (Months 4-6)

**Added Features:**
- RAG system with policy documents
- Risk detection and alerts
- Advisor portal with advisee list
- Email notifications
- Enhanced chat with citations

**Infrastructure:**
- Read replicas
- Redis caching
- Celery background workers

### Phase 3: Advanced Analytics (Months 7-9)

**Added Features:**
- ML-based risk prediction
- Schedule optimization algorithm
- Advisor analytics dashboard
- Historical trend analysis
- Mobile-responsive improvements

### Phase 4: Scale & Optimization (Months 10-12)

**Focus:**
- Multi-AZ deployment
- Auto-scaling optimization
- Cost optimization
- Performance tuning
- Comprehensive testing

---

## Maintenance & Operations

### Backup Strategy

```bash
# PostgreSQL backups
- Automated daily backups (RDS automated backups)
- Point-in-time recovery enabled
- 30-day retention
- Weekly manual snapshot to S3 (long-term retention)
- Test restore quarterly

# Redis persistence
- RDB snapshots every hour
- AOF (Append-Only File) enabled
```

### Update Procedures

```bash
# Database migrations
1. Test migration on staging
2. Create database backup
3. Run migration during maintenance window
4. Verify data integrity
5. Monitor application logs

# Application deployment
1. Deploy to staging
2. Run smoke tests
3. Blue-green deployment to production
4. Monitor error rates
5. Rollback plan: Keep previous version running
```

### Incident Response

**Severity Levels:**

- **P0 (Critical)**: System down, data breach
  - Response: Immediate, page on-call
  - Update frequency: Every 30 minutes

- **P1 (High)**: Core feature broken, performance degraded
  - Response: Within 1 hour
  - Update frequency: Every 2 hours

- **P2 (Medium)**: Non-core feature broken
  - Response: Within 4 hours
  - Update frequency: Daily

- **P3 (Low)**: Minor issue, cosmetic bug
  - Response: Next business day
  - Update frequency: As resolved

---

## Appendix

### Technology Alternatives

| Component | Primary Choice | Alternative |
|-----------|---------------|-------------|
| Backend Framework | FastAPI | Flask, Django |
| Database | PostgreSQL | MySQL, MongoDB |
| Cache | Redis | Memcached |
| Vector DB | Pinecone | Weaviate, Chroma, Qdrant |
| LLM | OpenAI GPT-4 | Anthropic Claude, Local Llama |
| Message Queue | RabbitMQ | AWS SQS, Redis |
| Container Orchestration | ECS Fargate | Kubernetes, EKS |

### Estimated Team Requirements

**Core Team:**
- Backend Engineer (2x) - API, database, integrations
- ML Engineer (1x) - RAG system, risk detection
- DevOps Engineer (1x) - Infrastructure, deployments
- QA Engineer (1x) - Testing, quality assurance
- Project Manager (1x) - Coordination, stakeholder management

**Additional Support:**
- Security Consultant - FERPA compliance, penetration testing
- UX Designer - Frontend collaboration
- Data Analyst - Analytics and reporting

### Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| AI hallucinations | High | RAG system, response validation, advisor oversight |
| SIS integration delays | High | Mock SIS for development, phased rollout |
| FERPA compliance violation | Critical | Security audit, access controls, encryption |
| High AI costs | Medium | Caching, rate limiting, model selection |
| Performance at scale | Medium | Load testing, caching, horizontal scaling |
| Student data accuracy | High | Regular SIS sync, data validation |

---

## Next Steps

1. **Set up development environment**
   - Initialize repository structure
   - Configure Poetry and dependencies
   - Set up Docker Compose

2. **Database initialization**
   - Create schema
   - Set up migrations with Alembic
   - Seed test data

3. **Core API implementation**
   - Authentication endpoints
   - Student profile endpoints
   - Basic CRUD operations

4. **AI integration POC**
   - Set up vector database
   - Implement basic RAG pipeline
   - Test with sample documents

5. **Frontend integration**
   - Connect existing Next.js frontend
   - Replace mock data with API calls
   - Implement WebSocket chat

---

**Document Version:** 1.0
**Last Updated:** 2024-12-22
**Author:** Architecture Team
**Status:** Draft for Review
