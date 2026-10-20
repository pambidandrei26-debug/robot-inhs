#!/usr/bin/env python3
"""
FULLY AUTONOMOUS WALL CRACK DETECTION ROBOT - v2.0
Optimized sensor architecture:
- Camera + Thermal = Crack Detection (with size measurements)
- Ultrasonic = Obstacle Avoidance ONLY

Updated: September 17, 2026
ENHANCED: Integrated ThermalAnalyzer module for maximum detection accuracy
"""

import serial
import time
import sys
import os
from datetime import datetime
import RPi.GPIO as GPIO

# Sensor imports
try:
    from picamera2 import Picamera2
    import cv2
    import numpy as np
    CAMERA_AVAILABLE = True
except Exception as e:
    CAMERA_AVAILABLE = False
    print(f" Camera not available: {e}")

try:
    import board
    import busio
    import adafruit_mlx90640
    THERMAL_AVAILABLE = True
except Exception as e:
    THERMAL_AVAILABLE = False
    print(f" Thermal camera not available: {e}")

# ADVANCED THERMAL ANALYSIS - Maximum detection power
try:
    from thermal_analyzer import ThermalAnalyzer
    THERMAL_ANALYZER_AVAILABLE = True
    print(" [✓] Advanced ThermalAnalyzer module loaded")
except Exception as e:
    THERMAL_ANALYZER_AVAILABLE = False
    print(f" [!] ThermalAnalyzer not available, using basic analysis: {e}")

# ========================================
# CONFIGURATION
# ========================================

# Serial port for MegaPi
# Auto-detect MegaPi serial port
import glob as _glob
_ports = sorted(_glob.glob('/dev/ttyUSB*') + _glob.glob('/dev/ttyACM*'))
MEGAPI_PORT = _ports[0] if _ports else '/dev/ttyUSB0'
print(f"[PORT] Using: {MEGAPI_PORT}")
MEGAPI_BAUD = 115200

# Distance parameters
OPTIMAL_WALL_DISTANCE = 35.0  # cm from wall (increased for safety)
MIN_WALL_DISTANCE = 25.0      # cm (increased to prevent collisions)
MAX_WALL_DISTANCE = 45.0      # cm (too far)
DISTANCE_TOLERANCE = 5.0      # cm (acceptable range)

# Movement parameters
FORWARD_SPEED = 70         # 0-255
BACKWARD_SPEED = 70
TURN_SPEED = 150       # Increased - pivot turns need more power
SCAN_MOVE_SPEED = 60       # Slower speed during scanning

# Timing
COMMAND_DELAY = 0.1        # Delay after sending command
MOVE_STEP_DURATION = 1000  # ms per step forward

# ROTATION TIMING - Load from calibration with progressive timing support
import json as _json, os as _os
_WHEEL_CAL = _os.path.expanduser("~/wheel_calibration.json")
if _os.path.exists(_WHEEL_CAL):
    try:
        with open(_WHEEL_CAL) as _wf:
            _wc = _json.load(_wf)
        TURN_90_DURATION  = int(_wc.get('right_90_ms', 2600))
        TURN_LEFT_90_DURATION = int(_wc.get('left_90_ms', TURN_90_DURATION))
        
        # IMPROVED: Use progressive timing if available (like web UI does)
        # Progressive timing compensates for motor warmup during 360° rotations
        if 'turn_durations_360' in _wc:
            TURN_DURATIONS_90 = _wc['turn_durations_360']
            print(f"[WHEEL CAL] Loaded PROGRESSIVE timing: {TURN_DURATIONS_90}")
        else:
            # Fallback: use fixed timing if progressive not available
            TURN_DURATIONS_90 = [TURN_90_DURATION] * 4
            print(f"[WHEEL CAL] Loaded FIXED timing: {TURN_90_DURATION}ms per 90° turn")
    except:
        TURN_90_DURATION  = 2600
        TURN_LEFT_90_DURATION = 2600
        TURN_DURATIONS_90 = [2600, 2600, 2600, 2600]
else:
    TURN_90_DURATION  = 2600
    TURN_LEFT_90_DURATION = 2600
    TURN_DURATIONS_90 = [2600, 2600, 2600, 2600]

TURN_STABILIZATION_DELAY = 1.5   # Match calibration tool's stabilization time
TURN_45_BASE = TURN_90_DURATION // 2

# Scan parameters
SCAN_STEP_CM = 30          # Distance to move between scans
WALL_SEARCH_TIMEOUT = 30   # seconds to search for wall

# Piezo for audio feedback
PIEZO_PIN = 18

# Data directory
DATA_DIR = "/home/pi/crack_data"

# LIVE SCAN MONITOR - Log file for web dashboard
SCAN_LOG_FILE = os.path.expanduser("~/scan_output.log")

def log_to_scan_monitor(message, level="INFO"):
    """Write formatted message to scan log for web dashboard monitoring
    
    Args:
        message: Message to log
        level: INFO, SUCCESS, WARNING, ERROR
    """
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Icon mapping
        icons = {
            "INFO": "🔍",
            "SUCCESS": "✅",
            "WARNING": "⚠️ ",
            "ERROR": "❌",
            "CRACK": "🚨",
            "POSITION": "📍",
            "MOVE": "→",
            "TURN": "↻",
            "THERMAL": "🌡️ ",
            "CAMERA": "📷",
            "DISTANCE": "📏"
        }
        
        icon = icons.get(level, "•")
        formatted = f"[{timestamp}] {icon} {message}\n"
        
        # Append to log file
        with open(SCAN_LOG_FILE, 'a') as f:
            f.write(formatted)
        
        # Also print to console
        print(f"{icon} {message}")
        
    except Exception as e:
        # Fallback to regular print if logging fails
        print(message)


# ========================================
# ROBOT CONTROLLER
# ========================================

