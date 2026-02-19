# W&M Business Advising Platform - Project Status Report
**Date:** February 17, 2026
**Status:** Phase 1 Complete - Backend Integration Operational

---

## Executive Summary

The W&M Business Advising Platform has successfully completed Phase 1: Frontend Development and Course Catalog Integration. The platform now features a fully functional dual-portal system (Student & Advisor) with live course data from the W&M course catalog. The next phases require institutional data access and authentication integration.

---

## ✅ Completed Work

### Phase 0: Foundation (Complete)
**Frontend Architecture**
- ✅ Next.js 15 with App Router implementation
- ✅ TypeScript type system for all data models
- ✅ Tailwind CSS responsive design system
- ✅ Component library (Cards, Buttons, Inputs, Badges, Progress)
- ✅ Dark mode support

**Portal Implementations**
- ✅ Landing page with portal selection
- ✅ Student Portal dashboard with 3 main views:
  - Overview (progress tracking, course lists)
  - Schedule Builder (course planning with balance scoring)
  - AI Chat Interface (simulated)
- ✅ Advisor Portal dashboard with:
  - Advisee list with risk indicators
  - Detailed student profiles
  - Aggregate statistics dashboard
  - Quick actions panel

**Mock Data System**
- ✅ Comprehensive mock data for development
- ✅ Student profiles, courses, milestones, chat history
- ✅ Advisor-advisee relationships
- ✅ Risk flag simulation

### Phase 1: Backend Integration (Complete ✅)
**Course Catalog Backend**
- ✅ FastAPI server with REST endpoints
- ✅ Firebase/Firestore database integration
- ✅ Course data collection and storage
- ✅ Automatic updates via scheduler
- ✅ Redis caching layer (optional)

**API Infrastructure**
- ✅ 5 Next.js API routes (proxy layer):
  - `/api/courses` - List courses with filtering
  - `/api/courses/search` - Search functionality
  - `/api/courses/[code]` - Single course details
  - `/api/subjects` - Subject code listing
  - `/api/term` - Current term information
- ✅ Type-safe data transformation (backend → frontend)
- ✅ Error handling with automatic fallback to mock data
- ✅ Loading states and status indicators
- ✅ CORS configuration for local development

**Integration Features**
- ✅ Real W&M course data in Schedule Builder
- ✅ Live course search functionality
- ✅ Graceful degradation when backend unavailable
- ✅ Status banners (green = live data, yellow = mock data)

**Deployment**
- ✅ Local development environment configured
- ✅ Both servers running and connected
- ✅ Firebase credentials configured
- ✅ Demo-ready state

---

## 📊 Current Capabilities

### What Works Now (Live Data)
1. **Course Catalog**: Real W&M courses from Banner/FOSE
   - Course codes, titles, descriptions
   - Credit hours and attributes
   - Section details (CRN, instructor, capacity)
   - Meeting times and locations
   - Enrollment status (open/closed)

2. **Schedule Builder**: Full functionality with real courses
   - Browse available courses by subject
   - Search for specific courses
   - Add/remove courses from schedule
   - Balance score calculation (credits, difficulty, labs)
   - Workload warnings

3. **Term Management**: Current semester tracking
   - Automatic term detection
   - Registration period status

### What's Still Simulated (Mock Data)
1. **Student Data**: Profiles, enrollment, grades
2. **AI Chat**: Responses and recommendations
3. **Progress Tracking**: Degree completion status
4. **Advisor Features**: Student notes, communication history

---

## 🔄 Phases 2-4: Remaining Work

### Phase 2: Authentication & Student Data Integration
**Priority: HIGH | Estimated: 4-6 weeks**

#### 2.1 Authentication System
**Status:** Not Started
**Dependencies:** W&M IT approval and SSO credentials

**Requirements from W&M:**
- ✋ **REQUIRED:** SSO/Shibboleth integration credentials
- ✋ **REQUIRED:** SAML 2.0 configuration details
- ✋ **REQUIRED:** Test accounts for development

**Implementation Tasks:**
- [ ] NextAuth.js or Auth0 integration
- [ ] SAML/Shibboleth provider configuration
- [ ] Session management and token handling
- [ ] Role-based access control (RBAC)
  - Student role
  - Advisor role
  - Admin role
- [ ] Protected routes and API endpoints
- [ ] Login/logout flow
- [ ] Session timeout handling

**Estimated Effort:** 2 weeks

---

#### 2.2 Student Information System (SIS) Integration
**Status:** Not Started
**Dependencies:** Banner API access, FERPA compliance approval

