import { NextRequest, NextResponse } from 'next/server';
import { CourseResponse } from '@/types/backend';
import { adaptCourse } from '@/lib/adapters';
import { mockAvailableCourses } from '@/data/mockData';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ courseCode: string }> }
) {
  const { courseCode } = await params;

  try {
    // URL encode the course code (handles spaces)
    const encodedCode = encodeURIComponent(courseCode);
    const backendUrl = `${BACKEND_URL}/api/courses/${encodedCode}`;

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`);
    }

    const data: CourseResponse = await response.json();
    const course = adaptCourse(data);

    return NextResponse.json({
      course,
      isFromBackend: true,
    });
  } catch (error) {
    console.error(`Error fetching course ${courseCode}:`, error);

    // Fallback: find in mock data
    const mockCourse = mockAvailableCourses.find(
      c => c.code === courseCode || c.code === courseCode.replace('-', ' ')
    );

    if (mockCourse) {
      return NextResponse.json({
        course: mockCourse,
        isFromBackend: false,
        error: 'Using mock data - backend unavailable',
      });
    }

    return NextResponse.json(
      { error: 'Course not found' },
      { status: 404 }
    );
  }
}
