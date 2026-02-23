import { NextResponse } from 'next/server';
import { TermInfo } from '@/types/backend';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const backendUrl = `${BACKEND_URL}/api/term`;

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`);
    }

    const data: TermInfo = await response.json();

    return NextResponse.json({
      ...data,
      isFromBackend: true,
    });
  } catch (error) {
    console.error('Error fetching term info:', error);

    // Fallback: mock term info
    return NextResponse.json({
      current: {
        term_code: '202602',
        display_name: 'Spring 2026',
        is_registration: true,
      },
      next_transition: {
        date: '2026-08-01',
        next_term: '202609',
        next_semester: 'Fall 2026',
      },
      is_registration_period: true,
      isFromBackend: false,
      error: 'Using mock data - backend unavailable',
    });
  }
}