**Requirements from W&M:**
- ✋ **REQUIRED:** Banner Student API access credentials
- ✋ **REQUIRED:** Banner Web Services documentation
- ✋ **REQUIRED:** Data access authorization (FERPA compliance)
- ✋ **REQUIRED:** Test Banner environment access
- ✋ **REQUIRED:** FERPA training for developers
- ✋ **REQUIRED:** Data governance review and approval

**Data Access Needed:**
1. **Student Profile Data**
   - Student ID (W&M ID)
   - Name, email
   - Class year, declared major(s)
   - Academic advisor assignment
   - Academic standing (good standing, probation, etc.)

2. **Academic Records**
   - Current enrollment (courses, sections, credits)
   - Historical transcripts (all completed courses)
   - Grades (by term)
   - GPA (overall, major, by term)
   - Transfer credits
   - AP/IB credit awards

3. **Degree Audit Data**
   - Degree requirements (by major/minor)
   - Requirement completion status
   - Outstanding requirements
   - In-progress requirement tracking

4. **Registration Data**
   - Current registration status
   - Registration holds
   - Add/drop history
   - Waitlist status

**Implementation Tasks:**
- [ ] Banner API client development
- [ ] Data synchronization jobs
  - Student profile sync (daily)
  - Enrollment sync (hourly during registration)
  - Grade sync (after each term)
- [ ] Backend endpoints for student data
  - `GET /api/student/profile`
  - `GET /api/student/transcript`
  - `GET /api/student/enrollment`
  - `GET /api/student/degree-audit`
- [ ] Frontend integration
  - Replace mock student data
  - Real-time enrollment display
  - Historical grade visualization
- [ ] Data caching strategy
- [ ] Privacy controls and data masking

**Estimated Effort:** 3-4 weeks

---

### Phase 3: AI-Powered Advising Features
**Priority: HIGH | Estimated: 6-8 weeks**

#### 3.1 AI Chat Backend
**Status:** Not Started
**Dependencies:** OpenAI/Anthropic API access, document corpus

**Requirements from W&M:**
- ✋ **REQUIRED:** Official advising documentation
  - Business School major requirements (all concentrations)
  - Pre-major requirements and timeline
  - Course catalog PDFs
  - Academic policies and procedures
  - Registration guides
  - Frequently asked questions
- ✋ **REQUIRED:** Legal review of AI-generated advice
- ✋ **REQUIRED:** Advisor oversight protocol approval

**Technical Requirements:**
- OpenAI API key or Anthropic API key (Claude)
- Vector database for document storage (Pinecone, Weaviate, or Qdrant)
- Document processing pipeline

**Implementation Tasks:**
- [ ] Document collection and ingestion
  - Convert PDFs to structured text
  - Chunk documents appropriately
  - Generate embeddings
  - Store in vector database
- [ ] RAG (Retrieval-Augmented Generation) system
  - Semantic search implementation
  - Context retrieval from documents
  - Prompt engineering for accurate responses
- [ ] Chat API development
  - `POST /api/chat/message` - Send message, get AI response
  - `GET /api/chat/history/:studentId` - Retrieve chat history
  - `POST /api/chat/feedback` - Collect response ratings
- [ ] Response validation
  - Source citation tracking
  - Confidence scoring
  - Advisor review flagging
- [ ] Frontend chat enhancements
  - Real AI streaming responses
  - Citation display
  - Copy/share functionality
  - Feedback mechanism

**Estimated Effort:** 4-5 weeks

---

#### 3.2 Schedule Optimization AI
**Status:** Not Started
**Dependencies:** Historical enrollment data, prerequisite mapping

**Requirements from W&M:**
- ✋ **RECOMMENDED:** Historical course offering patterns (3-5 years)
- ✋ **RECOMMENDED:** Course prerequisite graph/data
- ✋ **RECOMMENDED:** Course difficulty/workload surveys
- ✋ **RECOMMENDED:** Section enrollment patterns

**Implementation Tasks:**
- [ ] Prerequisite validation engine
- [ ] Conflict detection (time, requirements)
- [ ] Workload balancing algorithm
- [ ] Multi-semester planning
- [ ] "What-if" scenario modeling
- [ ] Schedule scoring improvements
- [ ] Alternative schedule suggestions

**Estimated Effort:** 3 weeks

---

#### 3.3 Risk Detection & Early Alerts
**Status:** Not Started
**Dependencies:** Historical student data, advisor intervention protocols

**Requirements from W&M:**
- ✋ **RECOMMENDED:** Historical student success/struggle patterns
- ✋ **RECOMMENDED:** Advisor intervention guidelines
- ✋ **RECOMMENDED:** Academic support service catalog

