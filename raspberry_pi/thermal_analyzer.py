#!/usr/bin/env python3
"""
Thermal Analysis Module for Crack Detection
Advanced thermal image processing and anomaly detection
"""

import numpy as np
from scipy import ndimage
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
import cv2


class ThermalAnalyzer:
    """Advanced thermal image analysis for crack detection"""
    
    def __init__(self, sensitivity='medium'):
        """
        Initialize thermal analyzer
        sensitivity: 'low', 'medium', 'high'
        """
        self.sensitivity = sensitivity
        
        # Thresholds based on sensitivity
        self.thresholds = {
            'low': {
                'variance': 2.5,
                'gradient': 0.5,
                'cluster_size': 5
            },
            'medium': {
                'variance': 1.5,
                'gradient': 0.3,
                'cluster_size': 3
            },
            'high': {
                'variance': 0.8,
                'gradient': 0.2,
                'cluster_size': 2
            }
        }
        
        self.config = self.thresholds[sensitivity]
    
    def detect_anomalies(self, thermal_image):
        """
        Main anomaly detection method
        Returns: (has_anomaly, severity, anomaly_map, details)
        """
        if thermal_image is None or thermal_image.size == 0:
            return False, 0, None, {}
        
        # Run multiple detection methods
        variance_result = self._detect_by_variance(thermal_image)
        gradient_result = self._detect_by_gradient(thermal_image)
        cluster_result = self._detect_clusters(thermal_image)
        edge_result = self._detect_edges(thermal_image)
        
        # Combine results
        has_anomaly = (
            variance_result['anomaly'] or
            gradient_result['anomaly'] or
            cluster_result['anomaly'] or
            edge_result['anomaly']
        )
        
        # Calculate overall severity (0-100)
        severity = int(np.mean([
            variance_result['score'],
            gradient_result['score'],
            cluster_result['score'],
            edge_result['score']
        ]))
        
        # Create composite anomaly map
        anomaly_map = self._create_anomaly_map(
            thermal_image,
            variance_result,
            gradient_result,
            cluster_result
        )
        
        # Compile detailed results
        details = {
            'variance_analysis': variance_result,
            'gradient_analysis': gradient_result,
            'cluster_analysis': cluster_result,
            'edge_analysis': edge_result,
            'detection_method': self._get_primary_method(
                variance_result, gradient_result, 
                cluster_result, edge_result
            )
        }
        
        return has_anomaly, severity, anomaly_map, details
    
    def _detect_by_variance(self, thermal_image):
        """Detect anomalies using temperature variance"""
        avg_temp = np.mean(thermal_image)
        variance = np.var(thermal_image)
        std_dev = np.std(thermal_image)
        
        # Find regions with high variance
        deviation_map = np.abs(thermal_image - avg_temp)
        high_deviation_pixels = np.sum(deviation_map > (2 * std_dev))
        deviation_percentage = (high_deviation_pixels / thermal_image.size) * 100
        
        # Check threshold
        anomaly = variance > self.config['variance']
        score = min(100, int(variance * 30 + deviation_percentage * 2))
        
        return {
            'anomaly': anomaly,
            'score': score,
            'variance': round(variance, 3),
            'std_dev': round(std_dev, 3),
            'deviation_percentage': round(deviation_percentage, 2),
            'avg_temp': round(avg_temp, 2)
        }
    
    def _detect_by_gradient(self, thermal_image):
        """Detect anomalies using temperature gradients (sharp transitions)"""
        # Calculate gradients
        gradient_x = np.gradient(thermal_image, axis=1)
        gradient_y = np.gradient(thermal_image, axis=0)
        gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
        
        # Find sharp temperature transitions
        max_gradient = np.max(gradient_magnitude)
        avg_gradient = np.mean(gradient_magnitude)
        
        # Sharp edges indicate cracks
        sharp_edges = np.sum(gradient_magnitude > (avg_gradient + 2*np.std(gradient_magnitude)))
        edge_percentage = (sharp_edges / thermal_image.size) * 100
        
        anomaly = max_gradient > self.config['gradient']
        score = min(100, int(max_gradient * 50 + edge_percentage * 3))
        
        return {
            'anomaly': anomaly,
            'score': score,
            'max_gradient': round(max_gradient, 3),
            'avg_gradient': round(avg_gradient, 3),
            'edge_percentage': round(edge_percentage, 2)
        }
    
    def _detect_clusters(self, thermal_image):
        """Detect temperature clusters (hot/cold spots)"""
        avg_temp = np.mean(thermal_image)
        std_dev = np.std(thermal_image)
        
        # Find hot and cold clusters
        hot_mask = thermal_image > (avg_temp + std_dev)
        cold_mask = thermal_image < (avg_temp - std_dev)
        
        # Label connected regions
        hot_clusters, hot_count = ndimage.label(hot_mask)
        cold_clusters, cold_count = ndimage.label(cold_mask)
        
        total_clusters = hot_count + cold_count
        
        # Calculate cluster sizes
        cluster_sizes = []
        if hot_count > 0:
            for i in range(1, hot_count + 1):
                cluster_sizes.append(np.sum(hot_clusters == i))
        if cold_count > 0:
            for i in range(1, cold_count + 1):
                cluster_sizes.append(np.sum(cold_clusters == i))
        
        avg_cluster_size = np.mean(cluster_sizes) if cluster_sizes else 0
        
        # Significant clusters indicate anomalies
        anomaly = total_clusters >= self.config['cluster_size']
        score = min(100, total_clusters * 15 + int(avg_cluster_size * 5))
        
        return {
            'anomaly': anomaly,
            'score': score,
            'hot_clusters': hot_count,
            'cold_clusters': cold_count,
            'total_clusters': total_clusters,
            'avg_cluster_size': round(avg_cluster_size, 2)
        }
    
    def _detect_edges(self, thermal_image):
        """Detect thermal edges using Sobel operator"""
        # Normalize image to 0-255 for edge detection
        normalized = ((thermal_image - np.min(thermal_image)) / 
                     (np.max(thermal_image) - np.min(thermal_image)) * 255).astype(np.uint8)
        
        # Apply Sobel edge detection
        sobelx = cv2.Sobel(normalized, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(normalized, cv2.CV_64F, 0, 1, ksize=3)
        sobel_magnitude = np.sqrt(sobelx**2 + sobely**2)
        
        # Find strong edges
        edge_threshold = np.mean(sobel_magnitude) + np.std(sobel_magnitude)
        strong_edges = np.sum(sobel_magnitude > edge_threshold)
        edge_percentage = (strong_edges / thermal_image.size) * 100
        
        anomaly = edge_percentage > 5  # More than 5% strong edges
        score = min(100, int(edge_percentage * 10))
        
        return {
            'anomaly': anomaly,
            'score': score,
            'strong_edges': int(strong_edges),
            'edge_percentage': round(edge_percentage, 2)
        }
    
    def _create_anomaly_map(self, thermal_image, variance_result, 
                           gradient_result, cluster_result):
        """Create visual anomaly map highlighting problem areas"""
        # Create empty map
        anomaly_map = np.zeros_like(thermal_image)
        
        # Mark high deviation areas
        avg_temp = variance_result['avg_temp']
        std_dev = variance_result['std_dev']
        deviation = np.abs(thermal_image - avg_temp)
        anomaly_map += (deviation > (2 * std_dev)).astype(float) * 0.4
        
        # Mark high gradient areas
        gradient_x = np.gradient(thermal_image, axis=1)
        gradient_y = np.gradient(thermal_image, axis=0)
        gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
        avg_gradient = gradient_result['avg_gradient']
        anomaly_map += (gradient_magnitude > avg_gradient * 2).astype(float) * 0.3
        
        # Mark cluster centers
        hot_mask = thermal_image > (avg_temp + std_dev)
        cold_mask = thermal_image < (avg_temp - std_dev)
        anomaly_map += hot_mask.astype(float) * 0.2
        anomaly_map += cold_mask.astype(float) * 0.1
        
        # Normalize to 0-1
        if np.max(anomaly_map) > 0:
            anomaly_map = anomaly_map / np.max(anomaly_map)
        
        return anomaly_map
    
    def _get_primary_method(self, variance_result, gradient_result,
                           cluster_result, edge_result):
        """Determine which detection method had strongest signal"""
        scores = {
            'variance': variance_result['score'],
            'gradient': gradient_result['score'],
            'cluster': cluster_result['score'],
            'edge': edge_result['score']
        }
        
        return max(scores, key=scores.get)
    
    def classify_crack_type(self, thermal_image, anomaly_map):
        """
        Classify the type of crack based on thermal signature
        Returns: crack_type string
        """
        if anomaly_map is None:
            return "unknown"
        
        avg_temp = np.mean(thermal_image)
        anomaly_temps = thermal_image[anomaly_map > 0.5]
        
        if len(anomaly_temps) == 0:
            return "no_crack"
        
        anomaly_avg = np.mean(anomaly_temps)
        
        # Classify based on temperature signature
        if anomaly_avg < avg_temp - 1.0:
            return "cold_crack"  # Air gap, possible void
        elif anomaly_avg > avg_temp + 1.0:
            return "hot_crack"   # Possible moisture, thermal bridge
        else:
            return "surface_crack"  # Minor temperature difference
    
    def estimate_crack_depth(self, thermal_severity, acoustic_confidence):
        """
        Estimate crack depth based on thermal + acoustic data
        Returns: depth category string
        """
        combined_score = (thermal_severity + acoustic_confidence) / 2
        
        if combined_score > 80:
            return "deep (>5cm)"
        elif combined_score > 60:
            return "medium (2-5cm)"
        elif combined_score > 40:
            return "shallow (<2cm)"
        else:
            return "surface only"
    
    def visualize_thermal(self, thermal_image, anomaly_map=None, 
                         save_path=None):
        """
        Create visualization of thermal data with anomalies highlighted
        """
        fig, axes = plt.subplots(1, 3 if anomaly_map is not None else 2, 
                                figsize=(15, 5))
        
        # Original thermal image
        im1 = axes[0].imshow(thermal_image, cmap='hot', interpolation='nearest')
        axes[0].set_title('Thermal Image')
        axes[0].axis('off')
        plt.colorbar(im1, ax=axes[0], label='Temperature (°C)')
        
        # Gradient visualization
        gradient_x = np.gradient(thermal_image, axis=1)
        gradient_y = np.gradient(thermal_image, axis=0)
        gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
        
        im2 = axes[1].imshow(gradient_magnitude, cmap='viridis', 
                           interpolation='nearest')
        axes[1].set_title('Temperature Gradient')
        axes[1].axis('off')
        plt.colorbar(im2, ax=axes[1], label='Gradient Magnitude')
        
        # Anomaly map
        if anomaly_map is not None:
            im3 = axes[2].imshow(anomaly_map, cmap='Reds', 
                               interpolation='nearest', vmin=0, vmax=1)
            axes[2].set_title('Anomaly Map')
            axes[2].axis('off')
            plt.colorbar(im3, ax=axes[2], label='Anomaly Score')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"📊 Thermal visualization saved: {save_path}")
        else:
            plt.show()
        
        plt.close()


