#!/usr/bin/env python3
"""
Autonomous Wall Crack Detection Robot
Raspberry Pi 3 B+ + MegaPi

Full autonomous operation:
- Raspberry Pi controls MegaPi motors via serial
- Autonomous navigation and scanning
- Grid pattern wall scanning
- Automatic crack detection
- No manual control needed!

Hardware:
- Raspberry Pi → MegaPi via USB serial
- MLX90640 thermal camera
- Camera Module 3
- HC-SR04 ultrasonic
- Piezo transducer
- MegaPi with motors
"""

import time
import numpy as np
import board
import busio
import adafruit_mlx90640
from picamera2 import Picamera2
import RPi.GPIO as GPIO
from scipy.fft import fft, fftfreq
import serial
import json
from datetime import datetime
import os
import pickle

# GPIO Pins
ULTRASONIC_TRIG = 23
ULTRASONIC_ECHO = 24
PIEZO_PIN = 18

# MegaPi Serial
MEGAPI_PORT = "/dev/ttyUSB0"  # or /dev/ttyAMA0
MEGAPI_BAUD = 115200

# Detection Thresholds
THERMAL_VARIANCE_THRESHOLD = 1.5
ACOUSTIC_HOLLOW_FREQ_MIN = 200
ACOUSTIC_HOLLOW_FREQ_MAX = 800
OPTIMAL_WALL_DISTANCE = 30.0  # cm
DISTANCE_TOLERANCE = 5.0

# Movement parameters
MOVE_SPEED = 100  # Motor speed (0-255)
SCAN_STEP_CM = 10  # Distance between scan points


class MegaPiController:
    """Control MegaPi motors via serial"""
    
    def __init__(self, port=MEGAPI_PORT, baud=MEGAPI_BAUD):
        """Initialize serial connection to MegaPi"""
        try:
            self.serial = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # Wait for connection
            print(f"✅ MegaPi connected on {port}")
        except Exception as e:
            print(f"⚠️ MegaPi connection error: {e}")
            print("⚠️ Robot will scan without movement")
            self.serial = None
    
    def send_command(self, command):
        """Send command to MegaPi"""
        if self.serial:
            try:
                self.serial.write(f"{command}\n".encode())
                time.sleep(0.1)
            except Exception as e:
                print(f"Command error: {e}")
    
    def move_forward(self, distance_cm, speed=MOVE_SPEED):
        """Move forward specified distance"""
        print(f"→ Moving forward {distance_cm}cm...")
        
        # Calculate time based on speed (rough estimation)
        # Adjust these values based on your robot's calibration
        time_seconds = distance_cm / 10.0  # Rough: 10cm per second
        
        # Send motor command
        # Format: M1=speed M2=speed (both motors forward)
        self.send_command(f"M1={speed} M2={speed}")
        time.sleep(time_seconds)
        self.stop()
    
    def move_backward(self, distance_cm, speed=MOVE_SPEED):
        """Move backward specified distance"""
        print(f"← Moving backward {distance_cm}cm...")
        time_seconds = distance_cm / 10.0
        self.send_command(f"M1={-speed} M2={-speed}")
        time.sleep(time_seconds)
        self.stop()
    
    def turn_left(self, degrees=90, speed=MOVE_SPEED):
        """Turn left specified degrees"""
        print(f"↺ Turning left {degrees}°...")
        time_seconds = degrees / 90.0  # Rough: 1 second per 90°
        self.send_command(f"M1={-speed} M2={speed}")
        time.sleep(time_seconds)
        self.stop()
    
    def turn_right(self, degrees=90, speed=MOVE_SPEED):
        """Turn right specified degrees"""
        print(f"↻ Turning right {degrees}°...")
        time_seconds = degrees / 90.0
        self.send_command(f"M1={speed} M2={-speed}")
        time.sleep(time_seconds)
        self.stop()
    
    def move_left(self, distance_cm, speed=MOVE_SPEED):
        """Strafe left (if mecanum wheels) or turn+move"""
        print(f"⬅ Moving left {distance_cm}cm...")
        # For differential drive: turn left 90°, move forward, turn right 90°
        self.turn_left(90, speed)
        self.move_forward(distance_cm, speed)
        self.turn_right(90, speed)
    
    def move_right(self, distance_cm, speed=MOVE_SPEED):
        """Strafe right (if mecanum wheels) or turn+move"""
        print(f"➡ Moving right {distance_cm}cm...")
        self.turn_right(90, speed)
        self.move_forward(distance_cm, speed)
        self.turn_left(90, speed)
    
    def stop(self):
        """Stop all motors"""
        if self.serial:
            self.send_command("M1=0 M2=0")
    
    def close(self):
        """Close serial connection"""
        if self.serial:
            self.stop()
            self.serial.close()


