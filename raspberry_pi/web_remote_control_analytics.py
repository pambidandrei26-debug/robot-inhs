#!/usr/bin/env python3
"""
WEB REMOTE CONTROL WITH DATA ANALYTICS
Enhanced crack detection robot dashboard with statistics and charts
"""

from flask import Flask, render_template_string, jsonify, request, Response, send_file
import serial
import time
import threading
import json
import csv
from datetime import datetime
from collections import deque
import os

# Try to import camera
try:
    from picamera2 import Picamera2
    import cv2
    CAMERA_AVAILABLE = True
except:
    CAMERA_AVAILABLE = False

app = Flask(__name__)

# ========================================
# CONFIGURATION
# ========================================

MEGAPI_PORT = '/dev/ttyUSB0'
MEGAPI_BAUD = 115200
FORWARD_SPEED = 70
TURN_SPEED = 80
MOVE_DURATION = 1000
TURN_90_DURATION = 2600

DATA_DIR = os.path.expanduser("~/crack_detector/data")
os.makedirs(DATA_DIR, exist_ok=True)

# ========================================
# DATA STORAGE
# ========================================

class RobotAnalytics:
    def __init__(self):
        self.session_start = datetime.now()
        self.total_commands = 0
        self.total_distance_traveled = 0
        self.distance_readings = deque(maxlen=100)  # Last 100 readings
        self.command_history = deque(maxlen=50)
        self.scan_sessions = []
        self.current_session = {
            'start_time': datetime.now().isoformat(),
            'commands': 0,
            'distance_data': [],
            'detections': []
        }
    
    def log_command(self, command, response):
        self.total_commands += 1
        self.current_session['commands'] += 1
        self.command_history.append({
            'time': datetime.now().isoformat(),
            'command': command,
            'response': response
        })
    
    def log_distance(self, distance):
        try:
            dist_float = float(distance)
            self.distance_readings.append({
                'time': time.time(),
                'distance': dist_float
            })
            self.current_session['distance_data'].append({
                'time': datetime.now().isoformat(),
                'distance': dist_float
            })
        except:
            pass
    
    def log_detection(self, detection_type, confidence=None):
        detection = {
            'time': datetime.now().isoformat(),
            'type': detection_type,
            'confidence': confidence
        }
        self.current_session['detections'].append(detection)
    
    def get_statistics(self):
        distances = [r['distance'] for r in self.distance_readings if 'distance' in r]
        
        stats = {
            'session_duration': str(datetime.now() - self.session_start).split('.')[0],
            'total_commands': self.total_commands,
            'current_session_commands': self.current_session['commands'],
            'total_detections': len(self.current_session['detections']),
            'distance_stats': {
                'min': min(distances) if distances else 0,
                'max': max(distances) if distances else 0,
                'avg': sum(distances) / len(distances) if distances else 0,
                'current': distances[-1] if distances else 0,
                'readings_count': len(distances)
            },
            'recent_commands': list(self.command_history)[-10:],
            'recent_distances': list(self.distance_readings)[-20:]
        }
        return stats
    
    def export_session_data(self):
        filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(self.current_session, f, indent=2)
        
        return filepath
    
    def export_csv(self):
        filename = f"distance_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Distance (cm)'])
            for reading in self.distance_readings:
                writer.writerow([reading.get('time', ''), reading.get('distance', '')])
        
        return filepath

analytics = RobotAnalytics()

# ========================================
# ROBOT CONNECTION
# ========================================

robot_serial = None

def connect_robot():
    global robot_serial
    try:
        robot_serial = serial.Serial(MEGAPI_PORT, MEGAPI_BAUD, timeout=1)
        time.sleep(2)
        return True
    except:
        return False

def send_command(cmd):
    if robot_serial:
        try:
            robot_serial.write(f"{cmd}\n".encode())
            time.sleep(0.1)
            if robot_serial.in_waiting:
                response = robot_serial.readline().decode().strip()
            else:
                response = "OK"
            analytics.log_command(cmd, response)
            return response
        except Exception as e:
            return f"ERROR: {e}"
    return "ERROR: Not connected"

