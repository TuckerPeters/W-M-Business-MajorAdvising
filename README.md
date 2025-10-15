# University Business Advising Platform - Frontend

A modern, AI-powered academic advising platform built with Next.js, React, and TypeScript. This frontend demonstrates a dual-portal system for students and academic advisors to streamline pre-major advising, course planning, and degree requirement tracking.

## Overview

This platform provides an intelligent interface for academic advising with two distinct user experiences:

### Student Portal
- **AI Chat Assistant**: Interactive chat interface for instant answers about course requirements, degree planning, and major declaration
- **Progress Tracking**: Visual dashboard showing credits earned, GPA, and milestone completion
- **Schedule Builder**: Drag-and-drop course planning with prerequisite validation and workload balancing
- **Personalized Recommendations**: Smart suggestions for courses based on academic history and goals

### Advisor Portal
- **Advisee Dashboard**: Comprehensive view of all assigned students with risk indicators
- **Detailed Student Profiles**: In-depth analysis of individual student progress, course history, and academic standing
- **Risk Monitoring**: Automated flagging of students with course overload, missing prerequisites, or GPA concerns
- **Communication Tools**: Interface for tracking advisor-student interactions and sending targeted reminders

## Technology Stack

### Frontend Framework
- **Next.js 15**: React framework with App Router for server-side rendering and routing
- **React 18**: Component-based UI library
- **TypeScript**: Type-safe development

### Styling
- **Tailwind CSS**: Utility-first CSS framework for responsive design
- **Lucide React**: Modern icon library
- **CSS Modules**: Component-scoped styling

### UI Components
- Custom-built reusable components including:
  - Cards, Buttons, Inputs
  - Progress indicators
  - Badges and status displays
  - Responsive navigation

## Project Structure

```
public-frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx           # Landing page with portal selection
│   │   ├── student/           # Student portal routes
│   │   │   └── page.tsx       # Student dashboard
│   │   └── advisor/           # Advisor portal routes
│   │       └── page.tsx       # Advisor dashboard
│   ├── components/
│   │   ├── ui/                # Reusable UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Badge.tsx
│   │   │   └── Progress.tsx
│   │   ├── student/           # Student-specific components
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── CourseList.tsx
│   │   │   ├── ProgressPanel.tsx
│   │   │   └── ScheduleBuilder.tsx
│   │   └── advisor/           # Advisor-specific components
│   │       ├── AdviseeList.tsx
│   │       └── AdviseeDetail.tsx
│   ├── data/
│   │   └── mockData.ts        # Sample data for development
│   ├── lib/
│   │   └── utils.ts           # Utility functions
│   └── types/
│       └── index.ts           # TypeScript type definitions
├── public/                     # Static assets
├── package.json               # Dependencies and scripts
├── tsconfig.json              # TypeScript configuration
├── tailwind.config.ts         # Tailwind CSS configuration
└── next.config.mjs            # Next.js configuration
```

## Key Features

### 1. AI-Powered Chat Interface
The student portal includes an interactive chat component designed to integrate with an AI backend. Students can:
- Ask questions about course requirements
- Get personalized schedule recommendations
- Receive guidance on major declaration
- Access source-grounded answers with citations

### 2. Smart Schedule Building
The schedule builder provides:
- Visual course selection and planning
- Prerequisite validation
- Credit hour balancing
- Difficulty distribution analysis
- Conflict detection (time slots, course restrictions)

### 3. Progress Visualization
Students can track:
- Overall credit completion toward graduation
- Major/minor requirements
- GPA trends
- Upcoming milestones and deadlines

### 4. Advisor Risk Management
Advisors receive:
- Real-time alerts for at-risk students
- Aggregate views of advisee cohorts
- Historical tracking of advisor-student interactions
- Tools to override AI recommendations when necessary

## Backend Integration (Not Included)

This frontend is designed to integrate with a backend system that would provide:

### Data Management
- **Student Records**: SSO authentication, transcript data, enrollment history
- **Course Catalog**: Real-time course offerings, prerequisites, scheduling data
- **Academic Policies**: Degree requirements, major/minor rules, academic regulations

