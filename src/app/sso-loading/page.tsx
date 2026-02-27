'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SSOLoadingPage() {
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      router.push('/student');
    }, 2000);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto mb-4" />
        <p className="text-lg text-gray-600">Authenticating with University SSO...</p>
      </div>
    </div>
  );
}
