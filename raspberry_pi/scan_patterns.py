#!/usr/bin/env python3
"""
Wall Scanning Pattern Algorithms
Different patterns for comprehensive wall coverage
"""

import numpy as np
import time
from enum import Enum


class ScanPattern(Enum):
    """Available scanning patterns"""
    GRID = "grid"
    ZIGZAG = "zigzag"
    SPIRAL = "spiral"
    ADAPTIVE = "adaptive"
    VERTICAL_STRIPS = "vertical_strips"
    HORIZONTAL_STRIPS = "horizontal_strips"


class WallScanner:
    """Generate and execute wall scanning patterns"""
    
    def __init__(self, wall_width, wall_height, step_size=10, 
                 overlap=0.2, optimal_distance=10):
        """
        Initialize wall scanner
        
        Args:
            wall_width: Width of wall to scan (cm)
            wall_height: Height of wall to scan (cm)
            step_size: Distance between scan points (cm)
            overlap: Overlap between scans (0.0-1.0)
            optimal_distance: Optimal distance from wall (cm)
        """
        self.wall_width = wall_width
        self.wall_height = wall_height
        self.step_size = step_size
        self.overlap = overlap
        self.optimal_distance = optimal_distance
        
        # Calculate effective step with overlap
        self.effective_step = int(step_size * (1 - overlap))
        
        print(f"📐 Wall Scanner initialized:")
        print(f"   Wall size: {wall_width} x {wall_height} cm")
        print(f"   Step size: {step_size} cm (effective: {self.effective_step} cm)")
        print(f"   Overlap: {overlap * 100}%")
    
    def generate_grid_pattern(self):
        """
        Generate simple grid pattern (left-to-right, top-to-bottom)
        Returns: list of (x, y) positions
        """
        positions = []
        
        for y in range(0, self.wall_height, self.effective_step):
            for x in range(0, self.wall_width, self.effective_step):
                positions.append((x, y))
        
        print(f"✅ Grid pattern: {len(positions)} positions")
        return positions
    
    def generate_zigzag_pattern(self):
        """
        Generate zigzag pattern (alternate direction each row)
        More efficient - reduces travel time
        Returns: list of (x, y) positions
        """
        positions = []
        left_to_right = True
        
        for y in range(0, self.wall_height, self.effective_step):
            if left_to_right:
                # Left to right
                x_range = range(0, self.wall_width, self.effective_step)
            else:
                # Right to left
                x_range = range(self.wall_width - 1, -1, -self.effective_step)
            
            for x in x_range:
                positions.append((x, y))
            
            left_to_right = not left_to_right
        
        print(f"✅ Zigzag pattern: {len(positions)} positions")
        return positions
    
    def generate_spiral_pattern(self, start_outside=True):
        """
        Generate spiral pattern (outside-in or inside-out)
        Good for perimeter inspection
        
        Args:
            start_outside: True for outside-in, False for inside-out
        Returns: list of (x, y) positions
        """
        positions = []
        
        # Create grid
        x_points = list(range(0, self.wall_width, self.effective_step))
        y_points = list(range(0, self.wall_height, self.effective_step))
        
        if not x_points or not y_points:
            return positions
        
        # Boundaries
        left, right = 0, len(x_points) - 1
        top, bottom = 0, len(y_points) - 1
        
        while left <= right and top <= bottom:
            # Top row (left to right)
            for i in range(left, right + 1):
                positions.append((x_points[i], y_points[top]))
            top += 1
            
            # Right column (top to bottom)
            for i in range(top, bottom + 1):
                positions.append((x_points[right], y_points[i]))
            right -= 1
            
            # Bottom row (right to left)
            if top <= bottom:
                for i in range(right, left - 1, -1):
                    positions.append((x_points[i], y_points[bottom]))
                bottom -= 1
            
            # Left column (bottom to top)
            if left <= right:
                for i in range(bottom, top - 1, -1):
                    positions.append((x_points[left], y_points[i]))
                left += 1
        
        if not start_outside:
            positions.reverse()
        
        print(f"✅ Spiral pattern: {len(positions)} positions")
        return positions
    
    def generate_vertical_strips(self):
        """
        Generate vertical strip pattern (scan column by column)
        Good for walls with vertical features
        Returns: list of (x, y) positions
        """
        positions = []
        
        for x in range(0, self.wall_width, self.effective_step):
            for y in range(0, self.wall_height, self.effective_step):
                positions.append((x, y))
        
        print(f"✅ Vertical strips: {len(positions)} positions")
        return positions
    
    def generate_horizontal_strips(self):
        """
        Generate horizontal strip pattern (scan row by row)
        Good for walls with horizontal features
        Returns: list of (x, y) positions
        """
        positions = []
        
        for y in range(0, self.wall_height, self.effective_step):
            for x in range(0, self.wall_width, self.effective_step):
                positions.append((x, y))
        
        print(f"✅ Horizontal strips: {len(positions)} positions")
        return positions
    
    def generate_adaptive_pattern(self, initial_step=20, detail_step=5):
        """
        Generate adaptive pattern (coarse scan first, then detail scan)
        Two-phase scanning:
        1. Quick coarse scan to find suspicious areas
        2. Detailed scan around suspicious areas
        
        Note: This returns initial coarse pattern. Detailed positions
        added dynamically based on scan results.
        
        Args:
            initial_step: Step size for initial coarse scan
            detail_step: Step size for detailed scan
        Returns: list of (x, y, scan_type) positions
        """
        positions = []
        
        # Phase 1: Coarse scan
        for y in range(0, self.wall_height, initial_step):
            for x in range(0, self.wall_width, initial_step):
                positions.append((x, y, 'coarse'))
        
        print(f"✅ Adaptive pattern (Phase 1): {len(positions)} coarse positions")
        print(f"   Phase 2 detail positions added dynamically during scan")
        
        return positions
    
    def add_detail_scan_around(self, center_x, center_y, radius=20, step=5):
        """
        Generate detailed scan positions around a point of interest
        Used in adaptive scanning after finding anomaly
        
        Args:
            center_x, center_y: Center position
            radius: Radius around center to scan (cm)
            step: Step size for detail scan
        Returns: list of (x, y) positions
        """
        positions = []
        
        x_min = max(0, center_x - radius)
        x_max = min(self.wall_width, center_x + radius)
        y_min = max(0, center_y - radius)
        y_max = min(self.wall_height, center_y + radius)
        
        for y in range(y_min, y_max, step):
            for x in range(x_min, x_max, step):
                # Skip center point (already scanned)
                if abs(x - center_x) < step and abs(y - center_y) < step:
                    continue
                positions.append((x, y))
        
        return positions
    
    def get_pattern(self, pattern_type):
        """
        Get scanning pattern by type
        
        Args:
            pattern_type: ScanPattern enum or string
        Returns: list of positions
        """
        if isinstance(pattern_type, str):
            pattern_type = ScanPattern(pattern_type.lower())
        
        if pattern_type == ScanPattern.GRID:
            return self.generate_grid_pattern()
        elif pattern_type == ScanPattern.ZIGZAG:
            return self.generate_zigzag_pattern()
        elif pattern_type == ScanPattern.SPIRAL:
            return self.generate_spiral_pattern()
        elif pattern_type == ScanPattern.VERTICAL_STRIPS:
            return self.generate_vertical_strips()
        elif pattern_type == ScanPattern.HORIZONTAL_STRIPS:
            return self.generate_horizontal_strips()
        elif pattern_type == ScanPattern.ADAPTIVE:
            return self.generate_adaptive_pattern()
        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")
    
    def calculate_scan_time(self, positions, scan_time_per_point=2.0, 
                           movement_speed=5.0):
        """
        Estimate total scan time
        
        Args:
            positions: List of (x, y) positions
            scan_time_per_point: Time to scan each point (seconds)
            movement_speed: Robot movement speed (cm/s)
        Returns: estimated time in seconds
        """
        if len(positions) < 2:
            return scan_time_per_point
        
        # Calculate total movement distance
        total_distance = 0
        for i in range(len(positions) - 1):
            x1, y1 = positions[i][:2]  # Handle (x,y) or (x,y,type)
            x2, y2 = positions[i+1][:2]
            distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            total_distance += distance
        
        # Total time = movement time + scan time
        movement_time = total_distance / movement_speed
        scan_time = len(positions) * scan_time_per_point
        total_time = movement_time + scan_time
        
        return total_time
    
    def optimize_path(self, positions):
        """
        Simple path optimization using nearest neighbor
        Reduces travel time between scan points
        
        Args:
            positions: List of (x, y) positions
        Returns: optimized list of positions
        """
        if len(positions) <= 2:
            return positions
        
        optimized = [positions[0]]
        remaining = list(positions[1:])
        
        current = positions[0]
        
        while remaining:
            # Find nearest unvisited position
            distances = [np.sqrt((p[0]-current[0])**2 + (p[1]-current[1])**2) 
                        for p in remaining]
            nearest_idx = np.argmin(distances)
            nearest = remaining[nearest_idx]
            
            optimized.append(nearest)
            current = nearest
            remaining.pop(nearest_idx)
        
        return optimized
    
    def visualize_pattern(self, positions, pattern_name="Pattern"):
        """
        Visualize scanning pattern (text-based)
        
        Args:
            positions: List of (x, y) positions
            pattern_name: Name for display
        """
        print(f"\n📍 {pattern_name} Visualization:")
        print(f"   Total positions: {len(positions)}")
        
        if len(positions) == 0:
            return
        
        # Create grid
        grid_width = self.wall_width // self.effective_step + 1
        grid_height = self.wall_height // self.effective_step + 1
        grid = [[' ' for _ in range(grid_width)] for _ in range(grid_height)]
        
        # Mark positions
        for i, pos in enumerate(positions):
            x, y = pos[:2]
            grid_x = x // self.effective_step
            grid_y = y // self.effective_step
            
            if 0 <= grid_x < grid_width and 0 <= grid_y < grid_height:
                if i == 0:
                    grid[grid_y][grid_x] = 'S'  # Start
                elif i == len(positions) - 1:
                    grid[grid_y][grid_x] = 'E'  # End
                else:
                    grid[grid_y][grid_x] = '•'  # Scan point
        
        # Print grid
        print("   +" + "-" * grid_width + "+")
        for row in grid:
            print("   |" + "".join(row) + "|")
        print("   +" + "-" * grid_width + "+")
        print("   S=Start, E=End, •=Scan point\n")
    
    def save_pattern_to_file(self, positions, filename):
        """
        Save scanning pattern to file
        
        Args:
            positions: List of positions
            filename: Output file path
        """
        try:
            with open(filename, 'w') as f:
                f.write(f"# Wall Scanning Pattern\n")
                f.write(f"# Wall size: {self.wall_width} x {self.wall_height} cm\n")
                f.write(f"# Step size: {self.step_size} cm\n")
                f.write(f"# Total positions: {len(positions)}\n\n")
                f.write("x,y\n")
                
                for pos in positions:
                    x, y = pos[:2]
                    f.write(f"{x},{y}\n")
            
            print(f"💾 Pattern saved to: {filename}")
            
        except Exception as e:
            print(f"❌ Error saving pattern: {e}")