class RobotController:
    """Controls robot via MegaPi serial communication"""
    
    def __init__(self, port=MEGAPI_PORT, baud=MEGAPI_BAUD):
        """Initialize serial connection to MegaPi"""
        self.serial_port = None
        try:
            print(f" Connecting to MegaPi on {port}...")
            self.serial_port = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset and boot
            self.serial_port.reset_input_buffer()  # Clear startup message
            print("[OK] MegaPi connected!")
        except Exception as e:
            print(f"[X] Failed to connect to MegaPi: {e}")
            self.serial_port = None
    
    def send_command(self, command):
        """Send command to MegaPi"""
        if not self.serial_port:
            print("[X] No serial connection")
            return False
        
        try:
            self.serial_port.write(f"{command}\n".encode())
            time.sleep(COMMAND_DELAY)
            return True
        except Exception as e:
            print(f"[X] Command failed: {e}")
            return False
    
    def get_ultrasonic_distance(self):
        """Get distance from ultrasonic sensor via MegaPi with clean buffer handling."""
        if not self.serial_port:
            return None
        try:
            # CRITICAL FIX: Clear buffer before sending command to prevent stale readings
            self.serial_port.reset_input_buffer()
            
            # Send G command
            self.serial_port.write(b'G\n')
            time.sleep(COMMAND_DELAY)

            # Read response with reduced timeout (500ms instead of 2.5s)
            # Ultrasonic responds in ~60ms, so 500ms is plenty
            start = time.time()
            while time.time() - start < 0.5:  # 500ms timeout
                if self.serial_port.in_waiting > 0:
                    response = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if response.startswith("DISTANCE:"):
                        dist_str = response.split(":")[1].strip()
                        try:
                            distance = float(dist_str)
                            # Accept 2–400cm (reject 999 "no object" and sensor errors)
                            if 2.0 < distance <= 400.0:
                                return distance
                            return None
                        except ValueError:
                            pass
                time.sleep(0.01)
            return None
        except Exception as e:
            print(f" Distance read error: {e}")
            return None
    
    def move_forward(self, speed=FORWARD_SPEED, duration_ms=MOVE_STEP_DURATION):
        """Move forward"""
        return self.send_command(f"F,{speed},{duration_ms}")
    
    def move_backward(self, speed=BACKWARD_SPEED, duration_ms=MOVE_STEP_DURATION):
        """Move backward"""
        return self.send_command(f"B,{speed},{duration_ms}")
    
    def turn_left(self, speed=TURN_SPEED, duration_ms=None):
        """Turn left - uses left_90_ms calibration (left motors faster than right)"""
        if duration_ms is None:
            duration_ms = TURN_LEFT_90_DURATION
        return self.send_command(f"L,{speed},{duration_ms}")
    
    def turn_right(self, speed=TURN_SPEED, duration_ms=TURN_90_DURATION):
        """Turn right"""
        return self.send_command(f"R,{speed},{duration_ms}")
    
    def get_ultrasonic_distance_robust(self, samples=3):
        """Get distance with multiple samples to filter sensor angle errors"""
        readings = []
        for i in range(samples):
            dist = self.get_ultrasonic_distance()
            if dist and dist < 400:  # Filter 400cm+ errors (angled sensor)
                readings.append(dist)
            time.sleep(0.2)
        
        if not readings:
            return None
        
        # Use median to filter outliers
        readings.sort()
        return readings[len(readings) // 2]
    
    def move_forward_safe(self, speed=FORWARD_SPEED, duration_ms=MOVE_STEP_DURATION):
        """Move forward with stuck detection"""
        # Get distance before
        dist_before = self.get_ultrasonic_distance_robust()
        
        # Execute movement
        if not self.move_forward(speed, duration_ms):
            return False
        
        time.sleep(duration_ms / 1000 + 0.5)
        
        # Get distance after
        dist_after = self.get_ultrasonic_distance_robust()
        
        # Check if actually moved — skip if either reading is None (sensor failure)
        if dist_before is not None and dist_after is not None:
            change = abs(dist_before - dist_after)
            if change < 2.0:
                print("[X] STUCK! Distance unchanged.")
                print(f"    Before: {dist_before:.1f}cm, After: {dist_after:.1f}cm")
                self.stop()
                return False
        # If readings are None (sensor out of range), assume movement succeeded
        
        return True
    
    def stop(self):
        """Stop all motors"""
        return self.send_command("S")
    
    def close(self):
        """Close serial connection"""
        if self.serial_port:
            self.stop()
            self.serial_port.close()
            print(" MegaPi disconnected")


# ========================================
# CRACK DETECTOR
# ========================================

class CrackDetector:
    """Multi-sensor crack detection system
    
    SENSOR ROLES:
    - Camera: Visual surface crack detection (length, width measurements)
    - Thermal: Subsurface crack detection (length, width, area, depth)
    
    ENHANCED: Uses ThermalAnalyzer module for maximum detection accuracy
    """
    
    def __init__(self, data_dir=DATA_DIR):
        """Initialize all sensors"""
        self.data_dir = data_dir
        self.crack_count = 0
        
        # Create directories
        os.makedirs(f"{data_dir}/cracks", exist_ok=True)
        os.makedirs(f"{data_dir}/scans", exist_ok=True)
        os.makedirs(f"{data_dir}/reports", exist_ok=True)
        
        # Initialize camera
        self.camera = None
        if CAMERA_AVAILABLE:
            try:
                self.camera = Picamera2()
                config = self.camera.create_still_configuration()
                self.camera.configure(config)
                self.camera.start()
                time.sleep(2)
                print("[OK] Camera ready (Surface crack detection)")
            except Exception as e:
                print(f" Camera init failed: {e}")
                self.camera = None
        
        # Initialize thermal camera
        self.thermal = None
        if THERMAL_AVAILABLE:
            try:
                i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
                self.thermal = adafruit_mlx90640.MLX90640(i2c)
                self.thermal.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
                print("[OK] Thermal camera ready (Subsurface crack detection)")
            except Exception as e:
                print(f" Thermal init failed: {e}")
                self.thermal = None
        
        # Initialize ADVANCED thermal analyzer for maximum detection power
        self.thermal_analyzer = None
        if THERMAL_ANALYZER_AVAILABLE:
            try:
                # Medium sensitivity balances accuracy and false positives
                self.thermal_analyzer = ThermalAnalyzer(sensitivity='medium')
                print("[OK] Advanced ThermalAnalyzer initialized (4-algorithm detection)")
            except Exception as e:
                print(f" ThermalAnalyzer init failed: {e}")
                self.thermal_analyzer = None
        
        # Initialize piezo
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(PIEZO_PIN, GPIO.OUT)
            print("[OK] Piezo ready")
        except Exception as e:
            print(f" Piezo init failed: {e}")
    
    def beep(self, duration=0.1):
        """Sound piezo buzzer"""
        try:
            pwm = GPIO.PWM(PIEZO_PIN, 2000)
            pwm.start(50)
            time.sleep(duration)
            pwm.stop()
        except:
            pass
    
    def capture_image(self, position):
        """Capture camera image"""
        if not self.camera:
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.data_dir}/scans/pos_{position[0]}_{position[1]}_{timestamp}.jpg"
            self.camera.capture_file(filename)
            return filename
        except Exception as e:
            print(f" Camera capture failed: {e}")
            return None
    
    def capture_thermal(self):
        """Capture thermal data"""
        if not self.thermal:
            return None
        
        try:
            frame = [0] * 768
            self.thermal.getFrame(frame)
            temps = np.array(frame).reshape(24, 32)
            return temps
        except Exception as e:
            print(f" Thermal capture failed: {e}")
            return None
    
    def analyze_crack(self, image_path):
        """Analyze image for crack detection using edge detection"""
        if not image_path or not os.path.exists(image_path):
            return False, 0.0
        
        try:
            # Read image
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False, 0.0
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(img, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Calculate edge density
            edge_count = np.sum(edges > 0)
            total_pixels = edges.size
            edge_ratio = edge_count / total_pixels
            
            # Threshold for crack detection (adjust based on testing)
            CRACK_THRESHOLD = 0.05
            is_crack = edge_ratio > CRACK_THRESHOLD
            
            return is_crack, edge_ratio
        
        except Exception as e:
            print(f" Image analysis failed: {e}")
            return False, 0.0
    
    def analyze_thermal(self, thermal_data):
        """Analyze thermal data for subsurface crack anomalies using ADVANCED detection
        
        ENHANCED: Uses ThermalAnalyzer module with 4 detection algorithms:
        1. Variance detection - Statistical anomalies
        2. Gradient analysis - Sharp temperature transitions
        3. Cluster detection - Hot/cold spot grouping
        4. Edge detection - Thermal boundaries
        
        Returns: (has_anomaly, thermal_analysis_dict)
        thermal_analysis_dict includes:
        - Basic stats (min, max, avg, std, range)
        - Detection scores (variance, gradient, cluster, edge)
        - Severity (0-100)
        - Crack classification (cold_crack, hot_crack, surface_crack)
        - Crack size estimation (length_cm, width_cm, area_cm2)
        - Depth estimation (depth_cm)
        """
        if thermal_data is None:
            return False, {}
        
        try:
            # CRITICAL FIX: Filter invalid temperature readings (like verify_real_wall does)
            # MLX90640 can output <0°C or >80°C during I2C glitches
            valid_mask = (thermal_data > 5.0) & (thermal_data < 80.0)
            valid_pixel_count = np.sum(valid_mask)
            
            # Require at least 80% valid pixels (same threshold as verify_real_wall)
            if valid_pixel_count < int(thermal_data.size * 0.8):
                print(" [!] Thermal frame corrupted (>20% bad pixels) - skipping")
                return False, {}
            
            # Use only valid pixels for analysis
            clean_data = thermal_data[valid_mask]
            
            # Basic statistics on clean data
            min_temp = float(np.min(clean_data))
            max_temp = float(np.max(clean_data))
            avg_temp = float(np.mean(clean_data))
            std_temp = float(np.std(clean_data))
            temp_range = max_temp - min_temp
            
            # ADVANCED DETECTION: Use ThermalAnalyzer if available
            if self.thermal_analyzer is not None:
                # Run 4-algorithm sophisticated detection
                has_anomaly, severity, anomaly_map, details = self.thermal_analyzer.detect_anomalies(thermal_data)
                
                # Classify crack type
                crack_type = self.thermal_analyzer.classify_crack_type(thermal_data, anomaly_map)
                
                print(f"  [ADVANCED] Thermal analysis:")
                print(f"    Severity: {severity}/100")
                print(f"    Detection method: {details.get('detection_method', 'unknown')}")
                print(f"    Variance: {details['variance_analysis']['anomaly']}")
                print(f"    Gradient: {details['gradient_analysis']['anomaly']}")
                print(f"    Clusters: {details['cluster_analysis']['total_clusters']}")
                print(f"    Edges: {details['edge_analysis']['strong_edges']}")
                
                # Build result with advanced metrics
                result = {
                    'min': min_temp,
                    'max': max_temp,
                    'avg': avg_temp,
                    'std': std_temp,
                    'range': temp_range,
                    'has_anomaly': has_anomaly,
                    'severity': severity,
                    'detection_method': details.get('detection_method'),
                    'crack_type': crack_type,
                    'variance_score': details['variance_analysis']['score'],
                    'gradient_score': details['gradient_analysis']['score'],
                    'cluster_score': details['cluster_analysis']['score'],
                    'edge_score': details['edge_analysis']['score'],
                }
                
                # If anomaly detected, estimate crack size using advanced anomaly map
                if has_anomaly and anomaly_map is not None:
                    # Crack size estimation using sophisticated anomaly detection
                    PIXEL_TO_CM_HORIZONTAL = 0.98
                    PIXEL_TO_CM_VERTICAL = 0.81
                    
                    # Use anomaly map from advanced detection (already identified anomalous regions)
                    anomaly_pixels = anomaly_map > 0.5  # Threshold the anomaly score map
                    
                    if np.any(anomaly_pixels):
                        y_coords, x_coords = np.where(anomaly_pixels)
                        
                        if len(x_coords) > 0:
                            min_x, max_x = x_coords.min(), x_coords.max()
                            min_y, max_y = y_coords.min(), y_coords.max()
                            
                            width_pixels = max_x - min_x + 1
                            height_pixels = max_y - min_y + 1
                            
                            width_cm = width_pixels * PIXEL_TO_CM_HORIZONTAL
                            height_cm = height_pixels * PIXEL_TO_CM_VERTICAL
                            
                            length_cm = max(width_cm, height_cm)
                            crack_width_cm = min(width_cm, height_cm)
                            
                            num_anomaly_pixels = np.sum(anomaly_pixels)
                            area_cm2 = num_anomaly_pixels * PIXEL_TO_CM_HORIZONTAL * PIXEL_TO_CM_VERTICAL
                            
                            # Depth estimation based on severity (more sophisticated)
                            if severity > 80:
                                depth_cm = 10  # Deep subsurface
                            elif severity > 60:
                                depth_cm = 7   # Medium depth
                            elif severity > 40:
                                depth_cm = 4   # Shallow subsurface
                            else:
                                depth_cm = 2   # Surface/shallow
                            
                            result['crack_size'] = {
                                'estimated_length_cm': round(length_cm, 1),
                                'estimated_width_cm': round(crack_width_cm, 1),
                                'estimated_area_cm2': round(area_cm2, 1),
                                'affected_pixels': int(num_anomaly_pixels)
                            }
                            result['estimated_depth_cm'] = depth_cm
                
                return has_anomaly, result
            
            # FALLBACK: Basic detection if ThermalAnalyzer not available
            print("  [BASIC] Using simple thermal analysis (ThermalAnalyzer not available)")
            
            # Detect anomalies (cracks often show temperature differences)
            TEMP_DIFF_THRESHOLD = 3.0  # °C
            has_anomaly = temp_range > TEMP_DIFF_THRESHOLD
            
            # Initialize result
            result = {
                'min': float(min_temp),
                'max': float(max_temp),
                'avg': float(avg_temp),
                'std': float(std_temp),
                'range': float(temp_range),
                'has_anomaly': has_anomaly
            }
            
            # If anomaly detected, estimate crack size
            if has_anomaly:
                # CRACK SIZE ESTIMATION using thermal anomaly clustering
                # MLX90640: 32x24 pixels, 55°x35° FOV
                # At 30cm distance (our optimal):
                PIXEL_TO_CM_HORIZONTAL = 0.98  # cm per pixel at 30cm
                PIXEL_TO_CM_VERTICAL = 0.81    # cm per pixel at 30cm
                
                # Find cold spots (potential cracks/voids) - use VALID pixels only
                cold_threshold = avg_temp - (2 * std_temp)
                cold_mask = valid_mask & (thermal_data < cold_threshold)
                
                # Find hot spots
                hot_threshold = avg_temp + (2 * std_temp)
                hot_mask = valid_mask & (thermal_data > hot_threshold)
                
                # Combine anomaly regions
                anomaly_mask = cold_mask | hot_mask
                
                if np.any(anomaly_mask):
                    # Get bounding box of anomaly
                    y_coords, x_coords = np.where(anomaly_mask)
                    
                    if len(x_coords) > 0:
                        min_x, max_x = x_coords.min(), x_coords.max()
                        min_y, max_y = y_coords.min(), y_coords.max()
                        
                        # Calculate dimensions
                        width_pixels = max_x - min_x + 1
                        height_pixels = max_y - min_y + 1
                        
                        # Convert to cm
                        width_cm = width_pixels * PIXEL_TO_CM_HORIZONTAL
                        height_cm = height_pixels * PIXEL_TO_CM_VERTICAL
                        
                        # Length is the longer dimension
                        length_cm = max(width_cm, height_cm)
                        crack_width_cm = min(width_cm, height_cm)
                        
                        # Area calculation
                        num_anomaly_pixels = np.sum(anomaly_mask)
                        area_cm2 = num_anomaly_pixels * PIXEL_TO_CM_HORIZONTAL * PIXEL_TO_CM_VERTICAL
                        
                        # Depth estimation from temperature deviation
                        max_deviation = max(abs(min_temp - avg_temp), abs(max_temp - avg_temp))
                        if max_deviation > 3:
                            depth_cm = 2  # Surface/shallow
                        elif max_deviation > 2:
                            depth_cm = 4  # Shallow subsurface
                        elif max_deviation > 1:
                            depth_cm = 7  # Medium depth
                        else:
                            depth_cm = 10  # Deep subsurface
                        
                        # Add crack size info to result
                        result['crack_size'] = {
                            'estimated_length_cm': round(length_cm, 1),
                            'estimated_width_cm': round(crack_width_cm, 1),
                            'estimated_area_cm2': round(area_cm2, 1),
                            'affected_pixels': int(num_anomaly_pixels)
                        }
                        result['estimated_depth_cm'] = depth_cm
                        result['anomaly_type'] = 'cold_spot' if np.sum(cold_mask) > np.sum(hot_mask) else 'hot_spot'
            
            return has_anomaly, result
            
        except Exception as e:
            print(f" Thermal analysis failed: {e}")
            return False, {}
    
    def scan_position(self, position, distance):
        """Perform complete scan at current position
        
        Uses Camera + Thermal for crack detection with size measurements
        """
        log_to_scan_monitor(f"SCANNING POSITION ({position[0]}, {position[1]})", "POSITION")
        log_to_scan_monitor(f"  Distance: {distance:.1f}cm", "DISTANCE")
        
        print(f"\n{'='*60}")
        print(f" SCANNING POSITION {position}")
        print(f" Distance from wall: {distance:.1f}cm")
        print(f"{'='*60}")
        
        # Capture image
        image_file = self.capture_image(position)
        if image_file:
            log_to_scan_monitor(f"  📷 Image captured", "CAMERA")
            print(f" Image captured: {os.path.basename(image_file)}")
        
        # Capture thermal
        thermal_data = self.capture_thermal()
        thermal_info = {}
        thermal_anomaly = False
        
        if thermal_data is not None:
            thermal_anomaly, thermal_info = self.analyze_thermal(thermal_data)
            
            # Log thermal basic stats
            log_to_scan_monitor(
                f"  🌡️  Thermal: avg={thermal_info.get('avg', 0):.1f}°C range={thermal_info.get('range', 0):.1f}°C",
                "THERMAL"
            )
            
            print(f"  Thermal: {thermal_info.get('avg', 0):.1f}°C (range: {thermal_info.get('range', 0):.1f}°C)")
            
            # Log ADVANCED detection results if available
            if 'severity' in thermal_info:
                log_to_scan_monitor(
                    f"  [ADVANCED] Severity: {thermal_info['severity']}/100",
                    "THERMAL"
                )
                log_to_scan_monitor(
                    f"  [ADVANCED] Detection: {thermal_info.get('detection_method', 'N/A')}",
                    "THERMAL"
                )
            
            if thermal_anomaly:
                log_to_scan_monitor("  ⚠️  Thermal anomaly detected!", "WARNING")
                print("  ⚠️ Thermal anomaly detected!")
                
                # Display crack size if available
                if 'crack_size' in thermal_info:
                    crack_size = thermal_info['crack_size']
                    log_to_scan_monitor(
                        f"     Length: {crack_size['estimated_length_cm']}cm × Width: {crack_size['estimated_width_cm']}cm",
                        "THERMAL"
                    )
                    log_to_scan_monitor(
                        f"     Area: {crack_size['estimated_area_cm2']}cm²",
                        "THERMAL"
                    )
                    print(f"     Estimated length: {crack_size['estimated_length_cm']} cm")
                    print(f"     Estimated width: {crack_size['estimated_width_cm']} cm")
                    print(f"     Estimated area: {crack_size['estimated_area_cm2']} cm²")
                
                if 'estimated_depth_cm' in thermal_info:
                    log_to_scan_monitor(
                        f"     Depth: ~{thermal_info['estimated_depth_cm']}cm",
                        "THERMAL"
                    )
                    print(f"     Estimated depth: ~{thermal_info['estimated_depth_cm']} cm")
                
                if 'crack_type' in thermal_info:
                    log_to_scan_monitor(
                        f"     Type: {thermal_info['crack_type']}",
                        "THERMAL"
                    )
        
        # Analyze crack
        crack_detected = False
        edge_ratio = 0.0
        
        if image_file:
            crack_detected, edge_ratio = self.analyze_crack(image_file)
            print(f" Edge density: {edge_ratio:.4f}")
        
        # Combined detection
        is_crack = crack_detected or thermal_anomaly
        
        if is_crack:
            self.crack_count += 1
            log_to_scan_monitor(f"🚨 CRACK DETECTED! (Total: {self.crack_count})", "CRACK")
            print(f"\n🚨 CRACK DETECTED! (Total: {self.crack_count})")
            
            # Log crack details in structured format
            if 'crack_size' in thermal_info:
                cs = thermal_info['crack_size']
                log_to_scan_monitor(
                    f"     Size: {cs['estimated_length_cm']}cm × {cs['estimated_width_cm']}cm",
                    "CRACK"
                )
                if 'crack_type' in thermal_info:
                    log_to_scan_monitor(
                        f"     Type: {thermal_info['crack_type']}",
                        "CRACK"
                    )
                if 'estimated_depth_cm' in thermal_info:
                    log_to_scan_monitor(
                        f"     Depth: ~{thermal_info['estimated_depth_cm']}cm",
                        "CRACK"
                    )
            
            self.beep(0.5)

            # Move image to cracks folder and update path in result
            final_image = image_file   # default — keeps original path if rename fails
            if image_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                crack_file = f"{self.data_dir}/cracks/crack_{self.crack_count}_{timestamp}.jpg"
                try:
                    os.rename(image_file, crack_file)
                    final_image = crack_file   # Bug #4 fix: use new path
                    print(f" Saved to: {crack_file}")
                except Exception as e:
                    print(f" Could not move image: {e}")
        else:
            log_to_scan_monitor("✅ No crack detected", "SUCCESS")
            print("✅ No crack detected")
            self.beep(0.05)
            final_image = image_file

        return {
            'position':       position,
            'distance':       distance,
            'crack_detected': is_crack,
            'image_file':     final_image,   # Bug #4 fix: always valid path
            'thermal_info':   thermal_info,
            'thermal_anomaly': thermal_anomaly,
            'edge_ratio':     edge_ratio,
            'timestamp':      datetime.now().isoformat()
        }


# ========================================
# AUTONOMOUS SCANNER
# ========================================

class AutonomousWallScanner:
    """Fully autonomous wall finding and scanning system
    
    SENSOR ARCHITECTURE:
    - Camera + Thermal = Crack Detection (with size measurements)
    - Ultrasonic = Obstacle Avoidance ONLY
    """
    
    def __init__(self):
        """Initialize scanner"""
        print("\n" + "="*60)
        print(" FULLY AUTONOMOUS WALL CRACK DETECTION ROBOT v2.0")
        print(" Optimized Sensor Architecture")
        print("="*60)
        print()
        print("🎯 SENSOR ROLES:")
        print("   📷 Camera → Surface crack detection")
        print("   🌡️  Thermal → Subsurface crack detection (with size)")
        print("   📡 Ultrasonic → Obstacle avoidance ONLY")
        print()
        
        self.robot = RobotController()
        self.detector = CrackDetector()
        self.scan_results = []
        self.wall_found = False
        self.initial_wall_distance = None  # remembered from find_wall()
        
        if not self.robot.serial_port:
            raise Exception("Cannot connect to MegaPi!")
    
    def find_wall(self):
        """Rotate 360° in 4×90° steps to find the nearest wall.
        
        Uses calibrated 90° timing from wheel_calibration.json (right_90_ms).
        4×90° matches exactly what calibrate_rotation.py calibrates.
        Robot ends at 270° (3 right turns), then turns back to face wall.
        """
        log_to_scan_monitor("SEARCHING FOR WALL...", "INFO")
        log_to_scan_monitor("Rotating 360° in 4×90° steps (calibrated)", "INFO")
        print("Rotating 360 degrees (4 x 90 degree steps)...\n")

        # SAFETY: If already too close to wall, back up first
        initial_dist = self.robot.get_ultrasonic_distance()
        if initial_dist and initial_dist < MIN_WALL_DISTANCE:
            log_to_scan_monitor(f"Too close ({initial_dist:.1f}cm) - backing up first...", "WARNING")
            print(f"Too close to wall ({initial_dist:.1f}cm) — backing up...")
            self.robot.move_backward(BACKWARD_SPEED, 2000)
            time.sleep(2.5)

        min_distance = 999
        best_step    = 0
        measurements = []

        for i in range(4):
            angle = i * 90
            time.sleep(0.3)

            # Take 3 readings and use median for stability
            # Walls give consistent readings; furniture gives variable ones
            readings = []
            for _ in range(3):
                d = self.robot.get_ultrasonic_distance()
                if d and 5 <= d <= 350:
                    readings.append(d)
                time.sleep(0.15)
            
            if not readings:
                log_to_scan_monitor(f"  {angle:3d}°: No reading", "WARNING")
                print(f"  {angle:3d}: No reading")
                if i < 3:
                    self.robot.turn_right(TURN_SPEED, TURN_90_DURATION)
                    time.sleep(TURN_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
                continue

            # Use median for stability
            readings.sort()
            distance = readings[len(readings) // 2]
            
            # Calculate stability (std dev) - walls are very stable
            import statistics
            stability = statistics.stdev(readings) if len(readings) > 1 else 0

            if 40 <= distance <= 350:
                marker = " <- closest" if distance < min_distance else ""
                log_to_scan_monitor(f"  {angle:3d}°: {distance:6.1f}cm  stability={stability:.1f}{marker}", "DISTANCE")
                print(f"  {angle:3d}: {distance:6.1f}cm  stdev={stability:.1f}cm{marker}")
                measurements.append((i, angle, distance))
                if distance < min_distance:
                    min_distance = distance
                    best_step    = i
            elif distance < 40:
                log_to_scan_monitor(f"  {angle:3d}°: {distance:6.1f}cm (too close - furniture ignored)", "WARNING")
                print(f"  {angle:3d}: {distance:6.1f}cm (too close - furniture/obstacle ignored)")
            else:
                log_to_scan_monitor(f"  {angle:3d}°: {distance:6.1f}cm (out of range)", "WARNING")
                print(f"  {angle:3d}: {distance:6.1f}cm (nothing in range)")

            if i < 3:
                self.robot.turn_right(TURN_SPEED, TURN_90_DURATION)
                time.sleep(TURN_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)

        log_to_scan_monitor(f"Completed 360° scan ({len(measurements)} valid readings)", "INFO")
        print(f"\nCompleted 360 scan ({len(measurements)} readings)")

        # Robot is now at 270° (3 right turns)
        if not measurements or min_distance >= 350:
            log_to_scan_monitor("No wall detected - returning to start heading", "WARNING")
            print("No wall detected — returning to start heading")
            for _ in range(3):
                self.robot.turn_left(TURN_SPEED, TURN_LEFT_90_DURATION)
                time.sleep(TURN_LEFT_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
            log_to_scan_monitor("Returned to original heading", "INFO")
            return False

        best_angle = best_step * 90
        log_to_scan_monitor(f"✓ Wall found at {best_angle}° ({min_distance:.1f}cm)", "SUCCESS")
        print(f"Wall found at {best_angle} degrees ({min_distance:.1f}cm)")

        # Turn from 270° back to face best_angle
        current_step = 3
        delta = (best_step - current_step) % 4

        if delta == 0:
            pass  # Already facing best angle
        elif delta == 1:
            log_to_scan_monitor("Turning RIGHT 90°...", "TURN")
            self.robot.turn_right(TURN_SPEED, TURN_90_DURATION)
            time.sleep(TURN_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
        elif delta == 2:
            log_to_scan_monitor("Turning LEFT 180°...", "TURN")
            for _ in range(2):
                self.robot.turn_left(TURN_SPEED, TURN_LEFT_90_DURATION)
                time.sleep(TURN_LEFT_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
        elif delta == 3:
            log_to_scan_monitor("Turning LEFT 90°...", "TURN")
            self.robot.turn_left(TURN_SPEED, TURN_LEFT_90_DURATION)
            time.sleep(TURN_LEFT_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)

        self.wall_found = True
        self.initial_wall_distance = min_distance
        log_to_scan_monitor(f"Initial wall distance locked: {min_distance:.1f}cm", "SUCCESS")
        print(f"   Initial wall distance locked: {min_distance:.1f}cm")
        return True
    
    def lateral_step(self, direction, step_cm):
        """Move laterally along the wall by turning 90°, stepping, then turning back.
        
        Uses calibrated left/right turn durations separately.
        Moves in small chunks checking ultrasonic to prevent wall collision.
        After step, approach_wall() corrects any angular drift.
        """
        duration_ms = int(step_cm * 100)  # 30cm → 3000ms at SCAN_MOVE_SPEED=60
        
        if direction == "right":
            log_to_scan_monitor(f"  ↻ Turning RIGHT 90°...", "TURN")
            self.robot.turn_right(TURN_SPEED, TURN_90_DURATION)
            time.sleep(TURN_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
            
            log_to_scan_monitor(f"  → Moving {step_cm}cm along wall...", "MOVE")
            self._safe_lateral_move(duration_ms)
            
            log_to_scan_monitor(f"  ↺ Turning LEFT 90°...", "TURN")
            self.robot.turn_left(TURN_SPEED, TURN_LEFT_90_DURATION)
            time.sleep(TURN_LEFT_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
            
        else:  # "left"
            log_to_scan_monitor(f"  ↺ Turning LEFT 90°...", "TURN")
            self.robot.turn_left(TURN_SPEED, TURN_LEFT_90_DURATION)
            time.sleep(TURN_LEFT_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
            
            log_to_scan_monitor(f"  ← Moving {step_cm}cm along wall...", "MOVE")
            self._safe_lateral_move(duration_ms)
            
            log_to_scan_monitor(f"  ↻ Turning RIGHT 90°...", "TURN")
            self.robot.turn_right(TURN_SPEED, TURN_90_DURATION)
            time.sleep(TURN_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
        
        # SAFETY CHECK: correct distance after lateral step
        time.sleep(0.3)
        self.approach_wall_safe()

    def _safe_lateral_move(self, total_ms, chunk_ms=500):
        """Move forward in small chunks with ultrasonic collision detection.
        Stops immediately if robot gets too close to wall during lateral move.
        """
        elapsed = 0
        while elapsed < total_ms:
            # Check distance BEFORE each chunk
            d = self.robot.get_ultrasonic_distance()
            if d is not None and d < 20.0:  # Emergency stop at 20cm
                log_to_scan_monitor(
                    f"  COLLISION RISK! Distance={d:.1f}cm - stopping lateral move",
                    "ERROR"
                )
                self.robot.stop()
                time.sleep(0.5)
                # Back up a little
                self.robot.move_backward(BACKWARD_SPEED, 1000)
                time.sleep(1.5)
                return
            
            # Move one chunk
            move_time = min(chunk_ms, total_ms - elapsed)
            self.robot.move_forward(SCAN_MOVE_SPEED, move_time)
            time.sleep(move_time / 1000 + 0.1)
            elapsed += move_time
    
    def approach_wall_safe(self):
        """Like approach_wall() but NEVER drives forward if within safe range.
        Only corrects if too far. Backs up if too close.
        This prevents wall collision from diagonal drift.
        """
        max_attempts = 5
        for _ in range(max_attempts):
            d = self.robot.get_ultrasonic_distance()
            if d is None:
                break
            
            if d < MIN_WALL_DISTANCE:
                # Too close - back up
                backup_ms = int((MIN_WALL_DISTANCE - d + 3) * 100)
                log_to_scan_monitor(f"  Too close ({d:.1f}cm) - backing up...", "WARNING")
                self.robot.move_backward(BACKWARD_SPEED, backup_ms)
                time.sleep(backup_ms / 1000 + 0.5)
            elif d > MAX_WALL_DISTANCE:
                # Too far - move forward
                fwd_ms = int((d - OPTIMAL_WALL_DISTANCE) * 80)
                fwd_ms = min(fwd_ms, 1000)
                log_to_scan_monitor(f"  Too far ({d:.1f}cm) - moving forward...", "INFO")
                self.robot.move_forward(FORWARD_SPEED, fwd_ms)
                time.sleep(fwd_ms / 1000 + 0.5)
            else:
                # Within safe range - stop
                log_to_scan_monitor(f"  Distance OK: {d:.1f}cm", "INFO")
                break
        """Fine-tune robot angle to face wall exactly perpendicular.
        
        Uses ultrasonic: minimum distance reading = facing wall directly.
        Tries small left/right nudges to find the minimum distance angle.
        """
        if not self.initial_wall_distance:
            return
            
        # Get baseline distance
        d_center = self.robot.get_ultrasonic_distance()
        if d_center is None:
            return
            
        log_to_scan_monitor(f"  Aligning perpendicular (baseline: {d_center:.1f}cm)...", "INFO")
        
        # Try nudge right - if distance decreases, we were angled left
        nudge_ms = 100
        self.robot.turn_right(TURN_SPEED, nudge_ms)
        time.sleep(nudge_ms / 1000 + 0.3)
        d_right = self.robot.get_ultrasonic_distance()
        
        # Try nudge left from center
        self.robot.turn_left(TURN_SPEED, nudge_ms)  # back to center
        time.sleep(nudge_ms / 1000 + 0.2)
        self.robot.turn_left(TURN_SPEED, nudge_ms)  # nudge left
        time.sleep(nudge_ms / 1000 + 0.3)
        d_left = self.robot.get_ultrasonic_distance()
        
        # Return to center
        self.robot.turn_right(TURN_SPEED, nudge_ms)
        time.sleep(nudge_ms / 1000 + 0.2)
        
        if d_right is None or d_left is None:
            return
            
        # Pick direction that gives SMALLER distance (more perpendicular)
        if d_right < d_center and d_right < d_left:
            # Turn right was better
            self.robot.turn_right(TURN_SPEED, nudge_ms)
            time.sleep(nudge_ms / 1000 + 0.3)
            log_to_scan_monitor(f"  Nudged RIGHT (d_right={d_right:.1f} < d_center={d_center:.1f})", "INFO")
        elif d_left < d_center and d_left < d_right:
            # Turn left was better
            self.robot.turn_left(TURN_SPEED, nudge_ms)
            time.sleep(nudge_ms / 1000 + 0.3)
            log_to_scan_monitor(f"  Nudged LEFT (d_left={d_left:.1f} < d_center={d_center:.1f})", "INFO")
        else:
            log_to_scan_monitor(f"  Already perpendicular!", "SUCCESS")
        """Use ultrasonic distance to confirm robot is facing the wall.
        
        After any turn sequence, the robot may be slightly off-angle.
        This method does small correction turns until the distance reading
        stabilizes — meaning the robot is perpendicular to the wall.
        
        Uses the principle: distance reading is MINIMUM when facing wall directly.
        """
        if not self.initial_wall_distance:
            return
        
        best_dist = None
        best_found = False
        
        for attempt in range(6):
            d = self.robot.get_ultrasonic_distance()
            if d is None:
                continue
            
            error = d - self.initial_wall_distance
            
            # Within 5cm tolerance = good enough
            if abs(error) <= 5.0:
                best_found = True
                log_to_scan_monitor(f"  Wall aligned: {d:.1f}cm ✓", "SUCCESS")
                break
            
            # Too far - small turn to find wall better
            # Try nudging left then right to find minimum distance
            if best_dist is None or d < best_dist:
                best_dist = d
            
            # Nudge slightly
            nudge_ms = 150
            if attempt % 2 == 0:
                self.robot.turn_left(TURN_SPEED, nudge_ms)
            else:
                self.robot.turn_right(TURN_SPEED, nudge_ms)
            time.sleep(nudge_ms / 1000 + 0.3)
        
        if not best_found:
            # Fall back to approach_wall to correct distance
            self.approach_wall()
    
    def capture_floor_features(self):
        """Capture floor image and extract features for rotation tracking"""
        if not CAMERA_AVAILABLE or self.camera is None:
            return None
        
        try:
            # Capture image
            frame = self.camera.capture_array()
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # Detect keypoints and compute descriptors using ORB
            orb = cv2.ORB_create(nfeatures=500)
            keypoints, descriptors = orb.detectAndCompute(gray, None)
            
            if descriptors is None or len(keypoints) < 10:
                return None
            
            return {
                'image': gray,
                'keypoints': keypoints,
                'descriptors': descriptors
            }
            
        except Exception as e:
            print(f"     Feature capture failed: {e}")
            return None
    
    def measure_rotation_angle(self, before_features):
        """Measure actual rotation angle by comparing floor features"""
        if not CAMERA_AVAILABLE or before_features is None:
            return None
        
        try:
            # Capture current image
            after = self.capture_floor_features()
            
            if after is None:
                return None
            
            # Match features between before and after
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(before_features['descriptors'], after['descriptors'])
            
            if len(matches) < 10:
                print(f"    ? Too few matches ({len(matches)}), cannot measure angle")
                return None
            
            # Sort matches by distance (best matches first)
            matches = sorted(matches, key=lambda x: x.distance)
            good_matches = matches[:50]  # Use top 50 matches
            
            # Get matched keypoint coordinates
            pts_before = np.float32([before_features['keypoints'][m.queryIdx].pt for m in good_matches])
            pts_after = np.float32([after['keypoints'][m.trainIdx].pt for m in good_matches])
            
            # Calculate transformation matrix
            M, mask = cv2.estimateAffinePartial2D(pts_before, pts_after)
            
            if M is None:
                return None
            
            # Extract rotation angle from transformation matrix
            # M = [[cos(), -sin(), tx],
            #      [sin(),  cos(), ty]]
            angle_rad = np.arctan2(M[1, 0], M[0, 0])
            angle_deg = np.degrees(angle_rad)
            
            # Normalize to 0-360 deg
            if angle_deg < 0:
                angle_deg += 360
            
            return abs(angle_deg)
            
        except Exception as e:
            print(f"     Angle measurement failed: {e}")
            return None
    
    def verify_real_wall(self):
        """Verify surface is a real wall using available sensors.
        
        Tests:
        - TEST 1: Ultrasonic stability (3 readings, std < 3cm)
        - TEST 2: AI vision (disabled — always 0)
        - TEST 3: Thermal uniformity (std < 3°C and range < 10°C)
        
        FIXED: Camera-disabled case no longer inflates max_score.
        If AI vision is disabled (returns 0.0), its 2 points are excluded
        from both score AND max_score so confidence is not penalized.
        """
        print("   Verifying surface...")

        verification_score = 0
        max_score = 0
        distance_mean = 0.0

        # TEST 1: Ultrasonic stability
        max_score += 1
        distances = []
        for _ in range(3):
            d = self.robot.get_ultrasonic_distance()
            if d:
                distances.append(d)
            time.sleep(0.2)

        if len(distances) >= 2:
            distance_std  = float(np.std(distances))
            distance_mean = float(np.mean(distances))
            if distance_std < 3.0:
                verification_score += 1
                print(f"   Distance stable: {distance_mean:.1f}cm")

        # TEST 2: AI vision — only count toward score if it actually works
        if CAMERA_AVAILABLE:
            conf = self.ai_detect_wall_surface()
            if conf >= 0.7:
                # Vision is active and confident — count it
                max_score += 2
                verification_score += 2
                print(f"   Vision: {conf*100:.0f}% wall confidence")
            else:
                # Vision disabled/stub — SKIP entirely (don't inflate max_score)
                print(f"   Vision: stub/disabled — skipping (not counted)")

        # TEST 3: Thermal uniformity — relaxed thresholds for Philippine climate
        if THERMAL_AVAILABLE and self.detector.thermal is not None:
            max_score += 1
            try:
                frame = [0] * 768
                self.detector.thermal.getFrame(frame)
                arr = np.array(frame).reshape(24, 32)
                valid = arr[(arr > 5) & (arr < 80)]
                if len(valid) > 100:
                    std_t   = float(np.std(valid))
                    range_t = float(np.max(valid) - np.min(valid))
                    if std_t < 3.0 and range_t < 10.0:
                        verification_score += 1
                        print(f"   Thermal uniform: std={std_t:.1f}C range={range_t:.1f}C")
                    else:
                        print(f"   Thermal variable: std={std_t:.1f}C range={range_t:.1f}C")
            except Exception as e:
                print(f"   Thermal check failed: {e}")

        confidence = (verification_score / max_score * 100) if max_score > 0 else 0
        print(f"   Score: {verification_score}/{max_score} ({confidence:.0f}%)")

        if confidence >= 33:
            print("   WALL CONFIRMED")
            return True
        else:
            print("   NOT A WALL")
            return False
    
    def ai_detect_wall_surface(self):
        """AI-powered computer vision to detect real wall vs cardboard"""
        # DISABLED - camera not working properly
        return 0.0  # Returns 0 so it never auto-passes verify_real_wall()
    
    def approach_wall(self):
        """Move to optimal distance from wall"""
        log_to_scan_monitor("APPROACHING WALL...", "INFO")
        log_to_scan_monitor(f"Target: {OPTIMAL_WALL_DISTANCE:.1f}cm", "INFO")
        print("\n APPROACHING WALL TO OPTIMAL DISTANCE...")
        print(f"Target: {OPTIMAL_WALL_DISTANCE:.1f}cm\n")
        
        max_attempts = 15
        attempts = 0
        
        while attempts < max_attempts:
            distance = self.robot.get_ultrasonic_distance()
            
            if distance is None:
                log_to_scan_monitor("No distance reading, retrying...", "WARNING")
                print(" No distance reading, retrying...")
                attempts += 1
                time.sleep(0.5)
                continue
            
            log_to_scan_monitor(f"  Distance: {distance:.1f}cm", "DISTANCE")
            print(f"  Attempt {attempts+1}: {distance:.1f}cm")
            
            # Check if we're in acceptable range
            if MIN_WALL_DISTANCE <= distance <= MAX_WALL_DISTANCE:
                log_to_scan_monitor(f"✓ OPTIMAL DISTANCE! ({distance:.1f}cm)", "SUCCESS")
                print(f"\n[OK] Optimal distance reached: {distance:.1f}cm")
                return True
            
            # Move forward or backward
            if distance > MAX_WALL_DISTANCE:
                move_cm = min((distance - OPTIMAL_WALL_DISTANCE) / 2, 10)
                log_to_scan_monitor(f"  → Moving forward {move_cm:.1f}cm...", "MOVE")
                print(f"  -> Moving forward {move_cm:.1f}cm...")
                duration = int(move_cm * 100)
                if not self.robot.move_forward_safe(FORWARD_SPEED, duration):
                    log_to_scan_monitor("Robot stuck! Cannot approach wall", "ERROR")
                    print("  [X] Robot stuck! Cannot approach wall.")
                    return False
                # Bug fix: move_forward_safe already sleeps internally — no extra sleep needed

            elif distance < MIN_WALL_DISTANCE:
                move_cm = min((OPTIMAL_WALL_DISTANCE - distance) / 2, 10)
                log_to_scan_monitor(f"  ← Moving backward {move_cm:.1f}cm...", "MOVE")
                print(f"   Moving backward {move_cm:.1f}cm...")
                duration = int(move_cm * 100)
                self.robot.move_backward(BACKWARD_SPEED, duration)
                time.sleep(duration / 1000 + 0.5)
            
            attempts += 1
        
        log_to_scan_monitor("Could not reach optimal distance, proceeding anyway...", "WARNING")
        print("\n Could not reach optimal distance, proceeding anyway...")
        return False
    
    def scan_wall_horizontal(self, scan_width_cm=150, step_cm=SCAN_STEP_CM):
        """Scan wall horizontally (left to right)"""
        print(f"\n SCANNING WALL HORIZONTALLY")
        print(f"Width: {scan_width_cm}cm, Step: {step_cm}cm")
        print(f"{'='*60}\n")
        
        num_steps = int(scan_width_cm / step_cm)
        
        for step in range(num_steps + 1):
            # Get distance
            distance = self.robot.get_ultrasonic_distance()
            if distance is None:
                distance = 0.0
            
            # Scan position
            position = (step, 0)
            result = self.detector.scan_position(position, distance)
            self.scan_results.append(result)
            
            # Move to next position (if not last)
            if step < num_steps:
                print(f"\n-> Moving right {step_cm}cm...")
                # CRITICAL FIX: use lateral_step() — turns 90°, moves, turns back
                self.lateral_step("right", step_cm)
    
    def scan_wall_grid(self, width_cm=150, height_cm=100, step_cm=SCAN_STEP_CM):
        """Scan wall in a boustrophedon (snake) grid pattern.

        Even rows → left to right.
        Odd rows  → right to left (Bug #3 fix: col order is reversed).
        Row transition: turn 90° toward wall, step up, turn 90° back to face wall.
        """
        log_to_scan_monitor("STARTING GRID SCAN", "INFO")
        log_to_scan_monitor(f"Area: {width_cm}×{height_cm}cm | Step: {step_cm}cm", "INFO")
        
        print(f"\n📋 SCANNING WALL IN GRID PATTERN")
        print(f"   Area: {width_cm}×{height_cm}cm  |  Step: {step_cm}cm")
        print(f"{'='*60}\n")

        cols = int(width_cm / step_cm) + 1
        rows = int(height_cm / step_cm) + 1
        total_positions = cols * rows

        log_to_scan_monitor(f"Grid: {cols} cols × {rows} rows = {total_positions} positions", "INFO")
        print(f"   Grid: {cols} cols × {rows} rows = {total_positions} positions\n")
        print("   Press Ctrl+C to stop anytime\n")

        position_count = 0

        for row in range(rows):
            # Bug #3 fix: reverse column order on odd rows so robot physically
            # scans in the direction it's already moving (right→left).
            col_range = range(cols) if row % 2 == 0 else range(cols - 1, -1, -1)

            for col in col_range:
                position_count += 1
                position = (col, row)

                log_to_scan_monitor(f"Position {position_count}/{total_positions}: ({col}, {row})", "POSITION")
                print(f"\n📍 Position {position_count}/{total_positions}: col={col} row={row}")

                # Check distance, adjust if needed
                distance = self.robot.get_ultrasonic_distance() or 0.0

                # ── WALL IDENTITY CHECK ────────────────────────────────────
                # If we have a locked initial wall distance, verify current surface
                # is still the same wall (within ±50cm). If too different, it's
                # a different object — skip scanning this position.
                if self.initial_wall_distance and distance:
                    dist_delta = abs(distance - self.initial_wall_distance)
                    if dist_delta > 50:
                        log_to_scan_monitor(
                            f"⚠️  DIFFERENT SURFACE! Expected ~{self.initial_wall_distance:.1f}cm, got {distance:.1f}cm - skipping",
                            "WARNING"
                        )
                        print(f"   ⚠️  DIFFERENT SURFACE detected! Expected ~{self.initial_wall_distance:.1f}cm, got {distance:.1f}cm — skipping position")
                        # Record as skipped but don't scan
                        self.scan_results.append({
                            'position': position,
                            'distance': distance,
                            'crack_detected': False,
                            'skipped': True,
                            'skip_reason': 'wrong_surface',
                            'timestamp': '',
                        })
                        continue  # move to next column without scanning

                if distance and (distance > MAX_WALL_DISTANCE or distance < MIN_WALL_DISTANCE):
                    log_to_scan_monitor(f"Distance {distance:.1f}cm out of range - adjusting...", "WARNING")
                    print(f"   Distance {distance:.1f}cm out of range — adjusting...")
                    self.approach_wall()
                    distance = self.robot.get_ultrasonic_distance() or distance
                # ── SCAN ──────────────────────────────────────────────────
                result = self.detector.scan_position(position, distance)
                self.scan_results.append(result)

                # ── MOVE ALONG ROW ─────────────────────────────────────────
                # Not the last column in this row
                is_last_col = (col == cols - 1) if row % 2 == 0 else (col == 0)
                if not is_last_col:
                    direction = "right" if row % 2 == 0 else "left"
                    log_to_scan_monitor(f"→ Moving {direction} {step_cm}cm...", "MOVE")
                    print(f"   → Moving {direction} {step_cm}cm...")
                    # CRITICAL FIX: use lateral_step() — turns 90°, moves, turns back
                    # Previously called move_forward() directly which drove INTO the wall!
                    self.lateral_step(direction, step_cm)

                    # ── OBSTACLE CHECK after lateral move ─────────────────
                    if self.initial_wall_distance:
                        d_now = self.robot.get_ultrasonic_distance()
                        if d_now and abs(d_now - self.initial_wall_distance) > 40:
                            log_to_scan_monitor(
                                f"⚠️  Orientation lost! dist={d_now:.1f}cm - realigning...",
                                "WARNING"
                            )
                            self.approach_wall_safe()

            # ── MOVE TO NEXT ROW ───────────────────────────────────────────
            if row < rows - 1:
                log_to_scan_monitor(f"↑ Moving up to row {row + 2}...", "MOVE")
                print(f"\n   ↑ Moving up to row {row + 2}...")
                duration = int(step_cm * 100)

                # Even row ends on the RIGHT → turn LEFT (face up along wall), step, turn RIGHT (face wall)
                # Odd  row ends on the LEFT  → turn RIGHT (face up along wall), step, turn LEFT (face wall)
                if row % 2 == 0:
                    log_to_scan_monitor("  Turning LEFT 90°...", "TURN")
                    self.robot.turn_left(TURN_SPEED, TURN_LEFT_90_DURATION)
                    time.sleep(TURN_LEFT_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
                    log_to_scan_monitor(f"  Moving forward {step_cm}cm...", "MOVE")
                    self.robot.move_forward(SCAN_MOVE_SPEED, duration)
                    time.sleep(duration / 1000 + 0.5)
                    log_to_scan_monitor("  Turning RIGHT 90°...", "TURN")
                    self.robot.turn_right(TURN_SPEED, TURN_90_DURATION)
                    time.sleep(TURN_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
                else:
                    log_to_scan_monitor("  Turning RIGHT 90°...", "TURN")
                    self.robot.turn_right(TURN_SPEED, TURN_90_DURATION)
                    time.sleep(TURN_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)
                    log_to_scan_monitor(f"  Moving forward {step_cm}cm...", "MOVE")
                    self.robot.move_forward(SCAN_MOVE_SPEED, duration)
                    time.sleep(duration / 1000 + 0.5)
                    log_to_scan_monitor("  Turning LEFT 90°...", "TURN")
                    self.robot.turn_left(TURN_SPEED, TURN_LEFT_90_DURATION)
                    time.sleep(TURN_LEFT_90_DURATION / 1000 + TURN_STABILIZATION_DELAY)

                # ALWAYS re-align to wall after row transition
                log_to_scan_monitor("  Re-aligning to wall after row transition...", "INFO")
                self.approach_wall_safe()
                
                # Update locked wall distance after re-alignment
                d_check = self.robot.get_ultrasonic_distance_robust(samples=3)
                if d_check and d_check < 350:
                    self.initial_wall_distance = d_check
                    log_to_scan_monitor(f"✓ Aligned! Wall distance: {d_check:.1f}cm", "SUCCESS")
                else:
                    log_to_scan_monitor("⚠️ Cannot verify alignment", "WARNING")
    
    def generate_report(self):
        """Generate and save scan report with full crack size measurements."""
        print("\n" + "="*60)
        print(" SCAN REPORT")
        print("="*60)

        crack_results = [r for r in self.scan_results if r['crack_detected']]
        print(f"Positions scanned : {len(self.scan_results)}")
        print(f"Cracks detected   : {self.detector.crack_count}")
        print()

        if crack_results:
            print("CRACKS FOUND AT:")
            for i, r in enumerate(crack_results):
                print(f"  {i+1}. Position {r['position']}  dist={r['distance']:.1f}cm")
                if r.get('thermal_info') and r['thermal_info'].get('crack_size'):
                    cs = r['thermal_info']['crack_size']
                    print(f"     Size: {cs.get('estimated_length_cm','?')}cm × "
                          f"{cs.get('estimated_width_cm','?')}cm  "
                          f"area={cs.get('estimated_area_cm2','?')}cm²  "
                          f"depth≈{r['thermal_info'].get('estimated_depth_cm','?')}cm")
        else:
            print("[OK] No cracks detected")

        # Build report filename
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H%M%S")
        building_name = 'INHS_Building'
        config_file = os.path.join(os.path.dirname(__file__), 'config_building.txt')
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            building_name = line
                            break
        except:
            pass
        building_name = building_name.replace(' ', '_')
        report_file = (f"{self.detector.data_dir}/reports/"
                       f"{building_name}_{date_str}_{time_str}.txt")

        with open(report_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("AUTONOMOUS WALL CRACK DETECTION REPORT\n")
            f.write("="*60 + "\n\n")
            f.write(f"Scan Date        : {datetime.now()}\n")
            f.write(f"Total Positions  : {len(self.scan_results)}\n")
            f.write(f"Cracks Detected  : {self.detector.crack_count}\n\n")

            f.write("="*60 + "\n")
            f.write("DETAILED RESULTS\n")
            f.write("="*60 + "\n\n")

            for i, result in enumerate(self.scan_results):
                f.write(f"Position {i+1}: {result['position']}\n")
                f.write(f"  Distance       : {result['distance']:.1f}cm\n")
                f.write(f"  Crack Detected : {'YES' if result['crack_detected'] else 'NO'}\n")
                f.write(f"  Edge Ratio     : {result.get('edge_ratio', 0):.4f}\n")

                info = result.get('thermal_info', {})
                if info:
                    f.write(f"  Thermal Avg    : {info.get('avg', 0):.1f}°C\n")
                    f.write(f"  Thermal Range  : {info.get('range', 0):.1f}°C\n")

                    # Bug #5 fix: write crack size measurements to report
                    cs = info.get('crack_size')
                    if cs:
                        f.write(f"  Crack Length   : {cs.get('estimated_length_cm', 0):.1f} cm\n")
                        f.write(f"  Crack Width    : {cs.get('estimated_width_cm',  0):.1f} cm\n")
                        f.write(f"  Crack Area     : {cs.get('estimated_area_cm2',  0):.1f} cm²\n")
                        f.write(f"  Crack Pixels   : {cs.get('affected_pixels', 0)}\n")
                    if 'estimated_depth_cm' in info:
                        f.write(f"  Estimated Depth: ~{info['estimated_depth_cm']} cm\n")
                    if 'anomaly_type' in info:
                        f.write(f"  Anomaly Type   : {info['anomaly_type']}\n")

                if result.get('image_file'):
                    f.write(f"  Image          : {result['image_file']}\n")
                f.write(f"  Time           : {result.get('timestamp', '')}\n")
                f.write("\n")

        print(f"\n✅ Report saved: {report_file}\n")
    
    def run_autonomous_scan(self, scan_mode=2, width_cm=150, height_cm=100, step_cm=SCAN_STEP_CM, skip_find_wall=False):
        """Main autonomous scanning routine."""
        try:
            # Clear previous scan log
            try:
                with open(SCAN_LOG_FILE, 'w') as f:
                    f.write(f"=== AUTONOMOUS SCAN LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            except:
                pass
            
            log_to_scan_monitor("🤖 AUTONOMOUS SCAN STARTING", "INFO")
            log_to_scan_monitor(f"Mode: {'Horizontal' if scan_mode==1 else 'Grid'}", "INFO")
            log_to_scan_monitor(f"Area: {width_cm}×{height_cm}cm | Step: {step_cm}cm", "INFO")

            if skip_find_wall:
                # Skip 360° search - scan whatever is directly in front
                log_to_scan_monitor("⚡ SKIP FIND WALL - scanning directly ahead", "INFO")
                print("⚡ Skipping wall search — scanning whatever is in front")
                dist = self.robot.get_ultrasonic_distance()
                if dist and dist < 350:
                    self.initial_wall_distance = dist
                    self.wall_found = True
                    log_to_scan_monitor(f"Current distance: {dist:.1f}cm", "DISTANCE")
            else:
                # Step 1: Wall search
                log_to_scan_monitor("", "INFO")
                log_to_scan_monitor("🔍 STEP 1: SEARCHING FOR WALL...", "INFO")
                print("🔍 SEARCHING FOR WALL...")
                wall_found = self.find_wall()
                if not wall_found:
                    log_to_scan_monitor("Wall search failed - scanning from current position", "WARNING")
                    print("   Wall search failed — scanning from current position")
                else:
                    log_to_scan_monitor("", "INFO")
                    log_to_scan_monitor("🔬 STEP 2: VERIFYING WALL...", "INFO")
                    print("\n🔬 VERIFYING WALL...")
                    if not self.verify_real_wall():
                        log_to_scan_monitor("⚠️  Surface is NOT a real wall - ABORTING SCAN!", "ERROR")
                        print("   ⚠️  Surface is NOT a real wall — aborting scan!")
                        self.robot.stop()
                        time.sleep(0.5)
                        return

            # Step 2: Approach wall if ultrasonic works
            test_dist = self.robot.get_ultrasonic_distance()
            if test_dist and test_dist < 350:
                log_to_scan_monitor("", "INFO")  # Blank line
                log_to_scan_monitor("📏 STEP 3: APPROACHING OPTIMAL DISTANCE...", "INFO")
                print("\n📏 Approaching optimal distance...")
                self.approach_wall()
            else:
                log_to_scan_monitor("Ultrasonic unavailable - maintaining current position", "WARNING")
                print("   Ultrasonic not available — maintaining current position")

            # Step 3: Scan
            log_to_scan_monitor("", "INFO")  # Blank line
            log_to_scan_monitor("📋 STEP 4: STARTING GRID SCAN...", "INFO")
            print(f"\n📋 STARTING GRID SCAN...")
            if scan_mode == 1:
                self.scan_wall_horizontal(width_cm, step_cm)
            else:
                self.scan_wall_grid(width_cm, height_cm, step_cm)

            # Step 4: Report
            log_to_scan_monitor("", "INFO")  # Blank line
            log_to_scan_monitor("📊 GENERATING REPORT...", "INFO")
            self.generate_report()
            
            log_to_scan_monitor("", "INFO")  # Blank line
            log_to_scan_monitor("✅ AUTONOMOUS SCAN COMPLETE!", "SUCCESS")
            log_to_scan_monitor(f"Total positions scanned: {len(self.scan_results)}", "SUCCESS")
            log_to_scan_monitor(f"Total cracks detected: {self.detector.crack_count}", "SUCCESS")
            print("\n✅ AUTONOMOUS SCAN COMPLETE!")

        except KeyboardInterrupt:
            log_to_scan_monitor("", "INFO")  # Blank line
            log_to_scan_monitor("⚠️  SCAN INTERRUPTED BY USER", "WARNING")
            print("\n\n⚠️  SCAN INTERRUPTED")
            if self.scan_results:
                self.generate_report()

        except Exception as e:
            log_to_scan_monitor("", "INFO")  # Blank line
            log_to_scan_monitor(f"❌ SCAN ERROR: {e}", "ERROR")
            print(f"\n[X] SCAN ERROR: {e}")
            import traceback
            traceback.print_exc()
            if self.scan_results:
                self.generate_report()

        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        print("\n Cleaning up...")
        self.robot.stop()
        self.robot.close()
        try:
            GPIO.cleanup()
        except:
            pass
        print("[OK] Cleanup complete")


# ========================================
# MAIN PROGRAM
# ========================================

def main():
    """Main entry point — supports CLI args for headless operation.

    Usage:
        python3 fully_autonomous_wall_scanner.py                  # default grid scan
        python3 fully_autonomous_wall_scanner.py --mode 1         # horizontal scan
        python3 fully_autonomous_wall_scanner.py --mode 2 --width 200 --height 120 --step 25
    """
    import argparse
    parser = argparse.ArgumentParser(description='Autonomous Wall Crack Scanner')
    parser.add_argument('--mode',   type=int, default=2,            help='1=horizontal 2=grid')
    parser.add_argument('--width',  type=int, default=150,          help='Scan width (cm)')
    parser.add_argument('--height', type=int, default=100,          help='Scan height (cm)')
    parser.add_argument('--step',   type=int, default=SCAN_STEP_CM, help='Step size (cm)')
    parser.add_argument('--skip-find-wall', action='store_true',    help='Skip 360 search - scan whatever is directly in front')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("   FULLY AUTONOMOUS WALL CRACK DETECTION ROBOT v2.0")
    print("   Camera + Thermal = Crack Detection")
    print("   Ultrasonic       = Obstacle Avoidance ONLY")
    print("="*70)
    print()
    print(f"System Status:")
    print(f"  Camera  : {'[OK]' if CAMERA_AVAILABLE else '[X] NOT AVAILABLE'}")
    print(f"  Thermal : {'[OK]' if THERMAL_AVAILABLE else '[X] NOT AVAILABLE'}")
    print(f"  Mode    : {'Horizontal' if args.mode == 1 else 'Grid'}")
    print(f"  Area    : {args.width}×{args.height}cm  Step: {args.step}cm")
    print()

    try:
        scanner = AutonomousWallScanner()
        scanner.run_autonomous_scan(
            scan_mode=args.mode,
            width_cm=args.width,
            height_cm=args.height,
            step_cm=args.step,
            skip_find_wall=args.skip_find_wall,
        )
    except KeyboardInterrupt:
        print("\n  Program interrupted")
    except Exception as e:
        print(f"\n[X] Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure GPIO and serial are always released
        try:
            if 'scanner' in dir():
                scanner.cleanup()
            else:
                GPIO.cleanup()
        except:
            pass


if __name__ == "__main__":
    main()














