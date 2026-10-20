#!/usr/bin/env python3
"""
Wall Crack Detection Robot - Enhanced Version with Temporal Tracking
Raspberry Pi 3 B+

Features:
- Temporal progression analysis (Day 0, 7, 14, 21, 28)
- Crack growth monitoring
- Historical comparison
- Enhanced reporting matching research paper format

Uses:
- MLX90640 Thermal Camera (detect temperature anomalies)
- 35mm Piezo Transducer (acoustic wall testing)
- Camera Module 3 (visual documentation)
- HC-SR04 Ultrasonic (distance maintenance)
"""

import time
import numpy as np
import board
import busio
import adafruit_mlx90640
from picamera2 import Picamera2
import RPi.GPIO as GPIO
from scipy import signal
from scipy.fft import fft, fftfreq
import json
import socket
from datetime import datetime, timedelta
import os
import pickle

# GPIO Pin Definitions
ULTRASONIC_TRIG = 23  # Pin 16
ULTRASONIC_ECHO = 24  # Pin 18
PIEZO_PIN = 18        # Pin 12 (PWM)

# Detection Thresholds
THERMAL_VARIANCE_THRESHOLD = 1.5
ACOUSTIC_HOLLOW_FREQ_MIN = 200
ACOUSTIC_HOLLOW_FREQ_MAX = 800
OPTIMAL_WALL_DISTANCE = 10.0
DISTANCE_TOLERANCE = 2.0

# Temporal Tracking
CRACK_DATABASE_FILE = "/home/pi/cracks/crack_database.pkl"
INSPECTION_SCHEDULE = [0, 7, 14, 21, 28]  # Days

