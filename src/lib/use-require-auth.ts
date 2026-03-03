'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './auth-context';

export function useRequireAuth() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const isDebug = process.env.NEXT_PUBLIC_DEBUG === 'true';

  useEffect(() => {
    if (!loading && !user && !isDebug) {
      router.push('/');
    }
  }, [user, loading, isDebug, router]);

  return { user, loading, isAuthenticated: !!user || isDebug };
}
