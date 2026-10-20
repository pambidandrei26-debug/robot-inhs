#!/usr/bin/env python3
"""
Acoustic Analysis Module for Crack Detection
Piezo transducer tap testing and frequency analysis
"""

import numpy as np
from scipy.fft import fft, fftfreq, ifft
from scipy.signal import find_peaks, butter, filtfilt, spectrogram
import matplotlib.pyplot as plt


class AcousticAnalyzer:
    """Advanced acoustic signal analysis for hollow/crack detection"""
    
    def __init__(self, sample_rate=8000):
        """
        Initialize acoustic analyzer
        sample_rate: samples per second (Hz)
        """
        self.sample_rate = sample_rate
        
        # Frequency bands for analysis
        self.freq_bands = {
            'very_low': (50, 200),      # Deep structural issues
            'low': (200, 500),          # Hollow areas
            'mid': (500, 1000),         # Medium density
            'high': (1000, 2000),       # Solid concrete
            'very_high': (2000, 4000)   # Surface/dense material
        }
        
        # Detection thresholds
        self.hollow_freq_range = (200, 800)  # Hz
        self.solid_freq_range = (1000, 3000)  # Hz
    
    def analyze_tap_response(self, signal_data, sample_rate=None):
        """
        Main acoustic analysis method
        Returns: (is_hollow, confidence, acoustic_signature, details)
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        if signal_data is None or len(signal_data) == 0:
            return False, 0, {}, {}
        
        # Run multiple analysis methods
        freq_result = self._frequency_analysis(signal_data, sample_rate)
        decay_result = self._decay_analysis(signal_data, sample_rate)
        resonance_result = self._resonance_analysis(signal_data, sample_rate)
        energy_result = self._energy_distribution(signal_data, sample_rate)
        
        # Determine if hollow/cracked
        is_hollow = (
            freq_result['is_hollow'] or
            decay_result['is_hollow'] or
            resonance_result['is_hollow']
        )
        
        # Calculate confidence (0-100)
        confidence = int(np.mean([
            freq_result['confidence'],
            decay_result['confidence'],
            resonance_result['confidence']
        ]))
        
        # Acoustic signature
        acoustic_signature = {
            'dominant_frequency': freq_result['dominant_freq'],
            'decay_time': decay_result['decay_time'],
            'resonance_peaks': resonance_result['peak_count'],
            'hollow_score': freq_result['hollow_ratio'],
            'quality_factor': resonance_result['q_factor']
        }
        
        # Detailed results
        details = {
            'frequency_analysis': freq_result,
            'decay_analysis': decay_result,
            'resonance_analysis': resonance_result,
            'energy_distribution': energy_result,
            'classification': self._classify_material(
                freq_result, decay_result, resonance_result
            )
        }
        
        return is_hollow, confidence, acoustic_signature, details
    
    def _frequency_analysis(self, signal_data, sample_rate):
        """Analyze frequency spectrum using FFT"""
        n = len(signal_data)
        
        # Perform FFT
        fft_values = fft(signal_data)
        fft_freq = fftfreq(n, 1/sample_rate)
        
        # Only positive frequencies
        positive_freq_idx = np.where(fft_freq > 0)
        frequencies = fft_freq[positive_freq_idx]
        magnitudes = np.abs(fft_values[positive_freq_idx])
        
        # Find dominant frequency
        dominant_idx = np.argmax(magnitudes)
        dominant_freq = frequencies[dominant_idx]
        dominant_magnitude = magnitudes[dominant_idx]
        
        # Calculate power in different frequency bands
        total_power = np.sum(magnitudes)
        
        hollow_band_mask = (frequencies >= self.hollow_freq_range[0]) & \
                          (frequencies <= self.hollow_freq_range[1])
        hollow_power = np.sum(magnitudes[hollow_band_mask])
        
        solid_band_mask = (frequencies >= self.solid_freq_range[0]) & \
                         (frequencies <= self.solid_freq_range[1])
        solid_power = np.sum(magnitudes[solid_band_mask])
        
        # Calculate ratios
        hollow_ratio = hollow_power / total_power if total_power > 0 else 0
        solid_ratio = solid_power / total_power if total_power > 0 else 0
        
        # Hollow detection logic
        # Hollow areas: dominant frequency in hollow band + high hollow ratio
        is_hollow = (
            (self.hollow_freq_range[0] <= dominant_freq <= self.hollow_freq_range[1]) and
            (hollow_ratio > 0.3)
        ) or (hollow_ratio > 0.5)
        
        confidence = min(100, int(hollow_ratio * 150))
        
        # Band power distribution
        band_powers = {}
        for band_name, (f_min, f_max) in self.freq_bands.items():
            band_mask = (frequencies >= f_min) & (frequencies <= f_max)
            band_power = np.sum(magnitudes[band_mask])
            band_powers[band_name] = round(band_power / total_power * 100, 2)
        
        return {
            'is_hollow': is_hollow,
            'confidence': confidence,
            'dominant_freq': round(dominant_freq, 2),
            'dominant_magnitude': round(dominant_magnitude, 2),
            'hollow_ratio': round(hollow_ratio, 3),
            'solid_ratio': round(solid_ratio, 3),
            'hollow_power': round(hollow_power, 2),
            'solid_power': round(solid_power, 2),
            'total_power': round(total_power, 2),
            'band_powers': band_powers
        }
    
    def _decay_analysis(self, signal_data, sample_rate):
        """
        Analyze signal decay characteristics
        Hollow areas: longer decay time (resonance)
        Solid areas: shorter decay time (damped)
        """
        # Calculate envelope (amplitude over time)
        envelope = np.abs(signal_data)
        
        # Smooth envelope
        window_size = max(1, int(sample_rate * 0.01))  # 10ms window
        if window_size > 1:
            envelope = np.convolve(envelope, np.ones(window_size)/window_size, mode='same')
        
        # Find peak
        peak_idx = np.argmax(envelope)
        peak_value = envelope[peak_idx]
        
        # Calculate decay time (time to drop to 10% of peak)
        decay_threshold = peak_value * 0.1
        
        decay_indices = np.where(envelope[peak_idx:] < decay_threshold)[0]
        
        if len(decay_indices) > 0:
            decay_samples = decay_indices[0]
            decay_time = decay_samples / sample_rate  # seconds
        else:
            decay_time = (len(envelope) - peak_idx) / sample_rate
        
        # Hollow areas have longer decay (>50ms)
        # Solid areas have shorter decay (<30ms)
        is_hollow = decay_time > 0.05  # 50ms
        
        confidence = min(100, int(decay_time * 1000))  # ms to confidence
        
        # Calculate decay rate
        if peak_idx < len(envelope) - 1:
            decay_portion = envelope[peak_idx:]
            if len(decay_portion) > 1:
                # Fit exponential decay
                time_axis = np.arange(len(decay_portion)) / sample_rate
                try:
                    # Simple decay rate estimation
                    decay_rate = -np.log(decay_portion[-1] / peak_value) / time_axis[-1]
                except:
                    decay_rate = 0
            else:
                decay_rate = 0
        else:
            decay_rate = 0
        
        return {
            'is_hollow': is_hollow,
            'confidence': confidence,
            'decay_time': round(decay_time * 1000, 2),  # ms
            'decay_rate': round(decay_rate, 2),
            'peak_value': round(peak_value, 4),
            'peak_time': round(peak_idx / sample_rate * 1000, 2)  # ms
        }
    
    def _resonance_analysis(self, signal_data, sample_rate):
        """
        Analyze resonance characteristics
        Hollow areas: clear resonance peaks, high Q factor
        Solid areas: damped, low Q factor
        """
        # Perform FFT
        n = len(signal_data)
        fft_values = fft(signal_data)
        fft_freq = fftfreq(n, 1/sample_rate)
        
        # Only positive frequencies
        positive_freq_idx = np.where(fft_freq > 0)
        frequencies = fft_freq[positive_freq_idx]
        magnitudes = np.abs(fft_values[positive_freq_idx])
        
        # Find peaks in spectrum
        peaks, properties = find_peaks(magnitudes, height=np.max(magnitudes)*0.1, 
                                      distance=int(sample_rate/100))
        
        peak_count = len(peaks)
        
        # Calculate Q factor (quality factor) of dominant peak
        if peak_count > 0:
            # Find dominant peak
            dominant_peak_idx = peaks[np.argmax(magnitudes[peaks])]
            peak_freq = frequencies[dominant_peak_idx]
            peak_magnitude = magnitudes[dominant_peak_idx]
            
            # Find -3dB points (half power)
            half_power = peak_magnitude / np.sqrt(2)
            
            # Search left and right of peak
            left_indices = np.where((frequencies < peak_freq) & 
                                   (magnitudes > half_power))[0]
            right_indices = np.where((frequencies > peak_freq) & 
                                    (magnitudes > half_power))[0]
            
            if len(left_indices) > 0 and len(right_indices) > 0:
                f_left = frequencies[left_indices[-1]]
                f_right = frequencies[right_indices[0]]
                bandwidth = f_right - f_left
                
                if bandwidth > 0:
                    q_factor = peak_freq / bandwidth
                else:
                    q_factor = 0
            else:
                q_factor = 0
        else:
            peak_freq = 0
            q_factor = 0
        
        # Hollow areas: multiple resonance peaks, high Q
        # Solid areas: few peaks, low Q
        is_hollow = (peak_count >= 3) or (q_factor > 10)
        
        confidence = min(100, peak_count * 20 + int(q_factor * 2))
        
        return {
            'is_hollow': is_hollow,
            'confidence': confidence,
            'peak_count': peak_count,
            'q_factor': round(q_factor, 2),
            'resonance_freq': round(peak_freq, 2) if peak_count > 0 else 0
        }
    
    def _energy_distribution(self, signal_data, sample_rate):
        """Analyze energy distribution across time and frequency"""
        # Calculate short-time energy
        frame_length = int(sample_rate * 0.02)  # 20ms frames
        hop_length = frame_length // 2
        
        energy_frames = []
        for i in range(0, len(signal_data) - frame_length, hop_length):
            frame = signal_data[i:i+frame_length]
            energy = np.sum(frame ** 2)
            energy_frames.append(energy)
        
        energy_frames = np.array(energy_frames)
        
        if len(energy_frames) > 0:
            total_energy = np.sum(energy_frames)
            peak_energy = np.max(energy_frames)
            avg_energy = np.mean(energy_frames)
            
            # Energy concentration (how much energy in peak vs average)
            energy_concentration = peak_energy / avg_energy if avg_energy > 0 else 0
        else:
            total_energy = 0
            peak_energy = 0
            avg_energy = 0
            energy_concentration = 0
        
        return {
            'total_energy': round(total_energy, 4),
            'peak_energy': round(peak_energy, 4),
            'avg_energy': round(avg_energy, 4),
            'energy_concentration': round(energy_concentration, 2)
        }
    
    def _classify_material(self, freq_result, decay_result, resonance_result):
        """
        Classify material type based on acoustic signature
        """
        dominant_freq = freq_result['dominant_freq']
        decay_time = decay_result['decay_time']
        q_factor = resonance_result['q_factor']
        
        # Classification logic
        if dominant_freq < 300 and decay_time > 80 and q_factor > 15:
            return "hollow_void"  # Large air gap
        elif 300 <= dominant_freq < 600 and decay_time > 50:
            return "cracked_hollow"  # Crack with air gap
        elif 600 <= dominant_freq < 1000 and decay_time > 30:
            return "partial_crack"  # Surface crack
        elif 1000 <= dominant_freq < 2000 and decay_time < 30:
            return "solid_concrete"  # Normal solid material
        elif dominant_freq >= 2000 and decay_time < 20:
            return "very_dense"  # Very dense/hard material
        else:
            return "unknown"
    
    def generate_tap_signal(self, frequency=1000, duration=0.05, 
                          amplitude=1.0, sample_rate=None):
        """
        Generate ideal tap signal for piezo transducer
        Returns: signal array
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        # Generate tone burst with envelope
        signal = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # Apply Gaussian envelope (bell shape)
        envelope = np.exp(-(t - duration/2)**2 / (2 * (duration/6)**2))
        signal = signal * envelope
        
        return signal
    
    def visualize_acoustic(self, signal_data, sample_rate=None, save_path=None):
        """
        Create visualization of acoustic analysis
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # Time domain
        time_axis = np.arange(len(signal_data)) / sample_rate * 1000  # ms
        axes[0].plot(time_axis, signal_data, 'b-', linewidth=0.5)
        axes[0].set_xlabel('Time (ms)')
        axes[0].set_ylabel('Amplitude')
        axes[0].set_title('Acoustic Signal - Time Domain')
        axes[0].grid(True, alpha=0.3)
        
        # Frequency domain
        n = len(signal_data)
        fft_values = fft(signal_data)
        fft_freq = fftfreq(n, 1/sample_rate)
        positive_freq_idx = np.where(fft_freq > 0)
        frequencies = fft_freq[positive_freq_idx]
        magnitudes = np.abs(fft_values[positive_freq_idx])
        
        axes[1].plot(frequencies, magnitudes, 'r-', linewidth=1)
        axes[1].set_xlabel('Frequency (Hz)')
        axes[1].set_ylabel('Magnitude')
        axes[1].set_title('Frequency Spectrum')
        axes[1].set_xlim([0, 2000])
        axes[1].grid(True, alpha=0.3)
        
        # Highlight hollow frequency band
        axes[1].axvspan(self.hollow_freq_range[0], self.hollow_freq_range[1], 
                       alpha=0.2, color='yellow', label='Hollow Band')
        axes[1].axvspan(self.solid_freq_range[0], self.solid_freq_range[1], 
                       alpha=0.2, color='green', label='Solid Band')
        axes[1].legend()
        
        # Spectrogram
        f, t, Sxx = spectrogram(signal_data, sample_rate, nperseg=256)
        im = axes[2].pcolormesh(t * 1000, f, 10 * np.log10(Sxx + 1e-10), 
                               shading='gouraud', cmap='viridis')
        axes[2].set_ylabel('Frequency (Hz)')
        axes[2].set_xlabel('Time (ms)')
        axes[2].set_title('Spectrogram')
        axes[2].set_ylim([0, 2000])
        plt.colorbar(im, ax=axes[2], label='Power (dB)')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"📊 Acoustic visualization saved: {save_path}")
        else:
            plt.show()
        
        plt.close()


# Example usage
if __name__ == "__main__":
    print("🧪 Testing Acoustic Analyzer...\n")
    
    # Create analyzer
    analyzer = AcousticAnalyzer(sample_rate=8000)
    
    # Test 1: Simulate hollow wall response
    print("Test 1: Hollow wall simulation")
    hollow_signal = (
        np.sin(2 * np.pi * 400 * np.linspace(0, 0.2, 1600)) * 
        np.exp(-np.linspace(0, 0.2, 1600) * 8)  # Slow decay
    )
    
    is_hollow, confidence, signature, details = analyzer.analyze_tap_response(
        hollow_signal, 8000
    )
    
    print(f"  Hollow detected: {is_hollow}")
    print(f"  Confidence: {confidence}%")
    print(f"  Dominant frequency: {signature['dominant_frequency']} Hz")
    print(f"  Decay time: {signature['decay_time']} ms")
    print(f"  Classification: {details['classification']}\n")
    
    # Test 2: Simulate solid wall response
    print("Test 2: Solid wall simulation")
    solid_signal = (
        np.sin(2 * np.pi * 1500 * np.linspace(0, 0.2, 1600)) * 
        np.exp(-np.linspace(0, 0.2, 1600) * 30)  # Fast decay
    )
    
    is_hollow, confidence, signature, details = analyzer.analyze_tap_response(
        solid_signal, 8000
    )
    
    print(f"  Hollow detected: {is_hollow}")
    print(f"  Confidence: {confidence}%")
    print(f"  Dominant frequency: {signature['dominant_frequency']} Hz")
    print(f"  Decay time: {signature['decay_time']} ms")
    print(f"  Classification: {details['classification']}\n")
    
    # Visualize
    print("Generating visualizations...")
    analyzer.visualize_acoustic(hollow_signal, 8000)
