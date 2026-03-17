'use client';
// Automatic mouse/gaze heatmap tracking — runs silently in the background
// Data saved to backend/tracking_data/ via the tracking API endpoints
import { useState, useEffect, useRef, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import html2canvas from 'html2canvas';
import { createTrackingSession, saveTrackingSnapshot, endTrackingSession } from '@/lib/api-client';

interface GazePoint {
  x: number;
  y: number;
  timestamp: number;
  type: 'gaze' | 'mouse';
  confidence: number;
}

export default function GazeTracker() {
  const pathname = usePathname();

  const [, setPointCount] = useState(0);

  const pageEventsRef = useRef<GazePoint[]>([]);
  const currentPathRef = useRef<string>(pathname);
  const trackingRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);
  const startedRef = useRef(false);

  const captureScreenshot = async (): Promise<string | null> => {
    try {
      const canvas = await html2canvas(document.body, {
        useCORS: true,
        scale: 1,
        width: window.innerWidth,
        height: window.innerHeight,
        windowWidth: window.innerWidth,
        windowHeight: window.innerHeight,
      });
      return canvas.toDataURL('image/png').split(',')[1];
    } catch {
      return null;
    }
  };

  const savePageSnapshot = useCallback(async (pagePath: string) => {
    const events = [...pageEventsRef.current];
    if (events.length === 0 || !sessionIdRef.current) return;

    const screenshot = await captureScreenshot();
    if (!screenshot) return;

    try {
      await saveTrackingSnapshot(sessionIdRef.current, pagePath, screenshot, events);
    } catch {
      // silently fail
    }
  }, []);

  // Detect page changes — save snapshot for old page, reset buffer
  useEffect(() => {
    if (!trackingRef.current) return;
    if (currentPathRef.current !== pathname) {
      const oldPath = currentPathRef.current;
      savePageSnapshot(oldPath).then(() => {
        pageEventsRef.current = [];
        setPointCount(0);
      });
      currentPathRef.current = pathname;
    }
  }, [pathname, savePageSnapshot]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    const now = Date.now();
    const last = pageEventsRef.current[pageEventsRef.current.length - 1];
    if (last && now - last.timestamp < 50) return;

    pageEventsRef.current.push({
      x: e.clientX,
      y: e.clientY,
      timestamp: now,
      type: 'mouse',
      confidence: 1.0,
    });
    setPointCount(c => c + 1);
  }, []);

  // Auto-start on mount
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    (async () => {
      try {
        const session = await createTrackingSession(window.innerWidth, window.innerHeight);
        sessionIdRef.current = session.sessionId;
        pageEventsRef.current = [];
        currentPathRef.current = pathname;
        trackingRef.current = true;
        window.addEventListener('mousemove', handleMouseMove);
      } catch {
        // tracking endpoints may not be enabled — silently fail
      }
    })();

    return () => {
      trackingRef.current = false;
      window.removeEventListener('mousemove', handleMouseMove);
      if (sessionIdRef.current) {
        endTrackingSession(sessionIdRef.current).catch(() => {});
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // No visible UI
  return null;
}
