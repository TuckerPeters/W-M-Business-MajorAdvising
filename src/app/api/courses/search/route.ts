import { NextRequest, NextResponse } from 'next/server';
import { SearchResponse } from '@/types/backend';
import { adaptCourses } from '@/lib/adapters';
import { mockAvailableCourses } from '@/data/mockData';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const query = searchParams.get('q');
  const limit = searchParams.get('limit') || '20';

  if (!query) {
    return NextResponse.json(
      { error: 'Query parameter "q" is required' },
      { status: 400 }
    );
  }

  try {
    const backendUrl = new URL(`${BACKEND_URL}/api/courses/search`);
    backendUrl.searchParams.set('q', query);
    backendUrl.searchParams.set('limit', limit);

    const response = await fetch(backendUrl.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`);
    }

    const data: SearchResponse = await response.json();
    const results = adaptCourses(data.results);

    return NextResponse.json({
      results,
      total: data.total,
      query: data.query,
      isFromBackend: true,
    });
  } catch (error) {
    console.error('Error searching courses:', error);

    // Fallback: search mock data
    const queryLower = query.toLowerCase();
    const filteredCourses = mockAvailableCourses.filter(
      course =>
        course.code.toLowerCase().includes(queryLower) ||
        course.title.toLowerCase().includes(queryLower)
    );

    return NextResponse.json({
      results: filteredCourses.slice(0, parseInt(limit)),
      total: filteredCourses.length,
      query,
      isFromBackend: false,
      error: 'Using mock data - backend unavailable',
    });
  }
}
