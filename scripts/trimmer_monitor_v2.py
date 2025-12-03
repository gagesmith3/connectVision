#!/usr/bin/env python3
"""
Trimmer Monitor with Integrated Web Interface
Runs on Raspberry Pi - Single application for calibration and production monitoring

Features:
- Web interface at http://<pi-ip>:8080 for ROI calibration
- Real-time production monitoring with event logging
- State machine for PLACE → TRIM → PUSH cycle detection
- Settings saved to database automatically
"""
import time
import argparse
import sys
import threading
import json
import socket
from pathlib import Path
from typing import Optional
from datetime import datetime
from enum import Enum
from threading import Lock

import cv2
import numpy as np
from picamera2 import Picamera2
from flask import Flask, Response, render_template_string, request, jsonify

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from connectvision.database import ConnectVisionDB, MySQLConfig, TrimmerConfig


# HTML template for web interface
HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
<title>connectVision - Trimmer {{ machine_id }}</title>
<style>
  body { margin:0; background:#111; color:#eee; font-family:sans-serif; }
  .container { max-width:1200px; margin:20px auto; padding:20px; }
  h1 { color:#0f0; margin-bottom:10px; }
  .status { font-size:24px; font-weight:bold; margin:10px 0; padding:10px; border-radius:5px; }
  .present { color:#0f0; background:#002200; }
  .empty { color:#f00; background:#220000; }
  .trimming { color:#ff0; background:#222200; }
  
  .stats-row { display:flex; gap:20px; margin:20px 0; }
  .stat-box { flex:1; background:#222; padding:15px; border-radius:5px; }
  .stat-box h3 { margin:0 0 10px 0; color:#0af; }
  .stat-box .value { font-size:32px; font-weight:bold; color:#0f0; }
  
  .controls { margin:20px 0; padding:15px; background:#222; border-radius:5px; }
  .controls h3 { margin-top:0; color:#0af; }
  .controls label { display:inline-block; width:140px; margin-right:10px; }
  .controls input[type=number] { width:70px; padding:5px; }
  .controls input[type=range] { width:200px; vertical-align:middle; }
  .controls button { padding:8px 15px; margin:5px; background:#0a0; color:#fff; border:none; border-radius:3px; cursor:pointer; }
  .controls button:hover { background:#0c0; }
  
  .video-container { position:relative; display:inline-block; margin:20px 0; }
  img { max-width:100%; border:2px solid #0f0; display:block; cursor:crosshair; }
  .info { font-size:14px; color:#aaa; margin-top:10px; }
  
  .events-log { background:#222; padding:15px; border-radius:5px; max-height:300px; overflow-y:auto; font-family:monospace; font-size:12px; }
  .events-log .event { padding:5px; border-bottom:1px solid #333; }
</style>
</head>
<body>
<div class="container">
  <h1>connectVision - Trimmer {{ machine_name }} (ID: {{ machine_id }})</h1>
  
  <div class="status" id="status">Connecting...</div>
  
  <div class="stats-row">
    <div class="stat-box">
      <h3>Total Cycles</h3>
      <div class="value" id="total-cycles">0</div>
    </div>
    <div class="stat-box">
      <h3>Cycles/Hour</h3>
      <div class="value" id="cycles-hour">0</div>
    </div>
    <div class="stat-box">
      <h3>Current Lot</h3>
      <div class="value" id="current-lot">N/A</div>
    </div>
    <div class="stat-box">
      <h3>Uptime</h3>
      <div class="value" id="uptime">0:00:00</div>
    </div>
  </div>
  
  <div class="controls">
    <h3>Vision Settings</h3>
    <div>
      <label>Machine ID:</label>
      <input type="number" id="machine-id" value="{{ machine_id }}" readonly style="background:#333;">
      <button onclick="reloadConfig()">Reload from DB</button>
    </div>
    <div style="margin-top:10px;">
      <label>ROI (x,y,w,h):</label>
      <input type="number" id="roi-x" value="{{ roi_x }}" min="0" max="640"> 
      <input type="number" id="roi-y" value="{{ roi_y }}" min="0" max="480"> 
      <input type="number" id="roi-w" value="{{ roi_w }}" min="10" max="640"> 
      <input type="number" id="roi-h" value="{{ roi_h }}" min="10" max="480">
      <button onclick="updateROI()">Update ROI</button>
    </div>
    <div style="margin-top:10px;">
      <label>Threshold:</label>
      <input type="range" id="threshold" min="0" max="255" value="{{ threshold }}" oninput="updateThreshold(this.value)">
      <span id="thresh-val">{{ threshold }}</span>
    </div>
    <div style="margin-top:10px;">
      <label>Min Area:</label>
      <input type="number" id="min-area" value="{{ min_area }}" min="0" max="10000">
      <button onclick="updateMinArea()">Update</button>
    </div>
    <div style="margin-top:15px;">
      <button onclick="saveToDatabase()" style="background:#00a;">💾 Save to Database</button>
    </div>
  </div>
  
  <div class="video-container">
    <img id="stream" src="/stream" alt="Live Stream" 
         onmousedown="startDrag(event)" 
         onmousemove="dragROI(event)" 
         onmouseup="endDrag(event)">
  </div>
  
  <div class="info">
    <p><strong>Instructions:</strong></p>
    <ul>
      <li>Click and drag on video to draw ROI over chuck</li>
      <li>Adjust threshold slider to tune detection sensitivity</li>
      <li>Green = object present | Red = empty | Yellow = trimming</li>
      <li>Click "Save to Database" to persist settings</li>
    </ul>
  </div>
  
  <div class="controls">
    <h3>Recent Events</h3>
    <div class="events-log" id="events-log">
      <div class="event">Waiting for events...</div>
    </div>
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

function saveToDatabase() {
  fetch('/save_config', {
    method: 'POST'
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      alert('✓ Configuration saved to database successfully!');
    } else {
      alert('✗ Failed to save configuration');
    }
  });
}

function reloadConfig() {
  fetch('/reload_config', {
    method: 'POST'
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      document.getElementById('roi-x').value = data.roi_x;
      document.getElementById('roi-y').value = data.roi_y;
      document.getElementById('roi-w').value = data.roi_w;
      document.getElementById('roi-h').value = data.roi_h;
      document.getElementById('threshold').value = data.threshold;
      document.getElementById('thresh-val').innerText = data.threshold;
      document.getElementById('min-area').value = data.min_area;
      alert('✓ Configuration reloaded from database');
    }
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

function formatUptime(seconds) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${hrs}:${mins.toString().padStart(2,'0')}:${secs.toString().padStart(2,'0')}`;
}

// Poll status
setInterval(() => {
  fetch('/status')
    .then(r => r.json())
    .then(data => {
      const statusEl = document.getElementById('status');
      let statusClass = 'status ';
      let statusText = '';
      
      if (data.state === 'TRIMMING') {
        statusClass += 'trimming';
        statusText = `TRIMMING - Area: ${data.area}`;
      } else if (data.present) {
        statusClass += 'present';
        statusText = `PART PLACED - Area: ${data.area}`;
      } else {
        statusClass += 'empty';
        statusText = `EMPTY - Area: ${data.area}`;
      }
      
      statusEl.className = statusClass;
      statusEl.innerText = statusText;
      
      // Update stats
      document.getElementById('total-cycles').innerText = data.total_cycles;
      document.getElementById('cycles-hour').innerText = data.cycles_per_hour;
      document.getElementById('current-lot').innerText = data.current_lot || 'N/A';
      document.getElementById('uptime').innerText = formatUptime(data.uptime);
    });
}, 500);

// Poll events log
setInterval(() => {
  fetch('/events')
    .then(r => r.json())
    .then(data => {
      const logEl = document.getElementById('events-log');
      if (data.events && data.events.length > 0) {
        logEl.innerHTML = data.events.map(e => 
          `<div class="event">[${e.time}] ${e.message}</div>`
        ).join('');
        logEl.scrollTop = logEl.scrollHeight;
      }
    });
}, 2000);
</script>
</body>
</html>
"""


class TrimmerState(Enum):
    """State machine states for trimmer cycle detection."""
    EMPTY = "EMPTY"
    PART_PLACED = "PLACED"
    TRIMMING = "TRIMMING"


class TrimmerMonitorApp:
    """Integrated trimmer monitor with web interface."""
    
    def __init__(self, machine_id: int, db: ConnectVisionDB, config: TrimmerConfig):
        self.machine_id = machine_id
        self.db = db
        self.config = config
        
        # State tracking
        self.state = TrimmerState.EMPTY
        self.cycle_id = None
        self.current_lot = None
        self.state_start_time = time.time()
        
        # Statistics
        self.total_cycles = 0
        self.cycles_last_hour = []
        self.boot_time = time.time()
        self.last_telemetry = time.time()
        
        # Event log for web display
        self.recent_events = []
        self.max_events = 20
        
        # Thread safety
        self.frame_lock = Lock()
        self.last_jpeg = None
        self.last_area = 0
        self.last_present = False
        
        # Initialize camera
        self.picam2 = Picamera2()
        camera_config = self.picam2.create_preview_configuration(
            main={"size": (640, 480)}
        )
        self.picam2.configure(camera_config)
        self.picam2.start()
        time.sleep(1)
        
        # Flask app
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Monitoring thread
        self.running = False
        self.monitor_thread = None
        
        print(f"TrimmerMonitorApp initialized: Machine {machine_id} ({config.machine_name})")
    
    def add_event_log(self, message: str):
        """Add event to recent events log."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.recent_events.append({
            'time': timestamp,
            'message': message
        })
        if len(self.recent_events) > self.max_events:
            self.recent_events.pop(0)
    
    def process_frame(self):
        """Capture frame, detect presence, and encode for web streaming."""
        frame = self.picam2.capture_array()
        
        # Normalize to BGR
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        else:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Extract ROI
        x, y, w, h = (self.config.roi_x, self.config.roi_y,
                      self.config.roi_w, self.config.roi_h)
        roi_frame = frame[y:y+h, x:x+w] if (y+h <= 480 and x+w <= 640) else frame
        
        # Detect presence
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(gray, self.config.threshold, 255, cv2.THRESH_BINARY)
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        
        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_area = sum(cv2.contourArea(c) for c in contours)
        is_present = total_area >= self.config.min_area
        
        # Draw ROI and status
        if self.state == TrimmerState.TRIMMING:
            status_color = (0, 255, 255)  # Yellow
        elif is_present:
            status_color = (0, 255, 0)    # Green
        else:
            status_color = (0, 0, 255)    # Red
        
        cv2.rectangle(frame, (x, y), (x+w, y+h), status_color, 2)
        
        # Status text
        status_text = f"{self.state.value} - Area: {int(total_area)}"
        cv2.putText(frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, status_color, 2)
        
        if self.current_lot:
            cv2.putText(frame, f"Lot: {self.current_lot}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Encode JPEG
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if ret:
            with self.frame_lock:
                self.last_jpeg = jpeg.tobytes()
                self.last_area = int(total_area)
                self.last_present = is_present
        
        return is_present, int(total_area)
    
    def monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                # Process frame and detect
                is_present, area = self.process_frame()
                
                # State machine logic
                current_time = time.time()
                time_in_state = current_time - self.state_start_time
                
                if self.state == TrimmerState.EMPTY:
                    if is_present:
                        self.state = TrimmerState.PART_PLACED
                        self.state_start_time = current_time
                        self.cycle_id = int(current_time * 1000)
                        self.current_lot = self.db.get_active_lot(self.machine_id)
                        
                        self.db.log_event(
                            trimmer_id=self.machine_id,
                            event_type="placed_in",
                            cycle_id=self.cycle_id,
                            req_lot=self.current_lot,
                            area=area
                        )
                        msg = f"PLACED - Cycle {self.cycle_id} (Lot: {self.current_lot or 'N/A'})"
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                        self.add_event_log(msg)
                
                elif self.state == TrimmerState.PART_PLACED:
                    if not is_present:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: Part removed too quickly")
                        self.state = TrimmerState.EMPTY
                        self.state_start_time = current_time
                        self.cycle_id = None
                    elif time_in_state > 1.0:
                        self.state = TrimmerState.TRIMMING
                        self.state_start_time = current_time
                        msg = f"TRIMMING - Cycle {self.cycle_id}"
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                        self.add_event_log(msg)
                
                elif self.state == TrimmerState.TRIMMING:
                    if not is_present:
                        cycle_duration = current_time - self.state_start_time
                        self.state = TrimmerState.EMPTY
                        self.state_start_time = current_time
                        
                        self.db.log_event(
                            trimmer_id=self.machine_id,
                            event_type="pushed_out",
                            cycle_id=self.cycle_id,
                            req_lot=self.current_lot,
                            area=area,
                            details=f"duration_sec:{cycle_duration:.2f}"
                        )
                        
                        self.db.log_event(
                            trimmer_id=self.machine_id,
                            event_type="CYCLE",
                            cycle_id=self.cycle_id,
                            req_lot=self.current_lot,
                            details=f"cycle_time_sec:{cycle_duration:.2f}"
                        )
                        
                        self.total_cycles += 1
                        self.cycles_last_hour.append(current_time)
                        
                        msg = f"PUSHED - Cycle complete ({cycle_duration:.1f}s)"
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                        self.add_event_log(msg)
                        
                        self.cycle_id = None
                        self.current_lot = None
                
                # Send telemetry periodically
                if current_time - self.last_telemetry >= 60:
                    hour_ago = current_time - 3600
                    self.cycles_last_hour = [t for t in self.cycles_last_hour if t > hour_ago]
                    
                    self.db.log_telemetry(
                        trimmer_id=self.machine_id,
                        cycles_last_hour=len(self.cycles_last_hour),
                        uptime_seconds=int(current_time - self.boot_time),
                        status="ONLINE"
                    )
                    self.last_telemetry = current_time
                
                time.sleep(0.1)
            
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(1)
    
    def setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            return render_template_string(
                HTML_TEMPLATE,
                machine_id=self.machine_id,
                machine_name=self.config.machine_name,
                roi_x=self.config.roi_x,
                roi_y=self.config.roi_y,
                roi_w=self.config.roi_w,
                roi_h=self.config.roi_h,
                threshold=self.config.threshold,
                min_area=self.config.min_area
            )
        
        @self.app.route('/stream')
        def stream():
            def generate():
                while True:
                    with self.frame_lock:
                        data = self.last_jpeg
                    if data:
                        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n")
                    time.sleep(0.03)
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/status')
        def status():
            hour_ago = time.time() - 3600
            cycles_in_hour = [t for t in self.cycles_last_hour if t > hour_ago]
            
            with self.frame_lock:
                return jsonify({
                    'present': self.last_present,
                    'area': self.last_area,
                    'state': self.state.value,
                    'total_cycles': self.total_cycles,
                    'cycles_per_hour': len(cycles_in_hour),
                    'current_lot': self.current_lot,
                    'uptime': int(time.time() - self.boot_time)
                })
        
        @self.app.route('/events')
        def events():
            return jsonify({'events': self.recent_events})
        
        @self.app.route('/set_roi', methods=['POST'])
        def set_roi():
            data = request.json
            self.config.roi_x = int(data['x'])
            self.config.roi_y = int(data['y'])
            self.config.roi_w = int(data['w'])
            self.config.roi_h = int(data['h'])
            return jsonify({'ok': True})
        
        @self.app.route('/set_threshold', methods=['POST'])
        def set_threshold():
            self.config.threshold = int(request.json['threshold'])
            return jsonify({'ok': True})
        
        @self.app.route('/set_min_area', methods=['POST'])
        def set_min_area():
            self.config.min_area = int(request.json['min_area'])
            return jsonify({'ok': True})
        
        @self.app.route('/save_config', methods=['POST'])
        def save_config():
            success = self.db.save_trimmer_config(self.config)
            return jsonify({'ok': success})
        
        @self.app.route('/reload_config', methods=['POST'])
        def reload_config():
            new_config = self.db.load_trimmer_config(self.machine_id)
            if new_config:
                self.config = new_config
                return jsonify({
                    'ok': True,
                    'roi_x': new_config.roi_x,
                    'roi_y': new_config.roi_y,
                    'roi_w': new_config.roi_w,
                    'roi_h': new_config.roi_h,
                    'threshold': new_config.threshold,
                    'min_area': new_config.min_area
                })
            return jsonify({'ok': False})
    
    def start(self, port=8080):
        """Start the monitoring and web server."""
        print(f"\n{'='*60}")
        print(f"Trimmer Monitor with Web Interface")
        print(f"Machine: {self.config.machine_name} (ID: {self.machine_id})")
        print(f"Web Interface: http://{socket.gethostbyname(socket.gethostname())}:{port}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        # Start monitoring thread
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start Flask server
        try:
            self.app.run(host='0.0.0.0', port=port, threaded=True)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop monitoring and cleanup."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        try:
            self.picam2.stop()
        except:
            pass
        
        print(f"\nSession Summary:")
        print(f"  Total Cycles: {self.total_cycles}")
        print(f"  Uptime: {int(time.time() - self.boot_time)}s")


def main():
    parser = argparse.ArgumentParser(
        description="Trimmer Monitor with Integrated Web Interface"
    )
    parser.add_argument("--machine-id", type=int, required=True,
                       help="Machine ID from secondary_machines table")
    parser.add_argument("--device-id", type=str,
                       help="Unique Pi device identifier (default: hostname)")
    parser.add_argument("--db-host", type=str, default="192.168.1.6",
                       help="Database host")
    parser.add_argument("--db-port", type=int, default=3306,
                       help="Database port")
    parser.add_argument("--db-user", type=str, default="webapp",
                       help="Database user")
    parser.add_argument("--db-password", type=str, default="STUDS2650",
                       help="Database password")
    parser.add_argument("--db-name", type=str, default="iwt_db",
                       help="Database name")
    parser.add_argument("--port", type=int, default=8080,
                       help="Web interface port")
    
    args = parser.parse_args()
    
    # Get device ID
    device_id = args.device_id or socket.gethostname()
    
    # Connect to database
    db_config = MySQLConfig(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name
    )
    
    db = ConnectVisionDB(db_config)
    
    # Register device
    db.register_device(machine_id=args.machine_id, device_id=device_id)
    
    # Load configuration
    config = db.load_trimmer_config(args.machine_id)
    if not config:
        print(f"ERROR: Could not load config for machine {args.machine_id}")
        print("Make sure the machine exists in secondary_machines table")
        return 1
    
    # Create and start app
    app = TrimmerMonitorApp(
        machine_id=args.machine_id,
        db=db,
        config=config
    )
    
    app.start(port=args.port)
    
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
