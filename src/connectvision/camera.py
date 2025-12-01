from typing import Optional

class Camera:
    """Simple camera wrapper.
    Uses PiCamera2 on Raspberry Pi; falls back to None capture elsewhere.
    """

    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self._picam2 = None
        try:
            from picamera2 import Picamera2
            self._picam2 = Picamera2()
            config = self._picam2.create_preview_configuration(
                main={"size": (self.width, self.height)}
            )
            self._picam2.configure(config)
            self._picam2.start()
        except Exception:
            # Running on non-Pi or camera unavailable; leave _picam2 as None
            self._picam2 = None

    def capture(self) -> Optional["numpy.ndarray"]:
        try:
            import numpy as np
        except Exception:
            return None
        if self._picam2:
            import cv2
            frame = self._picam2.capture_array()
            # Ensure BGR uint8
            if frame is None:
                return None
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            if len(frame.shape) == 2:
                frame = np.stack([frame]*3, axis=-1)
            return frame
        # Fallback: generate a blank frame so downstream code can run during dev
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def close(self):
        if self._picam2:
            self._picam2.stop()
