// frontend/src/lib/api-client.ts

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    credentials: "include", // important if using cookies
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
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
   Student Endpoints
======================== */

export const getStudentProfile = () =>
  apiRequest<{
    name: string;
    major: string;
    gpa: number;
  }>("/student/profile");

export const getCourseProgress = () =>
  apiRequest<{
    currentCourses: any[];
    completedCourses: any[];
    milestones: any[];
  }>("/student/progress");

export const getCourseCatalog = () =>
  apiRequest<{
    courses: any[];
  }>("/courses");

/* ========================
   Chat Endpoint
======================== */

export const sendChatMessage = (message: string) =>
  apiRequest<{ response: string }>("/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });