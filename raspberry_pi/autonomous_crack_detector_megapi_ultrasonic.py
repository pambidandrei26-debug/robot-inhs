#!/usr/bin/env python3
"""
AUTONOMOUS WALL CRACK DETECTION ROBOT - MegaPi Ultrasonic Version
Uses ultrasonic sensor connected to MegaPi instead of Raspberry Pi GPIO
All sensor data comes via serial communication from MegaPi
"""

import serial
import time
import sys
import os
from datetime import datetime
import threading

# Sensor imports
try:
    from picamera2 import Picamera2
    import cv2
    import numpy as np
    CAMERA_AVAILABLE = True
except:
    CAMERA_AVAILABLE = False
    print("⚠ Camera not available")

try:
    import board
    import busio
    import adafruit_mlx90640
    THERMAL_AVAILABLE = True
except:
    THERMAL_AVAILABLE = False
    print("⚠ Thermal camera not available")

# Configuration
OPTIMAL_DISTANCE = 30.0  # cm from wall
DISTANCE_TOLERANCE = 5.0  # cm
MOVE_SPEED = 150
TURN_SPEED = 120
TURN_DURATION_FACTOR = 15  # Adjust based on your robot


class UltrasonicSensorMegaPi:
    """Ultrasonic Sensor via MegaPi Serial Communication"""
    def __init__(self, serial_connection):
        self.serial = serial_connection
        self.last_distance = None
        self.distance_lock = threading.Lock()
        
    def measure_distance(self):
        """Request distance measurement from MegaPi"""
        try:
            # Send command to get distance
            self.serial.write(b'G\n')
            time.sleep(0.1)  # Wait for response
            
            # Read response
            if self.serial.in_waiting:
                response = self.serial.readline().decode('utf-8').strip()
                
                # Parse response: "DISTANCE:XX.XX"
                if response.startswith('DISTANCE:'):
                    distance_str = response.split(':')[1]
                    if distance_str != 'ERROR':
                        distance = float(distance_str)
                        with self.distance_lock:
                            self.last_distance = distance
                        return distance
            
            return self.last_distance  # Return last known distance if no new reading
            
        except Exception as e:
            print(f"❌ Ultrasonic error: {e}")
            return None
    
    def enable_auto_reporting(self):
        """Enable continuous distance reporting from MegaPi"""
        try:
            self.serial.write(b'A\n')  # 'A' = Auto distance ON
            print("✅ Auto distance reporting enabled")
        except Exception as e:
            print(f"❌ Failed to enable auto reporting: {e}")
    
    def disable_auto_reporting(self):
        """Disable continuous distance reporting"""
        try:
            self.serial.write(b'Z\n')  # 'Z' = Auto distance OFF
            print("✅ Auto distance reporting disabled")
        except Exception as e:
            print(f"❌ Failed to disable auto reporting: {e}")
    
    def parse_distance_message(self, message):
        """Parse incoming distance messages in background"""
        try:
            if message.startswith('DISTANCE:'):
                distance_str = message.split(':')[1]
                if distance_str != 'ERROR':
                    distance = float(distance_str)
                    with self.distance_lock:
                        self.last_distance = distance
        except:
            pass


class RobotController:
    """Motor control via MegaPi with ultrasonic sensor support"""
    def __init__(self, port='/dev/ttyUSB1'):
        try:
            self.serial = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)
            
            # Read startup message
            while self.serial.in_waiting:
                msg = self.serial.readline().decode('utf-8').strip()
                print(f"MegaPi: {msg}")
            
            print("✅ Connected to MegaPi with Ultrasonic")
            
        except Exception as e:
            print(f"❌ Serial error: {e}")
            self.serial = None
    
    def send_command(self, command):
        """Send command to MegaPi"""
        if self.serial:
            try:
                self.serial.write(f"{command}\n".encode('utf-8'))
                time.sleep(0.05)
                
                # Read response
                if self.serial.in_waiting:
                    response = self.serial.readline().decode('utf-8').strip()
                    return response
                    
            except Exception as e:
                print(f"❌ Command error: {e}")
        return None
    
    def read_responses(self):
        """Read all pending responses from MegaPi"""
        responses = []
        while self.serial and self.serial.in_waiting:
            try:
                response = self.serial.readline().decode('utf-8').strip()
                if response:
                    responses.append(response)
            except:
                break
        return responses
    
    def move_forward(self, speed=MOVE_SPEED, duration=0):
        """Move forward"""
        self.send_command(f"F,{speed},{duration}")
    
    def move_backward(self, speed=MOVE_SPEED, duration=0):
        """Move backward"""
        self.send_command(f"B,{speed},{duration}")
    
    def turn_left(self, speed=TURN_SPEED, duration=0):
        """Turn left"""
        self.send_command(f"L,{speed},{duration}")
    
    def turn_right(self, speed=TURN_SPEED, duration=0):
        """Turn right"""
        self.send_command(f"R,{speed},{duration}")
    
    def stop(self):
        """Stop all motors"""
        self.send_command("S")


