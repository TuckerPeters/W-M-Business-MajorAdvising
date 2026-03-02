'use client';
//Tracking is used for debugging purposes only 
//Must inform user that tracking is being used (test phase, not production)
//Server.py --debugtracking flag to enable tracking
import { useState, useEffect, useRef, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import html2canvas from 'html2canvas';
import { createTrackingSession, saveTrackingSnapshot, endTrackingSession } from '@/lib/api-client';
import { Eye, EyeOff, Crosshair, ImageIcon } from 'lucide-react';

interface GazePoint {
  x: number;
  y: number;
  timestamp: number;
  type: 'gaze' | 'mouse';
  confidence: number;
}

// 9-point calibration grid positions (as % of viewport)
const CALIBRATION_POINTS = [
  { x: 10, y: 10 }, { x: 50, y: 10 }, { x: 90, y: 10 },
  { x: 10, y: 50 }, { x: 50, y: 50 }, { x: 90, y: 50 },
  { x: 10, y: 90 }, { x: 50, y: 90 }, { x: 90, y: 90 },
];
const CLICKS_PER_POINT = 3;

export default function GazeTracker() {
  const pathname = usePathname();

  const [tracking, setTracking] = useState(false);
  const [, setSessionId] = useState<string | null>(null);
  const [mode, setMode] = useState<'gaze' | 'mouse' | null>(null);
  const [pointCount, setPointCount] = useState(0);
  const [minimized, setMinimized] = useState(true);
  const [savedFiles, setSavedFiles] = useState<string[]>([]);

  // Calibration state
  const [calibrating, setCalibrating] = useState(false);
  const [calibrationIndex, setCalibrationIndex] = useState(0);
  const [clicksOnPoint, setClicksOnPoint] = useState(0);

  // Per-page event buffer
  const pageEventsRef = useRef<GazePoint[]>([]);
  const currentPathRef = useRef<string>(pathname);
  const webgazerRef = useRef<any>(null);
  const collectingRef = useRef(false);
  const trackingRef = useRef(false); // ref mirror of tracking state for event handlers
  const sessionIdRef = useRef<string | null>(null);

  // Capture a screenshot of the current page
  const captureScreenshot = async (): Promise<string | null> => {
    try {
      const canvas = await html2canvas(document.body, {
        ignoreElements: (el) => {
          if (el.closest('[data-tracker-widget]')) return true;
          if (el.id?.startsWith('webgazer')) return true;
          return false;
        },
        useCORS: true,
        scale: 1,
        width: window.innerWidth,
        height: window.innerHeight,
        windowWidth: window.innerWidth,
        windowHeight: window.innerHeight,
      });
      // Return base64 without the data:image/png;base64, prefix
      return canvas.toDataURL('image/png').split(',')[1];
    } catch (err) {
      console.error('[GazeTracker] Screenshot capture failed:', err);
      return null;
    }
  };

  // Save snapshot for a page: screenshot + heatmap composite → saved as PNG
  const savePageSnapshot = useCallback(async (pagePath: string) => {
    const events = [...pageEventsRef.current];
    if (events.length === 0 || !sessionIdRef.current) return;

    const screenshot = await captureScreenshot();
    if (!screenshot) return;

    try {
      const result = await saveTrackingSnapshot(
        sessionIdRef.current,
        pagePath,
        screenshot,
        events,
      );
      if (result.filename) {
        setSavedFiles(prev => [...prev, result.filename!]);
        console.log(`[GazeTracker] Saved heatmap: ${result.filename}`);
      }
    } catch (err) {
      console.error('[GazeTracker] Failed to save snapshot:', err);
    }
  }, []);

  // Detect page changes — save snapshot for the old page, reset buffer
  useEffect(() => {
    if (!trackingRef.current || calibrating) return;
    if (currentPathRef.current !== pathname) {
      const oldPath = currentPathRef.current;
      // Save snapshot for the page we're leaving
      savePageSnapshot(oldPath).then(() => {
        pageEventsRef.current = [];
        setPointCount(0);
      });
      currentPathRef.current = pathname;
    }
  }, [pathname, calibrating, savePageSnapshot]);

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

  const startMouseTracking = useCallback(() => {
    setMode('mouse');
    window.addEventListener('mousemove', handleMouseMove);
  }, [handleMouseMove]);

  const stopMouseTracking = useCallback(() => {
    window.removeEventListener('mousemove', handleMouseMove);
  }, [handleMouseMove]);

  const loadWebGazer = useCallback((): Promise<boolean> => {
    return new Promise((resolve) => {
      if ((window as any).webgazer) {
        resolve(true);
        return;
      }
      const script = document.createElement('script');
      script.src = 'https://webgazer.cs.brown.edu/webgazer.js';
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => {
        console.error('[GazeTracker] Failed to load WebGazer from CDN');
        resolve(false);
      };
      document.head.appendChild(script);
    });
  }, []);

  const startGazeTracking = useCallback(async () => {
    console.log('[GazeTracker] Loading WebGazer...');
    const loaded = await loadWebGazer();
    if (!loaded) {
      console.warn('[GazeTracker] WebGazer failed, falling back to mouse');
      startMouseTracking();
      return;
    }

    const wg = (window as any).webgazer;
    if (!wg) {
      startMouseTracking();
      return;
    }

    try {
      webgazerRef.current = wg;
      wg.params.showVideoPreview = true;
      wg.params.showPredictionPoints = false;
      wg.params.showFaceOverlay = false;
      wg.params.showFaceFeedbackBox = false;

      wg.setRegression('ridge');
      wg.setGazeListener((data: any) => {
        if (!data || !collectingRef.current) return;
        const now = Date.now();
        const last = pageEventsRef.current[pageEventsRef.current.length - 1];
        if (last && now - last.timestamp < 50) return;

        pageEventsRef.current.push({
          x: Math.round(data.x),
          y: Math.round(data.y),
          timestamp: now,
          type: 'gaze',
          confidence: data.confidence || 0.8,
        });
        setPointCount(c => c + 1);
      });
      wg.saveDataAcrossSessions(false);
      await wg.begin();
      console.log('[GazeTracker] WebGazer started');

      await new Promise(r => setTimeout(r, 500));

      // Style webcam preview
      const videoEl = document.getElementById('webgazerVideoFeed') as HTMLVideoElement;
      if (videoEl) {
        videoEl.style.position = 'fixed';
        videoEl.style.bottom = '80px';
        videoEl.style.left = '10px';
        videoEl.style.width = '160px';
        videoEl.style.height = '120px';
        videoEl.style.borderRadius = '8px';
        videoEl.style.border = '2px solid #115740';
        videoEl.style.zIndex = '10000';
        videoEl.style.objectFit = 'cover';
      }
      ['webgazerVideoCanvas', 'webgazerFaceOverlay', 'webgazerFaceFeedbackBox', 'webgazerGazeDot'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
      });

      setMode('gaze');
      setCalibrating(true);
      setCalibrationIndex(0);
      setClicksOnPoint(0);
      collectingRef.current = false;
    } catch (err) {
      console.error('[GazeTracker] WebGazer init failed:', err);
      startMouseTracking();
    }
  }, [loadWebGazer, startMouseTracking]);

  const handleCalibrationClick = useCallback(() => {
    const newClicks = clicksOnPoint + 1;
    setClicksOnPoint(newClicks);

    if (newClicks >= CLICKS_PER_POINT) {
      const nextIndex = calibrationIndex + 1;
      if (nextIndex >= CALIBRATION_POINTS.length) {
        setCalibrating(false);
        collectingRef.current = true;
        console.log('[GazeTracker] Calibration complete');
        if (webgazerRef.current) {
          webgazerRef.current.showVideoPreview(false).showPredictionPoints(false);
          ['webgazerVideoFeed', 'webgazerVideoCanvas', 'webgazerFaceOverlay', 'webgazerFaceFeedbackBox'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
          });
        }
      } else {
        setCalibrationIndex(nextIndex);
        setClicksOnPoint(0);
      }
    }
  }, [clicksOnPoint, calibrationIndex]);

  const stopGazeTracking = useCallback(() => {
    collectingRef.current = false;
    if (webgazerRef.current) {
      try { webgazerRef.current.end(); } catch { /* ignore */ }
      webgazerRef.current = null;
    }
    const video = document.getElementById('webgazerVideoFeed') as HTMLVideoElement;
    if (video?.srcObject) {
      (video.srcObject as MediaStream).getTracks().forEach(t => t.stop());
    }
    document.querySelectorAll('[id^="webgazer"]').forEach(el => el.remove());
    setCalibrating(false);
  }, []);

  const start = async () => {
    try {
      const session = await createTrackingSession(
        window.innerWidth,
        window.innerHeight,
      );
      setSessionId(session.sessionId);
      sessionIdRef.current = session.sessionId;
      setPointCount(0);
      setSavedFiles([]);
      pageEventsRef.current = [];
      currentPathRef.current = pathname;
      setTracking(true);
      trackingRef.current = true;
      setMinimized(false);

      await startGazeTracking();
    } catch (err) {
      console.error('[GazeTracker] Failed to start session:', err);
    }
  };

  const stop = async () => {
    collectingRef.current = false;
    trackingRef.current = false;
    setTracking(false);

    // Save snapshot for the current page
    await savePageSnapshot(currentPathRef.current);
    pageEventsRef.current = [];

    if (mode === 'gaze') {
      stopGazeTracking();
    } else {
      stopMouseTracking();
    }

    if (sessionIdRef.current) {
      try {
        await endTrackingSession(sessionIdRef.current);
      } catch { /* ignore */ }
    }

    setMode(null);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      collectingRef.current = false;
      trackingRef.current = false;
      if (webgazerRef.current) {
        try { webgazerRef.current.end(); } catch { /* ignore */ }
      }
      const video = document.getElementById('webgazerVideoFeed') as HTMLVideoElement;
      if (video?.srcObject) {
        (video.srcObject as MediaStream).getTracks().forEach(t => t.stop());
      }
      window.removeEventListener('mousemove', handleMouseMove);
      document.querySelectorAll('[id^="webgazer"]').forEach(el => el.remove());
    };
  }, [handleMouseMove]);

  const currentCalibPoint = CALIBRATION_POINTS[calibrationIndex];

  return (
    <>
    {/* Calibration overlay */}
    {calibrating && currentCalibPoint && (
      <div
        className="fixed inset-0 z-[10001] cursor-pointer"
        style={{ background: 'rgba(0,0,0,0.75)' }}
        onClick={handleCalibrationClick}
      >
        <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-white/95 backdrop-blur rounded-lg px-5 py-3 shadow-xl text-center">
          <p className="text-sm font-semibold text-gray-800">
            Calibration — Point {calibrationIndex + 1} of {CALIBRATION_POINTS.length}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Look at the green dot and click it ({clicksOnPoint}/{CLICKS_PER_POINT} clicks)
          </p>
        </div>

        <div
          className="absolute"
          style={{
            left: `${currentCalibPoint.x}%`,
            top: `${currentCalibPoint.y}%`,
            transform: 'translate(-50%, -50%)',
          }}
        >
          <div
            className="rounded-full border-2 border-white/40"
            style={{
              width: 48,
              height: 48,
              background: `conic-gradient(#115740 ${(clicksOnPoint / CLICKS_PER_POINT) * 360}deg, transparent 0deg)`,
              opacity: 0.3,
            }}
          />
          <div
            className="absolute rounded-full shadow-lg"
            style={{
              width: 20,
              height: 20,
              background: '#115740',
              border: '3px solid white',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              boxShadow: '0 0 20px rgba(17, 87, 64, 0.6)',
            }}
          />
        </div>
      </div>
    )}

    <div className="fixed bottom-4 right-4 z-[9999]" data-tracker-widget>
      {minimized ? (
        <button
          onClick={() => setMinimized(false)}
          className="flex items-center gap-2 px-3 py-2 rounded-full shadow-lg text-xs font-medium transition-colors"
          style={{
            background: tracking ? '#115740' : '#262626',
            color: 'white',
          }}
        >
          {tracking ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
          {tracking
            ? calibrating
              ? 'Calibrating...'
              : `Tracking (${pointCount})`
            : 'Tracker'}
        </button>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg shadow-xl w-[260px] overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-[#262626] text-white">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Gaze Tracker
            </span>
            <button
              onClick={() => setMinimized(true)}
              className="text-gray-400 hover:text-white text-xs"
            >
              minimize
            </button>
          </div>

          <div className="p-3 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">
                Status:{' '}
                {calibrating ? (
                  <span className="text-amber-600 font-medium">
                    <Crosshair className="inline h-3 w-3 mr-0.5" />
                    Calibrating...
                  </span>
                ) : tracking ? (
                  <span className="text-green-600 font-medium">
                    {mode === 'gaze' ? 'Eye Tracking' : 'Mouse Tracking'}
                  </span>
                ) : (
                  <span className="text-gray-400">Idle</span>
                )}
              </span>
              {tracking && !calibrating && (
                <span className="text-xs text-gray-400">{pointCount} pts</span>
              )}
            </div>

            <div className="flex gap-2">
              {!tracking ? (
                <button
                  onClick={start}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-[#115740] text-white rounded text-xs font-medium hover:bg-[#0d4632] transition-colors"
                >
                  <Eye className="h-3.5 w-3.5" />
                  Start Tracking
                </button>
              ) : (
                <button
                  onClick={stop}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-red-600 text-white rounded text-xs font-medium hover:bg-red-700 transition-colors"
                >
                  <EyeOff className="h-3.5 w-3.5" />
                  Stop
                </button>
              )}
            </div>

            {/* Saved heatmap files */}
            {savedFiles.length > 0 && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <ImageIcon className="h-3.5 w-3.5 text-orange-500" />
                  <span className="text-xs font-medium text-gray-700">
                    {savedFiles.length} heatmap{savedFiles.length > 1 ? 's' : ''} saved
                  </span>
                </div>
                <div className="text-[10px] text-gray-400 space-y-0.5 max-h-20 overflow-y-auto">
                  {savedFiles.map((f, i) => (
                    <div key={i} className="truncate">{f}</div>
                  ))}
                </div>
              </div>
            )}

            <p className="text-[10px] text-gray-400 leading-tight">
              Debug only. Heatmaps saved to backend/tracking_data/
            </p>
          </div>
        </div>
      )}
    </div>
    </>
  );
}
