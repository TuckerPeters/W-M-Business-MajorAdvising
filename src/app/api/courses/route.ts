import { NextRequest, NextResponse } from 'next/server';
import { CourseListResponse } from '@/types/backend';
import { adaptCourses } from '@/lib/adapters';
import { mockAvailableCourses } from '@/data/mockData';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const subject = searchParams.get('subject');
  const limit = searchParams.get('limit') || '100';
  const offset = searchParams.get('offset') || '0';

  try {
    // Build backend URL with query params
    const backendUrl = new URL(`${BACKEND_URL}/api/courses`);
    if (subject) backendUrl.searchParams.set('subject', subject);
    backendUrl.searchParams.set('limit', limit);
    backendUrl.searchParams.set('offset', offset);

    const response = await fetch(backendUrl.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`);
    }

    const data: CourseListResponse = await response.json();

    // Convert backend courses to frontend format
    const courses = adaptCourses(data.courses);

    return NextResponse.json({
      courses,
      total: data.total,
      term_code: data.term_code,
      isFromBackend: true,
    });
  } catch (error) {
    console.error('Error fetching courses from backend:', error);

    // Fallback to mock data
    return NextResponse.json({
      courses: mockAvailableCourses,
      total: mockAvailableCourses.length,
      term_code: 'MOCK',
      isFromBackend: false,
      error: 'Using mock data - backend unavailable',
    });
  }
}
