import { NextResponse } from 'next/server';
import { SubjectResponse } from '@/types/backend';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const backendUrl = `${BACKEND_URL}/api/subjects`;

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`);
    }

    const data: SubjectResponse = await response.json();

    return NextResponse.json({
      subjects: data.subjects,
      total: data.total,
      isFromBackend: true,
    });
  } catch (error) {
    console.error('Error fetching subjects:', error);

    // Fallback: common W&M subjects
    const mockSubjects = ['BUS', 'CSCI', 'ECON', 'MATH', 'STAT', 'ACCT', 'FINC'];

    return NextResponse.json({
      subjects: mockSubjects,
      total: mockSubjects.length,
      isFromBackend: false,
      error: 'Using mock data - backend unavailable',
    });
  }
}
