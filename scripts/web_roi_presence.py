#!/usr/bin/env python3
"""
Web-based ROI Selector and Presence Detector
Access via http://<pi-ip>:8080/
- Click and drag to draw ROI
- Adjust threshold with slider
- View object presence status in real-time
"""
import time
import json
from threading import Lock
from io import BytesIO

from picamera2 import Picamera2
import cv2
import numpy as np
from flask import Flask, Response, render_template_string, request, jsonify

app = Flask(__name__)

# Global state
roi = [280, 260, 80, 80]  # [x, y, width, height]
threshold = 100
min_area = 500
frame_lock = Lock()
last_jpeg = None
last_status = {"present": False, "area": 0}

HTML = """
<!doctype html>
<html>
<head>
<title>connectVision - ROI & Presence</title>
<style>
  body { margin:0; background:#111; color:#eee; font-family:sans-serif; }
  .container { max-width:900px; margin:20px auto; padding:20px; }
  h1 { color:#0f0; margin-bottom:10px; }
  .status { font-size:24px; font-weight:bold; margin:10px 0; }
  .present { color:#0f0; }
  .empty { color:#f00; }
  .controls { margin:20px 0; padding:15px; background:#222; border-radius:5px; }
  .controls label { display:inline-block; width:120px; margin-right:10px; }
  .controls input[type=number] { width:60px; padding:5px; }
  .controls input[type=range] { width:200px; vertical-align:middle; }
  .controls button { padding:8px 15px; margin:5px; background:#0a0; color:#fff; border:none; border-radius:3px; cursor:pointer; }
  .controls button:hover { background:#0c0; }
  img { max-width:100%; border:2px solid #0f0; display:block; cursor:crosshair; }
  .info { font-size:14px; color:#aaa; margin-top:10px; }
  #canvas-overlay { position:relative; }
</style>
</head>
<body>
<div class="container">
  <h1>connectVision - ROI Selector & Presence Detector</h1>
  <div class="status" id="status">Connecting...</div>
  
  <div class="controls">
    <div>
      <label>ROI (x,y,w,h):</label>
      <input type="number" id="roi-x" value="280" min="0" max="640"> 
      <input type="number" id="roi-y" value="260" min="0" max="480"> 
      <input type="number" id="roi-w" value="80" min="10" max="640"> 
      <input type="number" id="roi-h" value="80" min="10" max="480">
      <button onclick="updateROI()">Update ROI</button>
    </div>
    <div style="margin-top:10px;">
      <label>Threshold:</label>
      <input type="range" id="threshold" min="0" max="255" value="100" oninput="updateThreshold(this.value)">
      <span id="thresh-val">100</span>
    </div>
    <div style="margin-top:10px;">
      <label>Min Area:</label>
      <input type="number" id="min-area" value="500" min="0" max="10000">
      <button onclick="updateMinArea()">Update Min Area</button>
    </div>
  </div>
  
  <div style="position:relative; display:inline-block;">
    <img id="stream" src="/stream" alt="Live Stream" 
         onmousedown="startDrag(event)" 
         onmousemove="dragROI(event)" 
         onmouseup="endDrag(event)">
  </div>
  
  <div class="info">
    <p><strong>Instructions:</strong></p>
    <ul>
      <li>Click and drag on the image to draw ROI (or use input boxes)</li>
      <li>Adjust threshold slider to tune detection sensitivity</li>
      <li>Green border = object present | Red border = empty</li>
    </ul>
  </div>
</div>

<script>
let dragging = false;
let startX = 0, startY = 0;

function updateROI() {
  const x = parseInt(document.getElementById('roi-x').value);
  const y = parseInt(document.getElementById('roi-y').value);
  const w = parseInt(document.getElementById('roi-w').value);
  const h = parseInt(document.getElementById('roi-h').value);
  
  fetch('/set_roi', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({x, y, w, h})
  });
}

function updateThreshold(val) {
  document.getElementById('thresh-val').innerText = val;
  fetch('/set_threshold', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({threshold: parseInt(val)})
  });
}

function updateMinArea() {
  const area = parseInt(document.getElementById('min-area').value);
  fetch('/set_min_area', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({min_area: area})
  });
}

function startDrag(e) {
  const rect = e.target.getBoundingClientRect();
  const scaleX = 640 / rect.width;
  const scaleY = 480 / rect.height;
  startX = Math.round((e.clientX - rect.left) * scaleX);
  startY = Math.round((e.clientY - rect.top) * scaleY);
  dragging = true;
}

function dragROI(e) {
  if (!dragging) return;
  const rect = e.target.getBoundingClientRect();
  const scaleX = 640 / rect.width;
  const scaleY = 480 / rect.height;
  const endX = Math.round((e.clientX - rect.left) * scaleX);
  const endY = Math.round((e.clientY - rect.top) * scaleY);
  
  const x = Math.min(startX, endX);
  const y = Math.min(startY, endY);
  const w = Math.abs(endX - startX);
  const h = Math.abs(endY - startY);
  
  document.getElementById('roi-x').value = x;
  document.getElementById('roi-y').value = y;
  document.getElementById('roi-w').value = w;
  document.getElementById('roi-h').value = h;
}

function endDrag(e) {
  if (dragging) {
    dragging = false;
    updateROI();
  }
}

// Poll status
setInterval(() => {
  fetch('/status')
    .then(r => r.json())
    .then(data => {
      const statusEl = document.getElementById('status');
      if (data.present) {
        statusEl.className = 'status present';
        statusEl.innerText = `OBJECT PRESENT (Area: ${data.area})`;
      } else {
        statusEl.className = 'status empty';
        statusEl.innerText = `EMPTY (Area: ${data.area})`;
      }
    });
}, 500);
</script>
</body>
</html>
"""

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()


