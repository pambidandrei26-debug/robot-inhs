#!/usr/bin/env python3
"""
Wall Crack Detection Robot - Main Controller
Raspberry Pi 3 B+

Uses:
- MLX90640 Thermal Camera (detect temperature anomalies)
- 35mm Piezo Transducer (acoustic wall testing)
- Camera Module 3 (visual documentation)
- HC-SR04 Ultrasonic (distance maintenance)

Detects structural cracks using thermal imaging + acoustic analysis
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
from datetime import datetime

# GPIO Pin Definitions
ULTRASONIC_TRIG = 23  # Pin 16
ULTRASONIC_ECHO = 24  # Pin 18
PIEZO_PIN = 18        # Pin 12 (PWM)

# Detection Thresholds
THERMAL_VARIANCE_THRESHOLD = 1.5  # Temperature variance indicating crack
ACOUSTIC_HOLLOW_FREQ_MIN = 200    # Hz - hollow sound range
ACOUSTIC_HOLLOW_FREQ_MAX = 800    # Hz
OPTIMAL_WALL_DISTANCE = 10.0      # cm from wall
DISTANCE_TOLERANCE = 2.0          # cm

class CrackDetector:
    """Main crack detection controller"""
    
    def __init__(self):
        """Initialize all sensors and systems"""
        print("🤖 Initializing Wall Crack Detection Robot...")
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Ultrasonic sensor
        GPIO.setup(ULTRASONIC_TRIG, GPIO.OUT)
        GPIO.setup(ULTRASONIC_ECHO, GPIO.IN)
        GPIO.output(ULTRASONIC_TRIG, False)
        
        # Piezo transducer (PWM output)
        GPIO.setup(PIEZO_PIN, GPIO.OUT)
        self.piezo_pwm = GPIO.PWM(PIEZO_PIN, 1000)  # 1kHz base frequency
        
        # Initialize I2C for thermal camera
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
            time.sleep(2)  # Warm-up
            print("✅ Camera Module 3 initialized")
        except Exception as e:
            print(f"⚠️ Camera error: {e}")
            self.camera = None
        
        # Scan data storage
        self.current_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.scan_results = []
        self.crack_count = 0
        
        # Orange Pi connection (data logger)
        self.orangepi_ip = "192.168.1.100"  # Update with actual IP
        self.orangepi_port = 5000
        
        print("✅ Crack Detection System Ready!\n")
    
    def get_distance(self):
        """Read distance from HC-SR04 ultrasonic sensor"""
        try:
            # Send trigger pulse
            GPIO.output(ULTRASONIC_TRIG, True)
            time.sleep(0.00001)
            GPIO.output(ULTRASONIC_TRIG, False)
            
            # Measure echo
            timeout = time.time() + 0.1  # 100ms timeout
            
            while GPIO.input(ULTRASONIC_ECHO) == 0:
                pulse_start = time.time()
                if time.time() > timeout:
                    return None
            
            while GPIO.input(ULTRASONIC_ECHO) == 1:
                pulse_end = time.time()
                if time.time() > timeout:
                    return None
            
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150  # Speed of sound / 2
            distance = round(distance, 2)
            
            return distance if 2 < distance < 400 else None
            
        except Exception as e:
            print(f"Ultrasonic error: {e}")
            return None
    
    def maintain_distance(self, target_distance=OPTIMAL_WALL_DISTANCE):
        """Maintain optimal distance from wall"""
        distance = self.get_distance()
        
        if distance is None:
            return False
        
        # Check if within tolerance
        if abs(distance - target_distance) <= DISTANCE_TOLERANCE:
            return True
        else:
            print(f"⚠️ Distance: {distance}cm (target: {target_distance}cm)")
            return False
    
    def read_thermal_frame(self):
        """Read thermal camera frame (24x32 pixels)"""
        if self.thermal_camera is None:
            return None
        
        try:
            frame = np.zeros((24*32,))
            self.thermal_camera.getFrame(frame)
            # Reshape to 2D array
            thermal_image = np.reshape(frame, (24, 32))
            return thermal_image
        except Exception as e:
            print(f"Thermal read error: {e}")
            return None
    
    def analyze_thermal_data(self, thermal_image):
        """
        Analyze thermal data for temperature anomalies
        Returns: (has_anomaly, severity, details)
        """
        if thermal_image is None:
            return False, 0, {}
        
        # Calculate statistics
        avg_temp = np.mean(thermal_image)
        min_temp = np.min(thermal_image)
        max_temp = np.max(thermal_image)
        temp_variance = np.var(thermal_image)
        temp_std = np.std(thermal_image)
        
        # Detect anomalies
        # Method 1: High variance indicates cracks
        high_variance = temp_variance > THERMAL_VARIANCE_THRESHOLD
        
        # Method 2: Significant hot/cold spots
        temp_range = max_temp - min_temp
        significant_range = temp_range > 3.0  # 3°C difference
        
        # Method 3: Detect isolated temperature regions
        # Find pixels that deviate significantly from average
        deviation_map = np.abs(thermal_image - avg_temp)
        anomaly_pixels = np.sum(deviation_map > (2 * temp_std))
        anomaly_percentage = (anomaly_pixels / thermal_image.size) * 100
        
        has_anomaly = high_variance or significant_range or (anomaly_percentage > 10)
        
        # Calculate severity (0-100)
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
        """Generate tap sound using piezo transducer"""
        try:
            self.piezo_pwm.ChangeFrequency(frequency)
            self.piezo_pwm.start(50)  # 50% duty cycle
            time.sleep(duration)
            self.piezo_pwm.stop()
        except Exception as e:
            print(f"Piezo tap error: {e}")
    
    def piezo_listen(self, duration=0.2, sample_rate=8000):
        """
        Listen for acoustic response after tap
        Note: This is a simplified version. For real acoustic analysis,
        you need an ADC module to read the piezo signal.
        
        Returns simulated acoustic data for demonstration.
        For production, connect piezo to ADC (e.g., MCP3008) to read actual signal.
        """
        # TODO: Implement actual ADC reading
        # For now, return simulated data
        
        # In production:
        # 1. Connect piezo to MCP3008 ADC
        # 2. Read analog signal during 'duration'
        # 3. Return time-series data
        
        # Simulated acoustic waveform
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        # Simulate response (mix of frequencies)
        signal_data = (
            np.sin(2 * np.pi * 400 * t) * np.exp(-t * 10) +  # Fundamental
            np.sin(2 * np.pi * 800 * t) * np.exp(-t * 15) * 0.5  # Harmonic
        )
        
        return signal_data, sample_rate
    
    def analyze_acoustic_data(self, signal_data, sample_rate):
        """
        Analyze acoustic response using FFT
        Returns: (is_hollow, confidence, details)
        """
        if signal_data is None or len(signal_data) == 0:
            return False, 0, {}
        
        # Perform FFT
        n = len(signal_data)
        fft_values = fft(signal_data)
        fft_freq = fftfreq(n, 1/sample_rate)
        
        # Only positive frequencies
        positive_freq_idx = np.where(fft_freq > 0)
        frequencies = fft_freq[positive_freq_idx]
        magnitudes = np.abs(fft_values[positive_freq_idx])
        
        # Find dominant frequency
        dominant_idx = np.argmax(magnitudes)
        dominant_freq = frequencies[dominant_idx]
        
        # Analyze frequency spectrum
        # Hollow/cracked areas: lower frequency resonance (200-800 Hz)
        # Solid areas: higher frequency response (>1000 Hz)
        
        hollow_band_power = np.sum(magnitudes[
            (frequencies >= ACOUSTIC_HOLLOW_FREQ_MIN) & 
            (frequencies <= ACOUSTIC_HOLLOW_FREQ_MAX)
        ])
        
        solid_band_power = np.sum(magnitudes[frequencies > 1000])
        
        total_power = np.sum(magnitudes)
        hollow_ratio = hollow_band_power / total_power if total_power > 0 else 0
        
        # Detect hollow area
        is_hollow = (
            (hollow_ratio > 0.4) or  # High hollow frequency content
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
    
    def capture_image(self, filename):
        """Capture photo of crack location"""
        if self.camera is None:
            return None
        
        try:
            self.camera.capture_file(filename)
            print(f"📷 Photo saved: {filename}")
            return filename
        except Exception as e:
            print(f"Camera capture error: {e}")
            return None
    
    def scan_position(self, x, y, z=0):
        """
        Scan specific wall position for cracks
        Returns: scan result dictionary
        """
        self.current_position = {'x': x, 'y': y, 'z': z}
        
        print(f"\n🔍 Scanning position ({x}, {y})...")
        
        # Step 1: Check distance to wall
        distance = self.get_distance()
        if distance is None:
            print("⚠️ Cannot read distance")
            distance = 0
        else:
            print(f"📏 Distance: {distance}cm")
        
        # Step 2: Thermal scan
        print("🌡️ Thermal scanning...")
        thermal_image = self.read_thermal_frame()
        thermal_anomaly, thermal_severity, thermal_details = \
            self.analyze_thermal_data(thermal_image)
        
        if thermal_anomaly:
            print(f"🔥 Thermal anomaly detected! Severity: {thermal_severity}")
        
        # Step 3: Acoustic test
        print("🔊 Acoustic testing...")
        self.piezo_tap()
        time.sleep(0.1)
        acoustic_signal, sample_rate = self.piezo_listen()
        acoustic_hollow, acoustic_confidence, acoustic_details = \
            self.analyze_acoustic_data(acoustic_signal, sample_rate)
        
        if acoustic_hollow:
            print(f"🎵 Hollow area detected! Confidence: {acoustic_confidence}%")
        
        # Step 4: Determine if crack detected
        crack_detected = thermal_anomaly or acoustic_hollow
        
        # Calculate overall severity
        overall_severity = max(thermal_severity, acoustic_confidence)
        
        # Step 5: If crack detected, take photo
        photo_file = None
        if crack_detected:
            self.crack_count += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_file = f"/home/pi/cracks/crack_{self.crack_count:03d}_{timestamp}.jpg"
            self.capture_image(photo_file)
            print(f"⚠️ CRACK DETECTED at ({x}, {y}) - Severity: {overall_severity}")
        else:
            print(f"✅ No anomalies at ({x}, {y})")
        
        # Compile scan result
        scan_result = {
            'timestamp': datetime.now().isoformat(),
            'position': {'x': x, 'y': y, 'z': z},
            'distance': distance,
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
            'crack_detected': crack_detected,
            'overall_severity': overall_severity,
            'photo_file': photo_file
        }
        
        # Store result
        self.scan_results.append(scan_result)
        
        # Send to Orange Pi for logging
        self.send_to_logger(scan_result)
        
        return scan_result
    
    def send_to_logger(self, data):
        """Send scan data to Orange Pi logger"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((self.orangepi_ip, self.orangepi_port))
            sock.sendall(json.dumps(data).encode('utf-8'))
            sock.close()
        except Exception as e:
            # Orange Pi not connected, save locally
            pass
    
    def scan_grid(self, width, height, step=10):
        """
        Scan wall in grid pattern
        width, height: in cm
        step: distance between scan points
        """
        print(f"\n🗺️ Starting grid scan: {width}x{height}cm, step={step}cm")
        print(f"Total positions: {(width//step) * (height//step)}\n")
        
        for y in range(0, height, step):
            for x in range(0, width, step):
                self.scan_position(x, y)
                time.sleep(0.5)  # Delay between scans
        
        print(f"\n✅ Grid scan complete!")
        print(f"Total scans: {len(self.scan_results)}")
        print(f"Cracks detected: {self.crack_count}")
        
        return self.scan_results
    
    def generate_summary(self):
        """Generate scan summary report"""
        if not self.scan_results:
            print("No scan data available")
            return
        
        print("\n" + "="*60)
        print("📊 WALL INSPECTION SUMMARY")
        print("="*60)
        
        total_scans = len(self.scan_results)
        cracks_found = sum(1 for r in self.scan_results if r['crack_detected'])
        thermal_anomalies = sum(1 for r in self.scan_results if r['thermal']['anomaly'])
        acoustic_anomalies = sum(1 for r in self.scan_results if r['acoustic']['hollow'])
        
        print(f"Total scan positions: {total_scans}")
        print(f"Cracks detected: {cracks_found}")
        print(f"Thermal anomalies: {thermal_anomalies}")
        print(f"Acoustic anomalies: {acoustic_anomalies}")
        
        if cracks_found > 0:
            print(f"\n⚠️ CRITICAL: {cracks_found} crack(s) found!")
            print("\nCrack locations:")
            for result in self.scan_results:
                if result['crack_detected']:
                    pos = result['position']
                    sev = result['overall_severity']
                    print(f"  • Position ({pos['x']}, {pos['y']}) - Severity: {sev}")
        else:
            print("\n✅ No structural issues detected")
        
        print("="*60 + "\n")
    
    def cleanup(self):
        """Cleanup GPIO and camera resources"""
        print("\n🛑 Shutting down...")
        
        if hasattr(self, 'piezo_pwm'):
            self.piezo_pwm.stop()
        
        GPIO.cleanup()
        
        if self.camera:
            self.camera.stop()
        
        print("✅ Shutdown complete")


