#!/usr/bin/env python3
"""
THERMAL WALL CALIBRATION
========================
Teaches the system the thermal signature difference between:
  - REAL WALL   (concrete/hollow block — high thermal mass, uniform temp)
  - CARDBOARD   (thin material — low thermal mass, noisier, less stable)

How it works:
  Step 1 — Capture 20 frames while pointing at a REAL WALL  → saves "wall" profile
  Step 2 — Capture 20 frames while pointing at CARDBOARD    → saves "cardboard" profile
  Step 3 — Computes decision thresholds from both profiles
  Step 4 — Saves thresholds to ~/thermal_calibration.json
  Step 5 — web_remote_control.py auto-loads that file on startup

Run ON THE PI:
  python3 ~/thermal_wall_calibration.py
"""

import json
import os
import time
import numpy as np

# ── Sensor import ────────────────────────────────────────────
try:
    import board
    import busio
    import adafruit_mlx90640
    THERMAL_OK = True
except ImportError:
    THERMAL_OK = False
    print("ERROR: adafruit-circuitpython-mlx90640 not installed")
    print("Run: pip3 install adafruit-circuitpython-mlx90640")
    exit(1)

CALIBRATION_FILE = os.path.expanduser("~/thermal_calibration.json")
NUM_FRAMES       = 20       # frames to average per surface
FRAME_DELAY      = 0.6      # seconds between frames (2Hz sensor)

# ─────────────────────────────────────────────────────────────

def init_sensor():
    """Initialize MLX90640 at 800kHz I2C"""
    try:
        i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
        mlx = adafruit_mlx90640.MLX90640(i2c)
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
        time.sleep(1)
        print("[OK] MLX90640 initialized")
        return mlx
    except Exception as e:
        print(f"[ERROR] Could not initialize sensor: {e}")
        exit(1)


def capture_frame(mlx):
    """Capture one 24x32 thermal frame, return numpy array"""
    buf = [0] * 768
    mlx.getFrame(buf)
    return np.array(buf, dtype=np.float32).reshape(24, 32)


def extract_features(frame):
    """
    Extract thermal features used for wall vs cardboard classification.
    These are the same features checked in verify_real_wall():
      - std_temp:   temperature std across all pixels
      - temp_range: max - min across the frame
      - gradient:   mean absolute gradient (edge sharpness)
      - stability:  not captured here (needs multiple frames over time)
    """
    std_temp   = float(np.std(frame))
    temp_range = float(np.max(frame) - np.min(frame))
    grad_x     = np.diff(frame, axis=1)
    grad_y     = np.diff(frame, axis=0)
    gradient   = float(np.mean(np.abs(grad_x)) + np.mean(np.abs(grad_y)))
    avg_temp   = float(np.mean(frame))
    return {
        'std_temp':   round(std_temp,   3),
        'temp_range': round(temp_range, 3),
        'gradient':   round(gradient,   4),
        'avg_temp':   round(avg_temp,   2),
    }


def collect_samples(mlx, label, n=NUM_FRAMES):
    """
    Collect n thermal frames and return list of feature dicts.
    Prints a live progress bar.
    """
    print(f"\n  Collecting {n} frames for [{label.upper()}]...")
    print(f"  Keep the sensor pointed at the {label} surface")
    print(f"  Starting in 3 seconds...")
    time.sleep(3)

    samples = []
    for i in range(n):
        frame = capture_frame(mlx)
        feat  = extract_features(frame)
        samples.append(feat)
        bar = "█" * (i + 1) + "░" * (n - i - 1)
        print(f"\r  [{bar}] {i+1}/{n}  "
              f"std={feat['std_temp']:.2f}  "
              f"range={feat['temp_range']:.2f}  "
              f"grad={feat['gradient']:.3f}", end="", flush=True)
        time.sleep(FRAME_DELAY)

    print("\n  Done!\n")
    return samples


def summarize(samples):
    """Compute mean and std of each feature across all collected frames"""
    keys = samples[0].keys()
    summary = {}
    for k in keys:
        vals = [s[k] for s in samples]
        summary[k] = {
            'mean': round(float(np.mean(vals)), 3),
            'std':  round(float(np.std(vals)),  3),
            'min':  round(float(np.min(vals)),  3),
            'max':  round(float(np.max(vals)),  3),
        }
    return summary


def compute_thresholds(wall_summary, cardboard_summary):
    """
    Compute decision thresholds midway between wall and cardboard profiles.
    
    Wall thermal signature:     LOW std, LOW range, LOW gradient (uniform)
    Cardboard thermal signature: HIGHER std/range/gradient (thinner material)

    Threshold = midpoint between wall_mean and cardboard_mean per feature.
    A surface is classified as WALL if its features are <= threshold.
    """
    thresholds = {}
    features = ['std_temp', 'temp_range', 'gradient']
    for f in features:
        wall_mean = wall_summary[f]['mean']
        card_mean = cardboard_summary[f]['mean']
        midpoint  = round((wall_mean + card_mean) / 2, 3)
        thresholds[f] = midpoint

    # Safety margin: push threshold 20% toward cardboard side so
    # we're less likely to confuse cardboard as a wall
    for f in features:
        wall_mean = wall_summary[f]['mean']
        card_mean = cardboard_summary[f]['mean']
        direction = 1 if card_mean > wall_mean else -1
        margin = abs(card_mean - wall_mean) * 0.15
        thresholds[f] = round(thresholds[f] - direction * margin, 3)

    return thresholds


