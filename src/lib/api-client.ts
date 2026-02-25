// src/lib/api-client.ts

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/* =====================================================
   Generic Request Helper
===================================================== */

async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    credentials: "include", // include cookies for auth
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    let message = res.statusText;

    try {
      const errorData = await res.json();
      message = errorData?.detail || errorData?.message || message;
    } catch {
      message = await res.text();
    }

    throw new Error(`API Error ${res.status}: ${message}`);
  }

  return res.json();
}

/* =====================================================
   Shared Types
===================================================== */

export interface StudentProfile {
  id: string;
  name: string;
  major: string;
  gpa: number;
  creditsEarned: number;
}

export interface Course {
  code: string;
  title: string;
  credits: number;
  dept: string;
  level: number;
  hasLab: boolean;
  difficultyIndex: number;
  prereqs: string[];
  description?: string;
  term?: string;
  grade?: string;
  status?: 'enrolled' | 'planned' | 'completed';
}

export interface Milestone {
  id: string;
  title: string;
  completed: boolean;
}

export interface ChatResponse {
  response: string;
  citations?: {
    title: string;
    url?: string;
  }[];
}

export interface AdviseeSummary {
  id: string;
  name: string;
  major: string;
  gpa: number;
  riskLevel: "low" | "medium" | "high";
}

/* =====================================================
   Authentication
===================================================== */

export const login = (email: string, password: string) =>
  apiRequest<void>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

export const logout = () =>
  apiRequest<void>("/auth/logout", {
    method: "POST",
  });

/* =====================================================
   Student Endpoints
===================================================== */

export const getStudentProfile = () =>
  apiRequest<StudentProfile>("/student/profile");

export const getStudentCourses = () =>
  apiRequest<{
    currentCourses: Course[];
    completedCourses: Course[];
  }>("/student/courses");

export const getStudentProgress = () =>
  apiRequest<{
    milestones: Milestone[];
    creditsEarned: number;
    creditsRequired: number;
    currentCourses: Course[];
    completedCourses: Course[];
  }>("/student/progress");

export const getCourseCatalog = () =>
  apiRequest<{
    courses: Course[];
  }>("/courses");

/* =====================================================
   Chat Endpoints
===================================================== */

export const sendChatMessage = (message: string) =>
  apiRequest<ChatResponse>("/chat/message", {
    method: "POST",
    body: JSON.stringify({ message }),
  });

export const getChatHistory = () =>
  apiRequest<{
    messages: {
      role: "user" | "assistant";
      content: string;
      timestamp: string;
    }[];
  }>("/chat/history");

/* =====================================================
   Schedule Endpoints
===================================================== */

export const evaluateSchedule = (courseIds: string[]) =>
  apiRequest<{
    valid: boolean;
    issues?: string[];
  }>("/schedule/evaluate", {
    method: "POST",
    body: JSON.stringify({ courseIds }),
  });

export const getScheduleRecommendations = () =>
  apiRequest<{
    recommendedCourses: Course[];
  }>("/schedule/recommendations");

/* =====================================================
   Advisor Endpoints
===================================================== */

export const getAdvisees = () =>
  apiRequest<AdviseeSummary[]>("/advisor/advisees");

export const getAdviseeDetail = (studentId: string) =>
  apiRequest<StudentProfile>(`/advisor/student/${studentId}`);

export const addAdvisorNote = (studentId: string, note: string) =>
  apiRequest<void>("/advisor/notes", {
    method: "POST",
    body: JSON.stringify({ studentId, note }),
  });

export const getAdvisorAlerts = () =>
  apiRequest<{
    studentId: string;
    message: string;
    severity: "info" | "warning" | "critical";
  }[]>("/advisor/alerts");