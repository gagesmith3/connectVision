#!/usr/bin/env python3
"""
Simple live camera feed for positioning and setup.
Run this on the Pi to verify camera placement over the chuck.
Press 'q' or ESC to quit.
"""
import sys
import cv2
from picamera2 import Picamera2

def main():
    print("Starting live camera feed...")
    print("Press 'q' or ESC to exit")
    
    # Initialize camera
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": (640, 480)})
    picam2.configure(config)
    picam2.start()
    
    try:
        while True:
            # Capture frame
            frame = picam2.capture_array()
            
            # Convert to BGR for OpenCV display
            if len(frame.shape) == 2:  # Grayscale
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:  # RGBA
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            
            # Add crosshair for centering
            h, w = frame.shape[:2]
            cv2.line(frame, (w//2, 0), (w//2, h), (0, 255, 0), 1)
            cv2.line(frame, (0, h//2), (w, h//2), (0, 255, 0), 1)
            
            # Add instructions
            cv2.putText(frame, "Live Feed - Press 'q' or ESC to quit", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Display
            cv2.imshow("connectVision - Live Feed", frame)
            
            # Check for quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' or ESC
                break
                
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        picam2.stop()
        cv2.destroyAllWindows()
        print("Camera stopped.")

if __name__ == "__main__":
    main()
