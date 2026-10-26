#!/usr/bin/env python3
"""
WEB-BASED REMOTE CONTROL FOR CRACK DETECTION ROBOT
Access from any device on same WiFi network
URL: http://ROBOT_IP:5000

FEATURES:
- Regular camera (visible light)
- Thermal camera (MLX90640 heat map)
- Manual controls with calibrated timing
- Live distance monitoring
"""

from flask import Flask, render_template_string, jsonify, request, Response
import serial
import time
import subprocess
import threading
import numpy as np
import json as _json
import os as _os

# Try to import regular camera
try:
    import cv2
    CAMERA_AVAILABLE = True
except:
    CAMERA_AVAILABLE = False

# Try to import thermal camera
try:
    import board
    import busio
    import adafruit_mlx90640
    THERMAL_AVAILABLE = True
except:
    THERMAL_AVAILABLE = False

app = Flask(__name__)

# ========================================
# CONFIGURATION
# ========================================

import glob as _portglob
_detected = sorted(_portglob.glob('/dev/ttyUSB*') + _portglob.glob('/dev/ttyACM*'))
MEGAPI_PORT = _detected[0] if _detected else '/dev/ttyUSB0'
print(f"[PORT] Auto-detected: {MEGAPI_PORT}")
MEGAPI_BAUD = 115200

FORWARD_SPEED = 70
BACKWARD_SPEED = 70
TURN_SPEED = 80

COMMAND_DELAY = 0.1
MOVE_STEP_DURATION = 1000

# -- Load wheel calibration if it exists ---------------------
_WHEEL_CAL_FILE = _os.path.expanduser("~/wheel_calibration.json")
_wheel_cal = {}
if _os.path.exists(_WHEEL_CAL_FILE):
    try:
        with open(_WHEEL_CAL_FILE) as _wf:
            _wheel_cal = _json.load(_wf)
        print(f"[WHEEL] Calibration loaded from {_WHEEL_CAL_FILE}")
        print(f"  Right 90deg = {_wheel_cal.get('right_90_ms','?')} ms")
        print(f"  Left  90deg  = {_wheel_cal.get('left_90_ms','?')} ms")
        print(f"  360deg durations = {_wheel_cal.get('turn_durations_360','?')}")
    except Exception as _we:
        print(f"[WHEEL] Could not load calibration: {_we} -- using defaults")
        _wheel_cal = {}
else:
    print("[WHEEL] No wheel calibration found -- using default 2600ms")
    print(f"        Run  python3 ~/wheel_calibration.py  to calibrate")

# Turn durations used by the web dashboard (overridden by calibration)
TURN_RIGHT_90_MS = int(_wheel_cal.get('right_90_ms', 2600))
TURN_LEFT_90_MS  = int(_wheel_cal.get('left_90_ms',  2600))
TURN_DURATIONS_360 = _wheel_cal.get('turn_durations_360',
                                    [TURN_RIGHT_90_MS] * 4)

# ========================================
# ROBOT CONNECTION
# ========================================

robot_serial = None
serial_lock = threading.Lock()

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
    """Send command to MegaPi with thread-safe error handling"""
    global robot_serial
    with serial_lock:
        if robot_serial:
            try:
                if robot_serial.in_waiting:
                    robot_serial.reset_input_buffer()
                robot_serial.write(f"{cmd}\n".encode())
                time.sleep(COMMAND_DELAY)
                start_time = time.time()
                while time.time() - start_time < 1.0:
                    if robot_serial.in_waiting:
                        response = robot_serial.readline().decode().strip()
                        return response if response else "OK"
                    time.sleep(0.01)
                return "OK"
            except serial.SerialException as e:
                print(f"Serial error: {e}")
                robot_serial = None
                return f"ERROR: Serial disconnected - {e}"
            except Exception as e:
                print(f"Command error: {e}")
                return f"ERROR: {e}"
        return "ERROR: Not connected"

def get_distance_value():
    try:
        response = send_command('G')
        if 'DISTANCE:' in response:
            dist_str = response.split(':')[1].strip()
            if dist_str != "ERROR":
                return dist_str
    except:
        pass
    return None

# ========================================
# CAMERA SETUP
# ========================================

camera = None
thermal = None
frame_lock = threading.Lock()
current_rgb_frame = None
current_thermal_frame = None

def init_camera():
    global camera
    if not CAMERA_AVAILABLE:
        return False
    try:
        camera = cv2.VideoCapture(0)
        if camera.isOpened():
            print("[CAMERA] RGB camera initialized!")
            return True
        else:
            camera = None
            return False
    except Exception as e:
        print(f"[CAMERA] init failed: {e}")
        camera = None
        return False

def init_thermal():
    global thermal
    if not THERMAL_AVAILABLE:
        return False
    try:
        i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
        thermal = adafruit_mlx90640.MLX90640(i2c)
        thermal.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
        time.sleep(1)
        return True
    except:
        return False

_cached_distance = None

_cam_lock = threading.Lock()

