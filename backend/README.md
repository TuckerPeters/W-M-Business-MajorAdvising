# W&M Business Major Advising - Backend

Python backend for W&M course catalog, student advising, and AI-powered academic guidance.

## Architecture

```
backend/
├── api/           # FOSE API client for W&M course catalog
├── core/          # Config, auth, semester logic
│   └── auth.py    # Firebase Auth with @wm.edu restriction
├── services/      # Business logic layer
│   ├── student.py       # Student profiles, enrollments, milestones
│   ├── advisor.py       # Advisor portal, notes, alerts
│   ├── prerequisites.py # Prerequisite validation engine
│   ├── embeddings.py    # RAG vector store (Firestore)
│   └── chat.py          # AI chat with curriculum context
├── scrapers/      # Curriculum PDF parser
├── tasks/         # Database population & scheduler
└── tests/         # Unit, integration, E2E tests
```

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `CONTACT_EMAIL` | Email for API User-Agent header |
| `FIREBASE_PROJECT_ID` | Firebase project ID |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to service account JSON |
| `REDIS_URL` | Redis connection URL (optional) |
| `OPENAI_API_KEY` | OpenAI API key for AI chat |
| `ALLOWED_EMAIL_DOMAIN` | Email domain restriction (default: `wm.edu`) |

## Services

### PrerequisiteEngine (`services/prerequisites.py`)

Validates course prerequisites and schedule constraints.

**Key Features:**
- Prerequisites fetched from Firebase `courses` collection (not curriculum scraper)
- Credit limits: 12-18 max (>15 = warning, >18 = invalid)
- Workload balance analysis
- Schedule quality scoring (0-100)

**Enrollment Validation Flow:**
```
1. add_enrollment() → check_prerequisites_met() → BLOCKS if prereqs missing
2. If prereqs pass → save enrollment → compute_student_validation_flags()
3. Returns validationWarnings (credit load, workload issues)
4. User acknowledges → acknowledge_enrollment_warnings() saves flags
```

### StudentService (`services/student.py`)

Manages student profiles, enrollments, and milestones.

**Term Format:** Use `"Season Year"` format (e.g., `"Fall 2025"`), not numeric codes.

### AdvisorService (`services/advisor.py`)

Advisor portal with advisee management, notes, and automated alerts.

**Alerts Generated:**
- GPA < 2.0 (high), GPA < 2.5 (medium)
- Account holds
- Undeclared major (juniors/seniors)

### ChatService (`services/chat.py`)

RAG-powered AI advisor using OpenAI + Firestore vector search.

**Context Sources:**
- Student profile and enrollments
- Curriculum documents (via embeddings)
- Validation flags (credit warnings, schedule issues)
- Advisor context (for advisor users)

## AI Chat Setup

### Firestore Vector Index (Required)

Create a vector index in Firebase Console or CLI:

```bash
firebase firestore:indexes:create --collection=advising_embeddings --field=embedding --vector-config='{"dimension":1536,"flat":{}}'
```

### Loading Curriculum Documents

```python
from services.embeddings import get_embeddings_service
from scrapers.curriculum_scraper import load_curriculum_data

embeddings = get_embeddings_service()
curriculum = load_curriculum_data()

for doc in curriculum:
    embeddings.add_document(
        content=doc['content'],
        source=doc['source'],
        metadata=doc.get('metadata', {})
    )
```

## Authentication

All student and advisor endpoints require Firebase Authentication. Include a Bearer token in the Authorization header:

```
Authorization: Bearer <firebase-id-token>
```

**Email Restriction:** Only `@wm.edu` email addresses are allowed. Users with non-W&M emails will receive a 403 Forbidden error.

### User Roles

| Role | Access |
|------|--------|
| `student` | Own profile, courses, and milestones |
| `advisor` | Own advisees + student permissions |
| `admin` | All resources |

### Setting Up Roles

Assign roles via Firebase Admin SDK custom claims:

```python
from firebase_admin import auth

# Make user an advisor
auth.set_custom_user_claims(uid, {'advisor': True})

# Make user an admin
auth.set_custom_user_claims(uid, {'admin': True})
```

### Public Endpoints (No Auth Required)

- `GET /` - Health check
- `GET /api/health` - API health
- `GET /api/term` - Current term info
- `GET /api/courses` - List courses
- `GET /api/courses/{code}` - Get course details
- `GET /api/courses/search` - Search courses
- `GET /api/subjects` - List subjects
- `GET /api/milestones` - List degree milestones
- `GET /api/courses/{code}/prerequisites` - Get prerequisites
- `GET /api/courses/{code}/prerequisite-chain` - Get prerequisite chain

## API Endpoints

