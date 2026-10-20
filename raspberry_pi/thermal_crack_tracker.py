#!/usr/bin/env python3
"""
THERMAL CRACK GROWTH TRACKER
Tracks subsurface crack growth over multiple days

Compares thermal crack measurements:
- Day 0 vs Day 7 vs Day 14 vs Day 21 vs Day 28
- Detects if internal crack is growing
- Generates growth reports
"""

import json
import os
from datetime import datetime
import numpy as np

class ThermalCrackTracker:
    """Track thermal crack measurements over time"""
    
    def __init__(self, data_dir="/home/pi/crack_data/thermal_tracking"):
        """
        Initialize tracker
        
        Args:
            data_dir: Directory to store tracking data
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def save_thermal_measurement(self, day_number, location, thermal_results):
        """
        Save thermal crack measurement for a specific day
        
        Args:
            day_number: Scan day (0, 7, 14, 21, 28...)
            location: Location identifier (e.g., "Column A-03")
            thermal_results: Detection results from thermal analyzer
        """
        # Create record
        record = {
            'day_number': day_number,
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'location': location,
            'thermal_data': {
                'anomaly_detected': thermal_results.get('anomaly_detected', False),
                'confidence': thermal_results.get('confidence', 0),
                'anomaly_type': thermal_results.get('anomaly_type', 'none'),
                'severity': thermal_results.get('severity', 'none'),
                'depth_cm': thermal_results.get('estimated_depth_cm', 0),
                'crack_length_cm': thermal_results.get('crack_size', {}).get('estimated_length_cm', 0),
                'crack_width_cm': thermal_results.get('crack_size', {}).get('estimated_width_cm', 0),
                'crack_area_cm2': thermal_results.get('crack_size', {}).get('estimated_area_cm2', 0),
                'temperature_stats': thermal_results.get('statistics', {})
            }
        }
        
        # Save to file
        filename = f"{self.data_dir}/{location.replace(' ', '_')}_day_{day_number}.json"
        with open(filename, 'w') as f:
            json.dump(record, f, indent=2)
        
        print(f"✅ Thermal measurement saved: {filename}")
        return filename
    
    def load_thermal_history(self, location):
        """
        Load all thermal measurements for a location
        
        Args:
            location: Location identifier
            
        Returns:
            List of measurements sorted by day
        """
        location_key = location.replace(' ', '_')
        pattern = f"{self.data_dir}/{location_key}_day_*.json"
        
        measurements = []
        import glob
        for filepath in sorted(glob.glob(pattern)):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    measurements.append(data)
            except:
                pass
        
        # Sort by day number
        measurements.sort(key=lambda x: x.get('day_number', 0))
        return measurements
    
    def analyze_crack_growth(self, location):
        """
        Analyze crack growth over time for a location
        
        Args:
            location: Location identifier
            
        Returns:
            dict with growth analysis
        """
        measurements = self.load_thermal_history(location)
        
        if len(measurements) < 2:
            return {
                'status': 'insufficient_data',
                'message': 'Need at least 2 measurements to compare',
                'measurements_count': len(measurements)
            }
        
        # Get baseline (first measurement)
        baseline = measurements[0]
        latest = measurements[-1]
        
        baseline_thermal = baseline['thermal_data']
        latest_thermal = latest['thermal_data']
        
        # Extract measurements
        baseline_length = baseline_thermal.get('crack_length_cm', 0)
        baseline_width = baseline_thermal.get('crack_width_cm', 0)
        baseline_area = baseline_thermal.get('crack_area_cm2', 0)
        baseline_depth = baseline_thermal.get('depth_cm', 0)
        
        latest_length = latest_thermal.get('crack_length_cm', 0)
        latest_width = latest_thermal.get('crack_width_cm', 0)
        latest_area = latest_thermal.get('crack_area_cm2', 0)
        latest_depth = latest_thermal.get('depth_cm', 0)
        
        # Calculate growth
        length_growth_cm = latest_length - baseline_length
        width_growth_cm = latest_width - baseline_width
        area_growth_cm2 = latest_area - baseline_area
        depth_change_cm = latest_depth - baseline_depth
        
        # Calculate percentages
        length_growth_pct = (length_growth_cm / baseline_length * 100) if baseline_length > 0 else 0
        width_growth_pct = (width_growth_cm / baseline_width * 100) if baseline_width > 0 else 0
        area_growth_pct = (area_growth_cm2 / baseline_area * 100) if baseline_area > 0 else 0
        
        # Determine severity
        max_growth_pct = max(length_growth_pct, width_growth_pct, area_growth_pct)
        
        if max_growth_pct < 5:
            status = 'STABLE'
            alert_level = 'success'
            message = 'Internal crack is stable. No significant growth detected.'
        elif max_growth_pct < 15:
            status = 'MONITOR'
            alert_level = 'warning'
            message = 'Internal crack showing slight growth. Continue monitoring closely.'
        elif max_growth_pct < 30:
            status = 'CONCERN'
            alert_level = 'danger'
            message = 'Internal crack is growing. Consider structural assessment.'
        else:
            status = 'CRITICAL'
            alert_level = 'critical'
            message = 'Significant internal crack growth! Immediate action required.'
        
        # Build result
        result = {
            'status': status,
            'alert_level': alert_level,
            'message': message,
            'location': location,
            'baseline_day': baseline['day_number'],
            'latest_day': latest['day_number'],
            'days_elapsed': latest['day_number'] - baseline['day_number'],
            'measurements_count': len(measurements),
            'baseline': {
                'date': baseline['scan_date'],
                'length_cm': baseline_length,
                'width_cm': baseline_width,
                'area_cm2': baseline_area,
                'depth_cm': baseline_depth,
                'severity': baseline_thermal.get('severity', 'none')
            },
            'latest': {
                'date': latest['scan_date'],
                'length_cm': latest_length,
                'width_cm': latest_width,
                'area_cm2': latest_area,
                'depth_cm': latest_depth,
                'severity': latest_thermal.get('severity', 'none')
            },
            'growth': {
                'length_cm': round(length_growth_cm, 1),
                'length_percent': round(length_growth_pct, 1),
                'width_cm': round(width_growth_cm, 1),
                'width_percent': round(width_growth_pct, 1),
                'area_cm2': round(area_growth_cm2, 1),
                'area_percent': round(area_growth_pct, 1),
                'depth_change_cm': round(depth_change_cm, 1),
                'max_growth_percent': round(max_growth_pct, 1)
            }
        }
        
        return result
    
    def generate_comparison_report(self, location):
        """
        Generate detailed comparison report
        
        Args:
            location: Location identifier
            
        Returns:
            Formatted text report
        """
        analysis = self.analyze_crack_growth(location)
        
        if analysis['status'] == 'insufficient_data':
            return f"Insufficient data for {location}. Need at least 2 measurements."
        
        report = []
        report.append("="*70)
        report.append("THERMAL CRACK GROWTH ANALYSIS REPORT")
        report.append("="*70)
        report.append(f"\nLocation: {location}")
        report.append(f"Analysis Period: Day {analysis['baseline_day']} → Day {analysis['latest_day']}")
        report.append(f"Days Elapsed: {analysis['days_elapsed']} days")
        report.append(f"Total Measurements: {analysis['measurements_count']}")
        report.append(f"\nStatus: {analysis['status']}")
        report.append(f"Alert Level: {analysis['alert_level'].upper()}")
        report.append(f"Assessment: {analysis['message']}")
        
        report.append(f"\n{'─'*70}")
        report.append("BASELINE MEASUREMENT (Day {})".format(analysis['baseline_day']))
        report.append(f"{'─'*70}")
        baseline = analysis['baseline']
        report.append(f"Date: {baseline['date']}")
        report.append(f"Internal Crack Length: {baseline['length_cm']} cm")
        report.append(f"Internal Crack Width: {baseline['width_cm']} cm")
        report.append(f"Affected Area: {baseline['area_cm2']} cm²")
        report.append(f"Estimated Depth: {baseline['depth_cm']} cm")
        report.append(f"Severity: {baseline['severity'].upper()}")
        
        report.append(f"\n{'─'*70}")
        report.append("LATEST MEASUREMENT (Day {})".format(analysis['latest_day']))
        report.append(f"{'─'*70}")
        latest = analysis['latest']
        report.append(f"Date: {latest['date']}")
        report.append(f"Internal Crack Length: {latest['length_cm']} cm")
        report.append(f"Internal Crack Width: {latest['width_cm']} cm")
        report.append(f"Affected Area: {latest['area_cm2']} cm²")
        report.append(f"Estimated Depth: {latest['depth_cm']} cm")
        report.append(f"Severity: {latest['severity'].upper()}")
        
        report.append(f"\n{'─'*70}")
        report.append("GROWTH ANALYSIS")
        report.append(f"{'─'*70}")
        growth = analysis['growth']
        report.append(f"Length Growth: {growth['length_cm']:+.1f} cm ({growth['length_percent']:+.1f}%)")
        report.append(f"Width Growth: {growth['width_cm']:+.1f} cm ({growth['width_percent']:+.1f}%)")
        report.append(f"Area Growth: {growth['area_cm2']:+.1f} cm² ({growth['area_percent']:+.1f}%)")
        report.append(f"Depth Change: {growth['depth_change_cm']:+.1f} cm")
        report.append(f"Maximum Growth: {growth['max_growth_percent']:.1f}%")
        
        report.append(f"\n{'─'*70}")
        report.append("RECOMMENDATION")
        report.append(f"{'─'*70}")
        
        if analysis['status'] == 'STABLE':
            report.append("✅ Internal structure appears stable.")
            report.append("   Continue regular monitoring schedule.")
        elif analysis['status'] == 'MONITOR':
            report.append("⚠️  Internal crack showing growth.")
            report.append("   Increase inspection frequency.")
            report.append("   Consider scheduling next scan sooner.")
        elif analysis['status'] == 'CONCERN':
            report.append("🚨 Internal crack growth detected.")
            report.append("   Recommend structural engineer assessment.")
            report.append("   Consider repair options.")
        else:  # CRITICAL
            report.append("🔴 CRITICAL: Significant internal deterioration!")
            report.append("   IMMEDIATE structural assessment required!")
            report.append("   May require urgent repairs.")
        
        report.append("\n" + "="*70)
        
        return "\n".join(report)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("THERMAL CRACK GROWTH TRACKER - DEMO")
    print("="*70)
    
    tracker = ThermalCrackTracker()
    
    # Simulate Day 0 measurement
    print("\n📅 Simulating Day 0 baseline scan...")
    day0_results = {
        'anomaly_detected': True,
        'confidence': 75,
        'anomaly_type': 'cold_spot_void',
        'severity': 'medium',
        'estimated_depth_cm': 5,
        'crack_size': {
            'estimated_length_cm': 8.5,
            'estimated_width_cm': 1.2,
            'estimated_area_cm2': 10.2
        },
        'statistics': {
            'mean': 24.5,
            'std': 1.2,
            'range': 3.5
        }
    }
    
    tracker.save_thermal_measurement(0, "Column A-03", day0_results)
    
    # Simulate Day 7 measurement (slight growth)
    print("\n📅 Simulating Day 7 scan...")
    day7_results = {
        'anomaly_detected': True,
        'confidence': 80,
        'anomaly_type': 'cold_spot_void',
        'severity': 'medium',
        'estimated_depth_cm': 6,
        'crack_size': {
            'estimated_length_cm': 9.2,  # +0.7cm growth
            'estimated_width_cm': 1.4,   # +0.2cm growth
            'estimated_area_cm2': 12.9   # +2.7cm² growth
        },
        'statistics': {
            'mean': 24.3,
            'std': 1.5,
            'range': 4.2
        }
    }
    
    tracker.save_thermal_measurement(7, "Column A-03", day7_results)
    
    # Analyze growth
    print("\n📊 Analyzing crack growth...\n")
    report = tracker.generate_comparison_report("Column A-03")
    print(report)
    
    print("\n✅ Demo complete!")
    print("Check data files in:", tracker.data_dir)