### AI Services
- **Natural Language Processing**: Chat interface powered by large language models
- **Schedule Optimization**: Algorithms for balanced course load recommendations
- **Risk Detection**: Analytics for identifying students who need advisor intervention
- **Document Retrieval**: RAG (Retrieval-Augmented Generation) system for grounding AI responses in official university documentation

### API Endpoints (Expected)
```
Authentication:
POST /api/auth/login
POST /api/auth/logout

Student Data:
GET /api/student/profile
GET /api/student/courses
GET /api/student/progress

Advising:
POST /api/chat/message
GET /api/chat/history
POST /api/schedule/evaluate
GET /api/schedule/recommendations

Advisor Functions:
GET /api/advisor/advisees
GET /api/advisor/student/:id
POST /api/advisor/notes
GET /api/advisor/alerts
```

### Security Considerations
The backend should implement:
- Role-based access control (RBAC)
- Data encryption in transit and at rest
- FERPA compliance for student data
- Audit logging for all data access
- Rate limiting on AI endpoints

## Getting Started

### Prerequisites
- Node.js 18+ and npm/yarn
- Modern web browser

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

The application will be available at `http://localhost:3000`

### Development Mode
In development mode, the application uses mock data defined in `src/data/mockData.ts`. This allows for frontend development without a backend connection.

## Configuration

### Environment Variables
Create a `.env.local` file for local development:

```env
# API Configuration (when backend is available)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=your_api_key_here

# Feature Flags
NEXT_PUBLIC_ENABLE_AI_CHAT=true
NEXT_PUBLIC_ENABLE_SCHEDULE_BUILDER=true
```

### Tailwind Configuration
The `tailwind.config.ts` file can be customized to match your institution's branding:
- Color scheme
- Typography
- Spacing and sizing
- Breakpoints

## Mock Data

For demonstration purposes, the application includes mock data representing:
- Sample student profiles
- Course catalogs with prerequisites
- Historical grades and enrollments
- Advisor-advisee relationships
- Chat conversation history

This data can be found in `src/data/mockData.ts` and should be replaced with real API calls in production.

## Component Architecture

### Type System
All data structures are strongly typed using TypeScript interfaces defined in `src/types/index.ts`:
- `Student`: Student profile and academic record
- `Course`: Course details and requirements
- `ChatMessage`: AI chat interaction structure
- `Advisee`: Advisor's view of student data
- `Milestone`: Academic milestone tracking

### UI Components
Base UI components follow a consistent pattern:
- Composable and reusable
- Typed props with TypeScript
- Responsive by default
- Accessible (ARIA labels, keyboard navigation)

## Roadmap & Potential Enhancements

### Phase 1: Core Functionality (Current)
- Landing page with portal selection
- Student dashboard with progress tracking
- Advisor dashboard with advisee list
- Mock data integration

### Phase 2: Backend Integration
- API client setup
- Authentication flow
- Real-time data fetching
- Error handling and loading states

### Phase 3: Advanced Features
- Real-time AI chat with streaming responses
- Interactive schedule builder with drag-and-drop
- Push notifications for important deadlines
- Mobile responsive design optimization
- Accessibility audit and improvements

### Phase 4: Analytics & Reporting
- Advisor analytics dashboard
- Student success metrics
- Usage tracking
- A/B testing framework

## Contributing

This is a demonstration frontend. If you're adapting it for your institution:

1. Update branding (colors, logos, institution name)
2. Customize data models to match your student information system
3. Integrate with your authentication system (SSO/SAML/OAuth)
4. Connect to your course catalog and registration systems
5. Implement appropriate data privacy controls

## License

This project is provided as-is for educational and demonstration purposes.

## Support

For questions about implementation or architecture decisions, please open an issue in the repository.

---

**Note**: This frontend is a demonstration of UI/UX patterns for an academic advising system. It requires a backend implementation to function in a production environment. The mock data and placeholder API calls are for development purposes only.