def get_camera_frame():
    global current_rgb_frame, camera
    if not camera or not camera.isOpened():
        return None
    try:
        ret, frame = camera.read()
        if ret:
            if _cached_distance:
                cv2.putText(frame, f"Dist: {_cached_distance} cm", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            ret2, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ret2:
                with frame_lock:
                    current_rgb_frame = buffer.tobytes()
        return current_rgb_frame
    except:
        return current_rgb_frame

_CAL_FILE = _os.path.expanduser("~/thermal_calibration.json")
_calibration = {}
if _os.path.exists(_CAL_FILE):
    try:
        with open(_CAL_FILE) as _f:
            _calibration = _json.load(_f)
        print(f"[THERMAL] Calibration loaded from {_CAL_FILE}")
    except Exception as _e:
        print(f"[THERMAL] Could not load calibration: {_e} -- using defaults")
        _calibration = {}
else:
    print("[THERMAL] No calibration file found -- using default thresholds")
    print(f"          Run  python3 ~/thermal_wall_calibration.py  to calibrate")


def classify_surface_type(temps):
    """Surface classification using thermal pattern."""
    valid = (temps > 5.0) & (temps < 80.0)
    if np.sum(valid) < 100:
        return 'WALL', 80
    clean = temps[valid]
    avg   = float(clean.mean())
    body_pixels = np.sum((temps >= 34.5) & (temps <= 39.0))
    body_pct    = body_pixels / temps.size * 100
    if body_pct > 20:
        return 'PERSON', min(100, int(body_pct * 3))
    return 'WALL', 90


latest_crack_analysis = {}
crack_analysis_lock   = threading.Lock()
_last_nonzero = {}

def analyze_thermal_for_cracks(temps):
    """Analyze thermal frame for crack size measurements."""
    PIXEL_CM_H = 0.98
    PIXEL_CM_V = 0.81
    if _calibration:
        TEMP_DIFF_THRESHOLD = _calibration.get('crack_detection', {}).get('temp_diff_threshold', 3.0)
        ANOMALY_SIGMA = _calibration.get('crack_detection', {}).get('anomaly_sigma', 2.0)
    else:
        TEMP_DIFF_THRESHOLD = 0.8
        ANOMALY_SIGMA = 0.8

    valid = (temps > 5.0) & (temps < 80.0)
    valid_count = np.sum(valid)
    if valid_count < int(temps.size * 0.8):
        return None

    clean      = temps[valid] if valid_count < temps.size else temps
    avg_temp   = float(clean.mean())
    std_temp   = float(clean.std())
    temp_min   = float(clean.min())
    temp_max   = float(clean.max())
    temp_range = temp_max - temp_min

    surface_type, surface_conf = classify_surface_type(temps)
    wall_flag = (surface_type == 'WALL')

    result = {
        'is_wall':         wall_flag,
        'wall_confidence': surface_conf,
        'surface_type':    surface_type,
        'anomaly':         False,
        'avg_temp':        round(avg_temp, 1),
        'min_temp':        round(temp_min, 1),
        'max_temp':        round(temp_max, 1),
        'temp_range':      round(temp_range, 2),
        'length_cm':       0.0,
        'width_cm':        0.0,
        'area_cm2':        0.0,
        'depth_cm':        0,
        'affected_pixels': 0,
        'anomaly_type':    'none',
        'wall_details':    {},
    }

    if not wall_flag:
        result['anomaly_type'] = 'not_a_wall'
        return result

    if temp_range <= TEMP_DIFF_THRESHOLD:
        return result

    result['anomaly'] = True
    clean_temps = np.where((temps > 5.0) & (temps < 80.0), temps, avg_temp)
    cold_mask    = clean_temps < (avg_temp - ANOMALY_SIGMA * std_temp)
    hot_mask     = clean_temps > (avg_temp + ANOMALY_SIGMA * std_temp)
    anomaly_mask = cold_mask | hot_mask

    if not np.any(anomaly_mask):
        cold_mask    = clean_temps < (avg_temp - ANOMALY_SIGMA * 0.5 * std_temp)
        hot_mask     = clean_temps > (avg_temp + ANOMALY_SIGMA * 0.5 * std_temp)
        anomaly_mask = cold_mask | hot_mask

    if not np.any(anomaly_mask):
        return result

    y_coords, x_coords = np.where(anomaly_mask)
    min_x, max_x = int(x_coords.min()), int(x_coords.max())
    min_y, max_y = int(y_coords.min()), int(y_coords.max())

    w_cm = (max_x - min_x + 1) * PIXEL_CM_H
    h_cm = (max_y - min_y + 1) * PIXEL_CM_V
    length_cm = round(max(w_cm, h_cm), 1)
    width_cm  = round(min(w_cm, h_cm), 1)
    num_px    = int(np.sum(anomaly_mask))
    area_cm2  = round(num_px * PIXEL_CM_H * PIXEL_CM_V, 1)

    max_dev = max(abs(temp_min - avg_temp), abs(temp_max - avg_temp))
    if max_dev > 3:   depth_cm = 2
    elif max_dev > 2: depth_cm = 4
    elif max_dev > 1: depth_cm = 7
    else:             depth_cm = 10

    result.update({
        'length_cm':       length_cm,
        'width_cm':        width_cm,
        'area_cm2':        area_cm2,
        'depth_cm':        depth_cm,
        'affected_pixels': num_px,
        'anomaly_type':    'cold_spot' if np.sum(cold_mask) > np.sum(hot_mask) else 'hot_spot',
    })
    return result


def get_thermal_frame():
    global current_thermal_frame, thermal, latest_crack_analysis
    if not thermal:
        return None
    try:
        frame = [0] * 768
        thermal.getFrame(frame)
        temps = np.array(frame).reshape(24, 32)

        analysis = analyze_thermal_for_cracks(temps)
        if analysis is None:
            with crack_analysis_lock:
                pass
        else:
            with crack_analysis_lock:
                if analysis.get('length_cm', 0) > 0:
                    _last_nonzero.update(analysis)
                if (analysis.get('anomaly') and
                        analysis.get('length_cm', 0) == 0 and
                        _last_nonzero.get('length_cm', 0) > 0):
                    analysis['length_cm']       = _last_nonzero['length_cm']
                    analysis['width_cm']        = _last_nonzero['width_cm']
                    analysis['area_cm2']        = _last_nonzero['area_cm2']
                    analysis['depth_cm']        = _last_nonzero['depth_cm']
                    analysis['affected_pixels'] = _last_nonzero.get('affected_pixels', 0)
                latest_crack_analysis = analysis

        valid_ratio = np.sum((temps > 5.0) & (temps < 80.0)) / temps.size
        if valid_ratio < 0.8:
            with frame_lock:
                return current_thermal_frame if current_thermal_frame else None

        temp_min = float(temps[temps > 5.0].min()) if np.any(temps > 5.0) else float(temps.min())
        temp_max = float(temps.max())
        if temp_max > temp_min:
            normalized = ((temps - temp_min) / (temp_max - temp_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros((24, 32), dtype=np.uint8)

        colored = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)
        resized = cv2.resize(colored, (480, 360), interpolation=cv2.INTER_NEAREST)

        cv2.putText(resized, f"Max: {temp_max:.1f}C", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(resized, f"Min: {temp_min:.1f}C", (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(resized, f"Avg: {temps.mean():.1f}C", (10, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        if analysis['anomaly']:
            cv2.putText(resized, "CRACK DETECTED", (50, 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(resized, f"L:{analysis['length_cm']}cm W:{analysis['width_cm']}cm",
                       (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            cv2.putText(resized, f"Area:{analysis['area_cm2']}cm2 D:~{analysis['depth_cm']}cm",
                       (20, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        elif analysis.get('surface_type') == 'PERSON':
            cv2.putText(resized, "PERSON DETECTED", (30, 130),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
            cv2.putText(resized, f"Temp: {analysis.get('avg_temp',0):.1f}C",
                       (80, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        elif analysis.get('surface_type') == 'OBJECT':
            cv2.putText(resized, "OBJECT/OBSTACLE", (30, 130),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        elif not analysis.get('is_wall', True):
            cv2.putText(resized, "NOT A WALL", (70, 130),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        else:
            cv2.putText(resized, "WALL OK - No Crack",
                       (40, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            wconf = analysis.get('wall_confidence', 0)
            cv2.putText(resized, f"Wall confidence: {wconf}%",
                       (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret:
            with frame_lock:
                current_thermal_frame = buffer.tobytes()
            return current_thermal_frame
    except Exception as e:
        print(f"[THERMAL] Error: {e}")
    return None

def generate_rgb_frames():
    """Generate RGB camera frames or fallback image if camera unavailable"""
    # Create a fallback "Camera Unavailable" image
    fallback_frame = None
    try:
        import cv2
        import numpy as np
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, "RGB Camera Unavailable", (120, 220),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 100, 100), 2)
        cv2.putText(img, "DV28 USB Camera Incompatible", (100, 270),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 1)
        cv2.putText(img, "Thermal camera is primary sensor", (90, 320),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 1)
        _, buffer = cv2.imencode('.jpg', img)
        fallback_frame = buffer.tobytes()
    except:
        pass
    
    no_frame_count = 0
    while True:
        frame = get_camera_frame()
        if frame:
            no_frame_count = 0
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            no_frame_count += 1
            # After 5 failed attempts, show fallback image
            if no_frame_count > 5 and fallback_frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + fallback_frame + b'\r\n')
        time.sleep(0.5)

def generate_thermal_frames():
    while True:
        frame = get_thermal_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.25)

def _distance_updater():
    """Background thread: update cached distance every 1.5s"""
    global _cached_distance
    while True:
        try:
            val = get_distance_value()
            if val:
                _cached_distance = val
        except:
            pass
        time.sleep(1.5)

# ========================================
# WEB INTERFACE
# ========================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>CrackBot Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg:      #060d1a;
            --card:    #0c1526;
            --card2:   #101d30;
            --border:  #1a2d4a;
            --border2: #223556;
            --accent:  #3b82f6;
            --accent2: #60a5fa;
            --green:   #22c55e;
            --red:     #ef4444;
            --orange:  #f97316;
            --text:    #e2e8f0;
            --muted:   #64748b;
            --muted2:  #94a3b8;
            --r:       12px;
            --rs:      8px;
        }
        *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; font-size:14px; }

        /* TOPBAR */
        .topbar {
            position:sticky; top:0; z-index:100; height:56px;
            background:rgba(6,13,26,.92); backdrop-filter:blur(12px);
            border-bottom:1px solid var(--border);
            display:flex; align-items:center; justify-content:space-between; padding:0 20px;
        }
        .brand { display:flex; align-items:center; gap:10px; }
        .brand-icon {
            width:34px; height:34px; background:linear-gradient(135deg,#1d4ed8,#3b82f6);
            border-radius:8px; display:flex; align-items:center; justify-content:center;
            font-size:18px; box-shadow:0 0 16px rgba(59,130,246,.4);
        }
        .brand-name { font-size:15px; font-weight:800; color:white; letter-spacing:-.4px; }
        .brand-sub  { font-size:10px; color:var(--muted2); margin-top:1px; }
        .pills { display:flex; gap:6px; }
        .pill {
            display:flex; align-items:center; gap:5px; padding:4px 10px;
            border-radius:20px; font-size:10px; font-weight:700; letter-spacing:.6px;
            font-family:'JetBrains Mono',monospace;
        }
        .pill-dot { width:5px; height:5px; border-radius:50%; }
        .pill-g { background:rgba(34,197,94,.12); color:var(--green); border:1px solid rgba(34,197,94,.25); }
        .pill-b { background:rgba(59,130,246,.12); color:var(--accent2); border:1px solid rgba(59,130,246,.25); }
        .pill-g .pill-dot { background:var(--green); box-shadow:0 0 5px var(--green); animation:pulse 2s infinite; }
        .pill-b .pill-dot { background:var(--accent2); }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

        /* STATS ROW */
        .stats-row { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; padding:14px 16px 0; max-width:1360px; margin:0 auto; }
        .stat { background:var(--card); border:1px solid var(--border); border-radius:var(--r); padding:12px 14px; display:flex; align-items:center; gap:12px; transition:border-color .2s, transform .2s; }
        .stat:hover { border-color:var(--border2); transform:translateY(-1px); }
        .stat-ico { width:40px; height:40px; border-radius:10px; flex-shrink:0; display:flex; align-items:center; justify-content:center; font-size:18px; }
        .ico-g { background:rgba(34,197,94,.1); }
        .ico-b { background:rgba(59,130,246,.1); }
        .ico-p { background:rgba(168,85,247,.1); }
        .ico-o { background:rgba(249,115,22,.1); }
        .stat-lbl { font-size:9px; color:var(--muted); text-transform:uppercase; letter-spacing:1.2px; font-weight:600; }
        .stat-val { font-size:20px; font-weight:700; margin-top:2px; font-family:'JetBrains Mono',monospace; }
        .val-g { color:var(--green); }
        .val-b { color:var(--accent2); }
        .val-p { color:#c084fc; }
        .val-o { color:var(--orange); }
        .stat-unit { font-size:11px; color:var(--muted); margin-left:2px; }

        /* MAIN GRID */
        .grid { display:grid; grid-template-columns:1fr 300px; gap:12px; padding:14px 16px; max-width:1360px; margin:0 auto; }
        .col-left  { display:flex; flex-direction:column; gap:12px; }
        .col-right { display:flex; flex-direction:column; gap:12px; }

        /* CARD */
        .card { background:var(--card); border:1px solid var(--border); border-radius:var(--r); overflow:hidden; }
        .card-head { padding:10px 14px; border-bottom:1px solid var(--border); background:var(--card2); display:flex; align-items:center; gap:8px; }
        .card-title { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1.4px; color:var(--muted2); }
        .card-dot { width:6px; height:6px; border-radius:50%; margin-left:auto; }
        .dot-on  { background:var(--green); box-shadow:0 0 6px var(--green); animation:pulse 2s infinite; }
        .dot-off { background:var(--red); }
        .card-body { padding:14px; }

        /* CAMERAS */
        .cam-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
        .cam-wrap img, .cam-wrap .no-cam { width:100%; display:block; background:#000; min-height:180px; }
        .no-cam { min-height:180px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; color:var(--muted); font-size:12px; background:linear-gradient(145deg,#080f1c,#0c1526); }

        /* SCAN MONITOR */
        .scan-mon { display:none; border:1px solid rgba(34,197,94,.25); border-radius:var(--r); overflow:hidden; }
        .scan-mon-head { padding:8px 14px; font-size:10px; font-weight:700; color:var(--green); letter-spacing:1.2px; background:rgba(34,197,94,.06); border-bottom:1px solid rgba(34,197,94,.15); display:flex; align-items:center; gap:6px; }
        .scan-mon-body { padding:10px; max-height:140px; overflow-y:auto; font-family:'JetBrains Mono',monospace; font-size:10px; line-height:1.8; background:var(--card); }

        /* CRACK ANALYSIS */
        .crack-status { padding:9px 13px; border-radius:var(--rs); font-size:12px; font-weight:700; margin-bottom:12px; font-family:'JetBrains Mono',monospace; display:flex; align-items:center; gap:8px; }
        .cs-ok   { background:rgba(34,197,94,.07);  color:var(--green);  border:1px solid rgba(34,197,94,.2); }
        .cs-bad  { background:rgba(239,68,68,.07);  color:var(--red);    border:1px solid rgba(239,68,68,.2); }
        .cs-warn { background:rgba(249,115,22,.07); color:var(--orange); border:1px solid rgba(249,115,22,.2); }
        .metrics-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:10px; }
        .metric { background:var(--card2); border:1px solid var(--border); border-radius:var(--rs); padding:10px 6px; text-align:center; }
        .m-lbl  { font-size:8px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; font-weight:600; }
        .m-val  { font-size:17px; font-weight:700; font-family:'JetBrains Mono',monospace; margin:4px 0 2px; color:var(--accent2); }
        .m-unit { font-size:8px; color:var(--muted); }
        .temp-bar { background:var(--card2); border:1px solid var(--border); border-radius:var(--rs); padding:8px 12px; font-size:10px; color:var(--muted); font-family:'JetBrains Mono',monospace; line-height:2; }
        .temp-bar b { color:var(--text); }
        .priority-badge { display:none; margin-top:10px; padding:9px 13px; border-radius:var(--rs); font-size:12px; font-weight:700; font-family:'JetBrains Mono',monospace; }

        /* TRIAL TABLE */
        .tbl { width:100%; border-collapse:collapse; font-size:11px; }
        .tbl th { padding:8px 10px; background:var(--card2); border:1px solid var(--border); color:var(--muted); font-weight:600; text-transform:uppercase; letter-spacing:.7px; font-size:9px; }
        .tbl td { padding:7px 10px; border:1px solid var(--border); color:var(--text); }
        .tbl tr:hover td { background:rgba(59,130,246,.04); }

        /* ACTIVITY LOG */
        .log-body { max-height:110px; overflow-y:auto; font-family:'JetBrains Mono',monospace; font-size:10px; }
        .log-entry { padding:3px 0; border-bottom:1px solid rgba(26,45,74,.5); line-height:1.6; }
        .log-entry:last-child { border:none; }
        .log-time { color:#334155; margin-right:5px; }
        .log-ok   { color:var(--green); }
        .log-warn { color:var(--orange); }
        .log-err  { color:var(--red); }

        /* JOYSTICK */
        .joy-wrap { display:flex; flex-direction:column; align-items:center; gap:10px; }
        .joystick-area { width:180px; height:180px; background:var(--card2); border:2px solid var(--border2); border-radius:50%; position:relative; cursor:pointer; touch-action:none; user-select:none; }
        .joystick-area::before { content:''; position:absolute; top:50%; left:12%; right:12%; height:1px; background:rgba(255,255,255,.03); transform:translateY(-50%); }
        .joystick-area::after  { content:''; position:absolute; left:50%; top:12%; bottom:12%; width:1px; background:rgba(255,255,255,.03); transform:translateX(-50%); }
        .joystick-knob { width:64px; height:64px; background:linear-gradient(145deg,#1e40af,#3b82f6); border-radius:50%; position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); box-shadow:0 4px 20px rgba(59,130,246,.35); pointer-events:none; transition:box-shadow .1s; }
        .joystick-knob.active { box-shadow:0 4px 32px rgba(59,130,246,.7); }
        .joy-dir  { font-size:11px; font-weight:700; letter-spacing:2px; color:var(--accent2); font-family:'JetBrains Mono',monospace; }
        .stop-btn { width:54px; height:54px; border-radius:50%; background:linear-gradient(145deg,#b91c1c,#ef4444); border:none; color:white; font-weight:800; font-size:10px; cursor:pointer; letter-spacing:1px; box-shadow:0 4px 16px rgba(239,68,68,.35); transition:all .15s; }
        .stop-btn:hover  { transform:scale(1.07); box-shadow:0 4px 24px rgba(239,68,68,.6); }
        .stop-btn:active { transform:scale(.92); }
        .joy-hint { font-size:9px; color:var(--muted); letter-spacing:.5px; }

        /* ACTION BUTTONS */
        .actions { display:flex; flex-direction:column; gap:7px; }
        .btn-act { width:100%; padding:10px 14px; border:1px solid transparent; border-radius:var(--rs); cursor:pointer; font-size:12px; font-weight:600; display:flex; align-items:center; gap:10px; transition:all .15s; font-family:'Inter',sans-serif; text-align:left; }
        .btn-act:hover  { filter:brightness(1.25); transform:translateY(-1px); }
        .btn-act:active { transform:scale(.97); }
        .ba-rotate    { background:rgba(168,85,247,.1); color:#c084fc; border-color:rgba(168,85,247,.25); }
        .ba-scan      { background:rgba(249,115,22,.1); color:var(--orange); border-color:rgba(249,115,22,.25); }
        .ba-analytics { background:rgba(59,130,246,.1); color:var(--accent2); border-color:rgba(59,130,246,.25); }

        /* TOAST */
        .toast { position:fixed; bottom:20px; right:20px; z-index:9999; padding:11px 16px; border-radius:10px; font-weight:600; font-size:12px; opacity:0; transform:translateY(10px); transition:all .3s ease; pointer-events:none; display:flex; align-items:center; gap:8px; max-width:280px; }
        .toast.show { opacity:1; transform:translateY(0); }
        .toast.success { background:#0a1f12; color:var(--green);  border:1px solid rgba(34,197,94,.3); }
        .toast.info    { background:#0a1428; color:var(--accent2); border:1px solid rgba(59,130,246,.3); }
        .toast.warning { background:#1f1008; color:var(--orange); border:1px solid rgba(249,115,22,.3); }
        .toast.error   { background:#1f0808; color:var(--red);    border:1px solid rgba(239,68,68,.3); }

        ::-webkit-scrollbar { width:3px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:var(--border2); border-radius:4px; }

        @media(max-width:1000px){ .grid{ grid-template-columns:1fr; } .col-right{ order:-1; } .stats-row{ grid-template-columns:repeat(2,1fr); } }
        @media(max-width:600px) { .cam-grid{ grid-template-columns:1fr; } .metrics-grid{ grid-template-columns:repeat(2,1fr); } .pills{ display:none; } }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>

    <header class="topbar">
        <div class="brand">
            <div class="brand-icon">&#x1F916;</div>
            <div>
                <div class="brand-name">CrackBot</div>
                <div class="brand-sub">Autonomous Crack Detection System</div>
            </div>
        </div>
        <div class="pills">
            <div class="pill pill-g"><div class="pill-dot"></div> ROBOT OK</div>
            <div class="pill pill-b"><div class="pill-dot"></div> %%RGB_STATUS%%</div>
            <div class="pill pill-b"><div class="pill-dot"></div> %%THERMAL_STATUS%%</div>
        </div>
    </header>

    <div class="stats-row">
        <div class="stat">
            <div class="stat-ico ico-g">&#x1F4E1;</div>
            <div>
                <div class="stat-lbl">Distance</div>
                <div class="stat-val val-g"><span id="distance">--</span><span class="stat-unit">cm</span></div>
            </div>
        </div>
        <div class="stat">
            <div class="stat-ico ico-b">&#x1F321;&#xFE0F;</div>
            <div>
                <div class="stat-lbl">Avg Temp</div>
                <div class="stat-val val-b"><span id="statTempAvg">--</span><span class="stat-unit">&deg;C</span></div>
            </div>
        </div>
        <div class="stat">
            <div class="stat-ico ico-p">&#x1F52C;</div>
            <div>
                <div class="stat-lbl">Crack Area</div>
                <div class="stat-val val-p"><span id="statCrackArea">--</span><span class="stat-unit">cm&sup2;</span></div>
            </div>
        </div>
        <div class="stat">
            <div class="stat-ico ico-o">&#x26A1;</div>
            <div>
                <div class="stat-lbl">Temp Range</div>
                <div class="stat-val val-o"><span id="statTempRange">--</span><span class="stat-unit">&deg;C</span></div>
            </div>
        </div>
    </div>

    <div class="grid">

        <div class="col-left">

            <div class="cam-grid">
                <div class="card">
                    <div class="card-head">
                        <span>&#x1F4F7;</span>
                        <span class="card-title">RGB Camera</span>
                        <div class="card-dot dot-on"></div>
                    </div>
                    <div class="cam-wrap">%%RGB_FEED%%</div>
                </div>
                <div class="card">
                    <div class="card-head">
                        <span>&#x1F321;&#xFE0F;</span>
                        <span class="card-title">Thermal Camera</span>
                        <div class="card-dot dot-on"></div>
                    </div>
                    <div class="cam-wrap">%%THERMAL_FEED%%</div>
                </div>
            </div>

            <div id="scanMonitor" class="scan-mon">
                <div class="scan-mon-head">&#x25CF; &nbsp;LIVE SCAN MONITOR</div>
                <div class="scan-mon-body" id="scanLogLines"></div>
            </div>

            <div class="card">
                <div class="card-head"><span>&#x1F52C;</span><span class="card-title">Thermal Crack Analysis</span></div>
                <div class="card-body">
                    <div id="crackStatus" class="crack-status cs-ok">&#x25CF; &nbsp;No Anomaly Detected</div>
                    <div class="metrics-grid">
                        <div class="metric"><div class="m-lbl">Length</div><div class="m-val" id="crackLength">--</div><div class="m-unit">cm</div></div>
                        <div class="metric"><div class="m-lbl">Width</div><div class="m-val" id="crackWidth">--</div><div class="m-unit">cm</div></div>
                        <div class="metric"><div class="m-lbl">Area</div><div class="m-val" id="crackArea">--</div><div class="m-unit">cm&sup2;</div></div>
                        <div class="metric"><div class="m-lbl">Est. Depth</div><div class="m-val" id="crackDepth">--</div><div class="m-unit">cm</div></div>
                    </div>
                    <div class="temp-bar">
                        Avg: <b><span id="tempAvg">--</span></b> &deg;C &nbsp;&middot;&nbsp;
                        Min: <b><span id="tempMin">--</span></b> &deg;C &nbsp;&middot;&nbsp;
                        Max: <b><span id="tempMax">--</span></b> &deg;C &nbsp;&middot;&nbsp;
                        Range: <b><span id="tempRange">--</span></b> &deg;C &nbsp;&middot;&nbsp;
                        Pixels: <b><span id="affectedPx">--</span></b>
                    </div>
                    <div id="priorityLevel" class="priority-badge"></div>
                </div>
            </div>

            <div class="card">
                <div class="card-head"><span>&#x1F4CB;</span><span class="card-title">Trial Summary</span></div>
                <div class="card-body" style="overflow-x:auto;">
                    <table class="tbl">
                        <thead><tr><th>Trial</th><th>Location</th><th>Crack Width</th><th>Crack Length</th><th>Thermal Anomaly</th></tr></thead>
                        <tbody id="trialTableBody">
                            <tr><td colspan="5" style="text-align:center;color:var(--muted);padding:16px;">No trials saved yet.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="card">
                <div class="card-head"><span>&#x1F4CB;</span><span class="card-title">Activity Log</span></div>
                <div class="card-body">
                    <div class="log-body" id="logEntries"></div>
                </div>
            </div>

        </div>

        <div class="col-right">

            <div class="card">
                <div class="card-head"><span>&#x1F579;&#xFE0F;</span><span class="card-title">Movement</span></div>
                <div class="card-body">
                    <div class="joy-wrap">
                        <div class="joystick-area" id="joystick">
                            <div class="joystick-knob" id="joystickKnob"></div>
                        </div>
                        <div class="joy-dir" id="joystickDir">-- IDLE --</div>
                        <button class="stop-btn" onclick="stop()">STOP</button>
                        <div class="joy-hint">Drag joystick &middot; WASD &middot; Arrow keys</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-head"><span>&#x26A1;</span><span class="card-title">Actions</span></div>
                <div class="card-body">
                    <div class="actions">
                        <button class="btn-act ba-rotate" onclick="rotate360()">&#x1F504; Rotate 360&deg;</button>
                        <button class="btn-act ba-scan" onclick="startScan()">&#x1F916; Start Auto Scan</button>
                        <button class="btn-act ba-analytics" onclick="openAnalytics()">&#x1F4CA; View Analytics</button>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <script>
        var logCount = 0;

        function showToast(msg, type, ms) {
            var t = document.getElementById('toast');
            t.innerHTML = msg;
            t.className = 'toast ' + (type||'info');
            t.classList.add('show');
            setTimeout(function(){ t.classList.remove('show'); }, ms||5000);
        }

        function log(msg) {
            var d = document.getElementById('logEntries');
            var time = new Date().toLocaleTimeString();
            var el = document.createElement('div');
            el.className = 'log-entry';
            var cls = msg.indexOf('[ERROR]')>=0||msg.indexOf('[WARN]')>=0 ? 'log-warn' : msg.indexOf('[OK]')>=0 ? 'log-ok' : '';
            el.innerHTML = '<span class="log-time">'+time+'</span><span class="'+cls+'">'+msg+'</span>';
            d.insertBefore(el, d.firstChild);
            if (++logCount > 25) { d.removeChild(d.lastChild); logCount--; }
        }

        function send(cmd, desc) {
            var jCmds = ['Forward','Backward','Turn Left','Turn Right','Stop','STOP','hold'];
            var isRep = jCmds.indexOf(desc) >= 0;
            if (!isRep) log(desc);
            fetch('/command', { method:'POST', headers:{"Content-Type":"application/json"}, body:JSON.stringify({command:cmd}) })
            .then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
            .then(function(d){ if(d.status==='error'&&!isRep) log('[ERROR] '+d.response); })
            .catch(function(e){ if(!isRep) log('[ERROR] '+e.message); });
        }

        var turnRightMs=2600, turnLeftMs=2600, turn360Durations=[2600,2630,2600,2600], turnCalibrated=false;
        fetch('/turn_config').then(function(r){return r.json();}).then(function(c){
            turnRightMs=c.right_90_ms; turnLeftMs=c.left_90_ms;
            turn360Durations=c.turn_durations_360; turnCalibrated=c.calibrated;
            log('[OK] Turn config loaded -- R:'+turnRightMs+'ms  L:'+turnLeftMs+'ms'+(turnCalibrated?'':' (default)'));
        }).catch(function(){ log('Using default turn durations'); });

        function stop() {
            send('S','STOP');
            fetch('/scan_status').then(function(r){return r.json();}).then(function(d){
                if(d.running){
                    fetch('/stop_scan',{method:'POST'}).then(function(r){return r.json();}).then(function(res){
                        log('[WARN] Scan killed: '+res.message);
                        showToast('Scan stopped!','warning',4000);
                        document.getElementById('scanMonitor').style.display='none';
                    }).catch(function(){});
                }
            }).catch(function(){});
        }

        (function(){
            var area=document.getElementById('joystick');
            var knob=document.getElementById('joystickKnob');
            var dirEl=document.getElementById('joystickDir');
            var active=false, curDir=null, dead=25, repeatTimer=null;
            function getCenter(){ var r=area.getBoundingClientRect(); return {cx:r.left+r.width/2,cy:r.top+r.height/2,r:r.width/2}; }
            function getDir(x,y,dist){ if(dist<dead)return null; return Math.abs(y)>=Math.abs(x)?(y<0?'F':'B'):(x<0?'L':'R'); }
            function sendDir(dir){ var cmds={F:'F,70,0',B:'B,70,0',L:'L,150,0',R:'R,150,0'}; var lbls={F:'Forward',B:'Backward',L:'Turn Left',R:'Turn Right'}; send(cmds[dir],lbls[dir]); }
            var labels={F:'&#x25B2; FORWARD',B:'&#x25BC; BACKWARD',L:'&#x25C4; TURN LEFT',R:'TURN RIGHT &#x25BA;'};
            function startRepeat(dir){ if(repeatTimer)clearInterval(repeatTimer); sendDir(dir); repeatTimer=setInterval(function(){if(curDir)sendDir(curDir);},800); }
            function stopRepeat(){ if(repeatTimer){clearInterval(repeatTimer);repeatTimer=null;} }
            function onMove(e){
                e.preventDefault();
                var c=getCenter();
                var cx=e.touches?e.touches[0].clientX:e.clientX;
                var cy=e.touches?e.touches[0].clientY:e.clientY;
                var dx=cx-c.cx, dy=cy-c.cy;
                var dist=Math.sqrt(dx*dx+dy*dy);
                var maxR=c.r-38; var clamp=Math.min(dist,maxR);
                var angle=Math.atan2(dy,dx);
                knob.style.left=(50+Math.cos(angle)*clamp/c.r*50)+'%';
                knob.style.top=(50+Math.sin(angle)*clamp/c.r*50)+'%';
                var dir=getDir(dx,dy,dist);
                if(dir!==curDir){ curDir=dir;
                    if(dir){ knob.classList.add('active'); dirEl.innerHTML=labels[dir]; startRepeat(dir); }
                    else   { knob.classList.remove('active'); dirEl.textContent='-- IDLE --'; stopRepeat(); send('S','Stop'); }
                }
            }
            function onRelease(){ if(!active)return; active=false; curDir=null; knob.style.left='50%'; knob.style.top='50%'; knob.classList.remove('active'); dirEl.textContent='-- IDLE --'; stopRepeat(); send('S','Stop'); }
            area.addEventListener('mousedown',  function(e){active=true;onMove(e);});
            area.addEventListener('touchstart', function(e){active=true;onMove(e);},{passive:false});
            area.addEventListener('mousemove',  function(e){if(active)onMove(e);});
            area.addEventListener('touchmove',  function(e){if(active)onMove(e);},{passive:false});
            document.addEventListener('mouseup',  onRelease);
            document.addEventListener('touchend', onRelease);
        })();

        var keyHeld={};
        var keyDirs={'ArrowUp':'F','w':'F','W':'F','ArrowDown':'B','s':'B','S':'B','ArrowLeft':'L','a':'L','A':'L','ArrowRight':'R','d':'R','D':'R'};
        var keyCmds={F:'F,70,0',B:'B,70,0',L:'L,150,0',R:'R,150,0'};
        document.addEventListener('keydown',function(e){ if(e.key===' '){send('S','Stop');return;} var dir=keyDirs[e.key]; if(!dir||keyHeld[e.key])return; keyHeld[e.key]=true; send(keyCmds[dir],e.key); });
        document.addEventListener('keyup',  function(e){ delete keyHeld[e.key]; if(Object.keys(keyHeld).length===0)send('S','Stop'); });

        function rotate360(){
            if(!confirm('Perform 360 degree rotation?'))return;
            log('Starting 360 rotation (4x90 turns)...');
            var n=0;
            function next(){ if(n>=turn360Durations.length){log('[OK] 360 rotation complete!');return;} var dur=turn360Durations[n]; log('Turn '+(n+1)+'/4 ('+dur+'ms)...'); send('R,150,'+dur,'Turn '+(n+1)+'/4'); n++; setTimeout(next,dur+2000); }
            next();
        }

        function startScan(){
            var skipWall=confirm('WALL DETECTION: OK = already facing wall, CANCEL = do 360 search first.');
            var width=parseInt(prompt('Scan width cm (default 90):','90')||'90');
            var height=parseInt(prompt('Scan height cm (default 60):','60')||'60');
            var step=parseInt(prompt('Step size cm (default 30):','30')||'30');
            var cols=Math.floor(width/step)+1, rows=Math.floor(height/step)+1;
            if(!confirm('Grid scan: '+cols+' cols x '+rows+' rows = '+(cols*rows)+' positions. Continue?'))return;
            log('[SCAN] Starting autonomous scan...');
            document.getElementById('scanMonitor').style.display='block';
            document.getElementById('scanLogLines').innerHTML='<div style="color:var(--orange)">Starting scan...</div>';
            showToast('Autonomous scan started!','info',4000);
            fetch('/start_scan',{method:'POST',headers:{"Content-Type":"application/json"},body:JSON.stringify({scan_mode:2,width_cm:width,height_cm:height,step_cm:step,skip_find_wall:skipWall})})
            .then(function(r){return r.json();})
            .then(function(data){
                log('[OK] '+data.message);
                var lastCount=0;
                var poller=setInterval(function(){
                    fetch('/scan_log').then(function(r){return r.json();}).then(function(d){
                        if(d.lines&&d.lines.length>lastCount){
                            var ld=document.getElementById('scanLogLines');
                            for(var i=lastCount;i<d.lines.length;i++){
                                var line=d.lines[i].trim(); if(!line)continue;
                                var el=document.createElement('div');
                                el.style.color=line.indexOf('CRACK DETECTED')>=0?'var(--red)':line.indexOf('No crack')>=0?'var(--green)':line.indexOf('SCANNING POSITION')>=0?'var(--accent2)':'var(--muted2)';
                                el.textContent=line; ld.appendChild(el); ld.scrollTop=ld.scrollHeight;
                                if(line.indexOf('SCAN COMPLETE')>=0||line.indexOf('AUTONOMOUS SCAN COMPLETE')>=0){showToast('Scan complete!','success',8000);log('[OK] Scan finished!');}
                                if(line.indexOf('CRACK DETECTED')>=0) showToast('CRACK DETECTED!','warning',6000);
                            }
                            lastCount=d.lines.length;
                        }
                    }).catch(function(){ clearInterval(poller); log('[OK] Scan complete!'); showToast('Scan complete!','success',10000); });
                },2000);
            })
            .catch(function(){ log('[WARN] Dashboard restarting -- refresh in ~30s'); var poll=setInterval(function(){fetch('/status').then(function(){clearInterval(poll);location.reload();}).catch(function(){});},3000); });
        }

        function openAnalytics(){ window.open('http://'+window.location.hostname+':8080','_blank'); }

        setInterval(function(){ fetch('/distance').then(function(r){return r.json();}).then(function(d){ document.getElementById('distance').textContent=d.distance||'--'; }).catch(function(){}); },2000);

        setInterval(function(){
            fetch('/crack_analysis').then(function(r){return r.json();}).then(function(d){
                document.getElementById('tempAvg').textContent    = d.avg_temp   !==undefined?d.avg_temp:'--';
                document.getElementById('tempMin').textContent    = d.min_temp   !==undefined?d.min_temp:'--';
                document.getElementById('tempMax').textContent    = d.max_temp   !==undefined?d.max_temp:'--';
                document.getElementById('tempRange').textContent  = d.temp_range !==undefined?d.temp_range:'--';
                document.getElementById('affectedPx').textContent = d.affected_pixels!==undefined?d.affected_pixels:'--';
                document.getElementById('statTempAvg').textContent   = d.avg_temp   !==undefined?d.avg_temp:'--';
                document.getElementById('statTempRange').textContent = d.temp_range !==undefined?d.temp_range:'--';

                var st=document.getElementById('crackStatus');
                var tag=d.surface_type?' <small style="opacity:.6;font-size:9px">['+d.surface_type+(d.wall_confidence!==undefined?' '+d.wall_confidence+'%':'')+']</small>':'';

                if(!d.is_wall&&d.surface_type==='PERSON'){
                    st.className='crack-status cs-warn'; st.innerHTML='&#x25CF; &nbsp;PERSON DETECTED'+tag;
                    ['crackLength','crackWidth','crackArea','crackDepth','statCrackArea'].forEach(function(id){document.getElementById(id).textContent='--';});
                } else if(!d.is_wall&&d.surface_type==='OBJECT'){
                    st.className='crack-status cs-warn'; st.innerHTML='&#x25CF; &nbsp;OBSTACLE DETECTED'+tag;
                    ['crackLength','crackWidth','crackArea','crackDepth','statCrackArea'].forEach(function(id){document.getElementById(id).textContent='--';});
                } else if(!d.is_wall&&d.surface_type){
                    st.className='crack-status cs-warn'; st.innerHTML='&#x25CF; &nbsp;NOT A WALL'+tag;
                    ['crackLength','crackWidth','crackArea','crackDepth','statCrackArea'].forEach(function(id){document.getElementById(id).textContent='--';});
                } else if(d.anomaly){
                    st.className='crack-status cs-bad'; st.innerHTML='&#x25CF; &nbsp;CRACK DETECTED'+tag+(d.anomaly_type?' ['+d.anomaly_type+']':'');
                    document.getElementById('crackLength').textContent=d.length_cm;
                    document.getElementById('crackWidth').textContent=d.width_cm;
                    document.getElementById('crackArea').textContent=d.area_cm2;
                    document.getElementById('crackDepth').textContent=d.depth_cm;
                    document.getElementById('statCrackArea').textContent=d.area_cm2||'--';
                    var wm=d.width_cm*10, lc=d.length_cm, pri='', pc='', pb='';
                    if(wm>2.0||lc>20){pri='HIGH PRIORITY';pc='var(--red)';pb='rgba(239,68,68,.1)';}
                    else if(wm>=1.0||lc>=10){pri='MODERATE PRIORITY';pc='var(--orange)';pb='rgba(249,115,22,.1)';}
                    else{pri='LOW PRIORITY';pc='var(--green)';pb='rgba(34,197,94,.1)';}
                    var pl=document.getElementById('priorityLevel');
                    pl.style.display='block'; pl.style.color=pc; pl.style.background=pb; pl.style.border='1px solid '+pc;
                    pl.innerHTML='PRIORITY: '+pri+'<br><small style="font-weight:400;opacity:.75">Width: '+wm.toFixed(1)+'mm &middot; Length: '+lc+'cm</small>';
                } else {
                    st.className='crack-status cs-ok'; st.innerHTML='&#x25CF; &nbsp;WALL - No Crack'+tag;
                    ['crackLength','crackWidth','crackArea','crackDepth','statCrackArea'].forEach(function(id){document.getElementById(id).textContent='--';});
                    document.getElementById('priorityLevel').style.display='none';
                }
            }).catch(function(){});
        },2000);

        setInterval(function(){ fetch('/status').then(function(r){return r.json();}).then(function(d){ if(d.robot==='disconnected')log('[WARN] Robot connection lost'); }).catch(function(){}); },5000);

        function loadTrialTable(){
            fetch('http://'+window.location.hostname+':8080/api/scans')
            .then(function(r){return r.json();})
            .then(function(scans){
                if(!scans||scans.length===0)return;
                var tbody=document.getElementById('trialTableBody');
                tbody.innerHTML='';
                scans.forEach(function(scan){
                    var tr=document.createElement('tr');
                    var th=scan.thermal_anomaly?'<span style="color:var(--red);font-weight:600">Detected</span>':'<span style="color:var(--green)">Not Detected</span>';
                    tr.innerHTML='<td style="padding:7px 10px;border:1px solid var(--border);">Trial '+(scan.trial_number||scan.day_number)+'</td>'+
                        '<td style="padding:7px 10px;border:1px solid var(--border);">'+(scan.location||'--')+'</td>'+
                        '<td style="padding:7px 10px;border:1px solid var(--border);text-align:center;">'+(scan.crack_width_cm?scan.crack_width_cm+' cm':'--')+'</td>'+
                        '<td style="padding:7px 10px;border:1px solid var(--border);text-align:center;">'+(scan.crack_length_cm?scan.crack_length_cm+' cm':'--')+'</td>'+
                        '<td style="padding:7px 10px;border:1px solid var(--border);text-align:center;">'+th+'</td>';
                    tbody.appendChild(tr);
                });
            }).catch(function(){});
        }
        loadTrialTable();
        setInterval(loadTrialTable, 30000);

        log('[OK] Dashboard ready!');
    </script>
</body>
</html>
"""


@app.route('/scan_log')
def scan_log():
    """Return last 30 lines of scan log for display in dashboard"""
    log_path = _os.path.expanduser('~/scan_output.log')
    try:
        if _os.path.exists(log_path):
            with open(log_path, 'r') as f:
                lines = f.readlines()
            return jsonify({'lines': lines[-30:], 'running': True})
        return jsonify({'lines': [], 'running': False})
    except:
        return jsonify({'lines': [], 'running': False})


@app.route('/scan_status')
def scan_status():
    """Check if autonomous scan is still running"""
    import subprocess as sp
    try:
        result = sp.run(['pgrep', '-f', 'fully_autonomous_wall_scanner.py'],
                       capture_output=True, text=True)
        running = bool(result.stdout.strip())
        return jsonify({'running': running})
    except:
        return jsonify({'running': False})


@app.route('/scan_done', methods=['POST'])
def scan_done():
    """Reconnect robot serial after autonomous scan finishes"""
    if connect_robot():
        return jsonify({'message': 'Robot reconnected! Web controls restored.'})
    return jsonify({'message': 'Reconnect failed -- check MegaPi'}), 500


@app.route('/stop_scan', methods=['POST'])
def stop_scan():
    """Kill the autonomous scan process and reconnect serial"""
    import subprocess as _sp
    try:
        _sp.run(['pkill', '-9', '-f', 'fully_autonomous_wall_scanner.py'],
                capture_output=True)
        time.sleep(1)
        connect_robot()
        return jsonify({'message': 'Scan stopped. Robot reconnected.'})
    except Exception as e:
        return jsonify({'message': f'Stop error: {e}'}), 500


@app.route('/turn_config')
def turn_config():
    """Return calibrated turn durations for use in the web dashboard JS"""
    return jsonify({
        'right_90_ms':        TURN_RIGHT_90_MS,
        'left_90_ms':         TURN_LEFT_90_MS,
        'turn_durations_360': TURN_DURATIONS_360,
        'calibrated':         bool(_wheel_cal),
    })


@app.route('/crack_analysis')
def crack_analysis():
    """Return latest thermal crack analysis as JSON"""
    with crack_analysis_lock:
        data = dict(latest_crack_analysis)
    return jsonify(data)


@app.route('/')
def index():
    rgb_status     = 'RGB CAM ON' if (CAMERA_AVAILABLE and camera is not None) else 'NO RGB'
    thermal_status = 'THERMAL ON' if (THERMAL_AVAILABLE and thermal is not None) else 'NO THERMAL'

    rgb_feed_img = (
        '<img class="camera-view" src="/rgb_feed" alt="RGB Camera">'
        if (CAMERA_AVAILABLE and camera is not None)
        else '<div class="no-cam">Camera Not Available</div>'
    )
    thermal_feed_img = (
        '<img class="camera-view" src="/thermal_feed" alt="Thermal Camera">'
        if (THERMAL_AVAILABLE and thermal is not None)
        else '<div class="no-cam">Thermal Not Available</div>'
    )

    html = (HTML_TEMPLATE
            .replace('%%RGB_STATUS%%',     rgb_status)
            .replace('%%THERMAL_STATUS%%', thermal_status)
            .replace('%%RGB_FEED%%',       rgb_feed_img)
            .replace('%%THERMAL_FEED%%',   thermal_feed_img))
    from flask import make_response
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route('/rgb_feed')
def rgb_feed():
    if not camera:
        return "Camera not available", 404
    return Response(generate_rgb_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/thermal_feed')
def thermal_feed():
    if not thermal:
        return "Thermal camera not available", 404
    return Response(generate_thermal_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def get_status():
    """Get robot connection status"""
    try:
        robot_status = 'disconnected'
        if robot_serial:
            try:
                if robot_serial.is_open:
                    robot_status = 'connected'
            except:
                robot_status = 'disconnected'
        return jsonify({
            'robot':   robot_status,
            'camera':  'ok' if camera else 'unavailable',
            'thermal': 'ok' if thermal else 'unavailable'
        })
    except Exception as e:
        print(f"[STATUS] Error: {e}")
        return jsonify({'robot': 'error', 'camera': 'error', 'thermal': 'error'})

@app.route('/command', methods=['POST'])
def command():
    """Handle robot commands with detailed response and auto-reconnect"""
    global robot_serial
    try:
        cmd = request.json.get('command', '')
        if not cmd:
            return jsonify({'status': 'error', 'response': 'No command provided'}), 400
        print(f"[WEB] Received command: {cmd}")
        if not robot_serial or not robot_serial.is_open:
            print("[WEB] Robot disconnected, attempting reconnect...")
            if connect_robot():
                print("[WEB] Reconnected successfully!")
            else:
                return jsonify({'status': 'error', 'response': 'Robot disconnected. Reconnect failed.'}), 500
        response = send_command(cmd)
        print(f"[WEB] Response: {response}")
        status = 'error' if 'ERROR' in response else 'success'
        return jsonify({'status': status, 'response': response})
    except serial.SerialException as e:
        print(f"[WEB] Serial exception: {e}")
        robot_serial = None
        return jsonify({'status': 'error', 'response': f'Serial error: {e}'}), 500
    except Exception as e:
        print(f"[WEB] Exception: {e}")
        return jsonify({'status': 'error', 'response': str(e)}), 500

@app.route('/distance')
def get_distance():
    """Get distance with thread safety"""
    try:
        distance = get_distance_value()
        return jsonify({'distance': distance})
    except Exception as e:
        print(f"[DISTANCE] Error: {e}")
        return jsonify({'distance': None})

@app.route('/start_scan', methods=['POST'])
@app.route('/start_scan', methods=['POST'])
def start_scan():
    """Start autonomous scan in background thread"""
    global robot_serial
    try:
        data           = request.get_json(silent=True) or {}
        scan_mode      = int(data.get('scan_mode', 2))
        width_cm       = int(data.get('width_cm',  150))
        height_cm      = int(data.get('height_cm', 100))
        step_cm        = int(data.get('step_cm',   30))
        skip_find_wall = bool(data.get('skip_find_wall', False))

        with serial_lock:
            if robot_serial and robot_serial.is_open:
                try:
                    robot_serial.close()
                except:
                    pass
                robot_serial = None

        def run_scan_bg():
            log_path = _os.path.expanduser('~/scan_output.log')
            with open(log_path, 'w') as lf:
                lf.write('=== SCAN STARTED ===\n')
            with open(log_path, 'a') as lf:
                cmd = [
                    'python3', '/home/pi/fully_autonomous_wall_scanner.py',
                    '--mode',   str(scan_mode),
                    '--width',  str(width_cm),
                    '--height', str(height_cm),
                    '--step',   str(step_cm),
                ]
                if skip_find_wall:
                    cmd.append('--skip-find-wall')
                subprocess.run(cmd, stdout=lf, stderr=lf)
            with open(log_path, 'a') as lf:
                lf.write('\n=== SCAN COMPLETE ===\n')
            connect_robot()

        threading.Thread(target=run_scan_bg, daemon=True).start()
        return jsonify({'message': 'Scan started! Watch progress in the monitor below.'})
    except Exception as e:
        return jsonify({'message': f'Error: {e}'}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("ROBOT REMOTE CONTROL DASHBOARD")
    print("="*60)

    print("\n[1/4] Connecting to MegaPi...")
    if connect_robot():
        print("      Robot connected!")
    else:
        print("      Robot not connected")

    print("\n[2/4] Initializing RGB camera...")
    if CAMERA_AVAILABLE:
        if init_camera():
            print("      RGB camera initialized!")
        else:
            print("      RGB camera failed")
    else:
        print("      RGB camera not available")

    print("\n[3/4] Initializing thermal camera...")
    if THERMAL_AVAILABLE:
        if init_thermal():
            print("      Thermal camera initialized!")
        else:
            print("      Thermal camera failed")
    else:
        print("      Thermal camera not available")

    print("\n[4/4] Starting web server...")
    _dist_thread = threading.Thread(target=_distance_updater, daemon=True)
    _dist_thread.start()
    try:
        ip = subprocess.check_output(['hostname', '-I']).decode().strip().split()[0]
        print(f"\n{'='*60}")
        print(f"ACCESS FROM ANY DEVICE:")
        print(f"   http://{ip}:5000")
        print(f"{'='*60}\n")
    except:
        print("\nAccess at: http://raspberrypi.local:5000\n")

    print("Press Ctrl+C to stop\n")

    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\nServer stopped")