### Course Catalog

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /api/term` | Current semester info |
| `GET /api/courses` | List courses (paginated) |
| `GET /api/courses/{code}` | Get single course |
| `GET /api/courses/search?q=` | Search courses |
| `GET /api/subjects` | List all subjects |

### Student Profile (Auth Required)

| Endpoint | Description |
|----------|-------------|
| `GET /api/student/{id}/profile` | Get student profile |
| `POST /api/student/{id}/profile` | Create student profile |
| `PUT /api/student/{id}/profile` | Update student profile |
| `POST /api/student/{id}/declare-major` | Declare major |

### Student Courses & Enrollments (Auth Required)

| Endpoint | Description |
|----------|-------------|
| `GET /api/student/{id}/courses` | Get courses (completed/current/planned) |
| `POST /api/student/{id}/courses` | Add enrollment (validates prerequisites) |
| `PUT /api/student/{id}/courses/{enrollmentId}` | Update enrollment |
| `DELETE /api/student/{id}/courses/{enrollmentId}` | Delete enrollment |
| `POST /api/student/{id}/courses/acknowledge` | Save validation warnings |

**Enrollment Response:** Includes `validationWarnings` with credit/workload flags after save.

### Student Milestones (Auth Required)

| Endpoint | Description |
|----------|-------------|
| `GET /api/student/{id}/milestones` | Get student milestone progress |
| `PUT /api/student/{id}/milestones/{milestoneId}` | Update milestone progress |
| `GET /api/milestones` | Get all degree milestones |

### Advisor Portal (Advisor Auth Required)

| Endpoint | Description |
|----------|-------------|
| `GET /api/advisor/{id}/advisees` | Get all advisees |
| `POST /api/advisor/{id}/advisees` | Assign student to advisor |
| `DELETE /api/advisor/{id}/advisees/{studentId}` | Remove advisee |
| `GET /api/advisor/{id}/advisees/{studentId}` | Get advisee details |
| `GET /api/advisor/{id}/advisees/{studentId}/notes` | Get notes for advisee |
| `POST /api/advisor/{id}/advisees/{studentId}/notes` | Create note |
| `PUT /api/advisor/{id}/advisees/{studentId}/notes/{noteId}` | Update note |
| `DELETE /api/advisor/{id}/advisees/{studentId}/notes/{noteId}` | Delete note |
| `GET /api/advisor/{id}/alerts` | Get alerts for all advisees |

### Schedule Validation & Prerequisites (Mixed Auth)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/student/validate-schedule` | Required | Validate proposed schedule |
| `GET /api/student/{id}/eligible-courses` | Required | Get courses student can take |
| `GET /api/courses/{code}/prerequisites` | Public | Get prerequisites for a course |
| `GET /api/courses/{code}/prerequisite-chain` | Public | Get full prerequisite chain |

**Validation Behavior:**
- Prerequisites: **Block enrollment** if not met (raises `PrerequisitesNotMetError`)
- Credit limits: **Warning only** (12-18 normal, >15 heavy, >18 invalid)
- Workload: **Warning only** (4+ upper-level courses triggers flag)
- Warnings returned in `validationWarnings` field after successful enrollment

### AI Chat (Auth Required)

| Endpoint | Description |
|----------|-------------|
| `POST /api/chat/message` | Send message to AI advisor |

**Request:**
```json
{
  "studentId": "...",
  "message": "What are the prerequisites for BUAD 327?",
  "chatHistory": []
}
```

**Response:**
```json
{
  "content": "BUAD 327 (Investments) requires...",
  "citations": [{"source": "Finance Major Requirements", "excerpt": "..."}],
  "risks": [{"type": "prerequisite", "severity": "medium", "message": "..."}],
  "nextSteps": [{"action": "Complete BUAD 323", "priority": "high"}]
}
```

**Features:**
- RAG-powered responses using curriculum and policy documents
- Citation extraction from source materials
- Risk identification (academic, deadline, prerequisite issues)
- Recommended next steps

## Scripts

```bash
python server.py                    # Run server (port 8000)
python server.py --no-scheduler     # Run without background updates
python -m tasks.populate            # Populate course database
python -m tasks.populate --term 202510 --delete-first  # Specific term
python -m tasks.scheduler           # Run background scheduler
```

## Testing

```bash
# Unit tests (mocked dependencies)
pytest tests/unit -v

# Integration tests (uses real Firebase)
pytest tests/integration -v -m integration

# E2E tests
pytest tests/e2e -v

# All tests
pytest

# Skip Firebase-dependent tests
pytest -m "not firebase"
```

**Note:** Integration tests dynamically discover courses from Firebase. Run `tasks.populate` first.