def main():
    """Main entry point"""
    detector = CrackDetector()
    
    try:
        print("\n" + "="*60)
        print("🏗️ WALL CRACK DETECTION ROBOT")
        print("="*60)
        print("\nMode Selection:")
        print("1. Single position scan")
        print("2. Grid scan (autonomous)")
        print("3. Manual mode (scan on command)")
        
        mode = input("\nSelect mode (1-3): ").strip()
        
        if mode == "1":
            # Single position
            x = float(input("Enter X position (cm): "))
            y = float(input("Enter Y position (cm): "))
            result = detector.scan_position(x, y)
            
        elif mode == "2":
            # Grid scan
            width = int(input("Enter wall width (cm): "))
            height = int(input("Enter wall height (cm): "))
            step = int(input("Enter step size (cm, default 10): ") or "10")
            results = detector.scan_grid(width, height, step)
            
        elif mode == "3":
            # Manual mode
            print("\nManual mode - Enter 'scan' to scan current position, 'quit' to exit")
            x, y = 0, 0
            while True:
                cmd = input("\nCommand: ").strip().lower()
                if cmd == "quit":
                    break
                elif cmd == "scan":
                    detector.scan_position(x, y)
                    y += 10  # Move to next position
                else:
                    print("Unknown command")
        
        # Show summary
        detector.generate_summary()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    
    finally:
        detector.cleanup()


if __name__ == "__main__":
    main()
