"""Gaze/mouse tracking service — stores data to Firestore for analytics.

Also saves composite heatmap PNGs locally when possible (local dev).
Firestore collections:
  - tracking_sessions: session metadata (userId, viewport, start/end times)
  - tracking_events: raw mouse/gaze events per page per session
  - tracking_snapshots: snapshot metadata (page, point count, timestamp)
"""

import base64
import io
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

# Local storage directory (fallback / dev)
DATA_DIR = Path(__file__).resolve().parent.parent / "tracking_data"


def _get_db():
    """Get Firestore client, or None if unavailable."""
    try:
        from core.config import get_firestore_client
        return get_firestore_client()
    except Exception:
        return None


class TrackingService:
    """Stores gaze/mouse tracking events to Firestore and generates heatmaps."""

    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return DATA_DIR / f"{session_id}.json"

    def create_session(self, user_id: str, viewport_width: int, viewport_height: int) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        doc = {
            "sessionId": session_id,
            "userId": user_id,
            "viewportWidth": viewport_width,
            "viewportHeight": viewport_height,
            "startTime": now,
            "endTime": None,
            "snapshotCount": 0,
            "totalEvents": 0,
        }

        # Save to Firestore
        db = _get_db()
        if db:
            try:
                db.collection("tracking_sessions").document(session_id).set(doc)
            except Exception as e:
                print(f"[Tracking] Firestore session create failed: {e}")

        # Also save locally
        try:
            with open(self._session_path(session_id), "w") as f:
                json.dump({**doc, "snapshots": []}, f)
        except Exception:
            pass

        return {"sessionId": session_id}

    def _generate_heatmap_rgba(self, events: List[Dict], vw: int, vh: int) -> Image.Image:
        """Generate a heatmap as an RGBA PIL Image sized to viewport."""
        xs = np.array([e["x"] for e in events], dtype=np.float64)
        ys = np.array([e["y"] for e in events], dtype=np.float64)
        weights = np.array([e.get("confidence", 1.0) for e in events], dtype=np.float64)

        grid_w = min(vw, 400)
        grid_h = min(vh, 300)
        heatmap = np.zeros((grid_h, grid_w), dtype=np.float64)

        scale_x = grid_w / vw
        scale_y = grid_h / vh
        gx = np.clip((xs * scale_x).astype(int), 0, grid_w - 1)
        gy = np.clip((ys * scale_y).astype(int), 0, grid_h - 1)

        for i in range(len(gx)):
            heatmap[gy[i], gx[i]] += weights[i]

        from scipy.ndimage import gaussian_filter
        heatmap = gaussian_filter(heatmap, sigma=grid_w * 0.02)

        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()

        cmap = plt.cm.jet
        colored = cmap(heatmap)
        colored[..., 3] = heatmap * 0.6
        rgba = (colored * 255).astype(np.uint8)

        heatmap_img = Image.fromarray(rgba, "RGBA")
        return heatmap_img.resize((vw, vh), Image.BILINEAR)

    def save_snapshot(
        self,
        session_id: str,
        page_url: str,
        screenshot_b64: str,
        events: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Save tracking snapshot — events to Firestore, heatmap PNG locally."""
        if not events:
            return None

        now = datetime.utcnow().isoformat()
        snapshot_id = str(uuid.uuid4())

        # Store raw events and snapshot metadata to Firestore
        db = _get_db()
        if db:
            try:
                # Snapshot metadata
                db.collection("tracking_snapshots").document(snapshot_id).set({
                    "snapshotId": snapshot_id,
                    "sessionId": session_id,
                    "pageUrl": page_url,
                    "eventCount": len(events),
                    "createdAt": now,
                })

                # Store events in batches (Firestore batch limit is 500)
                # Aggregate events into summary buckets for analytics instead of raw events
                # This keeps Firestore writes manageable
                bucket_size = 50  # aggregate every 50ms worth of events into zones
                zone_counts: Dict[str, int] = {}  # "x_zone,y_zone" -> count
                for e in events:
                    # Bucket into 50px grid zones for heatmap analytics
                    zx = e["x"] // 50
                    zy = e["y"] // 50
                    key = f"{zx},{zy}"
                    zone_counts[key] = zone_counts.get(key, 0) + 1

                db.collection("tracking_heatmaps").document(snapshot_id).set({
                    "snapshotId": snapshot_id,
                    "sessionId": session_id,
                    "pageUrl": page_url,
                    "zones": zone_counts,  # {"x,y": count} — compact heatmap data
                    "eventCount": len(events),
                    "createdAt": now,
                })

                # Update session totals
                db.collection("tracking_sessions").document(session_id).set({
                    "lastActivity": now,
                    "snapshotCount": db.collection("tracking_snapshots").where("sessionId", "==", session_id).count().get()[0][0].value if False else 0,
                }, merge=True)

                # Simpler: just increment
                from google.cloud.firestore_v1 import Increment
                db.collection("tracking_sessions").document(session_id).update({
                    "snapshotCount": Increment(1),
                    "totalEvents": Increment(len(events)),
                    "lastActivity": now,
                })

            except Exception as e:
                print(f"[Tracking] Firestore snapshot save failed: {e}")

        # Generate and save heatmap PNG locally
        filename = None
        try:
            screenshot_data = base64.b64decode(screenshot_b64)
            screenshot = Image.open(io.BytesIO(screenshot_data)).convert("RGBA")
            vw, vh = screenshot.size

            heatmap_img = self._generate_heatmap_rgba(events, vw, vh)
            composite = Image.alpha_composite(screenshot, heatmap_img)

            slug = page_url.strip("/").replace("/", "_").replace("?", "_") or "home"
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{session_id}_{slug}_{timestamp}.png"
            filepath = DATA_DIR / filename

            composite.save(filepath, "PNG")

            # Update local session file
            session_path = self._session_path(session_id)
            if session_path.exists():
                with open(session_path, "r") as f:
                    session = json.load(f)
                session["snapshots"].append({
                    "pageUrl": page_url,
                    "filename": filename,
                    "pointCount": len(events),
                    "savedAt": now,
                })
                with open(session_path, "w") as f:
                    json.dump(session, f)
        except Exception as e:
            print(f"[Tracking] Local heatmap save failed: {e}")

        return filename

    def end_session(self, session_id: str):
        now = datetime.utcnow().isoformat()

        # Update Firestore
        db = _get_db()
        if db:
            try:
                db.collection("tracking_sessions").document(session_id).set(
                    {"endTime": now}, merge=True
                )
            except Exception:
                pass

        # Update local file
        path = self._session_path(session_id)
        if path.exists():
            try:
                with open(path, "r") as f:
                    session = json.load(f)
                session["endTime"] = now
                with open(path, "w") as f:
                    json.dump(session, f)
            except Exception:
                pass

    def get_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get sessions — prefer Firestore, fall back to local files."""
        db = _get_db()
        if db:
            try:
                query = db.collection("tracking_sessions").order_by("startTime", direction="DESCENDING").limit(20)
                if user_id:
                    query = query.where("userId", "==", user_id)
                return [doc.to_dict() for doc in query.stream()]
            except Exception:
                pass

        # Fallback to local
        sessions = []
        if not DATA_DIR.exists():
            return sessions
        for p in sorted(DATA_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
            with open(p, "r") as f:
                data = json.load(f)
            if user_id and data.get("userId") != user_id:
                continue
            sessions.append(data)
            if len(sessions) >= 20:
                break
        return sessions


_tracking_service = None

def get_tracking_service() -> TrackingService:
    global _tracking_service
    if _tracking_service is None:
        _tracking_service = TrackingService()
    return _tracking_service