def get_distance():
    try:
        response = send_command('G')
        if 'DISTANCE:' in response:
            dist_str = response.split(':')[1].strip()
            if dist_str != "ERROR":
                analytics.log_distance(dist_str)
                return float(dist_str)
    except:
        pass
    return 400.0

# Background distance monitoring
def distance_monitor():
    while True:
        get_distance()
        time.sleep(1)

# ========================================
# HTML TEMPLATE WITH ANALYTICS
# ========================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Robot Control & Analytics</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        .header {
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 { color: #667eea; font-size: 28px; }
        
        .status-badges {
            display: flex;
            gap: 10px;
        }
        
        .badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }
        
        .badge-success { background: #10b981; color: white; }
        .badge-info { background: #3b82f6; color: white; }
        
        .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        
        button {
            padding: 20px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            color: white;
        }
        
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        button:active { transform: translateY(0); }
        
        .btn-forward { background: #10b981; grid-column: 2; }
        .btn-left { background: #3b82f6; }
        .btn-stop { background: #ef4444; grid-column: 2; }
        .btn-right { background: #3b82f6; }
        .btn-backward { background: #10b981; grid-column: 2; }
        .btn-rotate { background: #8b5cf6; grid-column: 1 / -1; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            color: white;
            text-align: center;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .stat-label {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        
        .log {
            background: #1f2937;
            color: #10b981;
            padding: 15px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            height: 250px;
            overflow-y: auto;
        }
        
        .log-entry {
            margin-bottom: 5px;
            padding: 5px;
            border-left: 3px solid #10b981;
            padding-left: 10px;
        }
        
        .export-buttons {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .btn-export {
            flex: 1;
            padding: 12px;
            background: #10b981;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .btn-export:hover { background: #059669; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Robot Control & Analytics Dashboard</h1>
            <div class="status-badges">
                <span class="badge badge-success">ROBOT OK</span>
                <span class="badge badge-info" id="distance-badge">Distance: --</span>
            </div>
        </div>
        
        <div class="grid">
            <!-- LEFT COLUMN -->
            <div>
                <!-- Statistics -->
                <div class="card">
                    <h2>📊 Session Statistics</h2>
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-label">Session Duration</div>
                            <div class="stat-value" id="duration">00:00:00</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Total Commands</div>
                            <div class="stat-value" id="commands">0</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Avg Distance</div>
                            <div class="stat-value" id="avg-distance">0.0 cm</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Detections</div>
                            <div class="stat-value" id="detections">0</div>
                        </div>
                    </div>
                </div>
                
                <!-- Distance Chart -->
                <div class="card" style="margin-top: 20px;">
                    <h2>📈 Distance Over Time</h2>
                    <div class="chart-container">
                        <canvas id="distanceChart"></canvas>
                    </div>
                </div>
                
                <!-- Export Data -->
                <div class="card" style="margin-top: 20px;">
                    <h2>💾 Export Data</h2>
                    <div class="export-buttons">
                        <button class="btn-export" onclick="exportJSON()">📄 Export JSON</button>
                        <button class="btn-export" onclick="exportCSV()">📊 Export CSV</button>
                    </div>
                    <a href="/reports" style="display: block; text-align: center; margin-top: 10px; color: #667eea; text-decoration: none; font-weight: bold;">
                        📥 View All Reports →
                    </a>
                </div>
            </div>
            
            <!-- RIGHT COLUMN -->
            <div>
                <!-- Controls -->
                <div class="card">
                    <h2>🎮 Robot Controls</h2>
                    <div class="controls">
                        <button class="btn-forward" onclick="sendCmd('forward')">▲<br>FORWARD</button>
                        <button class="btn-left" onclick="sendCmd('left')">◄<br>LEFT</button>
                        <button class="btn-stop" onclick="sendCmd('stop')">⬛<br>STOP</button>
                        <button class="btn-right" onclick="sendCmd('right')">►<br>RIGHT</button>
                        <button class="btn-backward" onclick="sendCmd('backward')">▼<br>BACK</button>
                        <button class="btn-rotate" onclick="sendCmd('rotate')">🔄 ROTATE 360°</button>
                    </div>
                </div>
                
                <!-- Activity Log -->
                <div class="card" style="margin-top: 20px;">
                    <h2>📝 Activity Log</h2>
                    <div class="log" id="log"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Chart setup
        const ctx = document.getElementById('distanceChart').getContext('2d');
        const distanceData = {
            labels: [],
            datasets: [{
                label: 'Distance (cm)',
                data: [],
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };
        
        const chart = new Chart(ctx, {
            type: 'line',
            data: distanceData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Distance (cm)' } },
                    x: { display: false }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
        
        function log(msg) {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = `[${time}] ${msg}`;
            logDiv.insertBefore(entry, logDiv.firstChild);
        }
        
        function sendCmd(cmd) {
            fetch('/command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd})
            })
            .then(r => r.json())
            .then(data => {
                log(data.message);
            });
        }
        
        function updateStats() {
            fetch('/statistics')
            .then(r => r.json())
            .then(data => {
                document.getElementById('duration').textContent = data.session_duration;
                document.getElementById('commands').textContent = data.total_commands;
                document.getElementById('avg-distance').textContent = data.distance_stats.avg.toFixed(1) + ' cm';
                document.getElementById('detections').textContent = data.total_detections;
                document.getElementById('distance-badge').textContent = 'Distance: ' + data.distance_stats.current.toFixed(1) + ' cm';
                
                // Update chart
                if (data.recent_distances.length > 0) {
                    distanceData.labels = data.recent_distances.map((_, i) => i);
                    distanceData.datasets[0].data = data.recent_distances.map(r => r.distance);
                    chart.update('none');
                }
            });
        }
        
        function exportJSON() {
            fetch('/export/json')
            .then(r => r.json())
            .then(data => {
                log('✓ Exported session data: ' + data.filename);
                if (confirm('Data exported! Download now?')) {
                    window.location.href = data.download_url;
                }
            });
        }
        
        function exportCSV() {
            fetch('/export/csv')
            .then(r => r.json())
            .then(data => {
                log('✓ Exported distance log: ' + data.filename);
                if (confirm('Data exported! Download now?')) {
                    window.location.href = data.download_url;
                }
            });
        }
        
        // Update every second
        setInterval(updateStats, 1000);
        log('System ready');
    </script>
</body>
</html>
"""

# ========================================
# ROUTES
# ========================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/statistics')
def statistics():
    return jsonify(analytics.get_statistics())

@app.route('/command', methods=['POST'])
def command():
    data = request.json
    cmd = data.get('command', '')
    
    if cmd == 'forward':
        response = send_command(f'F,{FORWARD_SPEED},{MOVE_DURATION}')
        return jsonify({'status': 'ok', 'message': f'Moving FORWARD ({response})'})
    
    elif cmd == 'backward':
        response = send_command(f'B,{FORWARD_SPEED},{MOVE_DURATION}')
        return jsonify({'status': 'ok', 'message': f'Moving BACKWARD ({response})'})
    
    elif cmd == 'left':
        response = send_command(f'L,{TURN_SPEED},{TURN_90_DURATION}')
        return jsonify({'status': 'ok', 'message': f'Turning LEFT 90° ({response})'})
    
    elif cmd == 'right':
        response = send_command(f'R,{TURN_SPEED},{TURN_90_DURATION}')
        return jsonify({'status': 'ok', 'message': f'Turning RIGHT 90° ({response})'})
    
    elif cmd == 'stop':
        response = send_command('S')
        return jsonify({'status': 'ok', 'message': f'EMERGENCY STOP! ({response})'})
    
    elif cmd == 'rotate':
        response = send_command(f'L,{TURN_SPEED},{TURN_90_DURATION * 4}')
        return jsonify({'status': 'ok', 'message': f'Rotating 360° ({response})'})
    
    return jsonify({'status': 'error', 'message': 'Unknown command'})

@app.route('/export/json')
def export_json():
    filepath = analytics.export_session_data()
    filename = os.path.basename(filepath)
    return jsonify({
        'status': 'ok',
        'filepath': filepath,
        'filename': filename,
        'download_url': f'/download/{filename}'
    })

@app.route('/export/csv')
def export_csv():
    filepath = analytics.export_csv()
    filename = os.path.basename(filepath)
    return jsonify({
        'status': 'ok',
        'filepath': filepath,
        'filename': filename,
        'download_url': f'/download/{filename}'
    })

@app.route('/download/<filename>')
def download_file(filename):
    """Download exported file"""
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File not found'}), 404

@app.route('/reports')
def reports_page():
    """View all available reports"""
    files = []
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            filepath = os.path.join(DATA_DIR, f)
            files.append({
                'name': f,
                'size': os.path.getsize(filepath),
                'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
            })
    
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reports & Downloads</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial; background: #f5f5f5; padding: 20px; }
            .container { max-width: 1000px; margin: 0 auto; }
            .header { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            h1 { color: #667eea; margin: 0; }
            .back-btn { 
                display: inline-block;
                padding: 10px 20px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            table {
                width: 100%;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            th {
                background: #667eea;
                color: white;
                padding: 15px;
                text-align: left;
            }
            td {
                padding: 12px 15px;
                border-bottom: 1px solid #eee;
            }
            tr:hover { background: #f9f9f9; }
            .download-btn {
                background: #10b981;
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
                text-decoration: none;
                display: inline-block;
            }
            .download-btn:hover { background: #059669; }
            .delete-btn {
                background: #ef4444;
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
                text-decoration: none;
                display: inline-block;
                margin-left: 5px;
                cursor: pointer;
                border: none;
            }
            .delete-btn:hover { background: #dc2626; }
            .no-files {
                text-align: center;
                padding: 40px;
                color: #999;
                background: white;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">← Back to Dashboard</a>
            
            <div class="header">
                <h1>📊 Reports & Downloads</h1>
                <p>All exported session data and distance logs</p>
            </div>
            
            {% if files %}
            <table>
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>Size</th>
                        <th>Date Modified</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for file in files %}
                    <tr>
                        <td>{{ file.name }}</td>
                        <td>{{ "%.2f"|format(file.size / 1024) }} KB</td>
                        <td>{{ file.modified.split('T')[0] }} {{ file.modified.split('T')[1].split('.')[0] }}</td>
                        <td>
                            <a href="/download/{{ file.name }}" class="download-btn">📥 Download</a>
                            <button class="delete-btn" onclick="deleteFile('{{ file.name }}')">🗑️ Delete</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="no-files">
                <h2>No reports yet</h2>
                <p>Export data from the dashboard to generate reports</p>
            </div>
            {% endif %}
        </div>
        
        <script>
            function deleteFile(filename) {
                if (confirm('Delete ' + filename + '?')) {
                    fetch('/delete/' + filename, {method: 'DELETE'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        location.reload();
                    });
                }
            }
        </script>
    </body>
    </html>
    """
    
    from flask import render_template_string
    return render_template_string(html, files=files)

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a report file"""
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'status': 'ok', 'message': f'Deleted {filename}'})
    return jsonify({'status': 'error', 'message': 'File not found'}), 404

# ========================================
# MAIN
# ========================================

if __name__ == '__main__':
    print("=" * 70)
    print("ROBOT CONTROL DASHBOARD WITH ANALYTICS")
    print("=" * 70)
    print()
    
    print("[1/2] Connecting to MegaPi...")
    if connect_robot():
        print("     ✅ Robot connected!")
    else:
        print("     ⚠️  Robot not connected")
    
    print()
    print("[2/2] Starting distance monitor...")
    monitor_thread = threading.Thread(target=distance_monitor, daemon=True)
    monitor_thread.start()
    print("     ✅ Monitoring started!")
    
    print()
    print("=" * 70)
    print("ACCESS DASHBOARD:")
    print("  http://192.168.168.106:5000")
    print("=" * 70)
    print()
    print("Features:")
    print("  📊 Real-time statistics")
    print("  📈 Distance graphs")
    print("  💾 Export data (JSON/CSV)")
    print("  📝 Activity logging")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=False)