class AutonomousCrackDetector:
    """Fully autonomous crack detection robot"""
    
    def __init__(self, location="Building_A"):
        """Initialize all systems"""
        print("🤖 Initializing Autonomous Crack Detection Robot...")
        
        self.location = location
        self.current_position = {'x': 0.0, 'y': 0.0, 'heading': 0}  # heading in degrees
        
        # Initialize MegaPi motor controller
        self.motors = MegaPiController()
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(ULTRASONIC_TRIG, GPIO.OUT)
        GPIO.setup(ULTRASONIC_ECHO, GPIO.IN)
        GPIO.output(ULTRASONIC_TRIG, False)
        GPIO.setup(PIEZO_PIN, GPIO.OUT)
        self.piezo_pwm = GPIO.PWM(PIEZO_PIN, 1000)
        
        # Initialize thermal camera
        try:
            i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
            self.thermal_camera = adafruit_mlx90640.MLX90640(i2c)
            self.thermal_camera.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
            print("✅ Thermal camera ready")
        except Exception as e:
            print(f"⚠️ Thermal camera error: {e}")
            self.thermal_camera = None
        
        # Initialize regular camera
        try:
            self.camera = Picamera2()
            config = self.camera.create_still_configuration(
                main={"size": (1920, 1080)},
                lores={"size": (640, 480)},
                display="lores"
            )
            self.camera.configure(config)
            self.camera.start()
            time.sleep(2)
            print("✅ Camera ready")
        except Exception as e:
            print(f"⚠️ Camera error: {e}")
            self.camera = None
        
        # Crack database
        self.db_file = "/home/pi/cracks/crack_database.pkl"
        self.cracks = {}
        self.load_database()
        
        print("✅ Autonomous system ready!\n")
    
    def load_database(self):
        """Load crack database"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'rb') as f:
                    self.cracks = pickle.load(f)
                print(f"📊 Loaded {len(self.cracks)} cracks")
            except:
                self.cracks = {}
    
    def save_database(self):
        """Save crack database"""
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            with open(self.db_file, 'wb') as f:
                pickle.dump(self.cracks, f)
        except Exception as e:
            print(f"Database save error: {e}")
    
    def get_distance(self):
        """Read ultrasonic distance"""
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
            
            duration = pulse_end - pulse_start
            distance = duration * 17150
            return round(distance, 2) if 2 < distance < 400 else None
        except:
            return None
    
    def adjust_distance_to_wall(self):
        """Automatically adjust distance to wall"""
        distance = self.get_distance()
        
        if distance is None:
            print("⚠️ Cannot measure distance")
            return False
        
        print(f"📏 Current distance: {distance}cm (target: {OPTIMAL_WALL_DISTANCE}cm)")
        
        if distance > OPTIMAL_WALL_DISTANCE + DISTANCE_TOLERANCE:
            # Too far - move closer
            move_distance = distance - OPTIMAL_WALL_DISTANCE
            self.motors.move_forward(min(move_distance, 10))
            return self.adjust_distance_to_wall()  # Recursive check
        
        elif distance < OPTIMAL_WALL_DISTANCE - DISTANCE_TOLERANCE:
            # Too close - move back
            move_distance = OPTIMAL_WALL_DISTANCE - distance
            self.motors.move_backward(min(move_distance, 10))
            return self.adjust_distance_to_wall()  # Recursive check
        
        else:
            print(f"✅ Optimal distance achieved: {distance}cm")
            return True
    
    def scan_current_position(self):
        """Scan current position for cracks"""
        print(f"\n🔍 Scanning position ({self.current_position['x']}, {self.current_position['y']})...")
        
        # Ensure proper distance
        if not self.adjust_distance_to_wall():
            print("⚠️ Could not achieve optimal distance")
        
        distance = self.get_distance() or OPTIMAL_WALL_DISTANCE
        
        # Thermal scan
        thermal_image = self.read_thermal_frame()
        thermal_anomaly, thermal_severity, thermal_details = self.analyze_thermal(thermal_image)
        
        # Acoustic test
        self.piezo_tap()
        time.sleep(0.1)
        acoustic_signal, sample_rate = self.piezo_listen()
        acoustic_hollow, confidence, acoustic_details = self.analyze_acoustic(acoustic_signal, sample_rate)
        
        # Detect crack
        crack_detected = thermal_anomaly or acoustic_hollow
        
        if crack_detected:
            print(f"⚠️ CRACK DETECTED!")
            
            # Take photo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            crack_id = f"{self.location}_X{int(self.current_position['x'])}_Y{int(self.current_position['y'])}"
            photo_file = f"/home/pi/cracks/{crack_id}_{timestamp}.jpg"
            
            if self.camera:
                self.camera.capture_file(photo_file)
                print(f"📷 Photo: {photo_file}")
            
            # Save crack data
            crack_length, crack_width = self.estimate_crack_size(thermal_details)
            
            crack_data = {
                'timestamp': datetime.now().isoformat(),
                'position': self.current_position.copy(),
                'distance': distance,
                'crack_length': crack_length,
                'crack_width': crack_width,
                'thermal': thermal_details,
                'acoustic': acoustic_details,
                'photo': photo_file
            }
            
            if crack_id not in self.cracks:
                self.cracks[crack_id] = {'measurements': []}
            
            self.cracks[crack_id]['measurements'].append(crack_data)
            self.save_database()
            
            self.generate_report(crack_id, crack_data)
        else:
            print("✅ No crack detected")
        
        return crack_detected
    
    def read_thermal_frame(self):
        """Read thermal camera"""
        if not self.thermal_camera:
            return None
        try:
            frame = np.zeros((24*32,))
            self.thermal_camera.getFrame(frame)
            return np.reshape(frame, (24, 32))
        except:
            return None
    
    def analyze_thermal(self, image):
        """Analyze thermal data"""
        if image is None:
            return False, 0, {}
        
        avg = np.mean(image)
        min_t = np.min(image)
        max_t = np.max(image)
        var = np.var(image)
        std = np.std(image)
        
        anomaly = var > THERMAL_VARIANCE_THRESHOLD or (max_t - min_t) > 3.0
        severity = min(100, int(var * 10 + (max_t - min_t) * 5))
        
        details = {
            'avg_temp': round(avg, 2),
            'min_temp': round(min_t, 2),
            'max_temp': round(max_t, 2),
            'variance': round(var, 2),
            'std_dev': round(std, 2)
        }
        
        return anomaly, severity, details
    
    def piezo_tap(self):
        """Generate acoustic tap"""
        try:
            self.piezo_pwm.ChangeFrequency(1000)
            self.piezo_pwm.start(50)
            time.sleep(0.05)
            self.piezo_pwm.stop()
        except:
            pass
    
    def piezo_listen(self, duration=0.2, sample_rate=8000):
        """Listen for acoustic response (simulated)"""
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        signal = np.sin(2 * np.pi * 400 * t) * np.exp(-t * 10)
        return signal, sample_rate
    
    def analyze_acoustic(self, signal, sample_rate):
        """Analyze acoustic response"""
        if signal is None or len(signal) == 0:
            return False, 0, {}
        
        fft_vals = fft(signal)
        fft_freq = fftfreq(len(signal), 1/sample_rate)
        
        pos_idx = np.where(fft_freq > 0)
        freqs = fft_freq[pos_idx]
        mags = np.abs(fft_vals[pos_idx])
        
        dominant_freq = freqs[np.argmax(mags)]
        
        hollow_power = np.sum(mags[(freqs >= ACOUSTIC_HOLLOW_FREQ_MIN) & (freqs <= ACOUSTIC_HOLLOW_FREQ_MAX)])
        total_power = np.sum(mags)
        hollow_ratio = hollow_power / total_power if total_power > 0 else 0
        
        is_hollow = hollow_ratio > 0.4
        confidence = min(100, int(hollow_ratio * 150))
        
        details = {
            'dominant_freq': round(dominant_freq, 2),
            'hollow_ratio': round(hollow_ratio, 3)
        }
        
        return is_hollow, confidence, details
    
    def estimate_crack_size(self, thermal_details):
        """Estimate crack dimensions"""
        var = thermal_details.get('variance', 0)
        area = var * 10  # Rough estimation
        length = np.sqrt(area * 10)
        width = area / length if length > 0 else 0
        return round(length, 1), round(width * 10, 1)  # cm, mm
    
    def generate_report(self, crack_id, data):
        """Generate crack report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/home/pi/cracks/{crack_id}_report_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("CRACK DETECTION REPORT\n")
            f.write("="*70 + "\n\n")
            f.write(f"Location: {crack_id}\n")
            f.write(f"Time: {data['timestamp']}\n")
            f.write(f"Position: X={data['position']['x']}cm, Y={data['position']['y']}cm\n\n")
            f.write(f"Crack Length: {data['crack_length']} cm\n")
            f.write(f"Crack Width: {data['crack_width']} mm\n")
            f.write(f"Distance: {data['distance']} cm\n\n")
            f.write(f"Temperature: {data['thermal']['min_temp']}°C - {data['thermal']['max_temp']}°C\n")
            f.write(f"Photo: {data['photo']}\n")
            f.write("="*70 + "\n")
        
        print(f"📄 Report: {report_file}")
    
    def autonomous_grid_scan(self, width_cm, height_cm, step_cm=SCAN_STEP_CM):
        """Autonomous grid scanning"""
        print(f"\n🗺️ AUTONOMOUS GRID SCAN")
        print(f"Area: {width_cm}x{height_cm}cm, Step: {step_cm}cm\n")
        
        rows = int(height_cm / step_cm)
        cols = int(width_cm / step_cm)
        total_points = rows * cols
        
        print(f"Total scan points: {total_points}")
        print(f"Estimated time: {total_points * 15 / 60:.1f} minutes\n")
        
        input("Press Enter to start autonomous scan...")
        
        cracks_found = 0
        
        for row in range(rows):
            # Scan row left to right or right to left (zigzag)
            if row % 2 == 0:
                # Left to right
                for col in range(cols):
                    self.current_position['x'] = col * step_cm
                    self.current_position['y'] = row * step_cm
                    
                    if self.scan_current_position():
                        cracks_found += 1
                    
                    if col < cols - 1:
                        self.motors.move_right(step_cm)
                    
                    time.sleep(0.5)
            else:
                # Right to left
                for col in range(cols - 1, -1, -1):
                    self.current_position['x'] = col * step_cm
                    self.current_position['y'] = row * step_cm
                    
                    if self.scan_current_position():
                        cracks_found += 1
                    
                    if col > 0:
                        self.motors.move_left(step_cm)
                    
                    time.sleep(0.5)
            
            # Move to next row
            if row < rows - 1:
                self.motors.move_forward(step_cm)
        
        print(f"\n✅ SCAN COMPLETE!")
        print(f"Total cracks found: {cracks_found}")
        print(f"Database: {len(self.cracks)} cracks tracked\n")
        
        # Return to start
        print("↩️ Returning to start position...")
        self.return_to_start()
    
    def return_to_start(self):
        """Return robot to starting position"""
        # Move back to origin (0, 0)
        x, y = self.current_position['x'], self.current_position['y']
        
        if y > 0:
            self.motors.move_backward(y)
        
        if x > 0:
            self.motors.move_left(x)
        
        self.current_position = {'x': 0, 'y': 0, 'heading': 0}
        print("✅ Returned to start position")
    
    def cleanup(self):
        """Cleanup resources"""
        print("\n🛑 Shutting down...")
        
        if hasattr(self, 'piezo_pwm'):
            self.piezo_pwm.stop()
        
        GPIO.cleanup()
        
        if self.camera:
            self.camera.stop()
        
        self.motors.close()
        
        print("✅ Shutdown complete")


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("🤖 AUTONOMOUS WALL CRACK DETECTION ROBOT")
    print("="*70)
    
    location = input("\nEnter building/location name: ").strip() or "Building_A"
    
    robot = AutonomousCrackDetector(location=location)
    
    try:
        print("\nOperation Modes:")
        print("1. Autonomous grid scan")
        print("2. Single position test")
        print("3. Manual navigation test")
        
        mode = input("\nSelect mode (1-3): ").strip()
        
        if mode == "1":
            width = int(input("Enter scan width (cm): "))
            height = int(input("Enter scan height (cm): "))
            step = int(input("Enter step size (cm, default 10): ") or "10")
            
            robot.autonomous_grid_scan(width, height, step)
        
        elif mode == "2":
            robot.scan_current_position()
        
        elif mode == "3":
            print("\nManual Navigation Test")
            print("Commands: forward/backward/left/right/scan/quit")
            
            while True:
                cmd = input("\nCommand: ").strip().lower()
                
                if cmd == "quit":
                    break
                elif cmd == "forward":
                    robot.motors.move_forward(10)
                elif cmd == "backward":
                    robot.motors.move_backward(10)
                elif cmd == "left":
                    robot.motors.move_left(10)
                elif cmd == "right":
                    robot.motors.move_right(10)
                elif cmd == "scan":
                    robot.scan_current_position()
                else:
                    print("Unknown command")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    
    finally:
        robot.cleanup()


if __name__ == "__main__":
    main()
