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
    from picamera2 import Picamera2
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
# All 4 turns use the same duration -- simpler and more consistent
TURN_DURATIONS_360 = _wheel_cal.get('turn_durations_360',
                                    [TURN_RIGHT_90_MS] * 4)

# ========================================
# ROBOT CONNECTION
# ========================================

robot_serial = None
serial_lock = threading.Lock()  # Prevent concurrent access

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
    
    with serial_lock:  # Prevent concurrent serial access
        if robot_serial:
            try:
                # Clear any pending data
                if robot_serial.in_waiting:
                    robot_serial.reset_input_buffer()
                
                # Send command
                robot_serial.write(f"{cmd}\n".encode())
                time.sleep(COMMAND_DELAY)
                
                # Wait for response (with timeout)
                start_time = time.time()
                while time.time() - start_time < 1.0:  # 1 second timeout
                    if robot_serial.in_waiting:
                        response = robot_serial.readline().decode().strip()
                        return response if response else "OK"
                    time.sleep(0.01)
                
                return "OK"  # No response but command sent
            except serial.SerialException as e:
                print(f"Serial error: {e}")
                robot_serial = None  # Mark for reconnection
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
        camera = Picamera2()
        # Use video configuration for better FPS (faster than still/preview)
        config = camera.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"},
            controls={"FrameRate": 30}   # target 30fps
        )
        camera.configure(config)
        camera.start()
        time.sleep(1)
        return True
    except:
        return False

def init_thermal():
    global thermal
    if not THERMAL_AVAILABLE:
        return False
    try:
        i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
        thermal = adafruit_mlx90640.MLX90640(i2c)
        # Bump to 4Hz for smoother thermal feed
        thermal.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
        time.sleep(1)
        return True
    except:
        return False

# Cache distance separately so frame loop doesn't block on serial every frame
_cached_distance = None