**Risk Indicators to Implement:**
- Course overload (credits, difficulty)
- Missing prerequisites
- GPA decline trends
- Repeated course attempts
- Late/missed major declaration
- Off-track for graduation
- Academic probation risk

**Implementation Tasks:**
- [ ] Risk scoring algorithm development
- [ ] Alert threshold configuration
- [ ] Advisor notification system
- [ ] Student nudge/reminder system
- [ ] Integration with academic support services
- [ ] Dashboard analytics for advisors

**Estimated Effort:** 2-3 weeks

---

### Phase 4: Production Deployment & Scaling
**Priority: MEDIUM | Estimated: 4-6 weeks**

#### 4.1 Infrastructure Setup
**Status:** Not Started
**Dependencies:** W&M hosting approval or cloud budget

**Requirements from W&M:**
- ✋ **REQUIRED:** Deployment approval (on-prem vs cloud)
- ✋ **REQUIRED:** Security review and penetration testing
- ✋ **REQUIRED:** Accessibility audit (WCAG 2.1 AA compliance)
- ✋ **REQUIRED:** Production domain name (e.g., advising.business.wm.edu)
- ✋ **REQUIRED:** SSL certificate

**Deployment Options:**
1. **Cloud Deployment** (Recommended)
   - Frontend: Vercel or Netlify (Next.js optimized)
   - Backend: Railway, Render, or Fly.io
   - Database: Firebase/Firestore (already set up)
   - Pros: Easier scaling, automatic SSL, CDN, monitoring
   - Cons: Monthly cost (~$50-150/month)

2. **On-Premises Deployment**
   - W&M's own servers
   - Requires IT support for maintenance
   - Pros: Full control, no external dependencies
   - Cons: More complex, requires DevOps resources

**Implementation Tasks:**
- [ ] Environment setup (staging, production)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Database backup strategy
- [ ] Monitoring and logging (Sentry, LogRocket)
- [ ] Performance optimization
- [ ] Load testing
- [ ] Disaster recovery plan

**Estimated Effort:** 3-4 weeks

---

#### 4.2 Security & Compliance
**Status:** Partially Complete (development security only)

**Requirements from W&M:**
- ✋ **REQUIRED:** FERPA compliance review
- ✋ **REQUIRED:** Security audit
- ✋ **REQUIRED:** Data retention policy approval
- ✋ **REQUIRED:** Incident response plan
- ✋ **REQUIRED:** User privacy policy and terms of service

**Implementation Tasks:**
- [ ] FERPA compliance audit
  - Data encryption (in transit, at rest)
  - Access logging and audit trails
  - User consent management
  - Data anonymization for analytics
- [ ] Security hardening
  - Rate limiting on all endpoints
  - SQL injection prevention (using ORMs)
  - XSS protection (sanitization)
  - CSRF tokens
  - Security headers (CSP, HSTS, etc.)
- [ ] Penetration testing
- [ ] Vulnerability scanning (Snyk, Dependabot)
- [ ] Privacy policy and terms of service
- [ ] Cookie consent banner

**Estimated Effort:** 2-3 weeks

---

#### 4.3 User Acceptance Testing & Training
**Status:** Not Started

**Requirements from W&M:**
- ✋ **REQUIRED:** Beta tester group (5-10 advisors, 20-30 students)
- ✋ **REQUIRED:** Feedback collection plan
- ✋ **REQUIRED:** Training materials approval

**Implementation Tasks:**
- [ ] Beta testing program
  - Recruit advisors and students
  - Collect feedback via surveys
  - Bug reporting system
  - Feature request tracking
- [ ] User documentation
  - Student user guide
  - Advisor user guide
  - FAQ documentation
  - Video tutorials
- [ ] Training sessions
  - Advisor training workshops
  - Student orientation sessions
  - Support staff training
- [ ] Support system setup
  - Help desk integration
  - In-app support chat
  - Email support address

**Estimated Effort:** 2-3 weeks

---

## 🔐 Data Access Requirements from W&M

### Critical (Phase 2 Blockers)

#### 1. Single Sign-On (SSO) Integration
**Contact:** W&M IT - Identity & Access Management
**Timeline:** Request 4-6 weeks before Phase 2 start

**What to Request:**
- Shibboleth/SAML 2.0 integration documentation
- Service Provider (SP) registration
- Test IdP (Identity Provider) access
- Production IdP endpoint details
- Attribute release policy
  - W&M ID (required)
  - Name (required)
  - Email (required)
  - Student/Faculty/Staff role (required)
  - Class year (for students)
  - Department (for advisors)

**Documentation Needed:**
- SSO implementation guide
- Attribute mapping specification
- Test account provisioning process