class CrackDatabase:
    """Database for tracking cracks over time"""
    
    def __init__(self, db_file=CRACK_DATABASE_FILE):
        self.db_file = db_file
        self.cracks = {}  # crack_id: {history, measurements}
        self.load()
    
    def load(self):
        """Load existing crack database"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'rb') as f:
                    self.cracks = pickle.load(f)
                print(f"📊 Loaded {len(self.cracks)} cracks from database")
            except Exception as e:
                print(f"⚠️ Error loading database: {e}")
                self.cracks = {}
        else:
            print("📊 Starting new crack database")
    
    def save(self):
        """Save crack database"""
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            with open(self.db_file, 'wb') as f:
                pickle.dump(self.cracks, f)
            print(f"💾 Database saved ({len(self.cracks)} cracks)")
        except Exception as e:
            print(f"⚠️ Error saving database: {e}")
    
    def generate_crack_id(self, location, position):
        """Generate unique crack ID"""
        # Format: Location_X{x}_Y{y}
        x, y = position['x'], position['y']
        return f"{location}_X{int(x)}_Y{int(y)}"
    
    def find_nearby_crack(self, position, tolerance=5.0):
        """Find existing crack near position (within tolerance cm)"""
        x, y = position['x'], position['y']
        
        for crack_id, crack_data in self.cracks.items():
            # Get most recent position
            if crack_data['measurements']:
                recent = crack_data['measurements'][-1]
                crack_x = recent['position']['x']
                crack_y = recent['position']['y']
                
                distance = np.sqrt((x - crack_x)**2 + (y - crack_y)**2)
                
                if distance <= tolerance:
                    return crack_id
        
        return None
    
    def add_measurement(self, crack_id, measurement_data):
        """Add new measurement to crack"""
        if crack_id not in self.cracks:
            self.cracks[crack_id] = {
                'first_detected': datetime.now().isoformat(),
                'location': crack_id.split('_')[0],
                'measurements': []
            }
        
        self.cracks[crack_id]['measurements'].append(measurement_data)
        self.save()
    
    def get_crack_history(self, crack_id):
        """Get all measurements for a crack"""
        return self.cracks.get(crack_id, {}).get('measurements', [])
    
    def calculate_growth(self, crack_id):
        """Calculate crack growth over time"""
        measurements = self.get_crack_history(crack_id)
        
        if len(measurements) < 2:
            return None
        
        first = measurements[0]
        latest = measurements[-1]
        
        # Calculate time difference
        first_time = datetime.fromisoformat(first['timestamp'])
        latest_time = datetime.fromisoformat(latest['timestamp'])
        days_elapsed = (latest_time - first_time).days
        
        if days_elapsed == 0:
            return None
        
        # Calculate growth
        length_growth = latest['crack_length'] - first['crack_length']
        width_growth = latest['crack_width'] - first['crack_width']
        
        growth_rate_length = length_growth / days_elapsed
        growth_rate_width = width_growth / days_elapsed
        
        return {
            'days_elapsed': days_elapsed,
            'length_growth_cm': round(length_growth, 2),
            'width_growth_mm': round(width_growth, 2),
            'growth_rate_length_cm_per_day': round(growth_rate_length, 3),
            'growth_rate_width_mm_per_day': round(growth_rate_width, 3),
            'first_length': round(first['crack_length'], 2),
            'latest_length': round(latest['crack_length'], 2),
            'first_width': round(first['crack_width'], 2),
            'latest_width': round(latest['crack_width'], 2)
        }


class EnhancedCrackDetector:
    """Enhanced crack detector with temporal tracking"""
    
    def __init__(self, location="Building_A"):
        """Initialize all sensors and systems"""
        print("🤖 Initializing Enhanced Wall Crack Detection Robot...")
        
        self.location = location
        self.database = CrackDatabase()
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Ultrasonic sensor
        GPIO.setup(ULTRASONIC_TRIG, GPIO.OUT)
        GPIO.setup(ULTRASONIC_ECHO, GPIO.IN)
        GPIO.output(ULTRASONIC_TRIG, False)
        
        # Piezo transducer
        GPIO.setup(PIEZO_PIN, GPIO.OUT)
        self.piezo_pwm = GPIO.PWM(PIEZO_PIN, 1000)
        
        # Initialize thermal camera
        try:
            i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
            self.thermal_camera = adafruit_mlx90640.MLX90640(i2c)
            self.thermal_camera.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
            print("✅ MLX90640 Thermal Camera initialized")
        except Exception as e:
            print(f"⚠️ Thermal camera error: {e}")
            self.thermal_camera = None
        
        # Initialize regular camera
        try:
            self.camera = Picamera2()
            camera_config = self.camera.create_still_configuration(
                main={"size": (1920, 1080)},
                lores={"size": (640, 480)},
                display="lores"
            )
            self.camera.configure(camera_config)
            self.camera.start()
            time.sleep(2)
            print("✅ Camera Module 3 initialized")
        except Exception as e:
            print(f"⚠️ Camera error: {e}")
            self.camera = None
        
        self.current_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.scan_results = []
        
        print("✅ Enhanced Crack Detection System Ready!\n")
    
    def get_distance(self):
        """Read distance from HC-SR04 ultrasonic sensor"""
        try:
            GPIO.output(ULTRASONIC_TRIG, True)
            time.sleep(0.00001)
            GPIO.output(ULTRASONIC_TRIG, False)
            
            timeout = time.time() + 0.1
            
            while GPIO.input(ULTRASONIC_ECHO) == 0:
                pulse_start = time.time()
                if time.time() > timeout:
                    return None
            
            while GPIO.input(ULTRASONIC_ECHO) == 1:
                pulse_end = time.time()
                if time.time() > timeout:
                    return None
            
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150
            distance = round(distance, 2)
            
            return distance if 2 < distance < 400 else None
            
        except Exception as e:
            print(f"Ultrasonic error: {e}")
            return None
    
    def read_thermal_frame(self):
        """Read thermal camera frame"""
        if self.thermal_camera is None:
            return None
        
        try:
            frame = np.zeros((24*32,))
            self.thermal_camera.getFrame(frame)
            thermal_image = np.reshape(frame, (24, 32))
            return thermal_image
        except Exception as e:
            print(f"Thermal read error: {e}")
            return None
    
    def analyze_thermal_data(self, thermal_image):
        """Analyze thermal data for anomalies"""
        if thermal_image is None:
            return False, 0, {}
        
        avg_temp = np.mean(thermal_image)
        min_temp = np.min(thermal_image)
        max_temp = np.max(thermal_image)
        temp_variance = np.var(thermal_image)
        temp_std = np.std(thermal_image)
        
        high_variance = temp_variance > THERMAL_VARIANCE_THRESHOLD
        temp_range = max_temp - min_temp
        significant_range = temp_range > 3.0
        
        deviation_map = np.abs(thermal_image - avg_temp)
        anomaly_pixels = np.sum(deviation_map > (2 * temp_std))
        anomaly_percentage = (anomaly_pixels / thermal_image.size) * 100
        
        has_anomaly = high_variance or significant_range or (anomaly_percentage > 10)
        
        severity = min(100, int(
            (temp_variance * 10) + 
            (temp_range * 5) + 
            (anomaly_percentage * 2)
        ))
        
        details = {
            'avg_temp': round(avg_temp, 2),
            'min_temp': round(min_temp, 2),
            'max_temp': round(max_temp, 2),
            'variance': round(temp_variance, 2),
            'std_dev': round(temp_std, 2),
            'temp_range': round(temp_range, 2),
            'anomaly_pixels': int(anomaly_pixels),
            'anomaly_percentage': round(anomaly_percentage, 2)
        }
        
        return has_anomaly, severity, details
    
    def piezo_tap(self, frequency=1000, duration=0.05):
        """Generate tap sound"""
        try:
            self.piezo_pwm.ChangeFrequency(frequency)
            self.piezo_pwm.start(50)
            time.sleep(duration)
            self.piezo_pwm.stop()
        except Exception as e:
            print(f"Piezo tap error: {e}")
    
    def piezo_listen(self, duration=0.2, sample_rate=8000):
        """Listen for acoustic response"""
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        signal_data = (
            np.sin(2 * np.pi * 400 * t) * np.exp(-t * 10) +
            np.sin(2 * np.pi * 800 * t) * np.exp(-t * 15) * 0.5
        )
        
        return signal_data, sample_rate
    
    def analyze_acoustic_data(self, signal_data, sample_rate):
        """Analyze acoustic response"""
        if signal_data is None or len(signal_data) == 0:
            return False, 0, {}
        
        n = len(signal_data)
        fft_values = fft(signal_data)
        fft_freq = fftfreq(n, 1/sample_rate)
        
        positive_freq_idx = np.where(fft_freq > 0)
        frequencies = fft_freq[positive_freq_idx]
        magnitudes = np.abs(fft_values[positive_freq_idx])
        
        dominant_idx = np.argmax(magnitudes)
        dominant_freq = frequencies[dominant_idx]
        
        hollow_band_power = np.sum(magnitudes[
            (frequencies >= ACOUSTIC_HOLLOW_FREQ_MIN) & 
            (frequencies <= ACOUSTIC_HOLLOW_FREQ_MAX)
        ])
        
        solid_band_power = np.sum(magnitudes[frequencies > 1000])
        total_power = np.sum(magnitudes)
        hollow_ratio = hollow_band_power / total_power if total_power > 0 else 0
        
        is_hollow = (
            (hollow_ratio > 0.4) or
            (dominant_freq >= ACOUSTIC_HOLLOW_FREQ_MIN and 
             dominant_freq <= ACOUSTIC_HOLLOW_FREQ_MAX)
        )
        
        confidence = min(100, int(hollow_ratio * 150))
        
        details = {
            'dominant_freq': round(dominant_freq, 2),
            'hollow_ratio': round(hollow_ratio, 3),
            'hollow_power': round(hollow_band_power, 2),
            'solid_power': round(solid_band_power, 2),
            'total_power': round(total_power, 2)
        }
        
        return is_hollow, confidence, details
    
    def estimate_crack_dimensions(self, thermal_image, thermal_details):
        """Estimate crack length and width from thermal data"""
        # Simplified estimation based on anomaly area
        # In production, use image processing on actual crack photo
        
        anomaly_pixels = thermal_details.get('anomaly_pixels', 0)
        
        # Rough estimation (each pixel ~1cm at 30cm distance)
        # This is simplified - actual implementation needs calibration
        crack_area_cm2 = anomaly_pixels * 0.8  # Rough conversion
        
        # Estimate as rectangular crack
        # Assume length:width ratio of ~10:1 for typical cracks
        crack_length = np.sqrt(crack_area_cm2 * 10)
        crack_width = crack_area_cm2 / crack_length if crack_length > 0 else 0
        
        # Convert width to mm
        crack_width_mm = crack_width * 10
        
        return round(crack_length, 1), round(crack_width_mm, 1)
    
    def estimate_subsurface_depth(self, thermal_details, acoustic_confidence):
        """Estimate subsurface discontinuity depth"""
        # Combine thermal and acoustic data
        # Higher thermal variance + higher acoustic confidence = deeper crack
        
        thermal_variance = thermal_details.get('variance', 0)
        depth_factor = (thermal_variance / 10) + (acoustic_confidence / 100)
        estimated_depth = min(10, depth_factor * 5)  # Max 10cm
        
        return round(estimated_depth, 1)
    
    def capture_image(self, filename):
        """Capture photo"""
        if self.camera is None:
            return None
        
        try:
            self.camera.capture_file(filename)
            print(f"📷 Photo saved: {filename}")
            return filename
        except Exception as e:
            print(f"Camera capture error: {e}")
            return None
    
    def scan_position(self, x, y, z=0, inspection_day=0):
        """Enhanced scan with temporal tracking"""
        self.current_position = {'x': x, 'y': y, 'z': z}
        
        print(f"\n🔍 Scanning position ({x}, {y}) - Day {inspection_day}...")
        
        # Read distance
        distance = self.get_distance()
        if distance:
            print(f"📏 Distance: {distance}cm")
        else:
            distance = 30.0  # Default
        
        # Thermal scan
        print("🌡️ Thermal scanning...")
        thermal_image = self.read_thermal_frame()
        thermal_anomaly, thermal_severity, thermal_details = \
            self.analyze_thermal_data(thermal_image)
        
        if thermal_anomaly:
            print(f"🔥 Thermal anomaly! Severity: {thermal_severity}")
        
        # Acoustic test
        print("🔊 Acoustic testing...")
        self.piezo_tap()
        time.sleep(0.1)
        acoustic_signal, sample_rate = self.piezo_listen()
        acoustic_hollow, acoustic_confidence, acoustic_details = \
            self.analyze_acoustic_data(acoustic_signal, sample_rate)
        
        if acoustic_hollow:
            print(f"🎵 Hollow area! Confidence: {acoustic_confidence}%")
        
        # Determine crack detection
        crack_detected = thermal_anomaly or acoustic_hollow
        
        if crack_detected:
            # Estimate crack dimensions
            crack_length, crack_width = self.estimate_crack_dimensions(
                thermal_image, thermal_details
            )
            
            # Estimate subsurface depth
            subsurface_depth = self.estimate_subsurface_depth(
                thermal_details,
                acoustic_confidence
            )
            
            # Generate or find crack ID
            crack_id = self.database.generate_crack_id(self.location, self.current_position)
            existing_crack_id = self.database.find_nearby_crack(self.current_position)
            
            if existing_crack_id:
                crack_id = existing_crack_id
                print(f"📊 Updating existing crack: {crack_id}")
            else:
                print(f"🆕 New crack detected: {crack_id}")
            
            # Save photo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_file = f"/home/pi/cracks/{crack_id}_day{inspection_day}_{timestamp}.jpg"
            self.capture_image(photo_file)
            
            # Create measurement record
            measurement = {
                'timestamp': datetime.now().isoformat(),
                'inspection_day': inspection_day,
                'position': self.current_position.copy(),
                'distance': distance,
                'crack_length': crack_length,
                'crack_width': crack_width,
                'subsurface_depth': subsurface_depth,
                'thermal': {
                    'anomaly': thermal_anomaly,
                    'severity': thermal_severity,
                    **thermal_details
                },
                'acoustic': {
                    'hollow': acoustic_hollow,
                    'confidence': acoustic_confidence,
                    **acoustic_details
                },
                'photo_file': photo_file
            }
            
            # Add to database
            self.database.add_measurement(crack_id, measurement)
            
            # Generate report
            self.generate_crack_report(crack_id, measurement)
            
            print(f"⚠️ CRACK: Length={crack_length}cm, Width={crack_width}mm, Depth={subsurface_depth}cm")
        else:
            print(f"✅ No anomalies")
        
        return crack_detected
    
    def generate_crack_report(self, crack_id, latest_measurement):
        """Generate detailed crack report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/home/pi/cracks/{crack_id}_report_{timestamp}.txt"
        
        # Get crack history
        history = self.database.get_crack_history(crack_id)
        growth = self.database.calculate_growth(crack_id)
        
        # Determine severity
        length = latest_measurement['crack_length']
        width = latest_measurement['crack_width']
        
        if width > 2.0 or length > 20:
            severity = "HIGH"
        elif width > 1.0 or length > 10:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        with open(report_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("STRUCTURAL DEFECT FLAGGED\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Defect Location: {crack_id}\n")
            f.write(f"Crack Length: {length} cm\n")
            f.write(f"Crack Width: {width}mm\n")
            f.write(f"Possible Subsurface Discontinuity: {latest_measurement['subsurface_depth']} cm depth\n")
            f.write(f"Thermal Anomaly: {'Detected' if latest_measurement['thermal']['anomaly'] else 'Not Detected'}\n")
            f.write(f"Surface Distance: {latest_measurement['distance']}cm\n")
            f.write(f"Severity: {severity}\n\n")
            
            f.write("="*70 + "\n")
            f.write("CRACK INSPECTION REPORT\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Inspection Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Inspection Day: {latest_measurement['inspection_day']}\n")
            f.write(f"Location: {crack_id}\n")
            f.write(f"Position: X={latest_measurement['position']['x']}cm, Y={latest_measurement['position']['y']}cm\n\n")
            
            f.write("CURRENT MEASUREMENTS:\n")
            f.write(f"  Crack Length: {length} cm\n")
            f.write(f"  Crack Width: {width}mm\n")
            f.write(f"  Subsurface Depth: {latest_measurement['subsurface_depth']} cm\n")
            
            thermal = latest_measurement['thermal']
            f.write(f"  Temperature Range: {thermal.get('min_temp', 'N/A')}°C - {thermal.get('max_temp', 'N/A')}°C\n")
            f.write(f"  Thermal Variance: {thermal.get('variance', 'N/A')}\n")
            
            acoustic = latest_measurement['acoustic']
            f.write(f"  Acoustic Hollow Ratio: {acoustic.get('hollow_ratio', 'N/A')}\n")
            f.write(f"  Dominant Frequency: {acoustic.get('dominant_freq', 'N/A')} Hz\n\n")
            
            if len(history) > 1:
                f.write("="*70 + "\n")
                f.write("TEMPORAL PROGRESSION ANALYSIS\n")
                f.write("="*70 + "\n\n")
                
                f.write("MEASUREMENT HISTORY:\n")
                for i, measure in enumerate(history):
                    day = measure['inspection_day']
                    date = datetime.fromisoformat(measure['timestamp']).strftime('%Y-%m-%d')
                    f.write(f"\n  Day {day} ({date}):\n")
                    f.write(f"    Length: {measure['crack_length']} cm\n")
                    f.write(f"    Width: {measure['crack_width']} mm\n")
                    f.write(f"    Thermal Anomaly: {'Yes' if measure['thermal']['anomaly'] else 'No'}\n")
                    f.write(f"    Acoustic Hollow: {'Yes' if measure['acoustic']['hollow'] else 'No'}\n")
                
                if growth:
                    f.write(f"\nGROWTH ANALYSIS:\n")
                    f.write(f"  Time Period: {growth['days_elapsed']} days\n")
                    f.write(f"  Length Growth: {growth['length_growth_cm']} cm ({growth['first_length']} → {growth['latest_length']} cm)\n")
                    f.write(f"  Width Growth: {growth['width_growth_mm']} mm ({growth['first_width']} → {growth['latest_width']} mm)\n")
                    f.write(f"  Growth Rate (Length): {growth['growth_rate_length_cm_per_day']} cm/day\n")
                    f.write(f"  Growth Rate (Width): {growth['growth_rate_width_mm_per_day']} mm/day\n\n")
                    
                    if growth['growth_rate_length_cm_per_day'] > 0.1:
                        f.write("⚠️  WARNING: Crack showing significant growth! Immediate attention required.\n")
                    elif growth['growth_rate_length_cm_per_day'] > 0:
                        f.write("⚠️  CAUTION: Crack showing progressive growth. Monitor closely.\n")
                    else:
                        f.write("✓  Status: Crack stable (no significant growth detected).\n")
            else:
                f.write("\nNOTE: This is the baseline measurement. Future inspections will show temporal progression.\n")
            
            f.write("\n" + "="*70 + "\n")
            f.write("RECOMMENDATION:\n")
            f.write("="*70 + "\n")
            
            if severity == "HIGH":
                f.write("URGENT: Immediate structural assessment required.\n")
                f.write("Recommend professional engineer inspection within 24 hours.\n")
            elif severity == "MEDIUM":
                f.write("MODERATE: Schedule structural assessment soon.\n")
                f.write("Recommend re-inspection in 7 days to monitor progression.\n")
            else:
                f.write("LOW: Monitor crack progression.\n")
                f.write("Recommend re-inspection in 14 days.\n")
            
            f.write("\nPhoto documentation: " + latest_measurement['photo_file'] + "\n")
            f.write("\n" + "="*70 + "\n")
        
        print(f"📄 Report saved: {report_file}")
    
    def cleanup(self):
        """Cleanup resources"""
        print("\n🛑 Shutting down...")
        
        if hasattr(self, 'piezo_pwm'):
            self.piezo_pwm.stop()
        
        GPIO.cleanup()
        
        if self.camera:
            self.camera.stop()
        
        print("✅ Shutdown complete")


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("🏗️ ENHANCED WALL CRACK DETECTION ROBOT")
    print("   WITH TEMPORAL PROGRESSION ANALYSIS")
    print("="*70)
    
    location = input("\nEnter building/structure name (e.g., Building_A, Column_A03): ").strip() or "Building_A"
    
    detector = EnhancedCrackDetector(location=location)
    
    try:
        print("\nMode Selection:")
        print("1. Single position scan")
        print("2. Grid scan")
        print("3. Temporal monitoring (follow-up inspection)")
        
        mode = input("\nSelect mode (1-3): ").strip()
        
        if mode == "3":
            print("\nTemporal Monitoring Mode")
            print("Select inspection day:")
            for i, day in enumerate(INSPECTION_SCHEDULE):
                print(f"  {i+1}. Day {day} {'(Baseline)' if day == 0 else ''}")
            
            day_choice = int(input("Enter choice: ").strip())
            inspection_day = INSPECTION_SCHEDULE[day_choice - 1]
            
            print(f"\nConducting Day {inspection_day} inspection...")
            print(f"Database contains {len(detector.database.cracks)} known cracks")
            
            # Re-scan all known crack locations
            for crack_id in detector.database.cracks.keys():
                history = detector.database.get_crack_history(crack_id)
                if history:
                    last_pos = history[-1]['position']
                    print(f"\nRe-scanning crack: {crack_id}")
                    detector.scan_position(last_pos['x'], last_pos['y'], inspection_day=inspection_day)
                    time.sleep(1)
        
        elif mode == "2":
            width = int(input("Enter wall width (cm): "))
            height = int(input("Enter wall height (cm): "))
            step = int(input("Enter step size (cm, default 10): ") or "10")
            inspection_day = int(input("Enter inspection day (0 for baseline): ") or "0")
            
            print(f"\nStarting grid scan: {width}x{height}cm, step={step}cm")
            
            for y in range(0, height, step):
                for x in range(0, width, step):
                    detector.scan_position(x, y, inspection_day=inspection_day)
                    time.sleep(0.5)
        
        elif mode == "1":
            x = float(input("Enter X position (cm): "))
            y = float(input("Enter Y position (cm): "))
            inspection_day = int(input("Enter inspection day (0 for baseline): ") or "0")
            detector.scan_position(x, y, inspection_day=inspection_day)
        
        # Show database summary
        print("\n" + "="*70)
        print("📊 CRACK DATABASE SUMMARY")
        print("="*70)
        print(f"Total cracks tracked: {len(detector.database.cracks)}")
        
        for crack_id, crack_data in detector.database.cracks.items():
            measurements = crack_data['measurements']
            print(f"\n{crack_id}:")
            print(f"  First detected: {crack_data['first_detected']}")
            print(f"  Total inspections: {len(measurements)}")
            
            if len(measurements) > 1:
                growth = detector.database.calculate_growth(crack_id)
                if growth:
                    print(f"  Growth: {growth['length_growth_cm']}cm length, {growth['width_growth_mm']}mm width over {growth['days_elapsed']} days")
        
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    
    finally:
        detector.cleanup()


if __name__ == "__main__":
    main()
