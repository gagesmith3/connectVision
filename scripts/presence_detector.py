#!/usr/bin/env python3
"""
Object Presence Detector - Detect if an object is present in the ROI.
Uses simple threshold + contour area to determine presence.
Press 't' to adjust threshold, 'q' or ESC to quit.
"""
import cv2
import numpy as np
from picamera2 import Picamera2

# Default ROI [x, y, width, height] - update this from roi_selector.py
ROI = [220, 140, 200, 200]

# Detection parameters
THRESHOLD = 100  # Brightness threshold
MIN_AREA = 500   # Minimum contour area to count as "object present"


def main():
    print("Object Presence Detector")
    print("Press 't'/'T' to adjust threshold, 'q' or ESC to quit")

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": (640, 480)})
    picam2.configure(config)
    picam2.start()

    threshold = THRESHOLD

    try:
        while True:
            frame = picam2.capture_array()
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            else:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Extract ROI
            x, y, w, h = ROI
            roi_frame = frame[y : y + h, x : x + w]

            # Convert to grayscale and threshold
            gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
            bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

            # Find contours
            contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            total_area = sum(cv2.contourArea(c) for c in contours)

            # Determine presence
            object_present = total_area >= MIN_AREA
            status_text = "OBJECT PRESENT" if object_present else "EMPTY"
            status_color = (0, 255, 0) if object_present else (0, 0, 255)

            # Draw ROI rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), status_color, 2)

            # Overlay info
            cv2.putText(
                frame,
                status_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                status_color,
                2,
            )
            cv2.putText(
                frame,
                f"Area: {int(total_area)} | Thresh: {threshold}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )
            cv2.putText(
                frame,
                "t/T: threshold | q: quit",
                (10, 470),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1,
            )

            # Show binary view in small inset
            bw_bgr = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
            bw_resized = cv2.resize(bw_bgr, (160, 120))
            frame[10:130, 480:640] = bw_resized

            cv2.imshow("Object Presence Detector", frame)
            key = cv2.waitKey(30) & 0xFF

            if key == ord("q") or key == 27:
                break
            elif key == ord("t"):
                threshold = max(0, threshold - 5)
                print(f"Threshold: {threshold}")
            elif key == ord("T"):
                threshold = min(255, threshold + 5)
                print(f"Threshold: {threshold}")

    except KeyboardInterrupt:
        pass
    finally:
        picam2.stop()
        cv2.destroyAllWindows()
        print("Stopped.")


if __name__ == "__main__":
    main()
