from typing import Tuple
import numpy as np
import cv2


def count_parts(
    frame: np.ndarray,
    roi: Tuple[int, int, int, int] | None,
    thresh: int,
    min_area: int,
) -> int:
    # Apply ROI
    if roi:
        x, y, w, h = roi
        frame = frame[y : y + h, x : x + w]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    count = 0
    for c in contours:
        area = cv2.contourArea(c)
        if area >= min_area:
            count += 1
    return count
