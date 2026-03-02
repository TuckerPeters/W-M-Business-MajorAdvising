'use client';

import dynamic from 'next/dynamic';

const GazeTracker = dynamic(() => import('./GazeTracker'), { ssr: false });

const isDebug = process.env.NEXT_PUBLIC_DEBUG === 'true';

export default function DebugOverlay() {
  if (!isDebug) return null;
  return <GazeTracker />;
}
