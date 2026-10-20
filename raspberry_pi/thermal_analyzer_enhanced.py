#!/usr/bin/env python3
"""
ENHANCED THERMAL ANALYZER FOR CRACK DETECTION
Subsurface discontinuity detection using MLX90640
Ready for new thermal sensor installation

Features:
- Advanced anomaly detection algorithms
- Temperature gradient analysis
- Subsurface crack identification
- Thermal pattern recognition
- Depth estimation
"""

import numpy as np
import cv2
from scipy import ndimage, signal
from datetime import datetime
import json

# Try to import thermal camera (will work when sensor is connected)
try:
    import board
    import busio
    import adafruit_mlx90640
    THERMAL_AVAILABLE = True
except ImportError:
    THERMAL_AVAILABLE = False
    print("⚠️ Thermal libraries not available - install when sensor arrives")

# ============================================================================
# THERMAL DETECTION THRESHOLDS
# ============================================================================

# Temperature variance thresholds
TEMP_VARIANCE_LOW = 0.5      # Minor anomaly
TEMP_VARIANCE_MEDIUM = 1.5   # Moderate anomaly
TEMP_VARIANCE_HIGH = 3.0     # Significant anomaly

# Temperature gradient thresholds (°C per pixel)
GRADIENT_THRESHOLD = 0.3     # Subsurface discontinuity
GRADIENT_STRONG = 0.8        # Strong thermal break

# Cold spot detection (indicates void/crack)
COLD_SPOT_THRESHOLD = 2.0    # °C below average

# Hot spot detection (indicates structural issue)
HOT_SPOT_THRESHOLD = 2.5     # °C above average

# Cluster analysis
MIN_ANOMALY_CLUSTER_SIZE = 4  # Minimum pixels to be considered real
MAX_ANOMALY_DEPTH_CM = 10     # Maximum detectable depth


