// Direct calls to Python backend — no Next.js proxy layer

import { getAuthToken, getCurrentUserId } from './firebase';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

function getStudentId(): string {
  return getCurrentUserId('demo-student');
}

function getAdvisorId(): string {
  return getCurrentUserId('demo-advisor');
}

async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const { headers: extraHeaders, ...restOptions } = options || {};

  const token = await getAuthToken();
  const authHeaders: Record<string, string> = {};
  if (token) {
    authHeaders['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BACKEND_URL}/api${endpoint}`, {
    ...restOptions,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...((extraHeaders as Record<string, string>) || {}),
    },
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(
      `API Error ${res.status}: ${errorText || res.statusText}`
    );
  }

  return res.json();
}

/* ========================
   Adapters
======================== */

function adaptEnrollment(enrollment: any) {
  const code = enrollment.courseCode || '';
  const parts = code.split(' ');
  return {
    enrollmentId: enrollment.id || undefined,
    code,
    title: enrollment.courseName || code,
    credits: enrollment.credits || 3,
    dept: parts[0] || '',
    level: parseInt(parts[1]) || 0,
    hasLab: false,
    difficultyIndex: 0,
    prereqs: [],
    term: enrollment.term,
    grade: enrollment.grade,
    status: enrollment.status,
    sectionNumber: enrollment.sectionNumber || undefined,
    crn: enrollment.crn || undefined,
    instructor: enrollment.instructor || undefined,
    meetingDays: enrollment.meeting_days || undefined,
    meetingTime: enrollment.meeting_time || undefined,
    building: enrollment.building || undefined,
    room: enrollment.room || undefined,
  };
}

function adaptCatalogCourse(course: any) {
  const code = course.course_code || '';
  const parts = code.split(' ');
  return {
    code,
    title: course.title || code,
    credits: course.credits || 3,
    dept: course.subject_code || parts[0] || '',
    level: parseInt(parts[1]) || 0,
    hasLab: (course.attributes || []).some((a: string) => /lab/i.test(a)),
    difficultyIndex: 0,
    prereqs: [],
    status: undefined,
    sections: (course.sections || []).map((s: any) => ({
      crn: s.crn || '',
      sectionNumber: s.section_number || '',
      instructor: s.instructor || '',
      status: s.status || '',
      capacity: s.capacity || 0,
      enrolled: s.enrolled || 0,
      available: s.available || 0,
      meetingDays: s.meeting_days || undefined,
      meetingTime: s.meeting_time || undefined,
      building: s.building || undefined,
      room: s.room || undefined,
    })),
  };
}

function adaptAssignment(assignment: any) {
  const student = assignment.student || {};
  return {
    id: student.userId || assignment.studentId,
    name: student.name || 'Unknown',
    email: student.email || '',
    classYear: student.classYear || 0,
    gpa: student.gpa || 0,
    creditsEarned: student.creditsEarned || 0,
    declared: student.declared || false,
    intendedMajor: student.intendedMajor || undefined,
    riskFlags: {
      overloadRisk: false,
      missingPrereqs: false,
      gpaDip: student.gpa != null && student.gpa < 2.0,
    },
    lastContact: assignment.assignedDate || undefined,
  };
}

/* ========================
   Student Endpoints
======================== */

export const getStudentProfile = async () => {
  const data = await apiRequest<any>(`/student/${getStudentId()}/profile`);
  return {
    name: data.name,
    major: data.intendedMajor || 'Undeclared',
    gpa: data.gpa,
    classYear: data.classYear,
    creditsEarned: data.creditsEarned,
    declared: data.declared,
    intendedMajor: data.intendedMajor,
    apCredits: data.apCredits,
  };
};

export const getCourseProgress = async () => {
  const [coursesData, milestonesData] = await Promise.all([
    apiRequest<any>(`/student/${getStudentId()}/courses`),
    apiRequest<any>(`/student/${getStudentId()}/milestones`),
  ]);
  return {
    currentCourses: (coursesData.current || []).map(adaptEnrollment),
    completedCourses: (coursesData.completed || []).map(adaptEnrollment),
    plannedCourses: (coursesData.planned || []).map(adaptEnrollment),
    milestones: milestonesData || [],
  };
};

