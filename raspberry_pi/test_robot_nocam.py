#!/usr/bin/env python3
"""
SIMPLIFIED ROBOT CONTROL - NO CAMERA REQUIRED
For testing motors when camera has issues
"""

from flask import Flask, render_template_string, jsonify, request
import serial
import time
import threading

app = Flask(__name__)

# Configuration
MEGAPI_PORT = '/dev/ttyUSB0'
MEGAPI_BAUD = 115200

FORWARD_SPEED = 70
BACKWARD_SPEED = 70
TURN_SPEED = 80
MOVE_DURATION = 1000
TURN_90_DURATION = 2600

# Robot connection
robot_serial = None

def connect_robot():
    global robot_serial
    try:
        robot_serial = serial.Serial(MEGAPI_PORT, MEGAPI_BAUD, timeout=1)
        time.sleep(2)
        if robot_serial.in_waiting:
            robot_serial.readline()
        return True
    except:
        return False

def send_command(cmd):
    if robot_serial:
        try:
            robot_serial.write(f"{cmd}\n".encode())
            time.sleep(0.1)
            if robot_serial.in_waiting:
                return robot_serial.readline().decode().strip()
            return "OK"
        except Exception as e:
            return f"ERROR: {e}"
    return "ERROR: Not connected"

def get_distance():
    try:
        response = send_command('G')
        if 'DISTANCE:' in response:
            dist_str = response.split(':')[1].strip()
            if dist_str != "ERROR":
                return float(dist_str)
    except:
        pass
    return 400.0

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Robot Control - Simple</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; text-align: center; background: #f0f0f0; margin: 0; padding: 20px; }
        h1 { color: #333; }
        .status { display: flex; justify-content: center; gap: 10px; margin: 20px 0; }
        .status-box { padding: 15px 30px; border-radius: 8px; font-weight: bold; }
        .status-ok { background: #4CAF50; color: white; }
        .status-info { background: #2196F3; color: white; }
        .controls { max-width: 400px; margin: 20px auto; }
        button { width: 100%; padding: 20px; margin: 5px 0; font-size: 18px; border: none; border-radius: 8px; cursor: pointer; color: white; font-weight: bold; }
        .forward { background: #4CAF50; }
        .backward { background: #4CAF50; }
        .left { background: #2196F3; }
        .right { background: #2196F3; }
        .stop { background: #f44336; }
        .rotate { background: #9C27B0; }
        button:active { opacity: 0.7; }
        #log { max-width: 600px; margin: 20px auto; padding: 20px; background: #333; color: #0f0; border-radius: 8px; text-align: left; font-family: monospace; font-size: 14px; max-height: 300px; overflow-y: auto; }
    </style>
</head>
<body>
    <h1>🤖 Robot Control Dashboard</h1>
    
    <div class="status">
        <div class="status-box status-ok">ROBOT OK</div>
        <div class="status-box status-info" id="distance">Distance: --</div>
    </div>
    
    <div class="controls">
        <button class="forward" onclick="sendCommand('forward')">▲ FORWARD</button>
        <div style="display: flex; gap: 5px;">
            <button class="left" onclick="sendCommand('left')" style="width: 48%;">◄ LEFT 90</button>
            <button class="right" onclick="sendCommand('right')" style="width: 48%;">RIGHT 90 ►</button>
        </div>
        <button class="stop" onclick="sendCommand('stop')">⬛ STOP</button>
        <button class="backward" onclick="sendCommand('backward')">▼ BACKWARD</button>
        <button class="rotate" onclick="sendCommand('rotate')">🔄 ROTATE 360</button>
    </div>
    
    <div id="log"></div>
    
    <script>
        function log(msg) {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            logDiv.innerHTML = `[${time}] ${msg}<br>` + logDiv.innerHTML;
        }
        
        function sendCommand(cmd) {
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
        
        function updateDistance() {
            fetch('/distance')
            .then(r => r.json())
            .then(data => {
                document.getElementById('distance').textContent = `Distance: ${data.distance} cm`;
            });
        }
        
        setInterval(updateDistance, 1000);
        log('System ready');
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/distance')
def distance():
    dist = get_distance()
    return jsonify({'distance': f'{dist:.2f}'})

@app.route('/command', methods=['POST'])
def command():
    data = request.json
    cmd = data.get('command', '')
    
    if cmd == 'forward':
        response = send_command(f'F,{FORWARD_SPEED},{MOVE_DURATION}')
        return jsonify({'status': 'ok', 'message': f'Moving FORWARD ({response})'})
    
    elif cmd == 'backward':
        response = send_command(f'B,{BACKWARD_SPEED},{MOVE_DURATION}')
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

if __name__ == '__main__':
    print("=" * 60)
    print("ROBOT CONTROL DASHBOARD - SIMPLE MODE (NO CAMERA)")
    print("=" * 60)
    print()
    
    print("[1/1] Connecting to MegaPi...")
    if connect_robot():
        print("     ✅ Robot connected!")
    else:
        print("     ⚠️  Robot not connected (check USB cable)")
    
    print()
    print("=" * 60)
    print("ACCESS FROM ANY DEVICE:")
    print("  http://192.168.168.106:5000")
    print("=" * 60)
    print()
    print("Press Ctrl+C to stop")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=False)
