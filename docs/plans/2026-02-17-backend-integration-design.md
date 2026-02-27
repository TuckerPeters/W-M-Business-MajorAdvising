# Backend Integration Design: Course Data Connection

**Date:** 2026-02-17
**Status:** Approved
**Approach:** Next.js API Routes Proxy Layer

## Overview

This design connects the frontend advising platform to the existing FastAPI course catalog backend. The integration will replace mock course data with real W&M course information while keeping student profile and AI chat features on mock data (as the backend doesn't yet support those features).

## Architecture

### System Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  React          │  fetch  │  Next.js API     │  fetch  │  FastAPI        │
│  Components     │ ──────> │  Routes          │ ──────> │  Backend        │
│  (Client)       │         │  /app/api/*      │         │  localhost:8000 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                     │                            │
                                     │                            ▼
                                     │                    ┌──────────────┐
                                     │                    │  Firebase/   │
                                     │                    │  Firestore   │
                                     │                    └──────────────┘
                                     ▼
                            ┌─────────────────┐
                            │  Mock Data      │
                            │  (fallback)     │
                            └─────────────────┘
```

### Why Next.js API Routes?

- **Abstraction:** Frontend doesn't need backend URL
- **Security:** Backend URL/credentials hidden from client
- **Middleware:** Easy to add caching, auth, logging
- **Flexibility:** Can swap backends without changing components
- **Native:** Uses Next.js built-in capabilities

## API Routes Structure

We'll create the following Next.js API routes:

### 1. GET /api/courses

**Purpose:** List all courses with optional filtering
**Proxies:** `GET http://localhost:8000/api/courses`
**Query Params:**
- `subject` (optional): Filter by subject code (e.g., "CSCI")
- `limit` (optional): Max results (default: 100)
- `offset` (optional): Pagination offset

**Response Schema:**
```typescript
{
  courses: Course[],
  total: number,
  term_code: string
}
```

### 2. GET /api/courses/search

**Purpose:** Search courses by code, title, or instructor
**Proxies:** `GET http://localhost:8000/api/courses/search`
**Query Params:**
- `q` (required): Search query string
- `limit` (optional): Max results (default: 20)

**Response Schema:**
```typescript
{
  results: Course[],
  total: number,
  query: string
}
```

### 3. GET /api/courses/[courseCode]

**Purpose:** Get single course details
**Proxies:** `GET http://localhost:8000/api/courses/{courseCode}`
**Path Param:** `courseCode` (e.g., "CSCI-141" or "BUS-203")

**Response Schema:**
```typescript
Course
```

### 4. GET /api/subjects

**Purpose:** List all available subject codes
**Proxies:** `GET http://localhost:8000/api/subjects`

**Response Schema:**
```typescript
{
  subjects: string[],
  total: number
}
```

### 5. GET /api/term

**Purpose:** Get current term information
**Proxies:** `GET http://localhost:8000/api/term`

**Response Schema:**
```typescript
{
  current: {
    term_code: string,
    display_name: string,
    is_registration: boolean
  },
  next_transition: {
    date: string,
    next_term: string,
    next_semester: string
  }
}
```

## Data Flow

### Request Lifecycle

1. **Component renders** → Calls `fetch('/api/courses')`
2. **Next.js API Route** → Receives request on server side
3. **Proxy Handler** → Forwards to `http://localhost:8000/api/courses`
4. **Backend** → Queries Firebase, returns course data
5. **API Route** → Receives backend response
6. **Transform** → Converts backend format to frontend types (if needed)
7. **Respond** → Sends data back to component
8. **Component** → Updates state, renders courses

### Error Flow

1. **Backend Down/Error** → API route catches error
2. **Fallback Logic** → Returns mock data with warning flag
3. **Component** → Displays data with optional "Using cached data" message
4. **User** → Can still use the app with mock data

## Frontend Component Changes

### Components to Update

**1. ScheduleBuilder (`src/components/student/ScheduleBuilder.tsx`)**
- Replace `mockAvailableCourses` import with `fetch('/api/courses')`
- Add loading state while fetching
- Add error state with fallback to mock data
- Update on mount to fetch real courses

**2. CourseList (`src/components/student/CourseList.tsx`)**
- Accept optional `courseIds` prop to fetch specific courses
- Add `fetchCourseDetails` function to get real course info
- Keep mock data for course status (completed/current) since backend doesn't track this
- Display real course titles, credits, descriptions from backend

**3. StudentDashboard (`src/app/student/page.tsx`)**
- Fetch available courses on mount
- Pass real data to ScheduleBuilder
- Keep mock data for student profile, progress, chat

**4. New Component: CourseSearch**
- Create new search component using `/api/courses/search`
- Add to student dashboard as new feature
- Show search results with course details

### Type Compatibility

Backend's `CourseResponse` matches frontend's `Course` type with minor differences:
- Backend uses `course_code`, frontend expects `code`
- Backend has `sections[]` array, frontend might not use initially
- Need type adapter utility to convert backend → frontend format

## Error Handling & Loading States

### Loading States

All data-fetching components will show:
- **Initial Load:** Skeleton UI or spinner
- **Subsequent Loads:** Subtle loading indicator
- **Empty State:** "No courses found" message

### Error Handling Strategy

**Level 1: API Route Error Handling**
```typescript
try {
  const response = await fetch(backendUrl);
  return await response.json();
} catch (error) {
  console.error('Backend error:', error);
  return { courses: mockData, isFromMock: true };
}
```

**Level 2: Component Error Handling**
```typescript
const [error, setError] = useState(null);
const [isUsingMockData, setIsUsingMockData] = useState(false);

// Display banner if using mock data
{isUsingMockData && (
  <Banner variant="warning">
    Using cached course data. Live data unavailable.
  </Banner>
)}
```

**Level 3: User Feedback**
- Toast notifications for transient errors
- Inline error messages for critical failures
- Graceful degradation to mock data

## Environment Configuration

### Backend (.env file exists)
Already configured with:
- `FIREBASE_PROJECT_ID`
- `FIREBASE_SERVICE_ACCOUNT_PATH`
- `REDIS_URL` (optional)

### Frontend (.env.local to create)
```env
# Backend API URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Feature flags
NEXT_PUBLIC_USE_MOCK_DATA_FALLBACK=true
NEXT_PUBLIC_ENABLE_COURSE_SEARCH=true

# Optional: API key if backend adds auth later
# BACKEND_API_KEY=your_key_here
```

### Configuration Utility

Create `src/lib/config.ts`:
```typescript
export const config = {
  backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000',
  useMockFallback: process.env.NEXT_PUBLIC_USE_MOCK_DATA_FALLBACK === 'true',
  enableCourseSearch: process.env.NEXT_PUBLIC_ENABLE_COURSE_SEARCH === 'true',
};
```

## Data Transformation

### Type Adapter Utility

Create `src/lib/adapters.ts` to convert backend types → frontend types:

```typescript
import { CourseResponse } from '@/types/backend';
import { Course } from '@/types';

export function adaptCourse(backendCourse: CourseResponse): Course {
  return {
    code: backendCourse.course_code,
    title: backendCourse.title,
    credits: backendCourse.credits,
    dept: backendCourse.subject_code,
    level: parseInt(backendCourse.course_number) || 0,
    hasLab: backendCourse.sections.some(s => s.section_number.includes('L')),
    difficultyIndex: 5, // Default; could calculate from course level
    prereqs: [], // Backend doesn't provide this yet
    description: backendCourse.description,
  };
}
```

## Mock Data Strategy

### Hybrid Approach

- **From Backend:** Course catalog, titles, credits, descriptions, sections
- **From Mock Data:** Student profiles, enrollment status, grades, chat history, advisor data

### Mock Data Retention

Keep `src/data/mockData.ts` for:
- `mockStudent` - student profile
- `mockMilestones` - degree progress
- `mockChatMessages` - AI chat history
- `mockAdvisees` - advisor portal data

### Fallback Logic

If backend is unavailable, API routes return mock course data with `isFromMock: true` flag.

## Testing Strategy

### Manual Testing Checklist

1. **Backend Running:**
   - Start backend: `cd backend && python server.py`
   - Verify: Visit `http://localhost:8000/api/courses`

2. **Frontend Running:**
   - Start frontend: `npm run dev`
   - Verify: Visit `http://localhost:3000`

3. **Course List:**
   - Navigate to student portal
   - Verify real course titles appear
   - Check course details are accurate

4. **Schedule Builder:**
   - Open schedule builder
   - Verify available courses from backend
   - Test adding courses to schedule

5. **Course Search:**
   - Use search feature (if enabled)
   - Verify search results
   - Test various search queries

6. **Error Scenarios:**
   - Stop backend server
   - Refresh frontend
   - Verify fallback to mock data
   - Verify error message displays

### Integration Test Points

- API routes proxy correctly
- Course data transforms properly
- Loading states appear
- Error states handled gracefully
- Mock fallback works
- No CORS issues (backend has CORS enabled for localhost:3000)

## Deployment for Demo

### Prerequisites
1. Backend Firebase configured with course data ✓
2. Node.js 18+ installed ✓
3. Python 3.x with backend dependencies ✓

### Demo Startup Steps

**Terminal 1 - Backend:**
```bash
cd backend
python server.py
# Runs on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd ../  # Back to root
npm run dev
# Runs on http://localhost:3000
```

**Verify Integration:**
1. Visit `http://localhost:3000`
2. Navigate to Student Portal
3. Check if real course names appear
4. Test schedule builder with real courses

## Future Enhancements

### Phase 2: Additional Backend Integration
- Student profile API endpoints
- Grade/transcript integration
- Enrollment status from Banner/SIS

### Phase 3: AI Features
- Chat backend with LLM integration
- Schedule optimization API
- Risk detection algorithms

### Phase 4: Production Deployment
- Deploy backend to cloud (Railway, Render, Fly.io)
- Update frontend env vars with production URL
- Add authentication/authorization
- Set up monitoring and logging

## Success Criteria

✅ Frontend displays real W&M course data
✅ Schedule builder uses backend course catalog
✅ Course search works with live data
✅ Error handling gracefully falls back to mock data
✅ Loading states provide good UX
✅ Demo runs smoothly on localhost
✅ Architecture allows easy future expansion

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Backend unavailable during demo | Mock data fallback |
| CORS issues | Backend already configured for localhost:3000 |
| Data format mismatch | Type adapter utility handles conversion |
| Slow backend responses | Add loading states and timeout handling |
| Firebase quota limits | Backend uses Redis caching |

---

**Next Steps:** Create implementation plan with specific tasks for building API routes and updating components.
