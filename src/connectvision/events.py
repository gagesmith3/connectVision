from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import cv2

@dataclass
class EventDetectionConfig:
    roi: Optional[Tuple[int, int, int, int]]
    diff_threshold: int
    min_event_area: int
    debounce_frames: int

class ChuckEventDetector:
    """Detects events of parts placed into and pushed out of a chuck.
    Strategy: frame differencing in ROI with debounce to avoid double-counts.
    - If motion enters ROI and stabilizes to a solid object area -> 'placed_in'
    - If motion indicates object leaving and area reduces below threshold -> 'pushed_out'
    """

    def __init__(self, cfg: EventDetectionConfig):
        self.cfg = cfg
        self.prev_gray: Optional[np.ndarray] = None
        self.object_present = False
        self.debounce = 0

    def _apply_roi(self, frame: np.ndarray) -> np.ndarray:
        if self.cfg.roi:
            x, y, w, h = self.cfg.roi
            return frame[y : y + h, x : x + w]
        return frame

    def step(self, frame: np.ndarray) -> Optional[str]:
        roi_frame = self._apply_roi(frame)
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        if self.prev_gray is None:
            self.prev_gray = gray
            return None

        diff = cv2.absdiff(gray, self.prev_gray)
        _, bw = cv2.threshold(diff, self.cfg.diff_threshold, 255, cv2.THRESH_BINARY)
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area_sum = sum(cv2.contourArea(c) for c in contours)

        event: Optional[str] = None
        if self.debounce > 0:
            self.debounce -= 1
        else:
            if not self.object_present and area_sum >= self.cfg.min_event_area:
                self.object_present = True
                event = "placed_in"
                self.debounce = self.cfg.debounce_frames
            elif self.object_present and area_sum < self.cfg.min_event_area:
                self.object_present = False
                event = "pushed_out"
                self.debounce = self.cfg.debounce_frames

        self.prev_gray = gray
        return event