def get_camera_frame():
    global current_rgb_frame, camera
    if not camera:
        return None
    try:
        frame = camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Use cached distance -- updated by background thread, not per-frame serial call
        if _cached_distance:
            cv2.putText(frame, f"Dist: {_cached_distance} cm", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Higher JPEG quality for clearer image
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if ret:
            with frame_lock:
                current_rgb_frame = buffer.tobytes()
            return current_rgb_frame
    except Exception as e:
        print(f"[CAMERA] Error: {e}")
        try:
            camera.stop()
        except:
            pass
        camera = None
    return None

# -- Load calibration file if it exists ----------------------

_CAL_FILE = _os.path.expanduser("~/thermal_calibration.json")
_calibration = {}
if _os.path.exists(_CAL_FILE):
    try:
        with open(_CAL_FILE) as _f:
            _calibration = _json.load(_f)
        print(f"[THERMAL] Calibration loaded from {_CAL_FILE}")
        _thr = _calibration.get('thresholds', {})
        _cd  = _calibration.get('crack_detection', {})
        print(f"  Wall thresholds: std<={_thr.get('std_temp','?')}  "
              f"range<={_thr.get('temp_range','?')}  "
              f"grad<={_thr.get('gradient','?')}")
        print(f"  Crack threshold: temp_diff>{_cd.get('temp_diff_threshold','?')} degC")
    except Exception as _e:
        print(f"[THERMAL] Could not load calibration: {_e} -- using defaults")
        _calibration = {}
else:
    print("[THERMAL] No calibration file found -- using default thresholds")
    print(f"          Run  python3 ~/thermal_wall_calibration.py  to calibrate")


def classify_surface_type(temps):
    """
    Surface classification using thermal pattern.
    
    In hot climates (PH ~30-35degC room temp), walls and objects have similar temps.
    Only reliable detection: PERSON (body heat 35-38degC distinct pattern).
    Everything else = treat as WALL (crack detection proceeds).
    """
    valid = (temps > 5.0) & (temps < 80.0)
    if np.sum(valid) < 100:
        return 'WALL', 80

    clean     = temps[valid]
    avg       = float(clean.mean())

    # PERSON: >20% of pixels at human body temperature (35-38.5degC)
    # This is reliable even in hot weather since body is ~3-4degC above room temp
    body_pixels = np.sum((temps >= 34.5) & (temps <= 39.0))
    body_pct    = body_pixels / temps.size * 100

    if body_pct > 20:
        return 'PERSON', min(100, int(body_pct * 3))

    # Everything else = WALL (concrete, hollow block, wood, cardboard all similar temp)
    # Ultrasonic handles actual obstacle avoidance, not thermal
    return 'WALL', 90


# Global to hold latest crack analysis result (updated by thermal thread)
latest_crack_analysis = {}
crack_analysis_lock   = threading.Lock()
_last_nonzero = {}  # last frame that had real measurements

def analyze_thermal_for_cracks(temps):
    """
    Analyze thermal frame for crack size measurements.
    Uses calibrated thresholds if ~/thermal_calibration.json exists.
    Returns dict with:
      - is_wall / wall_confidence / wall_details
      - anomaly / length_cm / width_cm / area_cm2 / depth_cm
    """
    PIXEL_CM_H = 0.98
    PIXEL_CM_V = 0.81

    # Use calibrated crack threshold if available, else default 3.0 degC
    if _calibration:
        TEMP_DIFF_THRESHOLD = _calibration.get(
            'crack_detection', {}).get('temp_diff_threshold', 3.0)
        ANOMALY_SIGMA = _calibration.get(
            'crack_detection', {}).get('anomaly_sigma', 2.0)
    else:
        TEMP_DIFF_THRESHOLD = 0.8   # Very sensitive -- catch even tiny voids in hollow blocks
        ANOMALY_SIGMA = 0.8         # Lower: catch the broad cold column visible in thermal

    # Filter bad pixels first (0degC or >80degC = sensor I2C glitch)
    valid = (temps > 5.0) & (temps < 80.0)
    valid_count = np.sum(valid)

    # If more than 20% of pixels are bad -- entire frame is corrupted, skip it
    if valid_count < int(temps.size * 0.8):
        return None  # Signal caller to skip this frame

    clean      = temps[valid] if valid_count < temps.size else temps
    avg_temp   = float(clean.mean())
    std_temp   = float(clean.std())
    temp_min   = float(clean.min())
    temp_max   = float(clean.max())
    temp_range = temp_max - temp_min

    # Smart surface classification -- identifies WALL vs PERSON vs OBJECT
    surface_type, surface_conf = classify_surface_type(temps)
    wall_flag   = (surface_type == 'WALL')
    wall_conf   = surface_conf
    wall_details = {}

    result = {
        'is_wall':         wall_flag,
        'wall_confidence': wall_conf,
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
        'wall_details':    wall_details,
    }

    # Only run crack detection on a confirmed real wall
    if not wall_flag:
        result['anomaly_type'] = 'not_a_wall'
        return result

    # Flag anomaly only if range exceeds calibrated threshold
    if temp_range <= TEMP_DIFF_THRESHOLD:
        return result

    result['anomaly'] = True

    # Build anomaly mask using CLEAN temps (filtered bad pixels)
    # Replace bad pixels (0degC) with avg_temp so they don't appear as fake cold spots
    clean_temps = np.where((temps > 5.0) & (temps < 80.0), temps, avg_temp)
    cold_mask    = clean_temps < (avg_temp - ANOMALY_SIGMA * std_temp)
    hot_mask     = clean_temps > (avg_temp + ANOMALY_SIGMA * std_temp)
    anomaly_mask = cold_mask | hot_mask

    # Require at least 2 connected anomaly pixels to avoid single bad pixels
    if not np.any(anomaly_mask):
        # Retry with half sigma if nothing found
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

    num_px   = int(np.sum(anomaly_mask))
    area_cm2 = round(num_px * PIXEL_CM_H * PIXEL_CM_V, 1)

    # Depth estimate from max deviation
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
        # Capture thermal frame (24x32 pixels)
        frame = [0] * 768
        thermal.getFrame(frame)
        temps = np.array(frame).reshape(24, 32)

        # Run crack analysis -- skip bad frames, keep last good result
        analysis = analyze_thermal_for_cracks(temps)
        if analysis is None:
            with crack_analysis_lock:
                pass  # keep last good analysis
        else:
            with crack_analysis_lock:
                # If current frame has measurements, store as last non-zero
                if analysis.get('length_cm', 0) > 0:
                    _last_nonzero.update(analysis)

                # If anomaly detected but measurements are 0, use last known measurements
                if (analysis.get('anomaly') and
                        analysis.get('length_cm', 0) == 0 and
                        _last_nonzero.get('length_cm', 0) > 0):
                    analysis['length_cm']       = _last_nonzero['length_cm']
                    analysis['width_cm']        = _last_nonzero['width_cm']
                    analysis['area_cm2']        = _last_nonzero['area_cm2']
                    analysis['depth_cm']        = _last_nonzero['depth_cm']
                    analysis['affected_pixels'] = _last_nonzero.get('affected_pixels', 0)

                latest_crack_analysis = analysis

        # Skip bad frames for display too (checkerboard = I2C glitch)
        valid_ratio = np.sum((temps > 5.0) & (temps < 80.0)) / temps.size
        if valid_ratio < 0.8:
            # Return last good frame if available
            with frame_lock:
                return current_thermal_frame if current_thermal_frame else None

        # Use cleaned temps for display
        temp_min = float(temps[temps > 5.0].min()) if np.any(temps > 5.0) else float(temps.min())
        temp_max = float(temps.max())
        if temp_max > temp_min:
            normalized = ((temps - temp_min) / (temp_max - temp_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros((24, 32), dtype=np.uint8)

        # Apply colormap (TURBO for heat visualization)
        colored = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)

        # Resize to 480x360 for sharper display (was 320x240)
        resized = cv2.resize(colored, (480, 360), interpolation=cv2.INTER_NEAREST)

        # Temperature labels
        cv2.putText(resized, f"Max: {temp_max:.1f}C", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(resized, f"Min: {temp_min:.1f}C", (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(resized, f"Avg: {temps.mean():.1f}C", (10, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Crack size overlay if anomaly detected
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

        # Encode as JPEG
        ret, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret:
            with frame_lock:
                current_thermal_frame = buffer.tobytes()
            return current_thermal_frame
    except Exception as e:
        print(f"[THERMAL] Error: {e}")
    return None

def generate_rgb_frames():
    while True:
        frame = get_camera_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.033)  # ~30fps cap

def generate_thermal_frames():
    while True:
        frame = get_thermal_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.25)  # 4Hz thermal sensor

def _distance_updater():
    """Background thread: update cached distance every 1.5s so camera loop stays fast"""
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
    <title>CrackBot -- Control Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg:       #0d1117;
            --surface:  #161b22;
            --surface2: #21262d;
            --border:   #30363d;
            --accent:   #58a6ff;
            --accent2:  #bc8cff;
            --green:    #3fb950;
            --red:      #f85149;
            --yellow:   #d29922;
            --orange:   #e3b341;
            --text:     #e6edf3;
            --muted:    #8b949e;
            --radius:   12px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 16px;
        }
        .layout {
            max-width: 1280px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 340px;
            grid-template-rows: auto auto 1fr auto;
            gap: 14px;
        }

        /* -- HEADER ------------------------------------- */
        .header {
            grid-column: 1 / -1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 14px 20px;
        }
        .header-brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header-brand .logo {
            width: 38px; height: 38px;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 20px;
        }
        .header-brand h1 {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, var(--accent), var(--accent2));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .header-brand p {
            font-size: 11px;
            color: var(--muted);
            margin-top: 1px;
            font-family: 'JetBrains Mono', monospace;
        }
        .header-pills {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .pill {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: 0.3px;
        }
        .pill-dot { width: 7px; height: 7px; border-radius: 50%; }
        .pill-green  { color: var(--green);  border-color: rgba(63,185,80,.35);  background: rgba(63,185,80,.08); }
        .pill-blue   { color: var(--accent); border-color: rgba(88,166,255,.35); background: rgba(88,166,255,.08); }
        .pill-red    { color: var(--red);    border-color: rgba(248,81,73,.35);  background: rgba(248,81,73,.08); }
        .pill-green  .pill-dot { background: var(--green); }
        .pill-blue   .pill-dot { background: var(--accent); }
        .pill-red    .pill-dot { background: var(--red); }

        /* -- STATUS BAR --------------------------------- */
        .status-bar {
            grid-column: 1 / -1;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
        }
        .stat-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 14px 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .stat-icon {
            width: 40px; height: 40px;
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
        }
        .stat-icon-green  { background: rgba(63,185,80,.15); }
        .stat-icon-blue   { background: rgba(88,166,255,.15); }
        .stat-icon-purple { background: rgba(188,140,255,.15); }
        .stat-icon-orange { background: rgba(227,179,65,.15); }
        .stat-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
        .stat-value { font-size: 20px; font-weight: 700; margin-top: 1px; font-family: 'JetBrains Mono', monospace; }
        .stat-value.green  { color: var(--green); }
        .stat-value.blue   { color: var(--accent); }
        .stat-value.purple { color: var(--accent2); }
        .stat-value.orange { color: var(--orange); }

        /* -- CAMERA GRID -------------------------------- */
        .cameras {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .cam-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }
        .cam-header {
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .cam-badge {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--muted);
        }
        .cam-indicator {
            width: 7px; height: 7px;
            border-radius: 50%;
            margin-left: auto;
        }
        .cam-indicator.on  { background: var(--green); box-shadow: 0 0 6px var(--green); animation: pulse-green 2s infinite; }
        .cam-indicator.off { background: var(--red); }
        @keyframes pulse-green { 0%,100% { opacity:1; } 50% { opacity:.4; } }
        .cam-body { position: relative; }
        .camera-view {
            width: 100%;
            display: block;
            background: #000;
            min-height: 180px;
        }
        .no-camera {
            min-height: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 8px;
            color: var(--muted);
            font-size: 13px;
            background: var(--surface2);
        }
        .no-camera span { font-size: 28px; }

        /* -- CRACK ANALYSIS ----------------------------- */
        .crack-panel {
            grid-column: 1;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
        }
        .panel-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 14px;
        }
        .panel-title {
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text);
        }
        .crack-status-line {
            font-size: 13px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            padding: 8px 12px;
            border-radius: 8px;
            margin-bottom: 12px;
        }
        .crack-status-ok   { background: rgba(63,185,80,.1);  color: var(--green); border: 1px solid rgba(63,185,80,.25); }
        .crack-status-bad  { background: rgba(248,81,73,.1);  color: var(--red);   border: 1px solid rgba(248,81,73,.25); }
        .crack-status-warn { background: rgba(227,179,65,.1); color: var(--orange); border: 1px solid rgba(227,179,65,.25); }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 10px;
        }
        .metric-card {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px;
            text-align: center;
        }
        .metric-label {
            font-size: 10px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .metric-value {
            font-size: 20px;
            font-weight: 700;
            color: var(--text);
            font-family: 'JetBrains Mono', monospace;
            line-height: 1;
        }
        .metric-unit {
            font-size: 10px;
            color: var(--muted);
            margin-top: 2px;
        }
        .temp-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            font-size: 12px;
            color: var(--muted);
            font-family: 'JetBrains Mono', monospace;
            padding: 8px 10px;
            background: var(--surface2);
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        .temp-row span { color: var(--text); font-weight: 600; }

        /* -- SIDEBAR: CONTROLS -------------------------- */
        .sidebar {
            grid-row: 3 / 5;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .control-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
        }

        /* Joystick */
        .joystick-wrap {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }
        .joystick-area {
            width: 210px;
            height: 210px;
            background: var(--surface2);
            border-radius: 50%;
            position: relative;
            border: 2px solid var(--border);
            cursor: pointer;
            touch-action: none;
            user-select: none;
        }
        .joystick-area::before {
            content: '';
            position: absolute;
            top: 50%; left: 10%; right: 10%;
            height: 1px;
            background: rgba(255,255,255,0.06);
            transform: translateY(-50%);
        }
        .joystick-area::after {
            content: '';
            position: absolute;
            left: 50%; top: 10%; bottom: 10%;
            width: 1px;
            background: rgba(255,255,255,0.06);
            transform: translateX(-50%);
        }
        .joystick-knob {
            width: 72px;
            height: 72px;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            border-radius: 50%;
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            box-shadow: 0 4px 20px rgba(88,166,255,.3);
            pointer-events: none;
            transition: box-shadow 0.1s;
        }
        .joystick-knob.active {
            box-shadow: 0 4px 35px rgba(88,166,255,.7);
        }
        .joystick-dir {
            font-size: 13px;
            font-weight: 700;
            color: var(--accent);
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: 2px;
            height: 20px;
        }
        .stop-btn {
            width: 64px; height: 64px;
            background: var(--red);
            border: none;
            border-radius: 50%;
            color: white;
            font-weight: 800;
            font-size: 11px;
            cursor: pointer;
            letter-spacing: 0.5px;
            box-shadow: 0 4px 20px rgba(248,81,73,.35);
            transition: all 0.15s;
        }
        .stop-btn:hover { background: #ff6b63; }
        .stop-btn:active { transform: scale(0.9); }

        /* Action buttons */
        .action-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
        }
        .btn-action {
            padding: 12px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 700;
            color: white;
            letter-spacing: 0.5px;
            text-align: left;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.15s;
            border: 1px solid transparent;
        }
        .btn-action:hover { filter: brightness(1.15); }
        .btn-action:active { transform: scale(0.97); }
        .btn-rotate   { background: rgba(188,140,255,.15); color: var(--accent2); border-color: rgba(188,140,255,.3); }
        .btn-scan     { background: rgba(227,179,65,.15);  color: var(--orange);  border-color: rgba(227,179,65,.3); }
        .btn-analytics{ background: rgba(88,166,255,.15);  color: var(--accent);  border-color: rgba(88,166,255,.3); }
        .btn-icon { font-size: 16px; }

        /* Scan monitor */
        .scan-monitor {
            background: var(--surface);
            border: 1px solid var(--green);
            border-radius: var(--radius);
            overflow: hidden;
        }
        .scan-monitor-header {
            padding: 10px 14px;
            background: rgba(63,185,80,.08);
            border-bottom: 1px solid rgba(63,185,80,.2);
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 700;
            color: var(--green);
            letter-spacing: 1px;
        }
        .scan-monitor-body {
            padding: 12px;
            max-height: 180px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            line-height: 1.7;
        }

        /* Log */
        .log-card {
            grid-column: 1 / -1;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }
        .log-header {
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 700;
            color: var(--muted);
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        .log-body {
            padding: 10px 14px;
            max-height: 130px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
        }
        .log-entry {
            padding: 2px 0;
            line-height: 1.6;
            color: var(--muted);
            border-bottom: 1px solid rgba(48,54,61,.5);
        }
        .log-entry:last-child { border: none; }
        .log-time { color: #444d56; margin-right: 8px; }
        .log-ok   { color: var(--green); }
        .log-err  { color: var(--red); }
        .log-warn { color: var(--orange); }

        /* Toast */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            padding: 14px 20px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 14px;
            color: white;
            box-shadow: 0 8px 30px rgba(0,0,0,0.4);
            opacity: 0;
            transform: translateY(16px);
            transition: all 0.35s cubic-bezier(.2,.8,.4,1);
            pointer-events: none;
            max-width: 320px;
            display: flex;
            align-items: center;
            gap: 10px;
            border: 1px solid rgba(255,255,255,.1);
        }
        .toast.show { opacity: 1; transform: translateY(0); }
        .toast.success { background: #1a3a2a; color: var(--green);  border-color: rgba(63,185,80,.4); }
        .toast.info    { background: #1a2a3a; color: var(--accent); border-color: rgba(88,166,255,.4); }
        .toast.warning { background: #3a2a0a; color: var(--orange); border-color: rgba(227,179,65,.4); }
        .toast.error   { background: #3a1a1a; color: var(--red);    border-color: rgba(248,81,73,.4); }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

        @media (max-width: 900px) {
            .layout { grid-template-columns: 1fr; }
            .sidebar { grid-row: auto; }
            .status-bar { grid-template-columns: repeat(2, 1fr); }
            .cameras { grid-template-columns: 1fr; }
            .metrics-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 480px) {
            .status-bar { grid-template-columns: 1fr; }
            .header-pills { display: none; }
        }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>

    <div class="layout">

        <!-- -- HEADER -- -->
        <header class="header">
            <div class="header-brand">
                <div class="logo">🤖</div>
                <div>
                    <h1>CrackBot</h1>
                    <p>Remote Control Dashboard</p>
                </div>
            </div>
            <div class="header-pills">
                <div class="pill pill-green">
                    <div class="pill-dot"></div>
                    ROBOT OK
                </div>
                <div class="pill pill-blue" id="pillRgb">
                    <div class="pill-dot"></div>
                    %%RGB_STATUS%%
                </div>
                <div class="pill pill-blue" id="pillThermal">
                    <div class="pill-dot"></div>
                    %%THERMAL_STATUS%%
                </div>
            </div>
        </header>

        <!-- -- STATUS BAR -- -->
        <div class="status-bar">
            <div class="stat-card">
                <div class="stat-icon stat-icon-green">📡</div>
                <div>
                    <div class="stat-label">Distance</div>
                    <div class="stat-value green"><span id="distance">--</span> <span style="font-size:13px;color:var(--muted)">cm</span></div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon stat-icon-blue">🌡️</div>
                <div>
                    <div class="stat-label">Avg Temp</div>
                    <div class="stat-value blue"><span id="statTempAvg">--</span> <span style="font-size:13px;color:var(--muted)">degC</span></div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon stat-icon-purple">🔬</div>
                <div>
                    <div class="stat-label">Crack Area</div>
                    <div class="stat-value purple"><span id="statCrackArea">--</span> <span style="font-size:13px;color:var(--muted)">cm²</span></div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon stat-icon-orange">⚡</div>
                <div>
                    <div class="stat-label">Temp Range</div>
                    <div class="stat-value orange"><span id="statTempRange">--</span> <span style="font-size:13px;color:var(--muted)">degC</span></div>
                </div>
            </div>
        </div>

        <!-- -- LEFT COLUMN -- -->
        <div style="display:flex;flex-direction:column;gap:12px;">

            <!-- Cameras -->
            <div class="cameras">
                <div class="cam-card">
                    <div class="cam-header">
                        <span style="font-size:14px;">📷</span>
                        <span class="cam-badge">RGB CAMERA</span>
                        <div class="cam-indicator on"></div>
                    </div>
                    <div class="cam-body">%%RGB_FEED%%</div>
                </div>
                <div class="cam-card">
                    <div class="cam-header">
                        <span style="font-size:14px;">🌡️</span>
                        <span class="cam-badge">THERMAL CAMERA</span>
                        <div class="cam-indicator on"></div>
                    </div>
                    <div class="cam-body">%%THERMAL_FEED%%</div>
                </div>
            </div>

            <!-- Scan Monitor (hidden until scan starts) -->
            <div id="scanMonitor" style="display:none;" class="scan-monitor">
                <div class="scan-monitor-header">
                    <span>◉</span> LIVE SCAN MONITOR
                </div>
                <div class="scan-monitor-body" id="scanLogLines"></div>
            </div>

            <!-- Crack Analysis -->
            <div class="crack-panel">
                <div class="panel-header">
                    <span>🔬</span>
                    <span class="panel-title">Thermal Crack Analysis</span>
                </div>
                <div id="crackStatus" class="crack-status-line crack-status-ok">* No Anomaly Detected</div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">Length</div>
                        <div class="metric-value" id="crackLength">--</div>
                        <div class="metric-unit">cm</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Width</div>
                        <div class="metric-value" id="crackWidth">--</div>
                        <div class="metric-unit">cm</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Area</div>
                        <div class="metric-value" id="crackArea">--</div>
                        <div class="metric-unit">cm²</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Est. Depth</div>
                        <div class="metric-value" id="crackDepth">--</div>
                        <div class="metric-unit">cm</div>
                    </div>
                </div>
                <div class="temp-row">
                    Avg: <span id="tempAvg">--</span>degC &nbsp;·&nbsp;
                    Min: <span id="tempMin">--</span>degC &nbsp;·&nbsp;
                    Max: <span id="tempMax">--</span>degC &nbsp;·&nbsp;
                    Range: <span id="tempRange">--</span>degC &nbsp;·&nbsp;
                    Pixels: <span id="affectedPx">--</span>
                </div>
            </div>
        </div>

        <!-- -- SIDEBAR -- -->
        <div class="sidebar">

            <!-- Joystick -->
            <div class="control-card">
                <div class="panel-header" style="margin-bottom:10px;">
                    <span>🕹️</span>
                    <span class="panel-title">Movement</span>
                </div>
                <div class="joystick-wrap">
                    <div class="joystick-area" id="joystick">
                        <div class="joystick-knob" id="joystickKnob"></div>
                    </div>
                    <div style="display:flex;align-items:center;gap:16px;">
                        <div class="joystick-dir" id="joystickDir">-- IDLE --</div>
                        <button class="stop-btn" onclick="stop()">STOP</button>
                    </div>
                    <p style="font-size:11px;color:var(--muted);text-align:center;">Drag joystick · Arrow keys / WASD · Space = stop</p>
                </div>
            </div>

            <!-- Action Buttons -->
            <div class="control-card">
                <div class="panel-header" style="margin-bottom:10px;">
                    <span>⚡</span>
                    <span class="panel-title">Actions</span>
                </div>
                <div class="action-grid">
                    <button class="btn-action btn-rotate" onclick="rotate360()">
                        <span class="btn-icon">🔄</span> Rotate 360deg
                    </button>
                    <button class="btn-action btn-scan" onclick="startScan()">
                        <span class="btn-icon">🤖</span> Start Auto Scan
                    </button>
                    <button class="btn-action btn-analytics" onclick="openAnalytics()">
                        <span class="btn-icon">📊</span> View Analytics
                    </button>
                </div>
            </div>
        </div>

        <!-- -- LOG -- -->
        <div class="log-card">
            <div class="log-header">
                <span>📋</span> Activity Log
            </div>
            <div class="log-body" id="logEntries"></div>
        </div>

    </div>

    <script>
        let logCount = 0;

        function showToast(msg, type, durationMs) {
            var icons = { success:'OK', info:'i', warning:'!', error:'X' };
            var t = document.getElementById('toast');
            t.innerHTML = '<span>' + (icons[type]||'i') + '</span> ' + msg;
            t.className = 'toast ' + (type || 'info');
            t.classList.add('show');
            setTimeout(function() { t.classList.remove('show'); }, durationMs || 5000);
        }

        function log(msg) {
            var logDiv = document.getElementById('logEntries');
            var time = new Date().toLocaleTimeString();
            var entry = document.createElement('div');
            entry.className = 'log-entry';
            var colorClass = msg.indexOf('[ERROR]') >= 0 || msg.indexOf('[WARN]') >= 0 ? 'log-warn' :
                             msg.indexOf('[OK]') >= 0 ? 'log-ok' : '';
            entry.innerHTML = '<span class="log-time">' + time + '</span><span class="' + colorClass + '">' + msg + '</span>';
            logDiv.insertBefore(entry, logDiv.firstChild);
            if (++logCount > 25) {
                logDiv.removeChild(logDiv.lastChild);
                logCount--;
            }
        }

        function send(cmd, description) {
            var joystickCmds = ['Forward','Backward','Turn Left','Turn Right','Stop','STOP','hold'];
            var isRepeat = joystickCmds.indexOf(description) >= 0;
            if (!isRepeat) log(description);
            fetch('/command', {
                method: 'POST',
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({command: cmd})
            })
            .then(function(r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function(data) {
                if (data.status === 'error' && !isRepeat) log('[ERROR] ' + data.response);
            })
            .catch(function(e) {
                if (!isRepeat) log('[ERROR] ' + e.message);
            });
        }

        // Load calibrated turn durations
        var turnRightMs = 2600, turnLeftMs = 2600;
        var turn360Durations = [2600, 2630, 2600, 2600];
        var turnCalibrated = false;
        fetch('/turn_config')
        .then(function(r) { return r.json(); })
        .then(function(cfg) {
            turnRightMs      = cfg.right_90_ms;
            turnLeftMs       = cfg.left_90_ms;
            turn360Durations = cfg.turn_durations_360;
            turnCalibrated   = cfg.calibrated;
            log('[OK] Turn config loaded -- R:' + turnRightMs + 'ms  L:' + turnLeftMs + 'ms' + (turnCalibrated ? '' : ' (default)'));
        })
        .catch(function() { log('Using default turn durations'); });

        function stop() {
            send('S', 'STOP');
            fetch('/scan_status')
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d.running) {
                    fetch('/stop_scan', {method:'POST'})
                    .then(function(r) { return r.json(); })
                    .then(function(res) {
                        log('[WARN] Scan killed: ' + res.message);
                        showToast('Scan stopped!', 'warning', 4000);
                        document.getElementById('scanMonitor').style.display = 'none';
                    }).catch(function(){});
                }
            }).catch(function(){});
        }

        // -- JOYSTICK ---------------------------------------------
        (function() {
            var area   = document.getElementById('joystick');
            var knob   = document.getElementById('joystickKnob');
            var dirEl  = document.getElementById('joystickDir');
            var active = false, curDir = null, dead = 25;
            var repeatTimer = null;

            function getCenter() {
                var r = area.getBoundingClientRect();
                return { cx: r.left + r.width/2, cy: r.top + r.height/2, r: r.width/2 };
            }
            function getDir(x, y, dist) {
                if (dist < dead) return null;
                return Math.abs(y) >= Math.abs(x) ? (y < 0 ? 'F' : 'B') : (x < 0 ? 'L' : 'R');
            }
            function sendDir(dir) {
                var cmds = { F:'F,70,0', B:'B,70,0', L:'L,150,0', R:'R,150,0' };
                var labels = { F:'Forward', B:'Backward', L:'Turn Left', R:'Turn Right' };
                send(cmds[dir], labels[dir]);
            }
            var labels = { F:'FORWARD', B:'BACKWARD', L:'TURN LEFT', R:'TURN RIGHT' };

            function startRepeat(dir) {
                if (repeatTimer) clearInterval(repeatTimer);
                sendDir(dir);
                repeatTimer = setInterval(function() {
                    if (curDir) sendDir(curDir);
                }, 400);
            }
            function stopRepeat() {
                if (repeatTimer) { clearInterval(repeatTimer); repeatTimer = null; }
            }

            function onMove(e) {
                e.preventDefault();
                var c = getCenter();
                var cx = e.touches ? e.touches[0].clientX : e.clientX;
                var cy = e.touches ? e.touches[0].clientY : e.clientY;
                var dx = cx - c.cx, dy = cy - c.cy;
                var dist = Math.sqrt(dx*dx + dy*dy);
                var maxR = c.r - 38;
                var clamp = Math.min(dist, maxR);
                var angle = Math.atan2(dy, dx);
                knob.style.left = (50 + Math.cos(angle)*clamp/c.r*50) + '%';
                knob.style.top  = (50 + Math.sin(angle)*clamp/c.r*50) + '%';
                var dir = getDir(dx, dy, dist);
                if (dir !== curDir) {
                    curDir = dir;
                    if (dir) {
                        knob.classList.add('active');
                        dirEl.textContent = labels[dir];
                        startRepeat(dir);
                    } else {
                        knob.classList.remove('active');
                        dirEl.textContent = '-- IDLE --';
                        stopRepeat();
                        send('S', 'Stop');
                    }
                }
            }
            function onRelease() {
                if (!active) return;
                active = false; curDir = null;
                knob.style.left = '50%'; knob.style.top = '50%';
                knob.classList.remove('active');
                dirEl.textContent = '-- IDLE --';
                stopRepeat();
                send('S', 'Stop');
            }
            area.addEventListener('mousedown',  function(e) { active=true; onMove(e); });
            area.addEventListener('touchstart', function(e) { active=true; onMove(e); }, {passive:false});
            area.addEventListener('mousemove',  function(e) { if(active) onMove(e); });
            area.addEventListener('touchmove',  function(e) { if(active) onMove(e); }, {passive:false});
            document.addEventListener('mouseup',  onRelease);
            document.addEventListener('touchend', onRelease);
        })();

        // -- KEYBOARD ----------------------------------------------
        var keyHeld = {};
        var keyDirs = { 'ArrowUp':'F','w':'F','W':'F','ArrowDown':'B','s':'B','S':'B','ArrowLeft':'L','a':'L','A':'L','ArrowRight':'R','d':'R','D':'R' };
        var keyCmds = { F:'F,70,0', B:'B,70,0', L:'L,150,0', R:'R,150,0' };
        document.addEventListener('keydown', function(e) {
            if (e.key === ' ') { send('S','Stop'); return; }
            var dir = keyDirs[e.key];
            if (!dir || keyHeld[e.key]) return;
            keyHeld[e.key] = true;
            send(keyCmds[dir], e.key);
        });
        document.addEventListener('keyup', function(e) {
            delete keyHeld[e.key];
            if (Object.keys(keyHeld).length === 0) send('S', 'Stop');
        });

        function rotate360() {
            if (!confirm('Perform 360deg rotation with calibrated timing?')) return;
            log('Starting 360deg rotation (4x90deg turns)...');
            var currentTurn = 0;
            function executeTurn() {
                if (currentTurn >= turn360Durations.length) { log('[OK] 360deg rotation complete!'); return; }
                var dur = turn360Durations[currentTurn], n = currentTurn + 1;
                log('Turn ' + n + '/4 (' + dur + 'ms)...');
                send('R,150,' + dur, 'Turn ' + n + '/4');
                currentTurn++;
                setTimeout(executeTurn, dur + 2000);
            }
            executeTurn();
        }

        function startScan() {
            var skipFindWall = confirm('WALL DETECTION: Click OK if robot already faces wall. Click CANCEL to do 360 search first.');
            var width = parseInt(prompt('Scan width in cm (default 90):', '90') || '90');
            var height = parseInt(prompt('Scan height in cm (default 60):', '60') || '60');
            var step = parseInt(prompt('Step size in cm (default 30):', '30') || '30');
            var cols = Math.floor(width/step) + 1;
            var rows = Math.floor(height/step) + 1;
            if (!confirm('Grid scan: ' + cols + ' cols x ' + rows + ' rows = ' + (cols*rows) + ' positions. Continue?')) return;
            log('[SCAN] Starting autonomous scan...');
            document.getElementById('scanMonitor').style.display = 'block';
            document.getElementById('scanLogLines').innerHTML = '<div style="color:var(--orange)">Starting scan...</div>';
            showToast('Autonomous scan started!', 'info', 4000);
            fetch('/start_scan', {
                method: 'POST',
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({scan_mode:2, width_cm:width, height_cm:height, step_cm:step, skip_find_wall: skipFindWall})
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                log('[OK] ' + data.message);
                var lastLineCount = 0;
                var scanPoller = setInterval(function() {
                    fetch('/scan_log')
                    .then(function(r) { return r.json(); })
                    .then(function(d) {
                        if (d.lines && d.lines.length > lastLineCount) {
                            var logDiv = document.getElementById('scanLogLines');
                            for (var i = lastLineCount; i < d.lines.length; i++) {
                                var line = d.lines[i].trim();
                                if (!line) continue;
                                var el = document.createElement('div');
                                el.style.color = line.indexOf('CRACK DETECTED') >= 0 ? 'var(--red)' :
                                                 line.indexOf('No crack') >= 0 ? 'var(--green)' :
                                                 line.indexOf('SCANNING POSITION') >= 0 ? 'var(--accent)' :
                                                 line.indexOf('Thermal') >= 0 ? 'var(--accent2)' : 'var(--muted)';
                                el.textContent = line;
                                logDiv.appendChild(el);
                                logDiv.scrollTop = logDiv.scrollHeight;
                                if (line.indexOf('SCAN COMPLETE') >= 0 || line.indexOf('AUTONOMOUS SCAN COMPLETE') >= 0) {
                                    showToast('Scan complete! Check results.', 'success', 8000);
                                    log('[OK] Autonomous scan finished!');
                                }
                                if (line.indexOf('CRACK DETECTED') >= 0) showToast('CRACK DETECTED during scan!', 'warning', 6000);
                            }
                            lastLineCount = d.lines.length;
                        }
                    })
                    .catch(function() {
                        clearInterval(scanPoller);
                        log('[OK] Scan complete! Robot reconnecting...');
                        showToast('Scan complete! Robot has finished.', 'success', 10000);
                    });
                }, 2000);
            })
            .catch(function() {
                log('[WARN] Dashboard restarting -- refresh in ~30s');
                var poll = setInterval(function() {
                    fetch('/status').then(function(){clearInterval(poll); location.reload();}).catch(function(){});
                }, 3000);
            });
        }

        function openAnalytics() {
            window.open('http://' + window.location.hostname + ':8080', '_blank');
        }

        // Distance poller
        setInterval(function() {
            fetch('/distance').then(function(r){return r.json();})
            .then(function(data) {
                document.getElementById('distance').textContent = data.distance || '--';
            }).catch(function(){});
        }, 2000);

        // Crack analysis poller
        setInterval(function() {
            fetch('/crack_analysis').then(function(r){return r.json();})
            .then(function(d) {
                var avg = d.avg_temp  !== undefined ? d.avg_temp  : '--';
                var min = d.min_temp  !== undefined ? d.min_temp  : '--';
                var max = d.max_temp  !== undefined ? d.max_temp  : '--';
                var rng = d.temp_range !== undefined ? d.temp_range : '--';
                var px  = d.affected_pixels !== undefined ? d.affected_pixels : '--';

                document.getElementById('tempAvg').textContent    = avg;
                document.getElementById('tempMin').textContent    = min;
                document.getElementById('tempMax').textContent    = max;
                document.getElementById('tempRange').textContent  = rng;
                document.getElementById('affectedPx').textContent = px;
                document.getElementById('statTempAvg').textContent  = avg;
                document.getElementById('statTempRange').textContent = rng;

                var statusEl   = document.getElementById('crackStatus');
                var surfaceTag = d.surface_type
                    ? ' <small style="opacity:.7;font-size:10px">[' + d.surface_type + (d.wall_confidence !== undefined ? ' ' + d.wall_confidence + '%' : '') + ']</small>'
                    : '';

                if (!d.is_wall && d.surface_type === 'PERSON') {
                    statusEl.className = 'crack-status-line crack-status-warn';
                    statusEl.innerHTML = '* PERSON DETECTED -- Not scanning' + surfaceTag;
                    document.getElementById('crackLength').textContent = '--';
                    document.getElementById('crackWidth').textContent  = '--';
                    document.getElementById('crackArea').textContent   = '--';
                    document.getElementById('crackDepth').textContent  = '--';
                    document.getElementById('statCrackArea').textContent = '--';
                } else if (!d.is_wall && d.surface_type === 'OBJECT') {
                    statusEl.className = 'crack-status-line crack-status-warn';
                    statusEl.innerHTML = '* OBSTACLE DETECTED -- Not a wall' + surfaceTag;
                    document.getElementById('crackLength').textContent = '--';
                    document.getElementById('crackWidth').textContent  = '--';
                    document.getElementById('crackArea').textContent   = '--';
                    document.getElementById('crackDepth').textContent  = '--';
                    document.getElementById('statCrackArea').textContent = '--';
                } else if (!d.is_wall && d.surface_type) {
                    statusEl.className = 'crack-status-line crack-status-warn';
                    statusEl.innerHTML = '* CARDBOARD / NOT A WALL' + surfaceTag;
                    document.getElementById('crackLength').textContent = '--';
                    document.getElementById('crackWidth').textContent  = '--';
                    document.getElementById('crackArea').textContent   = '--';
                    document.getElementById('crackDepth').textContent  = '--';
                    document.getElementById('statCrackArea').textContent = '--';
                } else if (d.anomaly) {
                    statusEl.className = 'crack-status-line crack-status-bad';
                    statusEl.innerHTML = '* CRACK DETECTED' + surfaceTag + (d.anomaly_type ? ' <small style="opacity:.7;font-size:10px">[' + d.anomaly_type + ']</small>' : '');
                    document.getElementById('crackLength').textContent = d.length_cm;
                    document.getElementById('crackWidth').textContent  = d.width_cm;
                    document.getElementById('crackArea').textContent   = d.area_cm2;
                    document.getElementById('crackDepth').textContent  = d.depth_cm;
                    document.getElementById('statCrackArea').textContent = d.area_cm2 || '--';
                } else {
                    statusEl.className = 'crack-status-line crack-status-ok';
                    statusEl.innerHTML = '* WALL -- No Crack' + surfaceTag;
                    document.getElementById('crackLength').textContent = '--';
                    document.getElementById('crackWidth').textContent  = '--';
                    document.getElementById('crackArea').textContent   = '--';
                    document.getElementById('crackDepth').textContent  = '--';
                    document.getElementById('statCrackArea').textContent = '--';
                }
            }).catch(function(){});
        }, 2000);

        // Connection status check
        setInterval(function() {
            fetch('/status').then(function(r){return r.json();})
            .then(function(data) {
                if (data.robot === 'disconnected') log('[WARN] Robot connection lost');
            }).catch(function(){});
        }, 5000);

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
        'right_90_ms':       TURN_RIGHT_90_MS,
        'left_90_ms':        TURN_LEFT_90_MS,
        'turn_durations_360': TURN_DURATIONS_360,
        'calibrated':        bool(_wheel_cal),
    })


@app.route('/crack_analysis')
def crack_analysis():
    """Return latest thermal crack analysis as JSON"""
    with crack_analysis_lock:
        data = dict(latest_crack_analysis)
    return jsonify(data)


@app.route('/')
def index():
    # Build the two dynamic status strings in Python, not Jinja2
    # This avoids ALL Jinja2/JS curly-brace conflicts
    rgb_status    = 'RGB CAM ON' if (CAMERA_AVAILABLE and camera is not None) else 'NO RGB'
    thermal_status = 'THERMAL ON' if (THERMAL_AVAILABLE and thermal is not None) else 'NO THERMAL'

    rgb_feed_img = (
        '<img class="camera-view" src="/rgb_feed" alt="RGB Camera">'
        if (CAMERA_AVAILABLE and camera is not None)
        else '<div class="no-camera">Camera Not Available</div>'
    )
    thermal_feed_img = (
        '<img class="camera-view" src="/thermal_feed" alt="Thermal Camera">'
        if (THERMAL_AVAILABLE and thermal is not None)
        else '<div class="no-camera">Thermal Not Available</div>'
    )

    html = (HTML_TEMPLATE
            .replace('%%RGB_STATUS%%',         rgb_status)
            .replace('%%THERMAL_STATUS%%',     thermal_status)
            .replace('%%RGB_FEED%%',           rgb_feed_img)
            .replace('%%THERMAL_FEED%%',       thermal_feed_img))
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
        # Check robot serial connection
        robot_status = 'disconnected'
        if robot_serial:
            try:
                if robot_serial.is_open:
                    robot_status = 'connected'
            except:
                robot_status = 'disconnected'
        
        camera_status = 'ok' if camera else 'unavailable'
        thermal_status = 'ok' if thermal else 'unavailable'
        
        return jsonify({
            'robot': robot_status,
            'camera': camera_status,
            'thermal': thermal_status
        })
    except Exception as e:
        print(f"[STATUS] Error: {e}")
        return jsonify({
            'robot': 'error',
            'camera': 'error',
            'thermal': 'error'
        })

@app.route('/command', methods=['POST'])
def command():
    """Handle robot commands with detailed response and auto-reconnect"""
    global robot_serial
    
    try:
        cmd = request.json.get('command', '')
        if not cmd:
            return jsonify({'status': 'error', 'response': 'No command provided'}), 400
        
        print(f"[WEB] Received command: {cmd}")
        
        # Check connection and attempt reconnect if needed
        if not robot_serial or not robot_serial.is_open:
            print("[WEB] Robot disconnected, attempting reconnect...")
            if connect_robot():
                print("[WEB] Reconnected successfully!")
            else:
                return jsonify({'status': 'error', 'response': 'Robot disconnected. Reconnect failed.'}), 500
        
        response = send_command(cmd)
        print(f"[WEB] Response: {response}")
        
        # Determine status
        if 'ERROR' in response:
            status = 'error'
        else:
            status = 'success'
        
        return jsonify({'status': status, 'response': response})
    except serial.SerialException as e:
        print(f"[WEB] Serial exception: {e}")
        # Try to reconnect
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
    """Start autonomous scan in background thread -- web dashboard stays alive for monitoring"""
    global robot_serial
    try:
        data      = request.get_json(silent=True) or {}
        scan_mode      = int(data.get('scan_mode', 2))
        width_cm       = int(data.get('width_cm',  150))
        height_cm      = int(data.get('height_cm', 100))
        step_cm        = int(data.get('step_cm',   30))
        skip_find_wall = bool(data.get('skip_find_wall', False))

        # Close web serial so scanner subprocess gets exclusive access
        with serial_lock:
            if robot_serial and robot_serial.is_open:
                try:
                    robot_serial.close()
                except:
                    pass
                robot_serial = None

        # Run scanner as subprocess -- web dashboard keeps running
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
            # Reconnect robot serial when done
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
    # Start background distance updater (keeps camera loop fast)
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
        if camera:
            camera.stop()