export const getCourseCatalog = async (term?: string) => {
  const params = new URLSearchParams({ limit: '100', offset: '0' });
  if (term) params.set('term', term);
  const data = await apiRequest<{ courses: any[] }>(`/courses?${params}`);
  return { courses: (data.courses || []).map(adaptCatalogCourse) };
};

export const searchCourses = async (query: string) => {
  const data = await apiRequest<{ results: any[] }>(
    `/courses/search?q=${encodeURIComponent(query)}&limit=20`
  );
  return (data.results || []).map(adaptCatalogCourse);
};

/* ========================
   Advisor Endpoints
======================== */

export const getAdvisorProfile = async (advisorId: string = getAdvisorId()) => {
  const data = await apiRequest<any>(`/advisor/${advisorId}/profile`);
  return {
    name: data.name,
    email: data.email,
    department: data.department,
    office: data.office,
  };
};

export const getAdvisees = async (advisorId: string = getAdvisorId()) => {
  const assignments = await apiRequest<any[]>(`/advisor/${advisorId}/advisees`);
  return (assignments || []).map(adaptAssignment);
};

export const getStudentCoursesForAdvisor = async (studentId: string) => {
  const data = await apiRequest<any>(`/student/${studentId}/courses`);
  return {
    current: (data.current || []).map(adaptEnrollment),
    completed: (data.completed || []).map(adaptEnrollment),
    planned: (data.planned || []).map(adaptEnrollment),
  };
};

export const getStudentMilestonesForAdvisor = async (studentId: string) => {
  return apiRequest<any[]>(`/student/${studentId}/milestones`);
};

export const getCommonQuestions = async (limit: number = 5) => {
  const data = await apiRequest<{ questions: { text: string; count: number; conversationIds: string[] }[] }>(
    `/advisor/common-questions?limit=${limit}`
  );
  return data.questions || [];
};

export interface AdvisorAlert {
  type: string;
  severity: string;
  studentId: string;
  studentName: string;
  message: string;
  createdAt: string;
}

export const getAdvisorAlerts = async (advisorId: string = getAdvisorId()) => {
  const data = await apiRequest<AdvisorAlert[]>(`/advisor/${advisorId}/alerts`);
  return data || [];
};

export const assignAdvisee = async (studentId: string, advisorId: string = getAdvisorId()) => {
  const result = await apiRequest<any>(`/advisor/${advisorId}/advisees`, {
    method: "POST",
    body: JSON.stringify({ studentId }),
  });
  return adaptAssignment(result);
};

export const removeAdvisee = async (studentId: string, advisorId: string = getAdvisorId()) =>
  apiRequest<{ success: boolean; message: string }>(`/advisor/${advisorId}/advisees/${studentId}`, {
    method: "DELETE",
  });

const ADVISOR_HEADERS = { "X-User-Role": "advisor" };

export const getAdvisorConversations = async (advisorId: string = getAdvisorId()) => {
  const data = await apiRequest<{
    conversations: any[];
    total: number;
  }>(`/student/${advisorId}/conversations?limit=50`, {
    headers: ADVISOR_HEADERS,
  });
  return (data.conversations || []).map((c: any): ConversationSummary => ({
    id: c.id,
    title: c.title || 'New conversation',
    status: c.status,
    messageCount: c.messageCount || 0,
    updatedAt: c.updatedAt,
    lastMessagePreview: c.lastMessagePreview,
  }));
};

export const sendAdvisorChatMessage = async (message: string, conversationId?: string | null) =>
  apiRequest<{
    content: string;
    citations: any[];
    risks: any[];
    nextSteps: any[];
    conversationId: string;
  }>("/chat/message", {
    method: "POST",
    headers: ADVISOR_HEADERS,
    body: JSON.stringify({
      message,
      studentId: getAdvisorId(),
      conversationId: conversationId || undefined,
    }),
  });

export const deleteAdvisorConversation = async (conversationId: string) =>
  apiRequest<{ success: boolean; message: string }>(`/conversations/${conversationId}`, {
    method: "DELETE",
    headers: ADVISOR_HEADERS,
  });

/* ========================
   Conversation Endpoints
======================== */

export interface ConversationSummary {
  id: string;
  title: string;
  status: string;
  messageCount: number;
  updatedAt: string;
  lastMessagePreview?: string;
}

