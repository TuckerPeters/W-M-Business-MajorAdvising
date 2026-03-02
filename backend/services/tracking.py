"""Gaze/mouse tracking service for debug mode heatmap generation.

Stores all data locally as JSON files — no Firebase dependency.
Saves composite heatmap images (screenshot + heatmap) as PNGs.
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

# Local storage directory
DATA_DIR = Path(__file__).resolve().parent.parent / "tracking_data"


class TrackingService:
    """Stores gaze/mouse tracking events locally and generates heatmaps."""

    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return DATA_DIR / f"{session_id}.json"

    def create_session(self, user_id: str, viewport_width: int, viewport_height: int) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        doc = {
            "sessionId": session_id,
            "userId": user_id,
            "viewportWidth": viewport_width,
            "viewportHeight": viewport_height,
            "startTime": datetime.utcnow().isoformat(),
            "endTime": None,
            "snapshots": [],
        }
        with open(self._session_path(session_id), "w") as f:
            json.dump(doc, f)
        return {"sessionId": session_id}

    def _generate_heatmap_rgba(self, events: List[Dict], vw: int, vh: int) -> Image.Image:
        """Generate a heatmap as an RGBA PIL Image sized to viewport."""
        xs = np.array([e["x"] for e in events], dtype=np.float64)
        ys = np.array([e["y"] for e in events], dtype=np.float64)
        weights = np.array([e.get("confidence", 1.0) for e in events], dtype=np.float64)

        # Create heatmap grid
        grid_w = min(vw, 400)
        grid_h = min(vh, 300)
        heatmap = np.zeros((grid_h, grid_w), dtype=np.float64)

        # Scale points to grid
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

        # Convert to RGBA using jet colormap
        cmap = plt.cm.jet
        colored = cmap(heatmap)  # (H, W, 4) float in [0,1]
        # Set alpha proportional to intensity so cool areas are transparent
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
        """Composite heatmap onto screenshot and save as PNG."""
        if not events:
            return None

        # Decode screenshot
        screenshot_data = base64.b64decode(screenshot_b64)
        screenshot = Image.open(io.BytesIO(screenshot_data)).convert("RGBA")
        vw, vh = screenshot.size

        # Generate heatmap overlay
        heatmap_img = self._generate_heatmap_rgba(events, vw, vh)

        # Composite: screenshot + heatmap
        composite = Image.alpha_composite(screenshot, heatmap_img)

        # Build filename from page path
        slug = page_url.strip("/").replace("/", "_").replace("?", "_") or "home"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{session_id}_{slug}_{timestamp}.png"
        filepath = DATA_DIR / filename

        composite.save(filepath, "PNG")

        # Update session metadata
        session_path = self._session_path(session_id)
        if session_path.exists():
            with open(session_path, "r") as f:
                session = json.load(f)
            session["snapshots"].append({
                "pageUrl": page_url,
                "filename": filename,
                "pointCount": len(events),
                "savedAt": datetime.utcnow().isoformat(),
            })
            with open(session_path, "w") as f:
                json.dump(session, f)

        return filename

    def end_session(self, session_id: str):
        path = self._session_path(session_id)
        if not path.exists():
            return
        with open(path, "r") as f:
            session = json.load(f)
        session["endTime"] = datetime.utcnow().isoformat()
        with open(path, "w") as f:
            json.dump(session, f)

    def get_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
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

    def cleanup_sessions(self):
        """Delete all local tracking data."""
        if DATA_DIR.exists():
            for p in DATA_DIR.glob("*"):
                p.unlink()


_tracking_service = None

def get_tracking_service() -> TrackingService:
    global _tracking_service
    if _tracking_service is None:
        _tracking_service = TrackingService()
    return _tracking_service