---

#### 2. Banner Student API Access
**Contact:** W&M IT - Enterprise Applications / Registrar's Office
**Timeline:** Request 6-8 weeks before Phase 2 start (requires FERPA approval)

**What to Request:**
- Banner Web Services API documentation
- API endpoint URLs (test and production)
- API credentials (service account)
- Rate limits and SLA
- Test environment access
- Sample API responses

**Data Access Authorization:**
- Student demographic data (name, ID, email, class year)
- Academic records (transcripts, grades, GPA)
- Enrollment data (current and historical)
- Degree audit data
- Academic standing
- Registration holds

**Compliance Requirements:**
- FERPA training for all developers
- Data use agreement
- Security requirements review
- Data retention policy acknowledgment

---

#### 3. Course Catalog & Scheduling Data
**Status:** ✅ Already have this (via current backend)
**Source:** Banner Course Catalog / FOSE API

**Current Access:**
- Course offerings by term
- Section details (times, instructors, capacity)
- Enrollment counts
- Course attributes

**Additional Needed (Phase 3):**
- Course prerequisite chains
- Historical offering patterns (last 3-5 years)
- Course difficulty ratings (if available)

---

### Important (Phase 3 Enhancements)

#### 4. Advising Documentation & Policies
**Contact:** Business School - Director of Advising
**Timeline:** Request 4 weeks before Phase 3 start

**Documents to Collect:**
- Major requirement sheets (all concentrations)
  - Accounting
  - Business Analytics
  - Finance
  - International Business
  - Management
  - Marketing
- Pre-major requirements and timeline
- Course sequencing guidelines
- Double major policies
- Minor requirements
- Study abroad credit transfer policies
- AP/IB credit acceptance policies
- Academic standing policies
- Registration procedures
- Add/drop deadlines
- Graduation requirements

**Format Needed:**
- PDF versions (for RAG system)
- Structured data (if available)
- Latest version with date stamps

---

#### 5. Historical Student Data (Anonymized)
**Contact:** Institutional Research / Registrar's Office
**Timeline:** Request 6-8 weeks before Phase 3 start
**Purpose:** AI model training and risk detection

**What to Request (De-identified/Aggregated):**
- Course enrollment patterns (3-5 years)
- Grade distributions by course
- Time-to-graduation data by major
- Course difficulty rankings (student surveys)
- Common course sequences
- Success/struggle indicators
  - Courses with high drop rates
  - Courses with low pass rates
  - GPA decline patterns
- Major declaration timing
- Academic support service utilization

**Privacy Requirements:**
- All data must be anonymized
- No personally identifiable information (PII)
- Aggregate statistics only
- Institutional Review Board (IRB) approval may be needed

---

### Nice-to-Have (Phase 4 Optimization)

#### 6. Advisor Directory & Assignment Data
**Contact:** Business School Advising Office
**What to Request:**
- Advisor roster (name, email, photo)
- Student-advisor assignments
- Advisor availability/office hours
- Advisor specializations (study abroad, pre-law, etc.)

---

#### 7. Academic Calendar Integration
**Contact:** Registrar's Office
**What to Request:**
- Academic calendar API (if available)
- Registration dates
- Add/drop deadlines
- Break periods
- Final exam schedule

---

#### 8. Academic Support Services Data
**Contact:** Dean of Students / Academic Success Office
**What to Request:**
- Tutoring services catalog
- Writing center resources
- Career services information
- Study abroad office data
- For integration into AI recommendations

---

## 📋 Action Items for W&M Administration

### Immediate (Next 2 Weeks)
- [ ] Assign project sponsor (likely Assistant/Associate Dean)
- [ ] Form steering committee
  - IT representative
  - Registrar representative
  - FERPA compliance officer
  - Business School advising director
  - Student representative
- [ ] Schedule kickoff meeting for Phase 2 planning
- [ ] Begin SSO integration request process
- [ ] Initiate FERPA training for development team

### Short-Term (Next 4-6 Weeks)
- [ ] Complete data governance review
- [ ] Approve Banner API access request
- [ ] Provide SSO integration credentials
- [ ] Deliver advising documentation corpus
- [ ] Establish security review process
- [ ] Define success metrics and KPIs

### Medium-Term (Next 8-12 Weeks)
- [ ] Beta testing group recruitment
- [ ] Legal review of AI-generated content policies
- [ ] Accessibility audit planning
- [ ] Production deployment approval
- [ ] User training plan development
- [ ] Support resources allocation

---

## 📊 Project Timeline

### Completed
- **Phase 0:** Frontend Development (Complete)
- **Phase 1:** Course Catalog Integration (Complete ✅)