export const getConversations = async () => {
  const data = await apiRequest<{
    conversations: any[];
    total: number;
  }>(`/student/${getStudentId()}/conversations?limit=50`);
  return (data.conversations || []).map((c: any): ConversationSummary => ({
    id: c.id,
    title: c.title || 'New conversation',
    status: c.status,
    messageCount: c.messageCount || 0,
    updatedAt: c.updatedAt,
    lastMessagePreview: c.lastMessagePreview,
  }));
};

export const getConversationMessages = async (conversationId: string) => {
  const data = await apiRequest<{
    messages: any[];
    total: number;
  }>(`/conversations/${conversationId}/messages?limit=200`);
  return (data.messages || []).map((m: any) => ({
    id: m.id,
    role: m.role as 'user' | 'assistant',
    content: m.content,
    citations: (m.citations || []).map((c: any) => ({
      title: c.source || 'Source',
      url: '',
      version: c.relevance ? `relevance: ${c.relevance}` : '',
    })),
    risks: (m.risks || []).map((r: any) =>
      `[${r.severity?.toUpperCase()}] ${r.message}`
    ),
    nextSteps: (m.nextSteps || []).map((s: any) =>
      `${s.action}${s.deadline ? ` (by ${s.deadline})` : ''}`
    ),
    timestamp: new Date(m.createdAt),
  }));
};

export const deleteConversation = async (conversationId: string, headers?: Record<string, string>) =>
  apiRequest<{ success: boolean; message: string }>(`/conversations/${conversationId}`, {
    method: "DELETE",
    ...(headers ? { headers } : {}),
  });

/* ========================
   Term Info
======================== */

export const getNextTermCode = async (): Promise<string> => {
  const data = await apiRequest<{
    current: { term_code: string };
    next_transition: { next_term: string; next_semester: string };
  }>("/term");
  return data.next_transition.next_term;
};

/* ========================
   Enrollment Mutations
======================== */

export const addPlannedCourse = async (course: {
  courseCode: string;
  courseName?: string;
  term: string;
  credits: number;
  sectionNumber?: string;
  crn?: string;
  instructor?: string;
  meetingDays?: string;
  meetingTime?: string;
  building?: string;
  room?: string;
}) => {
  const result = await apiRequest<any>(`/student/${getStudentId()}/courses`, {
    method: "POST",
    body: JSON.stringify({
      courseCode: course.courseCode,
      courseName: course.courseName,
      term: course.term,
      status: "planned",
      credits: course.credits,
      sectionNumber: course.sectionNumber,
      crn: course.crn,
      instructor: course.instructor,
      meeting_days: course.meetingDays,
      meeting_time: course.meetingTime,
      building: course.building,
      room: course.room,
    }),
  });
  return adaptEnrollment(result);
};

export const deletePlannedCourse = async (enrollmentId: string) =>
  apiRequest<{ success: boolean }>(`/student/${getStudentId()}/courses/${enrollmentId}`, {
    method: "DELETE",
  });

/* ========================
   Chat Endpoint
======================== */

/* ========================
   Tracking Endpoints (debug)
======================== */

export const createTrackingSession = async (viewportWidth: number, viewportHeight: number) =>
  apiRequest<{ sessionId: string }>("/tracking/sessions", {
    method: "POST",
    body: JSON.stringify({ userId: getStudentId(), viewportWidth, viewportHeight }),
  });

export const saveTrackingSnapshot = async (
  sessionId: string,
  pageUrl: string,
  screenshot: string,
  events: { x: number; y: number; timestamp: number; type: string; confidence: number }[],
) =>
  apiRequest<{ saved: boolean; filename: string | null }>("/tracking/snapshot", {
    method: "POST",
    body: JSON.stringify({ sessionId, pageUrl, screenshot, events }),
  });

export const endTrackingSession = async (sessionId: string) =>
  apiRequest<{ status: string }>(`/tracking/sessions/${sessionId}/end`, { method: "POST" });

/* ========================
   Chat Endpoint
======================== */

export const sendChatMessage = async (message: string, conversationId?: string | null) =>
  apiRequest<{
    content: string;
    citations: any[];
    risks: any[];
    nextSteps: any[];
    conversationId: string;
  }>("/chat/message", {
    method: "POST",
    body: JSON.stringify({
      message,
      studentId: getStudentId(),
      conversationId: conversationId || undefined,
    }),
  });