def classify(features, thresholds):
    """
    Classify a feature dict as WALL or CARDBOARD.
    Wall = features are below the thresholds (lower = more uniform = solid).
    """
    votes_wall = 0
    votes_card = 0
    details    = {}

    for f in ['std_temp', 'temp_range', 'gradient']:
        val = features[f]
        thr = thresholds[f]
        if val <= thr:
            votes_wall += 1
            details[f] = f"{val:.3f} <= {thr:.3f} → WALL"
        else:
            votes_card += 1
            details[f] = f"{val:.3f} >  {thr:.3f} → CARDBOARD"

    result = "WALL" if votes_wall >= 2 else "CARDBOARD"
    confidence = max(votes_wall, votes_card) / 3 * 100
    return result, confidence, details


def live_test(mlx, thresholds, n=10):
    """
    Run n frames of live classification to verify calibration works.
    Point sensor at different surfaces to see the result.
    """
    print("\n" + "="*60)
    print("  LIVE VERIFICATION — point sensor at different surfaces")
    print("  Press Ctrl+C to stop")
    print("="*60 + "\n")
    for _ in range(n):
        try:
            frame = capture_frame(mlx)
            feat  = extract_features(frame)
            result, conf, details = classify(feat, thresholds)

            tag = "[WALL ✅]" if result == "WALL" else "[CARDBOARD ⚠️ ]"
            print(f"  {tag}  conf={conf:.0f}%  "
                  f"std={feat['std_temp']:.2f}  "
                  f"range={feat['temp_range']:.2f}  "
                  f"grad={feat['gradient']:.3f}")
            time.sleep(FRAME_DELAY)
        except KeyboardInterrupt:
            break


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print("\n" + "="*60)
    print("  THERMAL WALL CALIBRATION v1.0")
    print("  MLX90640 — Wall vs Cardboard Classifier")
    print("="*60)
    print()

    mlx = init_sensor()

    # ── STEP 1: Capture WALL samples ─────────────────────────
    print("┌─────────────────────────────────────────┐")
    print("│  STEP 1 of 2:  Point sensor at REAL WALL│")
    print("│  (concrete, hollow block, plywood, etc.) │")
    print("└─────────────────────────────────────────┘")
    input("  Press Enter when ready...")
    wall_samples = collect_samples(mlx, "WALL")
    wall_summary = summarize(wall_samples)

    print("  WALL profile:")
    for k, v in wall_summary.items():
        print(f"    {k:12s}  mean={v['mean']:.3f}  std={v['std']:.3f}  "
              f"min={v['min']:.3f}  max={v['max']:.3f}")

    # ── STEP 2: Capture CARDBOARD samples ────────────────────
    print("\n┌──────────────────────────────────────────┐")
    print("│  STEP 2 of 2:  Point sensor at CARDBOARD │")
    print("│  (cardboard box, thin sheet, etc.)        │")
    print("└──────────────────────────────────────────┘")
    input("  Press Enter when ready...")
    card_samples = collect_samples(mlx, "CARDBOARD")
    card_summary = summarize(card_samples)

    print("  CARDBOARD profile:")
    for k, v in card_summary.items():
        print(f"    {k:12s}  mean={v['mean']:.3f}  std={v['std']:.3f}  "
              f"min={v['min']:.3f}  max={v['max']:.3f}")

    # ── STEP 3: Compute thresholds ────────────────────────────
    thresholds = compute_thresholds(wall_summary, card_summary)
    print("\n  Decision thresholds (surface is WALL if value <= threshold):")
    for f, t in thresholds.items():
        print(f"    {f:12s}  threshold = {t:.3f}")

    # ── STEP 4: Save calibration file ─────────────────────────
    calibration = {
        'version':           '1.0',
        'created':           time.strftime('%Y-%m-%d %H:%M:%S'),
        'num_frames_used':   NUM_FRAMES,
        'wall_profile':      wall_summary,
        'cardboard_profile': card_summary,
        'thresholds':        thresholds,
        # Crack detection thresholds (tuned from wall baseline)
        'crack_detection': {
            # Only flag as crack if thermal range > this value ON a confirmed wall
            # Set to wall_range_mean + 2*wall_range_std so normal wall variation
            # doesn't trigger false positives
            'temp_diff_threshold': round(
                wall_summary['temp_range']['mean'] +
                2 * wall_summary['temp_range']['std'], 2
            ),
            # Only flag anomaly pixels beyond this many std-devs from mean
            'anomaly_sigma': 2.5,
        }
    }

    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(calibration, f, indent=2)
    print(f"\n  [SAVED] Calibration written to: {CALIBRATION_FILE}")

    # ── STEP 5: Live verification ─────────────────────────────
    print("\n  Do you want to run a live verification test? (y/n) ", end="")
    ans = input().strip().lower()
    if ans == 'y':
        live_test(mlx, thresholds)

    # ── SUMMARY ───────────────────────────────────────────────
    print("\n" + "="*60)
    print("  CALIBRATION COMPLETE")
    print("="*60)
    print(f"\n  Calibration file: {CALIBRATION_FILE}")
    print("\n  THRESHOLDS SUMMARY:")
    print(f"    std_temp   <= {thresholds['std_temp']:.3f} °C  → WALL")
    print(f"    temp_range <= {thresholds['temp_range']:.3f} °C  → WALL")
    print(f"    gradient   <= {thresholds['gradient']:.3f}      → WALL")
    print(f"\n  Crack detection threshold (on confirmed wall):")
    print(f"    temp_diff  >  {calibration['crack_detection']['temp_diff_threshold']:.2f} °C → flag as anomaly")
    print()
    print("  Restart web_remote_control.py to apply calibration:")
    print("    pkill -f web_remote_control.py")
    print("    python3 ~/web_remote_control.py")
    print()


if __name__ == '__main__':
    main()