### Upcoming
- **Phase 2:** Authentication & SIS Integration
  - Start Date: TBD (pending W&M approvals)
  - Duration: 4-6 weeks
  - Blockers: SSO credentials, Banner API access

- **Phase 3:** AI Features
  - Start Date: After Phase 2 completion
  - Duration: 6-8 weeks
  - Blockers: Advising documentation, API access

- **Phase 4:** Production Deployment
  - Start Date: After Phase 3 completion
  - Duration: 4-6 weeks
  - Blockers: Security review, hosting approval

### Total Estimated Timeline
**14-20 weeks** (3.5-5 months) from Phase 2 start to production launch

---

## 💰 Budget Considerations

### Infrastructure Costs (Annual)
- **Cloud Hosting:** $600-1,800/year
  - Frontend (Vercel): $240/year
  - Backend (Railway/Render): $360-1,200/year
  - Firebase: $0-360/year (depends on usage)
- **AI API Costs:** $500-2,000/year
  - OpenAI/Anthropic: $0.50-2.00 per 1,000 student queries
  - Estimated 100,000-500,000 queries/year
- **Monitoring & Analytics:** $0-600/year
  - Sentry error tracking
  - LogRocket user analytics
- **Domain & SSL:** $20-100/year

**Total Estimated:** $1,120-4,500/year

### On-Premises Alternative
- Infrastructure: $0 (W&M servers)
- Maintenance: Staff time (2-4 hours/week)
- AI Costs: Still $500-2,000/year

### One-Time Costs
- Security audit: $2,000-5,000
- Penetration testing: $3,000-8,000
- Accessibility audit: $1,500-3,000
- **Total:** $6,500-16,000

---

## 🎯 Success Metrics

### Technical Metrics
- System uptime: >99.5%
- Page load time: <2 seconds
- API response time: <500ms
- Error rate: <0.1%

### User Engagement Metrics
- Student adoption rate: Target 60% in first semester
- Advisor adoption rate: Target 80% in first semester
- Average session duration: Target 5-10 minutes
- Return user rate: Target 40% weekly active users

### Advising Outcomes
- Reduction in advising appointment wait times
- Increase in on-time major declaration
- Reduction in prerequisite errors
- Improvement in 4-year graduation rate

---

## 🚨 Risks & Mitigation

### High Risk
1. **FERPA Compliance Delays**
   - Risk: Approval process takes longer than expected
   - Mitigation: Start process early, engage compliance office proactively

2. **Banner API Limitations**
   - Risk: API doesn't provide all needed data
   - Mitigation: Identify data gaps early, plan workarounds

3. **AI Hallucination/Errors**
   - Risk: AI provides incorrect advising information
   - Mitigation: Mandatory advisor review, clear disclaimers, confidence scoring

### Medium Risk
4. **Student Privacy Concerns**
   - Risk: Students reluctant to use system
   - Mitigation: Transparent privacy policy, opt-in features, strong encryption

5. **Advisor Resistance**
   - Risk: Advisors see AI as replacement rather than tool
   - Mitigation: Position as advisor augmentation, provide training, gather feedback

6. **Scalability Issues**
   - Risk: System can't handle peak registration periods
   - Mitigation: Load testing, auto-scaling infrastructure, caching

---

## 📞 Next Steps & Contacts

### Development Team
- **Lead Developer:** [Your Name]
- **Project Manager:** [TBD]
- **UX Designer:** [TBD]

### W&M Contacts to Engage
1. **IT Department**
   - Identity & Access Management (SSO)
   - Enterprise Applications (Banner API)
   - Information Security (Security review)

2. **Registrar's Office**
   - Data access approval
   - Banner API coordination
   - Academic calendar integration

3. **Business School**
   - Director of Advising
   - Associate Dean for Academic Programs
   - Faculty advising committee

4. **Compliance**
   - FERPA compliance officer
   - Legal counsel
   - Data governance office

5. **Institutional Research**
   - Historical data requests
   - Success metrics tracking

---

## Conclusion

The W&M Business Advising Platform has successfully completed its foundational phases and is ready for institutional integration. The next critical step is securing data access approvals and authentication credentials from W&M IT and administrative offices.

**Immediate Priority:** Schedule meetings with W&M IT, Registrar's Office, and Business School leadership to begin Phase 2 planning and approval processes.

**Timeline to Production:** With prompt approvals, the platform could be production-ready in 4-5 months, targeting a Fall 2026 soft launch with Business School students.

---

**Report Generated:** February 17, 2026
**Last Updated:** February 17, 2026
**Version:** 1.0
