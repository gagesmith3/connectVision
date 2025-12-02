#!/usr/bin/env python3
"""
MJPEG web server for Raspberry Pi camera using Picamera2.
Visit http://<pi-ip>:8080/ to view the live stream in a browser.
"""
import time
from threading import Lock
from io import BytesIO

from picamera2 import Picamera2
import cv2
from flask import Flask, Response, render_template_string

app = Flask(__name__)

HTML = """
<!doctype html>
<title>connectVision - Live Stream</title>
<style>
  body { margin: 0; background: #111; color: #eee; font-family: sans-serif; }
  .wrap { display:flex; align-items:center; justify-content:center; height:100vh; }
  img { max-width: 95vw; max-height: 95vh; border: 2px solid #0f0; }
</style>
<div class="wrap">
  <img src="/stream" alt="Live Stream" />
</div>
"""

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

frame_lock = Lock()
last_jpeg = None


def get_jpeg_frame():
    global last_jpeg
    frame = picam2.capture_array()
    # Normalize to BGR then JPEG encode
    if len(frame.shape) == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.shape[2] == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    else:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    # Optional crosshair overlay
    h, w = frame.shape[:2]
    cv2.line(frame, (w // 2, 0), (w // 2, h), (0, 255, 0), 1)
    cv2.line(frame, (0, h // 2), (w, h // 2), (0, 255, 0), 1)

    ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if ret:
        with frame_lock:
            last_jpeg = jpeg.tobytes()
    return last_jpeg


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/stream')
def stream():
    def generate():
        boundary = 'frame'
        while True:
            data = get_jpeg_frame()
            if not data:
                time.sleep(0.01)
                continue
            yield (b"--" + boundary.encode() + b"\r\n"
                   b"Content-Type: image/jpeg\r\n"
                   b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n")
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    try:
        # Run on 0.0.0.0 to expose to LAN
        app.run(host='0.0.0.0', port=8080, threaded=True)
    finally:
        try:
            picam2.stop()
        except Exception:
            pass
