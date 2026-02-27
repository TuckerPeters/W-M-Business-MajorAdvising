# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Next.js 15-based academic advising platform for William & Mary Business School. It provides a dual-portal system (Student & Advisor) for pre-major and major advising, built with TypeScript, React 18, and Tailwind CSS.

**Current State**: Frontend-only implementation with mock data. The application is designed for future backend integration but currently operates standalone for development.

## Development Commands

```bash
# Development server (runs on http://localhost:3000)
npm run dev

# Production build
npm run build

# Start production server (must run build first)
npm start

# Lint code
npm run lint
```

## Architecture

### Routing Structure

This project uses Next.js 15's App Router with the following structure:

- `/` - Landing page with portal selection (src/app/page.tsx)
- `/student` - Student portal dashboard (src/app/student/page.tsx)
- `/advisor` - Advisor portal dashboard (src/app/advisor/page.tsx)

All pages use the `'use client'` directive as they require client-side interactivity.

### Component Organization

**UI Components** (`src/components/ui/`):
- Reusable base components (Button, Card, Input, Badge, Progress)
- Built with composition patterns using `forwardRef` for ref forwarding
- Styled with Tailwind CSS using the `cn()` utility for conditional class merging
- Export multiple related components from single files (e.g., Card exports Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter)

**Domain Components**:
- `src/components/student/`: Student-specific features (ChatInterface, CourseList, ProgressPanel, ScheduleBuilder)
- `src/components/advisor/`: Advisor-specific features (AdviseeList, AdviseeDetail)

### Type System

All data models are defined in `src/types/index.ts`:
- `Student` - Student profile with academic records
- `Course` - Course details with prerequisites and difficulty metrics
- `ChatMessage` - AI chat interface with citations and next steps
- `Advisee` - Advisor's view of student with risk flags
- `Milestone` - Academic milestone tracking with completion status
- `ScheduleScore` - Schedule evaluation results

**Important**: Always use these types when working with data structures. Do not create inline types or duplicate definitions.

### Data Layer

**Mock Data** (`src/data/mockData.ts`):
- All mock data for development is centralized here
- Exports: `mockStudent`, `mockCompletedCourses`, `mockCurrentCourses`, `mockAvailableCourses`, `mockMilestones`, `mockChatMessages`, `mockAdvisees`
- When adding features, extend mock data here rather than hardcoding in components

### Utilities

**`src/lib/utils.ts`**:
- `cn()` - Combines `clsx` and `tailwind-merge` for conditional Tailwind class merging
- Usage: `cn('base-classes', condition && 'conditional-classes', className)`

### Path Aliases

TypeScript is configured with path alias `@/*` → `./src/*`
- Always use: `import { Component } from '@/components/ui/Component'`
- Never use: `import { Component } from '../../../components/ui/Component'`

## Styling Conventions

- **Tailwind CSS**: Primary styling method using utility classes
- **Color Scheme**: Green/yellow accent colors (`from-green-50 via-white to-yellow-50`)
- **Responsive**: Mobile-first with `md:` and `lg:` breakpoints
- **Dark Mode**: Tailwind's dark mode classes are used (`dark:from-gray-900`)
- **Icons**: Lucide React icon library

## Key Implementation Patterns

### Chat Interface (AI Integration Point)

The `ChatInterface` component in `src/components/student/ChatInterface.tsx` uses a simulated AI response with `setTimeout`. In production:
- Replace the `setTimeout` mock with API calls to backend
- Structure: POST to `/api/chat/message` with user input
- Expected response should include `content`, `citations`, `risks`, and `nextSteps`

### Risk Flags

Advisor portal uses `riskFlags` object on `Advisee` type:
- `overloadRisk`: Too many credits or difficult courses
- `missingPrereqs`: Enrolled in courses without prerequisites
- `gpaDip`: Recent GPA decline

When building features, check these flags to determine visual indicators and alert priorities.

### Prerequisites and Course Dependencies

Course objects include a `prereqs` array of course codes. When implementing schedule validation:
- Check that all courses in `prereqs` array are either completed or enrolled
- Course codes follow pattern: `DEPT ###` (e.g., "BUS 203", "STAT 250")

## Backend Integration Guidelines

While currently using mock data, the application expects these API patterns:

**Authentication**: SSO/OAuth integration point should be added to `src/app/layout.tsx`

**Expected API Endpoints**:
- `GET /api/student/profile` → `Student` type
- `GET /api/student/courses` → `Course[]` type
- `POST /api/chat/message` → `ChatMessage` type
- `GET /api/advisor/advisees` → `Advisee[]` type

**Environment Variables** (create `.env.local`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=your_api_key_here
```

## Data Privacy Considerations

This platform deals with FERPA-protected student data:
- Never log student personal information to console
- Ensure advisor portal checks proper authorization before displaying student data
- Student SSN, financial aid, and disciplinary records should never be included in API responses or UI

## Common Development Patterns

### Adding a New Student Feature
1. Define types in `src/types/index.ts` if needed
2. Add mock data to `src/data/mockData.ts`
3. Create component in `src/components/student/`
4. Import and use in `src/app/student/page.tsx`

### Adding a New UI Component
1. Create in `src/components/ui/`
2. Use `forwardRef` pattern for ref support
3. Accept `className` prop and merge with `cn()` utility
4. Use Tailwind for styling
5. Export multiple related components from single file if appropriate

### Working with Dates
- Mock data uses `new Date()` for timestamps
- Display dates using `toLocaleDateString()` or similar formatters
- Milestone deadlines use `Date` objects

## Testing Notes

No test suite is currently configured. When adding tests:
- Use Jest + React Testing Library
- Test student/advisor components separately
- Mock the mock data module for consistent test data
- Focus on interaction flows (chat, schedule building, risk flag display)