class CrackDetectionSystem:
    """Main system integrating all sensors and motors"""
    
    def __init__(self):
        print("🤖 Initializing Autonomous Crack Detection Robot (MegaPi Ultrasonic)")
        
        # Initialize robot controller
        self.robot = RobotController('/dev/ttyUSB1')
        
        # Initialize ultrasonic sensor via MegaPi
        if self.robot.serial:
            self.ultrasonic = UltrasonicSensorMegaPi(self.robot.serial)
            print("✅ Ultrasonic via MegaPi initialized")
        else:
            print("❌ Cannot initialize ultrasonic - no serial connection")
            sys.exit(1)
        
        # Initialize camera
        if CAMERA_AVAILABLE:
            try:
                self.camera = Picamera2()
                config = self.camera.create_still_configuration()
                self.camera.configure(config)
                self.camera.start()
                time.sleep(2)
                print("✅ Camera initialized")
            except Exception as e:
                print(f"❌ Camera error: {e}")
                CAMERA_AVAILABLE = False
        
        # Initialize thermal camera
        if THERMAL_AVAILABLE:
            try:
                i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
                self.thermal = adafruit_mlx90640.MLX90640(i2c)
                self.thermal.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
                print("✅ Thermal camera initialized")
            except Exception as e:
                print(f"❌ Thermal camera error: {e}")
                THERMAL_AVAILABLE = False
        
        # Scan results
        self.scan_points = []
        self.scan_number = 0
        
        print("\n✅ System ready!")
    
    def maintain_wall_distance(self):
        """Adjust robot position to maintain optimal distance from wall"""
        distance = self.ultrasonic.measure_distance()
        
        if distance is None:
            print("⚠ No distance reading")
            return False
        
        print(f"📏 Distance: {distance:.1f}cm (target: {OPTIMAL_DISTANCE}cm)")
        
        if distance < OPTIMAL_DISTANCE - DISTANCE_TOLERANCE:
            # Too close - move back
            print("⬅ Too close, moving back...")
            self.robot.move_backward(MOVE_SPEED, 500)
            time.sleep(0.6)
            return False
            
        elif distance > OPTIMAL_DISTANCE + DISTANCE_TOLERANCE:
            # Too far - move forward
            print("➡ Too far, moving closer...")
            self.robot.move_forward(MOVE_SPEED, 500)
            time.sleep(0.6)
            return False
        
        # Distance OK
        return True
    
    def capture_scan_point(self):
        """Capture all sensor data at current position"""
        self.scan_number += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scan_id = f"scan_{self.scan_number:03d}_{timestamp}"
        
        print(f"\n📸 Capturing scan point {self.scan_number}...")
        
        scan_data = {
            'id': scan_id,
            'timestamp': timestamp,
            'distance': self.ultrasonic.measure_distance()
        }
        
        # Capture camera image
        if CAMERA_AVAILABLE:
            try:
                filename = f"/home/pi/crack_data/{scan_id}_camera.jpg"
                self.camera.capture_file(filename)
                scan_data['camera_image'] = filename
                print(f"  ✅ Camera image saved")
            except Exception as e:
                print(f"  ❌ Camera capture failed: {e}")
        
        # Capture thermal image
        if THERMAL_AVAILABLE:
            try:
                frame = [0] * 768
                self.thermal.getFrame(frame)
                thermal_array = np.array(frame).reshape(24, 32)
                
                filename = f"/home/pi/crack_data/{scan_id}_thermal.npy"
                np.save(filename, thermal_array)
                scan_data['thermal_data'] = filename
                
                # Also save as image for viewing
                thermal_img = ((thermal_array - thermal_array.min()) / 
                              (thermal_array.max() - thermal_array.min()) * 255).astype(np.uint8)
                thermal_colored = cv2.applyColorMap(thermal_img, cv2.COLORMAP_JET)
                cv2.imwrite(f"/home/pi/crack_data/{scan_id}_thermal.jpg", thermal_colored)
                
                print(f"  ✅ Thermal data saved")
            except Exception as e:
                print(f"  ❌ Thermal capture failed: {e}")
        
        self.scan_points.append(scan_data)
        print(f"✅ Scan point {self.scan_number} complete")
        
        return scan_data
    
    def scan_wall_section(self, num_points=10, move_distance_cm=20):
        """Scan a section of wall by moving along it"""
        print(f"\n🔍 Starting wall scan: {num_points} points, {move_distance_cm}cm apart")
        
        # Enable auto distance reporting for smoother operation
        self.ultrasonic.enable_auto_reporting()
        
        for i in range(num_points):
            print(f"\n--- Point {i+1}/{num_points} ---")
            
            # Maintain distance from wall
            attempts = 0
            while not self.maintain_wall_distance() and attempts < 3:
                attempts += 1
                time.sleep(0.5)
            
            # Capture scan point
            self.capture_scan_point()
            
            # Move to next position (if not last point)
            if i < num_points - 1:
                print(f"➡ Moving to next scan position...")
                
                # Calculate move duration based on distance
                # Assuming robot moves ~10cm per second at MOVE_SPEED
                move_duration = int((move_distance_cm / 10.0) * 1000)
                
                self.robot.move_forward(MOVE_SPEED, move_duration)
                time.sleep(move_duration / 1000.0 + 0.5)
        
        # Disable auto reporting when done
        self.ultrasonic.disable_auto_reporting()
        
        print(f"\n✅ Wall scan complete! {len(self.scan_points)} points captured")
    
    def run_autonomous_scan(self):
        """Main autonomous scanning routine"""
        print("\n" + "="*50)
        print("🚀 STARTING AUTONOMOUS WALL CRACK DETECTION")
        print("="*50)
        
        try:
            # Create data directory
            os.makedirs("/home/pi/crack_data", exist_ok=True)
            
            # Perform scan
            self.scan_wall_section(num_points=10, move_distance_cm=20)
            
            # Save scan summary
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = f"/home/pi/crack_data/scan_summary_{timestamp}.txt"
            
            with open(summary_file, 'w') as f:
                f.write(f"Autonomous Wall Crack Detection Scan\n")
                f.write(f"Date: {datetime.now()}\n")
                f.write(f"Total points: {len(self.scan_points)}\n\n")
                
                for point in self.scan_points:
                    f.write(f"\n{point['id']}:\n")
                    f.write(f"  Distance: {point['distance']:.1f}cm\n")
                    if 'camera_image' in point:
                        f.write(f"  Camera: {point['camera_image']}\n")
                    if 'thermal_data' in point:
                        f.write(f"  Thermal: {point['thermal_data']}\n")
            
            print(f"\n📄 Scan summary saved: {summary_file}")
            
        except KeyboardInterrupt:
            print("\n\n⚠ Scan interrupted by user")
        
        finally:
            # Stop robot
            self.robot.stop()
            print("\n🛑 Robot stopped")
            print(f"📊 Total scans captured: {len(self.scan_points)}")


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("  AUTONOMOUS WALL CRACK DETECTION ROBOT")
    print("  MegaPi Ultrasonic Sensor Version")
    print("="*60 + "\n")
    
    try:
        # Initialize system
        system = CrackDetectionSystem()
        
        # Wait a moment
        time.sleep(1)
        
        # Run autonomous scan
        system.run_autonomous_scan()
        
    except Exception as e:
        print(f"\n❌ System error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