def process_frame():
    global last_jpeg, last_status
    frame = picam2.capture_array()
    
    # Normalize to BGR
    if len(frame.shape) == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.shape[2] == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    else:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    # Extract ROI and detect presence
    x, y, w, h = roi
    roi_frame = frame[y:y+h, x:x+w] if (y+h <= 480 and x+w <= 640) else frame
    
    gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    total_area = sum(cv2.contourArea(c) for c in contours)
    
    object_present = total_area >= min_area
    status_color = (0, 255, 0) if object_present else (0, 0, 255)
    
    with frame_lock:
        last_status = {"present": object_present, "area": int(total_area)}
    
    # Draw ROI
    cv2.rectangle(frame, (x, y), (x+w, y+h), status_color, 2)
    
    # Status text
    status_text = "PRESENT" if object_present else "EMPTY"
    cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, status_color, 2)
    cv2.putText(frame, f"Area: {int(total_area)} | Thresh: {threshold}", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
    
    # Encode JPEG
    ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
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
        while True:
            data = process_frame()
            if data:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n")
            time.sleep(0.03)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/status')
def status():
    with frame_lock:
        return jsonify(last_status)


@app.route('/set_roi', methods=['POST'])
def set_roi():
    global roi
    data = request.json
    roi = [int(data['x']), int(data['y']), int(data['w']), int(data['h'])]
    print(f"ROI updated: {roi}")
    return jsonify({"ok": True, "roi": roi})


@app.route('/set_threshold', methods=['POST'])
def set_threshold():
    global threshold
    threshold = int(request.json['threshold'])
    print(f"Threshold: {threshold}")
    return jsonify({"ok": True, "threshold": threshold})


@app.route('/set_min_area', methods=['POST'])
def set_min_area():
    global min_area
    min_area = int(request.json['min_area'])
    print(f"Min Area: {min_area}")
    return jsonify({"ok": True, "min_area": min_area})


if __name__ == '__main__':
    try:
        print("Starting web server on http://0.0.0.0:8080")
        print("Access from browser to select ROI and monitor presence")
        app.run(host='0.0.0.0', port=8080, threaded=True)
    finally:
        try:
            picam2.stop()
        except:
            pass
