#!/usr/bin/env python3
"""
ROI Selection Tool - Use keyboard to adjust a rectangle over the chuck.
Arrow keys: Move ROI
+/- or w/s: Resize width
a/d: Resize height
'c' to print coordinates
'q' or ESC to quit and save
"""
import cv2
from picamera2 import Picamera2

# Initial ROI [x, y, width, height]
roi = [220, 140, 200, 200]


def main():
    print("ROI Selector - Use arrow keys to move, +/- (or w/s) for width, a/d for height")
    print("Press 'c' to print coordinates, 'q' or ESC to save and quit")

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": (640, 480)})
    picam2.configure(config)
    picam2.start()

    step = 5

    try:
        while True:
            frame = picam2.capture_array()
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            else:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Draw ROI rectangle
            x, y, w, h = roi
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"ROI: [{x}, {y}, {w}, {h}]",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                "Arrows: move | +/-: width | a/d: height | c: print | q: quit",
                (10, 460),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1,
            )

            cv2.imshow("ROI Selector", frame)
            key = cv2.waitKey(30) & 0xFF

            if key == ord("q") or key == 27:
                break
            elif key == ord("c"):
                print(f"Current ROI: {roi}")
            elif key == 82 or key == 0:  # Up arrow
                roi[1] = max(0, roi[1] - step)
            elif key == 84 or key == 1:  # Down arrow
                roi[1] = min(480 - roi[3], roi[1] + step)
            elif key == 81 or key == 2:  # Left arrow
                roi[0] = max(0, roi[0] - step)
            elif key == 83 or key == 3:  # Right arrow
                roi[0] = min(640 - roi[2], roi[0] + step)
            elif key == ord("+") or key == ord("=") or key == ord("w"):
                roi[2] = min(640 - roi[0], roi[2] + step)
            elif key == ord("-") or key == ord("_") or key == ord("s"):
                roi[2] = max(10, roi[2] - step)
            elif key == ord("a"):
                roi[3] = max(10, roi[3] - step)
            elif key == ord("d"):
                roi[3] = min(480 - roi[1], roi[3] + step)

    except KeyboardInterrupt:
        pass
    finally:
        picam2.stop()
        cv2.destroyAllWindows()
        print(f"\nFinal ROI: {roi}")
        print(f"Copy this to your config: roi: {roi}")


if __name__ == "__main__":
    main()