# Example usage and comparison
if __name__ == "__main__":
    print("🧪 Testing Wall Scanning Patterns...\n")
    
    # Create scanner for 100x100cm wall
    scanner = WallScanner(
        wall_width=100,
        wall_height=100,
        step_size=10,
        overlap=0.1
    )
    
    print("\n" + "="*70)
    print("PATTERN COMPARISON")
    print("="*70)
    
    patterns = [
        (ScanPattern.GRID, "Grid Pattern"),
        (ScanPattern.ZIGZAG, "Zigzag Pattern"),
        (ScanPattern.SPIRAL, "Spiral Pattern"),
        (ScanPattern.VERTICAL_STRIPS, "Vertical Strips"),
    ]
    
    for pattern_type, pattern_name in patterns:
        print(f"\n--- {pattern_name} ---")
        positions = scanner.get_pattern(pattern_type)
        
        # Calculate time estimate
        estimated_time = scanner.calculate_scan_time(positions)
        
        print(f"Positions: {len(positions)}")
        print(f"Estimated time: {estimated_time/60:.1f} minutes")
        
        # Visualize (small wall only)
        if scanner.wall_width <= 100:
            scanner.visualize_pattern(positions, pattern_name)
    
    # Test adaptive pattern
    print("\n--- Adaptive Pattern (Two-Phase) ---")
    adaptive_positions = scanner.generate_adaptive_pattern(
        initial_step=20,
        detail_step=5
    )
    print(f"Phase 1 (coarse): {len(adaptive_positions)} positions")
    
    # Simulate finding anomaly at (40, 60)
    detail_positions = scanner.add_detail_scan_around(40, 60, radius=15, step=5)
    print(f"Phase 2 (detail around anomaly): {detail_positions} positions")
    
    print("\n✅ Pattern testing complete!")
