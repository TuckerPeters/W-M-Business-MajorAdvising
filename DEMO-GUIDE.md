# Backend Integration Demo Guide

## Quick Start

### Terminal 1: Start Backend
```bash
cd backend
python server.py
```
Backend runs on: **http://localhost:8000**

### Terminal 2: Start Frontend
```bash
cd ..  # Back to root directory
npm run dev
```
Frontend runs on: **http://localhost:3000**

## What's Connected

### ✅ Live Backend Data
- **Schedule Builder**: Shows real W&M courses from Firebase
- **Course Search**: Real-time search of course catalog
- **Course Details**: Live course information with sections, instructors, times

### 📦 Still Using Mock Data
- Student profiles and progress
- Enrollment status and grades
- AI chat messages
- Advisor portal data

## Testing the Integration

### 1. Check Backend is Running
Visit: http://localhost:8000/api/courses

You should see JSON with course data.

### 2. Open Frontend
Visit: http://localhost:3000

### 3. Navigate to Student Portal
Click "Enter Student Portal"

### 4. Check Status Banner
- **Green banner** = Connected to backend ✅
- **Yellow banner** = Using mock data (backend offline)

### 5. Test Schedule Builder
1. Click "Schedule Builder" in sidebar
2. Scroll through "Available Courses" list
3. Verify you see real W&M course names (not generic mock data)
4. Add courses to your schedule
5. See balance score update

### 6. Test with Backend Offline
1. Stop the backend server (Ctrl+C in Terminal 1)
2. Refresh the frontend
3. You should see yellow banner: "Using demo data"
4. App still works with mock data fallback

## API Routes Created

All routes proxy to backend and fallback to mock data on error:

- `GET /api/courses` - List courses (with filtering)
- `GET /api/courses/search?q=CSCI` - Search courses
- `GET /api/courses/[code]` - Get single course
- `GET /api/subjects` - List all subjects
- `GET /api/term` - Current term info

## Architecture

```
React Components
      ↓
  fetch('/api/...')
      ↓
Next.js API Routes (proxy layer)
      ↓
  fetch('http://localhost:8000/api/...')
      ↓
FastAPI Backend
      ↓
Firebase/Firestore
```

## Troubleshooting

### "Using demo data" banner shows
- **Check**: Is backend running? `http://localhost:8000/api/health`
- **Check**: Are Firebase credentials configured in backend/.env?
- **Check**: Backend logs for errors

### CORS errors
- Backend is configured for `http://localhost:3000`
- Make sure frontend is on port 3000

### No courses showing
- Check backend has data: `http://localhost:8000/api/courses`
- Check browser console for fetch errors
- Verify `.env.local` has correct `NEXT_PUBLIC_BACKEND_URL`

## Environment Variables

### Frontend (.env.local)
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK_DATA_FALLBACK=true
```

### Backend (.env)
Already configured with Firebase credentials.

## Demo Script

1. **Show landing page** - Dual portal design
2. **Show backend health** - `localhost:8000/api/health`
3. **Navigate to Student Portal** - Point out green "Live Data" banner
4. **Open Schedule Builder** - Show real W&M courses
5. **Add courses to schedule** - Demonstrate balance scoring
6. **Stop backend** - Show graceful fallback to mock data
7. **Restart backend** - Show reconnection

## Next Steps

### Phase 2: Additional Features
- Student profile API endpoints
- Real enrollment status from SIS
- Grade/transcript integration

### Phase 3: AI Integration
- Chat backend with LLM
- Schedule optimization API
- Risk detection algorithms

### Phase 4: Production
- Deploy backend to cloud (Railway, Render, Fly.io)
- Update frontend env vars
- Add authentication
- Set up monitoring