class EnhancedThermalAnalyzer:
    """Advanced thermal analysis for subsurface crack detection"""
    
    def __init__(self, i2c_bus=1, refresh_rate=2):
        """
        Initialize thermal analyzer
        
        Args:
            i2c_bus: I2C bus number (default 1)
            refresh_rate: 2Hz or 4Hz (default 2Hz for accuracy)
        """
        self.thermal_camera = None
        self.frame_buffer = []
        self.calibration_baseline = None
        
        if THERMAL_AVAILABLE:
            try:
                i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
                self.thermal_camera = adafruit_mlx90640.MLX90640(i2c)
                
                # Set refresh rate
                if refresh_rate == 4:
                    self.thermal_camera.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
                else:
                    self.thermal_camera.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
                
                print("✅ Enhanced thermal analyzer initialized")
                print(f"   Sensor: MLX90640 (32x24 pixels)")
                print(f"   Refresh: {refresh_rate}Hz")
                print(f"   Resolution: 55° x 35° FOV")
                
            except Exception as e:
                print(f"❌ Thermal sensor initialization failed: {e}")
                print("   Please check:")
                print("   1. Sensor is connected to I2C")
                print("   2. I2C is enabled (sudo raspi-config)")
                print("   3. Correct I2C address (0x33)")
                self.thermal_camera = None
        else:
            print("⚠️ Thermal sensor not available (libraries not installed)")
    
    def is_available(self):
        """Check if thermal sensor is available"""
        return self.thermal_camera is not None
    
    def capture_frame(self):
        """
        Capture single thermal frame
        
        Returns:
            numpy array (24x32) of temperatures in Celsius
            None if capture failed
        """
        if not self.thermal_camera:
            return None
        
        try:
            frame = [0] * 768  # MLX90640 has 768 pixels (24x32)
            self.thermal_camera.getFrame(frame)
            thermal_array = np.array(frame).reshape(24, 32)
            return thermal_array
        except Exception as e:
            print(f"❌ Frame capture error: {e}")
            return None
    
    def capture_averaged_frame(self, num_frames=5):
        """
        Capture and average multiple frames for noise reduction
        
        Args:
            num_frames: Number of frames to average (default 5)
            
        Returns:
            Averaged thermal frame
        """
        if not self.thermal_camera:
            return None
        
        frames = []
        for i in range(num_frames):
            frame = self.capture_frame()
            if frame is not None:
                frames.append(frame)
        
        if frames:
            return np.mean(frames, axis=0)
        return None
    
    def set_calibration_baseline(self, frame=None):
        """
        Set baseline temperature for comparison
        Useful for detecting anomalies relative to normal wall temperature
        
        Args:
            frame: Thermal frame to use as baseline (captures new if None)
        """
        if frame is None:
            frame = self.capture_averaged_frame(num_frames=10)
        
        if frame is not None:
            self.calibration_baseline = frame
            print(f"✅ Calibration baseline set (avg: {frame.mean():.1f}°C)")
        else:
            print("❌ Failed to set calibration baseline")
    
    def detect_subsurface_anomalies(self, frame):
        """
        Detect subsurface anomalies (cracks, voids, discontinuities)
        
        Args:
            frame: Thermal frame (24x32 numpy array)
            
        Returns:
            dict with detection results including crack size estimation
        """
        if frame is None:
            return None
        
        results = {
            'anomaly_detected': False,
            'confidence': 0,
            'anomaly_type': 'none',
            'severity': 'none',
            'cold_spots': [],
            'hot_spots': [],
            'thermal_breaks': [],
            'estimated_depth_cm': 0,
            'crack_size': {
                'estimated_length_cm': 0,
                'estimated_width_cm': 0,
                'estimated_area_cm2': 0,
                'affected_pixels': 0
            },
            'statistics': {}
        }
        
        # Basic statistics
        temp_mean = frame.mean()
        temp_std = frame.std()
        temp_min = frame.min()
        temp_max = frame.max()
        temp_range = temp_max - temp_min
        
        results['statistics'] = {
            'mean': float(temp_mean),
            'std': float(temp_std),
            'min': float(temp_min),
            'max': float(temp_max),
            'range': float(temp_range)
        }
        
        # 1. VARIANCE ANALYSIS
        # High variance indicates temperature inconsistencies
        variance_score = 0
        if temp_std > TEMP_VARIANCE_HIGH:
            variance_score = 100
        elif temp_std > TEMP_VARIANCE_MEDIUM:
            variance_score = 60
        elif temp_std > TEMP_VARIANCE_LOW:
            variance_score = 30
        
        # 2. COLD SPOT DETECTION
        # Cold spots indicate voids/cracks (less thermal mass)
        cold_threshold = temp_mean - COLD_SPOT_THRESHOLD
        cold_mask = frame < cold_threshold
        cold_spots = self._find_clusters(cold_mask)
        
        if cold_spots:
            results['cold_spots'] = cold_spots
            results['anomaly_type'] = 'cold_spot_void'
            variance_score = max(variance_score, 70)
        
        # 3. HOT SPOT DETECTION
        # Hot spots can indicate structural stress/compression
        hot_threshold = temp_mean + HOT_SPOT_THRESHOLD
        hot_mask = frame > hot_threshold
        hot_spots = self._find_clusters(hot_mask)
        
        if hot_spots:
            results['hot_spots'] = hot_spots
            if results['anomaly_type'] == 'none':
                results['anomaly_type'] = 'hot_spot_stress'
            variance_score = max(variance_score, 60)
        
        # 4. GRADIENT ANALYSIS
        # Sharp temperature gradients indicate subsurface discontinuities
        gradient_x = np.gradient(frame, axis=1)
        gradient_y = np.gradient(frame, axis=0)
        gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
        
        strong_gradients = gradient_magnitude > GRADIENT_STRONG
        moderate_gradients = gradient_magnitude > GRADIENT_THRESHOLD
        
        thermal_breaks = self._find_thermal_breaks(gradient_magnitude)
        
        if thermal_breaks:
            results['thermal_breaks'] = thermal_breaks
            if results['anomaly_type'] == 'none':
                results['anomaly_type'] = 'thermal_break'
            variance_score = max(variance_score, 80)
        
        # 5. PATTERN RECOGNITION
        # Look for linear patterns (typical of cracks)
        linear_features = self._detect_linear_patterns(gradient_magnitude)
        
        if linear_features:
            results['anomaly_type'] = 'linear_crack_pattern'
            variance_score = max(variance_score, 90)
        
        # 6. DEPTH ESTIMATION
        # Estimate depth based on temperature deviation
        if cold_spots or hot_spots:
            max_deviation = max(
                abs(temp_min - temp_mean),
                abs(temp_max - temp_mean)
            )
            # Empirical formula: deeper = less temperature difference
            # Surface: 3-5°C diff, 5cm deep: 1-2°C diff, 10cm: <1°C diff
            if max_deviation > 3:
                depth = 1  # Surface level
            elif max_deviation > 2:
                depth = 3  # Shallow subsurface
            elif max_deviation > 1:
                depth = 6  # Medium depth
            else:
                depth = 10  # Deep subsurface
            
            results['estimated_depth_cm'] = depth
        
        # 7. CRACK SIZE ESTIMATION
        # Calculate crack dimensions from thermal anomaly
        if cold_spots or thermal_breaks:
            crack_size = self._estimate_crack_size(
                frame, cold_spots, thermal_breaks, gradient_magnitude
            )
            results['crack_size'] = crack_size
        
        # FINAL ASSESSMENT
        results['confidence'] = min(100, variance_score)
        results['anomaly_detected'] = variance_score > 40
        
        # Severity classification
        if variance_score >= 80:
            results['severity'] = 'high'
        elif variance_score >= 60:
            results['severity'] = 'medium'
        elif variance_score >= 40:
            results['severity'] = 'low'
        else:
            results['severity'] = 'none'
        
        return results
    
    def _estimate_crack_size(self, frame, cold_spots, thermal_breaks, gradient_magnitude):
        """
        Estimate crack size from thermal anomaly patterns
        
        MLX90640 specs:
        - Resolution: 32x24 pixels
        - Field of View: 55° x 35°
        - At 15cm distance: ~1.5cm per pixel (horizontal), ~1.2cm per pixel (vertical)
        
        Args:
            frame: Thermal frame
            cold_spots: List of cold spot clusters
            thermal_breaks: List of thermal break clusters
            gradient_magnitude: Gradient map
            
        Returns:
            dict with size estimates
        """
        # Default values
        size_info = {
            'estimated_length_cm': 0,
            'estimated_width_cm': 0,
            'estimated_area_cm2': 0,
            'affected_pixels': 0,
            'calculation_method': 'none'
        }
        
        # Pixel to cm conversion (at optimal distance of 15cm)
        # MLX90640: 55° horizontal FOV, 32 pixels wide
        # At 15cm: width_cm = 2 * 15 * tan(55°/2) = 15.7cm total
        # Per pixel: 15.7cm / 32 = 0.49cm per pixel horizontal
        
        # MLX90640: 35° vertical FOV, 24 pixels tall
        # At 15cm: height_cm = 2 * 15 * tan(35°/2) = 9.7cm total
        # Per pixel: 9.7cm / 24 = 0.40cm per pixel vertical
        
        PIXEL_TO_CM_HORIZONTAL = 0.49  # cm per pixel
        PIXEL_TO_CM_VERTICAL = 0.40    # cm per pixel
        
        # Combine all anomaly regions
        all_anomaly_pixels = []
        
        # Add cold spots
        for spot in cold_spots:
            all_anomaly_pixels.extend(self._get_cluster_pixels(spot))
        
        # Add thermal breaks
        for break_cluster in thermal_breaks:
            all_anomaly_pixels.extend(self._get_cluster_pixels(break_cluster))
        
        if not all_anomaly_pixels:
            return size_info
        
        # Convert to array for analysis
        pixels_array = np.array(all_anomaly_pixels)
        
        # Get bounding box
        x_coords = pixels_array[:, 0]
        y_coords = pixels_array[:, 1]
        
        min_x, max_x = x_coords.min(), x_coords.max()
        min_y, max_y = y_coords.min(), y_coords.max()
        
        # Calculate dimensions in pixels
        width_pixels = max_x - min_x + 1
        height_pixels = max_y - min_y + 1
        
        # Convert to centimeters
        width_cm = width_pixels * PIXEL_TO_CM_HORIZONTAL
        height_cm = height_pixels * PIXEL_TO_CM_VERTICAL
        
        # Determine which is length vs width
        # Typically: length > width for cracks
        if width_cm > height_cm:
            length_cm = width_cm
            width_crack_cm = height_cm
        else:
            length_cm = height_cm
            width_crack_cm = width_cm
        
        # Calculate area (only anomaly pixels, not full bounding box)
        num_anomaly_pixels = len(all_anomaly_pixels)
        area_cm2 = num_anomaly_pixels * PIXEL_TO_CM_HORIZONTAL * PIXEL_TO_CM_VERTICAL
        
        # Apply depth correction factor
        # Deeper cracks appear smaller in thermal
        depth = self._estimate_depth_from_gradient(gradient_magnitude)
        depth_factor = 1.0 + (depth / 10.0)  # Deeper = bigger actual crack
        
        length_cm *= depth_factor
        width_crack_cm *= depth_factor
        area_cm2 *= depth_factor
        
        size_info = {
            'estimated_length_cm': round(length_cm, 1),
            'estimated_width_cm': round(width_crack_cm, 1),
            'estimated_area_cm2': round(area_cm2, 1),
            'affected_pixels': num_anomaly_pixels,
            'calculation_method': 'thermal_anomaly_clustering',
            'bounding_box_pixels': {
                'x_min': int(min_x),
                'y_min': int(min_y),
                'x_max': int(max_x),
                'y_max': int(max_y)
            }
        }
        
        return size_info
    
    def _get_cluster_pixels(self, cluster):
        """Extract all pixel coordinates from a cluster's bounding box"""
        bbox = cluster['bbox']
        x_min, y_min, x_max, y_max = bbox
        
        pixels = []
        for y in range(y_min, y_max + 1):
            for x in range(x_min, x_max + 1):
                pixels.append((x, y))
        
        return pixels
    
    def _estimate_depth_from_gradient(self, gradient_magnitude):
        """Estimate depth from gradient strength"""
        max_gradient = gradient_magnitude.max()
        
        if max_gradient > 0.8:
            return 2  # Shallow (strong gradient)
        elif max_gradient > 0.5:
            return 5  # Medium depth
        else:
            return 8  # Deep (weak gradient)
        
        # FINAL ASSESSMENT
        results['confidence'] = min(100, variance_score)
        results['anomaly_detected'] = variance_score > 40
        
        # Severity classification
        if variance_score >= 80:
            results['severity'] = 'high'
        elif variance_score >= 60:
            results['severity'] = 'medium'
        elif variance_score >= 40:
            results['severity'] = 'low'
        else:
            results['severity'] = 'none'
        
        return results
    
    def _find_clusters(self, mask):
        """
        Find connected clusters in binary mask
        
        Returns:
            List of cluster info (size, centroid, bounding box)
        """
        labeled, num_features = ndimage.label(mask)
        clusters = []
        
        for i in range(1, num_features + 1):
            cluster_mask = (labeled == i)
            size = cluster_mask.sum()
            
            if size >= MIN_ANOMALY_CLUSTER_SIZE:
                # Find centroid
                y_coords, x_coords = np.where(cluster_mask)
                centroid = (int(x_coords.mean()), int(y_coords.mean()))
                
                # Bounding box
                bbox = (
                    int(x_coords.min()),
                    int(y_coords.min()),
                    int(x_coords.max()),
                    int(y_coords.max())
                )
                
                clusters.append({
                    'size': int(size),
                    'centroid': centroid,
                    'bbox': bbox
                })
        
        return clusters
    
    def _find_thermal_breaks(self, gradient_magnitude):
        """Find sharp thermal discontinuities (possible crack lines)"""
        strong_mask = gradient_magnitude > GRADIENT_STRONG
        return self._find_clusters(strong_mask)
    
    def _detect_linear_patterns(self, gradient_magnitude):
        """
        Detect linear patterns in gradient map
        Uses Hough Line Transform
        """
        # Convert to 8-bit for Hough transform
        grad_8bit = ((gradient_magnitude / gradient_magnitude.max()) * 255).astype(np.uint8)
        
        # Edge detection
        edges = cv2.Canny(grad_8bit, 50, 150)
        
        # Hough Line Transform
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=5)
        
        return lines is not None and len(lines) > 0
    
    def generate_thermal_visualization(self, frame, results=None, colormap=cv2.COLORMAP_JET):
        """
        Generate color-coded thermal visualization
        
        Args:
            frame: Thermal frame
            results: Detection results (optional, will overlay markers)
            colormap: OpenCV colormap (JET, TURBO, etc.)
            
        Returns:
            Color image (480x640) ready for display
        """
        if frame is None:
            return None
        
        # Normalize to 0-255
        frame_normalized = ((frame - frame.min()) / (frame.max() - frame.min()) * 255).astype(np.uint8)
        
        # Apply colormap
        colored = cv2.applyColorMap(frame_normalized, colormap)
        
        # Resize for better visibility (32x24 -> 640x480)
        resized = cv2.resize(colored, (640, 480), interpolation=cv2.INTER_NEAREST)
        
        # Overlay detection results
        if results and results['anomaly_detected']:
            # Draw cold spots (blue circles)
            for spot in results.get('cold_spots', []):
                cx, cy = spot['centroid']
                cv2.circle(resized, (cx*20, cy*20), 30, (255, 0, 0), 3)
                cv2.putText(resized, "COLD", (cx*20-20, cy*20-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Draw hot spots (red circles)
            for spot in results.get('hot_spots', []):
                cx, cy = spot['centroid']
                cv2.circle(resized, (cx*20, cy*20), 30, (0, 0, 255), 3)
                cv2.putText(resized, "HOT", (cx*20-20, cy*20-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Add info overlay
            cv2.rectangle(resized, (10, 10), (350, 180), (0, 0, 0), -1)
            cv2.rectangle(resized, (10, 10), (350, 180), (255, 255, 255), 2)
            
            cv2.putText(resized, f"Anomaly: {results['anomaly_type']}", (20, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(resized, f"Confidence: {results['confidence']}%", (20, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(resized, f"Depth: ~{results['estimated_depth_cm']}cm", (20, 85),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(resized, f"Severity: {results['severity'].upper()}", (20, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Add crack size if available
            crack_size = results.get('crack_size', {})
            if crack_size.get('estimated_length_cm', 0) > 0:
                cv2.putText(resized, f"Length: {crack_size['estimated_length_cm']}cm", (20, 135),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
                cv2.putText(resized, f"Width: {crack_size['estimated_width_cm']}cm", (20, 160),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        
        # Add temperature scale
        self._add_temperature_scale(resized, frame.min(), frame.max())
        
        return resized
    
    def _add_temperature_scale(self, image, temp_min, temp_max):
        """Add temperature scale bar to image"""
        scale_height = 200
        scale_width = 30
        scale_x = image.shape[1] - scale_width - 20
        scale_y = 20
        
        # Create gradient bar
        gradient = np.linspace(255, 0, scale_height).reshape(-1, 1)
        gradient = np.repeat(gradient, scale_width, axis=1).astype(np.uint8)
        gradient_colored = cv2.applyColorMap(gradient, cv2.COLORMAP_JET)
        
        # Place on image
        image[scale_y:scale_y+scale_height, scale_x:scale_x+scale_width] = gradient_colored
        
        # Add labels
        cv2.putText(image, f"{temp_max:.1f}C", (scale_x-50, scale_y+15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, f"{temp_min:.1f}C", (scale_x-50, scale_y+scale_height),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def save_thermal_data(self, frame, results, filename_base):
        """
        Save thermal data and analysis results
        
        Args:
            frame: Thermal frame
            results: Detection results
            filename_base: Base filename (without extension)
        """
        # Save raw numpy data
        np.save(f"{filename_base}_raw.npy", frame)
        
        # Save visualization
        visualization = self.generate_thermal_visualization(frame, results)
        if visualization is not None:
            cv2.imwrite(f"{filename_base}_thermal.jpg", visualization)
        
        # Save results JSON
        with open(f"{filename_base}_analysis.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"✅ Thermal data saved: {filename_base}_*")


# ============================================================================
# STANDALONE TEST/DEMO
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("ENHANCED THERMAL ANALYZER - TEST MODE")
    print("="*70)
    
    # Initialize analyzer
    analyzer = EnhancedThermalAnalyzer(refresh_rate=2)
    
    if not analyzer.is_available():
        print("\n⚠️ Thermal sensor not available!")
        print("This module is ready for when your new MLX90640 arrives.")
        print("\nTo test:")
        print("1. Connect MLX90640 to I2C (SDA=GPIO2, SCL=GPIO3)")
        print("2. Enable I2C: sudo raspi-config")
        print("3. Install: pip3 install adafruit-circuitpython-mlx90640")
        print("4. Run this script again")
    else:
        print("\n✅ Thermal sensor detected! Running test scan...\n")
        
        # Set baseline
        print("Calibrating baseline...")
        analyzer.set_calibration_baseline()
        
        # Capture and analyze
        print("\nCapturing thermal frame...")
        frame = analyzer.capture_averaged_frame(num_frames=5)
        
        if frame is not None:
            print("\nAnalyzing for subsurface anomalies...")
            results = analyzer.detect_subsurface_anomalies(frame)
            
            # Print results
            print("\n" + "="*70)
            print("THERMAL ANALYSIS RESULTS")
            print("="*70)
            print(f"Anomaly Detected: {results['anomaly_detected']}")
            print(f"Confidence: {results['confidence']}%")
            print(f"Type: {results['anomaly_type']}")
            print(f"Severity: {results['severity']}")
            print(f"Estimated Depth: {results['estimated_depth_cm']} cm")
            
            print(f"\nCrack Size Estimation:")
            crack_size = results['crack_size']
            print(f"  Length: {crack_size['estimated_length_cm']} cm")
            print(f"  Width: {crack_size['estimated_width_cm']} cm")
            print(f"  Area: {crack_size['estimated_area_cm2']} cm²")
            print(f"  Affected pixels: {crack_size['affected_pixels']}")
            
            print(f"\nTemperature Stats:")
            print(f"  Mean: {results['statistics']['mean']:.2f}°C")
            print(f"  Std Dev: {results['statistics']['std']:.2f}°C")
            print(f"  Range: {results['statistics']['range']:.2f}°C")
            print(f"  Min: {results['statistics']['min']:.2f}°C")
            print(f"  Max: {results['statistics']['max']:.2f}°C")
            
            if results['cold_spots']:
                print(f"\nCold Spots: {len(results['cold_spots'])}")
            if results['hot_spots']:
                print(f"Hot Spots: {len(results['hot_spots'])}")
            if results['thermal_breaks']:
                print(f"Thermal Breaks: {len(results['thermal_breaks'])}")
            
            # Save data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            analyzer.save_thermal_data(frame, results, f"thermal_test_{timestamp}")
            
            print("\n✅ Test complete! Check output files.")
        else:
            print("❌ Failed to capture thermal frame")