# Example usage
if __name__ == "__main__":
    # Create sample thermal data with simulated crack
    print("🧪 Testing Thermal Analyzer...\n")
    
    # Simulate 24x32 thermal image
    thermal_image = np.random.normal(25, 0.5, (24, 32))  # Normal wall ~25°C
    
    # Add simulated crack (temperature anomaly)
    thermal_image[10:14, 15:18] = 28  # Hot spot
    thermal_image[8, 16] = 22  # Cold spot
    
    # Create analyzer
    analyzer = ThermalAnalyzer(sensitivity='medium')
    
    # Detect anomalies
    has_anomaly, severity, anomaly_map, details = analyzer.detect_anomalies(thermal_image)
    
    print(f"Anomaly detected: {has_anomaly}")
    print(f"Severity: {severity}/100")
    print(f"\nDetection method: {details['detection_method']}")
    print(f"\nVariance analysis: {details['variance_analysis']}")
    print(f"Gradient analysis: {details['gradient_analysis']}")
    print(f"Cluster analysis: {details['cluster_analysis']}")
    
    # Classify crack
    crack_type = analyzer.classify_crack_type(thermal_image, anomaly_map)
    print(f"\nCrack type: {crack_type}")
    
    # Visualize
    analyzer.visualize_thermal(thermal_image, anomaly_map)
