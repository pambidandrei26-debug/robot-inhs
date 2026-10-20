#!/usr/bin/env python3
"""
DATA ANALYTICS & REPORTS DASHBOARD
Multi-day crack monitoring with comparison and alerts
Port: 8080
"""

from flask import Flask, render_template_string, jsonify, send_file, request
import os
import json
import csv
from datetime import datetime
from collections import deque
import glob

app = Flask(__name__)

DATA_DIR = os.path.expanduser("~/crack_detector/data")
SCANS_DIR = os.path.join(DATA_DIR, "scans")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCANS_DIR, exist_ok=True)

# ========================================
# DATA LOADING & ANALYSIS
# ========================================

def load_all_scans():
    """Load all saved scans - supports both day_*.json and trial_*.json"""
    scans = []
    for pattern in [os.path.join(SCANS_DIR, "trial_*.json"),
                    os.path.join(SCANS_DIR, "day_*.json")]:
        for filepath in sorted(glob.glob(pattern)):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    data['filepath'] = filepath
                    # Normalize: ensure trial_number exists
                    if 'trial_number' not in data:
                        data['trial_number'] = data.get('day_number', 0)
                    scans.append(data)
            except:
                pass
    # Deduplicate by filepath, sort by trial_number
    seen = set()
    unique = []
    for s in scans:
        if s['filepath'] not in seen:
            seen.add(s['filepath'])
            unique.append(s)
    return sorted(unique, key=lambda x: x.get('trial_number', x.get('day_number', 0)))

def extract_crack_size(scan):
    """
    Pull crack size from a scan record.
    Checks both 'crack_size' (thermal) and flat fields (crack_width_cm etc).
    Returns dict with length_cm, width_cm, area_cm2, depth_cm.
    """
    # Priority 1: thermal crack_size block
    cs = scan.get('crack_size') or scan.get('thermal_data', {}).get('crack_size') or {}
    length = cs.get('estimated_length_cm') or cs.get('crack_length_cm') or 0
    width  = cs.get('estimated_width_cm')  or cs.get('crack_width_cm')  or 0
    area   = cs.get('estimated_area_cm2')  or cs.get('crack_area_cm2')  or 0
    depth  = (scan.get('thermal_data') or scan).get('estimated_depth_cm', 0)

    # Priority 2: flat fields from report-parsed save
    if not length:
        length = scan.get('crack_length_cm', 0)
    if not width:
        width  = scan.get('crack_width_cm', 0)
    if not area:
        area   = scan.get('crack_area_cm2', 0)
    if not depth:
        depth  = scan.get('crack_depth_cm', 0)

    # Priority 3: detections list (camera-based)
    if not length:
        for det in scan.get('detections', []):
            length = length or det.get('length', 0)
            width  = width  or det.get('width', 0)

    return {
        'length_cm': round(float(length or 0), 1),
        'width_cm':  round(float(width  or 0), 1),
        'area_cm2':  round(float(area   or 0), 1),
        'depth_cm':  round(float(depth  or 0), 1),
    }

# Register after function is defined
app.jinja_env.filters['extract_size'] = extract_crack_size


def analyze_crack_growth(scans):
    """Analyze crack growth between scans — includes size metrics"""
    if len(scans) < 2:
        return None

    baseline = scans[0]
    latest   = scans[-1]

    b_size = extract_crack_size(baseline)
    l_size = extract_crack_size(latest)

    baseline_cracks = baseline.get('detections', [])
    latest_cracks   = latest.get('detections', [])

    # Growth calculations (area is the primary growth indicator)
    def pct(new, old):
        if old > 0:
            return round(((new - old) / old) * 100, 1)
        return 0.0

    length_growth_pct = pct(l_size['length_cm'], b_size['length_cm'])
    width_growth_pct  = pct(l_size['width_cm'],  b_size['width_cm'])
    area_growth_pct   = pct(l_size['area_cm2'],  b_size['area_cm2'])
    max_growth        = max(length_growth_pct, width_growth_pct, area_growth_pct)

    if max_growth < 5:
        status  = "OK"
        level   = "success"
        message = "No significant crack growth detected. Continue monitoring."
    elif max_growth < 15:
        status  = "MONITOR"
        level   = "warning"
        message = "Slight crack growth detected. Monitor closely in next inspection."
    elif max_growth < 30:
        status  = "ACTION NEEDED"
        level   = "danger"
        message = "Significant crack growth detected! Immediate structural assessment recommended."
    else:
        status  = "CRITICAL"
        level   = "danger"
        message = "CRITICAL growth! Immediate action required."

    return {
        'baseline_day':   baseline.get('day_number', 0),
        'latest_day':     latest.get('day_number', 0),
        'baseline_count': len(baseline_cracks),
        'latest_count':   len(latest_cracks),
        'growth_percent': max_growth,
        'status':  status,
        'level':   level,
        'message': message,
        'days_elapsed': latest.get('day_number', 0) - baseline.get('day_number', 0),
        # Size snapshots
        'baseline_size': b_size,
        'latest_size':   l_size,
        # Per-dimension growth
        'length_growth_cm':  round(l_size['length_cm'] - b_size['length_cm'], 1),
        'width_growth_cm':   round(l_size['width_cm']  - b_size['width_cm'],  1),
        'area_growth_cm2':   round(l_size['area_cm2']  - b_size['area_cm2'],  1),
        'depth_change_cm':   round(l_size['depth_cm']  - b_size['depth_cm'],  1),
        'length_growth_pct': length_growth_pct,
        'width_growth_pct':  width_growth_pct,
        'area_growth_pct':   area_growth_pct,
    }

def load_session_files():
    """Load all session JSON files"""
    files = []
    pattern = os.path.join(DATA_DIR, "session_*.json")
    for filepath in glob.glob(pattern):
        try:
            stat = os.stat(filepath)
            files.append({
                'name': os.path.basename(filepath),
                'path': filepath,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        except:
            pass
    return sorted(files, key=lambda x: x['modified'], reverse=True)

def load_csv_files():
    """Load all CSV files"""
    files = []
    pattern = os.path.join(DATA_DIR, "distance_log_*.csv")
    for filepath in glob.glob(pattern):
        try:
            stat = os.stat(filepath)
            files.append({
                'name': os.path.basename(filepath),
                'path': filepath,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        except:
            pass
    return sorted(files, key=lambda x: x['modified'], reverse=True)


def load_reports():
    """
    Load all scan reports from ~/crack_data/reports/
    Sorted by file modification time DESC (newest first) — reliable regardless of filename.
    """
    reports_dir = os.path.expanduser("~/crack_data/reports")
    os.makedirs(reports_dir, exist_ok=True)

    reports = []
    for filepath in glob.glob(os.path.join(reports_dir, "*.txt")):
        try:
            stat  = os.stat(filepath)
            name  = os.path.basename(filepath)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            size  = stat.st_size

            # Parse building name from filename
            building = 'Scan Report'
            parts = name.replace('.txt', '').split('_')
            if not name.startswith('scan_report_'):
                # INHS_Building_2026-10-16_231603.txt
                date_idx = None
                for i, p in enumerate(parts):
                    if len(p) == 10 and p.count('-') == 2:
                        date_idx = i
                        break
                if date_idx is not None:
                    building = ' '.join(parts[:date_idx]).replace('_', ' ')

            # Count cracks and positions from file content
            crack_count = 0
            positions   = 0
            try:
                with open(filepath, 'r', errors='ignore') as f:
                    for line in f:
                        if ':' in line:
                            key = line.split(':')[0].strip()
                            val = line.split(':')[1].strip()
                            if key in ('Cracks Detected', 'Cracks detected'):
                                try: crack_count = int(val)
                                except: pass
                            if key in ('Total Positions', 'Positions scanned'):
                                try: positions = int(val)
                                except: pass
            except:
                pass

            reports.append({
                'name':     name,
                'path':     filepath,
                'building': building,
                'scan_date': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                'mtime':    stat.st_mtime,   # raw float for reliable sort
                'size_kb':  round(size / 1024, 1),
                'cracks':   crack_count,
                'positions': positions,
            })
        except:
            pass

    # Sort by file modification time — newest first
    return sorted(reports, key=lambda x: x['mtime'], reverse=True)

# ========================================
# HTML TEMPLATES
# ========================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crack Monitoring Analytics</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 {
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            font-size: 16px;
        }
        
        /* Alert Toast */
        .alert-section {
            margin-bottom: 20px;
        }
        .alert-toast {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            border-left: 6px solid;
            animation: slideIn 0.5s ease;
        }
        @keyframes slideIn {
            from {
                transform: translateX(-100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        .alert-toast.success {
            border-color: #10b981;
        }
        .alert-toast.warning {
            border-color: #f59e0b;
        }
        .alert-toast.danger {
            border-color: #ef4444;
        }
        .alert-icon {
            font-size: 48px;
            display: inline-block;
            margin-right: 20px;
            vertical-align: middle;
        }
        .alert-content {
            display: inline-block;
            vertical-align: middle;
        }
        .alert-status {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .alert-status.success { color: #10b981; }
        .alert-status.warning { color: #f59e0b; }
        .alert-status.danger { color: #ef4444; }
        .alert-message {
            color: #666;
            font-size: 16px;
        }
        .alert-details {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 14px;
        }
        
        /* Comparison Table */
        .comparison-section {
            background: white;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 24px;
        }
        .comparison-table {
            width: 100%;
            border-collapse: collapse;
        }
        .comparison-table th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: 600;
        }
        .comparison-table td {
            padding: 15px;
            border-bottom: 1px solid #eee;
            text-align: center;
        }
        .comparison-table tr:hover {
            background: #f9f9f9;
        }
        .day-label {
            font-weight: bold;
            color: #667eea;
            font-size: 18px;
        }
        .crack-count {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .growth-indicator {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }
        .growth-positive {
            background: #fef3c7;
            color: #d97706;
        }
        .growth-negative {
            background: #d1fae5;
            color: #059669;
        }

        /* Crack Size Cards */
        .size-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        .size-card {
            background: #f9fafb;
            border-radius: 12px;
            padding: 18px;
            border: 2px solid #e5e7eb;
        }
        .size-card-title {
            font-size: 13px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
            font-weight: 600;
        }
        .size-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #e5e7eb;
            font-size: 14px;
        }
        .size-row:last-child { border-bottom: none; }
        .size-label { color: #6b7280; }
        .size-val   { font-weight: bold; color: #1f2937; }
        .size-val.growing { color: #ef4444; }
        .size-val.stable  { color: #10b981; }

        /* Growth breakdown */
        .growth-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 15px;
        }
        .growth-metric {
            background: #f9fafb;
            border-radius: 10px;
            padding: 14px;
            text-align: center;
            border: 2px solid #e5e7eb;
        }
        .growth-metric .label { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; }
        .growth-metric .delta { font-size: 20px; font-weight: bold; margin: 4px 0; }
        .growth-metric .delta.pos { color: #ef4444; }
        .growth-metric .delta.neg { color: #10b981; }
        .growth-metric .pct   { font-size: 12px; color: #6b7280; }
        
        /* Save Scan Form */
        .save-scan-section {
            background: white;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-weight: 600;
        }
        input[type="number"], input[type="text"], select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
        }
        input[type="number"]:focus, input[type="text"]:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            padding: 12px 30px;
            border-radius: 8px;
            border: none;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5568d3;
        }
        .btn-success {
            background: #10b981;
            color: white;
        }
        .btn-success:hover {
            background: #059669;
        }
        
        /* Files Section */
        .files-section {
            background: white;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        tr:hover {
            background: #f9f9f9;
        }
        .download-btn {
            background: #10b981;
            color: white;
            padding: 8px 16px;
            border-radius: 5px;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
        }
        .download-btn:hover {
            background: #059669;
        }
        .no-data {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        .control-link {
            display: inline-block;
            margin-top: 15px;
            margin-right: 10px;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
        }
        .control-link:hover {
            background: #5568d3;
        }
        .nav-buttons {
            margin-top: 15px;
        }
        
        .info-note {
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 15px;
            margin-top: 20px;
            border-radius: 5px;
            color: #1e40af;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Multi-Day Crack Monitoring System</h1>
            <p class="subtitle">Compare crack progression over time and get smart alerts</p>
            <div class="nav-buttons">
                <a href="http://192.168.168.111:5000" class="control-link">🎮 Robot Control</a>
                <a href="/" class="control-link" style="background: #10b981;">🔄 Refresh Data</a>
            </div>
        </div>
        
        {% if analysis %}
        <div class="alert-section">
            <div class="alert-toast {{ analysis.level }}">
                <span class="alert-icon">
                    {% if analysis.level == 'success' %}✅{% endif %}
                    {% if analysis.level == 'warning' %}⚠️{% endif %}
                    {% if analysis.level == 'danger' %}🚨{% endif %}
                </span>
                <div class="alert-content">
                    <div class="alert-status {{ analysis.level }}">{{ analysis.status }}</div>
                    <div class="alert-message">{{ analysis.message }}</div>
                    <div class="alert-details">
                        Day {{ analysis.baseline_day }} → Day {{ analysis.latest_day }}
                        ({{ analysis.days_elapsed }} days elapsed) |
                        Max growth: {{ analysis.growth_percent }}% |
                        Cracks detected: {{ analysis.baseline_count }} → {{ analysis.latest_count }}
                    </div>
                </div>
            </div>

            <!-- Size comparison cards -->
            <div class="size-grid" style="margin-top:15px;">
                <div class="size-card">
                    <div class="size-card-title">📏 Baseline — Day {{ analysis.baseline_day }}</div>
                    <div class="size-row"><span class="size-label">Length</span><span class="size-val">{{ analysis.baseline_size.length_cm }} cm</span></div>
                    <div class="size-row"><span class="size-label">Width</span> <span class="size-val">{{ analysis.baseline_size.width_cm }} cm</span></div>
                    <div class="size-row"><span class="size-label">Area</span>  <span class="size-val">{{ analysis.baseline_size.area_cm2 }} cm²</span></div>
                    <div class="size-row"><span class="size-label">Depth</span> <span class="size-val">{{ analysis.baseline_size.depth_cm }} cm</span></div>
                </div>
                <div class="size-card">
                    <div class="size-card-title">📏 Latest — Day {{ analysis.latest_day }}</div>
                    <div class="size-row"><span class="size-label">Length</span><span class="size-val {% if analysis.length_growth_cm > 0 %}growing{% else %}stable{% endif %}">{{ analysis.latest_size.length_cm }} cm</span></div>
                    <div class="size-row"><span class="size-label">Width</span> <span class="size-val {% if analysis.width_growth_cm > 0 %}growing{% else %}stable{% endif %}">{{ analysis.latest_size.width_cm }} cm</span></div>
                    <div class="size-row"><span class="size-label">Area</span>  <span class="size-val {% if analysis.area_growth_cm2 > 0 %}growing{% else %}stable{% endif %}">{{ analysis.latest_size.area_cm2 }} cm²</span></div>
                    <div class="size-row"><span class="size-label">Depth</span> <span class="size-val {% if analysis.depth_change_cm > 0 %}growing{% else %}stable{% endif %}">{{ analysis.latest_size.depth_cm }} cm</span></div>
                </div>
            </div>

            <!-- Growth breakdown row -->
            <div class="growth-grid">
                <div class="growth-metric">
                    <div class="label">Length Δ</div>
                    <div class="delta {% if analysis.length_growth_cm > 0 %}pos{% else %}neg{% endif %}">{{ '%+.1f'|format(analysis.length_growth_cm) }} cm</div>
                    <div class="pct">{{ '%+.1f'|format(analysis.length_growth_pct) }}%</div>
                </div>
                <div class="growth-metric">
                    <div class="label">Width Δ</div>
                    <div class="delta {% if analysis.width_growth_cm > 0 %}pos{% else %}neg{% endif %}">{{ '%+.1f'|format(analysis.width_growth_cm) }} cm</div>
                    <div class="pct">{{ '%+.1f'|format(analysis.width_growth_pct) }}%</div>
                </div>
                <div class="growth-metric">
                    <div class="label">Area Δ</div>
                    <div class="delta {% if analysis.area_growth_cm2 > 0 %}pos{% else %}neg{% endif %}">{{ '%+.1f'|format(analysis.area_growth_cm2) }} cm²</div>
                    <div class="pct">{{ '%+.1f'|format(analysis.area_growth_pct) }}%</div>
                </div>
                <div class="growth-metric">
                    <div class="label">Depth Δ</div>
                    <div class="delta {% if analysis.depth_change_cm > 0 %}pos{% else %}neg{% endif %}">{{ '%+.1f'|format(analysis.depth_change_cm) }} cm</div>
                    <div class="pct">&nbsp;</div>
                </div>
            </div>
        </div>
        {% endif %}
        
        {% if scans %}
        <!-- ================================================ -->
        <!-- CRACK GROWTH MONITORING TABLES                    -->
        <!-- ================================================ -->
        <div class="comparison-section" style="margin-bottom:20px;">
            <h2>📊 Crack Growth Monitoring Tables</h2>

            <!-- TABLE 1: Inspection Period Mean Change -->
            <h3 style="margin:20px 0 10px;color:#667eea">Table 1 — Trial Period Mean Change</h3>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Trial Period</th>
                        <th>Mean Width Change</th>
                        <th>Mean Length Change</th>
                    </tr>
                </thead>
                <tbody>
                    {% set ns = namespace(prev=none) %}
                    {% for scan in scans %}
                    {% if ns.prev %}
                    {% set prev_sz = ns.prev | extract_size %}
                    {% set curr_sz = scan | extract_size %}
                    {% set dw = curr_sz.width_cm - prev_sz.width_cm %}
                    {% set dl = curr_sz.length_cm - prev_sz.length_cm %}
                    <tr>
                        <td>Trial {{ ns.prev.trial_number if ns.prev.trial_number else ns.prev.day_number }} → {{ scan.trial_number if scan.trial_number else scan.day_number }}</td>
                        <td style="text-align:center;color:{% if dw > 0 %}#ef4444{% else %}#10b981{% endif %}">
                            {{ '%+.2f'|format(dw) }} cm
                        </td>
                        <td style="text-align:center;color:{% if dl > 0 %}#ef4444{% else %}#10b981{% endif %}">
                            {{ '%+.2f'|format(dl) }} cm
                        </td>
                    </tr>
                    {% endif %}
                    {% set ns.prev = scan %}
                    {% endfor %}
                    <!-- Overall Mean Row -->
                    {% if scans|length >= 2 %}
                    {% set first_sz = scans[0] | extract_size %}
                    {% set last_sz  = scans[-1] | extract_size %}
                    {% set total_w = last_sz.width_cm  - first_sz.width_cm %}
                    {% set total_l = last_sz.length_cm - first_sz.length_cm %}
                    <tr style="background:#f0f4ff;font-weight:bold">
                        <td>Overall Mean Change</td>
                        <td style="text-align:center;color:{% if total_w > 0 %}#ef4444{% else %}#10b981{% endif %}">
                            {{ '%+.2f'|format(total_w) }} cm
                        </td>
                        <td style="text-align:center;color:{% if total_l > 0 %}#ef4444{% else %}#10b981{% endif %}">
                            {{ '%+.2f'|format(total_l) }} cm
                        </td>
                    </tr>
                    <!-- Screening Classification -->
                    {% set max_change = [total_w, total_l] | max %}
                    <tr style="background:#fffbeb;">
                        <td colspan="3" style="padding:12px">
                            <strong>Screening Classification:</strong>
                            {% if scans|length < 2 %}
                            <span style="color:#f59e0b">Insufficient Data</span>
                            {% elif max_change < 0.2 %}
                            <span style="color:#10b981">✅ Low Priority</span>
                            {% elif max_change < 0.5 %}
                            <span style="color:#f59e0b">⚠️ Moderate Priority</span>
                            {% else %}
                            <span style="color:#ef4444">🚨 High Priority</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endif %}
                </tbody>
            </table>

            <!-- TABLE 2: Trial Summary -->
            <h3 style="margin:20px 0 10px;color:#667eea">Table 2 — Trial Summary (Trial 1 → {{ scans|length }})</h3>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Trial</th>
                        <th>Location</th>
                        <th>Crack Width</th>
                        <th>Crack Length</th>
                        <th>Thermal Anomaly</th>
                    </tr>
                </thead>
                <tbody>
                    {% for scan in scans %}
                    {% set sz = scan | extract_size %}
                    <tr>
                        <td><span class="day-label">Trial {{ scan.trial_number if scan.trial_number else scan.day_number }}</span></td>
                        <td>{{ scan.location if scan.location else '—' }}</td>
                        <td style="text-align:center">{{ sz.width_cm ~ ' cm' if sz.width_cm > 0 else '—' }}</td>
                        <td style="text-align:center">{{ sz.length_cm ~ ' cm' if sz.length_cm > 0 else '—' }}</td>
                        <td style="text-align:center">
                            {% if scan.thermal_anomaly %}
                            <span style="color:#ef4444;font-weight:bold">— Detected</span>
                            {% else %}
                            <span style="color:#10b981">— Not Detected</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            <p style="color:#666;font-size:12px;margin-top:8px">
                Data auto-populated from scan records. Use "Save Scan for Trial Comparison" to add measurements for each trial.
            </p>
        </div>

        <!-- Multi-Trial Comparison Table -->
        <div class="comparison-section">
            <h2>📋 Multi-Trial Comparison</h2>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Trial</th>
                        <th>Date</th>
                        <th>Cracks Detected</th>
                        <th>Length (cm)</th>
                        <th>Width (cm)</th>
                        <th>Area (cm²)</th>
                        <th>Depth (cm)</th>
                        <th>Status</th>
                        <th>Download</th>
                    </tr>
                </thead>
                <tbody>
                    {% for scan in scans %}
                    {% set sz = scan | extract_size %}
                    <tr>
                        <td><span class="day-label">Trial {{ scan.trial_number if scan.trial_number else scan.day_number }}</span></td>
                        <td>{{ scan.scan_date }}</td>
                        <td><span class="crack-count">{{ scan.crack_count if scan.crack_count else scan.detections|length }}</span></td>
                        <td><strong>{{ sz.length_cm if sz.length_cm > 0 else '—' }}</strong></td>
                        <td><strong>{{ sz.width_cm if sz.width_cm > 0 else '—' }}</strong></td>
                        <td><strong>{{ sz.area_cm2 if sz.area_cm2 > 0 else '—' }}</strong></td>
                        <td><strong>{{ sz.depth_cm if sz.depth_cm > 0 else '—' }}</strong></td>
                        <td>
                            {% if loop.index > 1 %}
                                {% set prev_cracks = scans[loop.index-2].crack_count if scans[loop.index-2].crack_count else scans[loop.index-2].detections|length %}
                                {% set curr_cracks = scan.crack_count if scan.crack_count else scan.detections|length %}
                                {% if prev_cracks < curr_cracks %}
                                <span class="growth-indicator growth-positive">▲ Growth</span>
                                {% else %}
                                <span class="growth-indicator growth-negative">✓ Stable</span>
                                {% endif %}
                            {% else %}
                            <span class="growth-indicator growth-negative">✓ Baseline</span>
                            {% endif %}
                        </td>
                        <td>
                            <a href="/download_scan/{{ scan.day_number }}" class="download-btn">📥 Download</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}
        
        <div class="save-scan-section">
            <h2>💾 Save Current Scan</h2>
            <form action="/save_scan" method="POST">
                <div class="form-group">
                    <label>Trial Number (1, 2, 3, 4...)</label>
                    <input type="number" name="trial_number" required placeholder="e.g., 1">
                </div>
                <div class="form-group">
                    <label>Location (e.g., Column A-03)</label>
                    <input type="text" name="location" placeholder="e.g., Column A-03, Wall Section B">
                </div>
                <div class="form-group">
                    <label>Report File to Save</label>
                    <select name="report_file" required>
                        {% if reports %}
                            {% for report in reports %}
                            <option value="{{ report.name }}">{{ report.name }} ({{ report.scan_date }})</option>
                            {% endfor %}
                        {% else %}
                            <option value="">No reports found - run a scan first</option>
                        {% endif %}
                    </select>
                </div>
                <button type="submit" class="btn btn-primary">💾 Save Scan for Trial Comparison</button>
            </form>
            
            <div class="info-note">
                <strong>💡 How to use:</strong> After each inspection (Trial 1, 2, 3, etc.), save the scan data here. 
                The system will automatically compare and alert you about crack growth.
            </div>
        </div>
        
                <div class="files-section">
            <h2>Scan Reports</h2>
            {% if reports %}
            <div style="text-align:right;margin-bottom:10px;">
                <a href="/delete_all_reports"
                   class="download-btn"
                   style="background:#ef4444"
                   onclick="return confirm('Delete ALL {{ reports|length }} reports?')">
                   Delete All Reports
                </a>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Building</th>
                        <th>Date and Time</th>
                        <th>Positions</th>
                        <th>Cracks</th>
                        <th>Size</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in reports %}
                    <tr style="background: {% if r.cracks > 0 %}#fff5f5{% else %}white{% endif %}">
                        <td>
                            <strong>{{ r.building }}</strong><br>
                            <small style="color:#999;font-size:11px">{{ r.name }}</small>
                        </td>
                        <td>{{ r.scan_date }}</td>
                        <td>{{ r.positions }}</td>
                        <td>
                            {% if r.cracks > 0 %}
                            <span style="color:#ef4444;font-weight:bold">{{ r.cracks }} crack(s)</span>
                            {% else %}
                            <span style="color:#10b981">None</span>
                            {% endif %}
                        </td>
                        <td>{{ r.size_kb }} KB</td>
                        <td>
                            <a href="/download_report/{{ r.name }}" class="download-btn">Download</a>
                            &nbsp;
                            <a href="/delete_report/{{ r.name }}"
                               class="download-btn"
                               style="background:#ef4444"
                               onclick="return confirm('Delete this report?')">Delete</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="no-data">No scan reports yet. Run AUTO SCAN to generate.</div>
            {% endif %}
        </div>

        <div class="files-section">
            <h2>Raw Session Data</h2>
            {% if json_files %}
            <table>
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>Size</th>
                        <th>Date Modified</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for file in json_files %}
                    <tr>
                        <td>{{ file.name }}</td>
                        <td>{{ "%.2f"|format(file.size / 1024) }} KB</td>
                        <td>{{ file.modified.split('T')[0] }} {{ file.modified.split('T')[1].split('.')[0] }}</td>
                        <td>
                            <a href="/download/{{ file.name }}" class="download-btn">📥 Download</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="no-data">No session files yet. Start scanning to generate data!</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# ========================================
# ROUTES
# ========================================

@app.route('/')
def index():
    scans      = load_all_scans()
    json_files = load_session_files()
    csv_files  = load_csv_files()
    reports    = load_reports()
    analysis   = analyze_crack_growth(scans) if len(scans) >= 2 else None

    return render_template_string(
        DASHBOARD_HTML,
        scans=scans,
        json_files=json_files,
        csv_files=csv_files,
        reports=reports,
        analysis=analysis
    )

@app.route('/save_scan', methods=['POST'])
def save_scan():
    """Save a report as a trial scan for comparison"""
    try:
        trial_number = int(request.form.get('trial_number', 1))
        location = request.form.get('location', '')
        report_file = request.form.get('report_file', '')
        
        # Load the report data from TXT file
        report_path = os.path.join(os.path.expanduser("~/crack_data/reports"), report_file)
        
        # Default values
        crack_count  = 0
        positions    = 0
        crack_width  = 0.0
        crack_length = 0.0
        crack_area   = 0.0
        crack_depth  = 0.0
        thermal      = False
        
        # Parse report file
        if os.path.exists(report_path):
            try:
                with open(report_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if ':' in line:
                            key = line.split(':')[0].strip()
                            val = line.split(':')[1].strip()
                            if key in ('Cracks Detected', 'Cracks detected'):
                                try: crack_count = int(val)
                                except: pass
                            if key in ('Total Positions', 'Positions scanned'):
                                try: positions = int(val)
                                except: pass
                            if 'Crack Length' in key or 'Length' in key:
                                try: crack_length = float(val.split()[0])
                                except: pass
                            if 'Crack Width' in key or 'Width' in key:
                                try: crack_width = float(val.split()[0])
                                except: pass
                            if 'Crack Area' in key or 'Area' in key:
                                try: crack_area = float(val.split()[0])
                                except: pass
                            if 'Estimated Depth' in key or 'Depth' in key:
                                try: crack_depth = float(val.split()[0].replace('~',''))
                                except: pass
                            if 'Thermal' in key and 'anomaly' in line.lower():
                                thermal = True
                            if crack_count > 0:
                                thermal = True
            except:
                pass
        
        # Create trial scan record
        scan_record = {
            'trial_number': trial_number,
            'day_number': trial_number,  # For backwards compatibility
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'location': location,
            'crack_count': crack_count,
            'positions': positions,
            'crack_width_cm': crack_width,
            'crack_length_cm': crack_length,
            'crack_area_cm2': crack_area,
            'crack_depth_cm': crack_depth,
            'thermal_anomaly': thermal,
            'report_file': report_file,
            'detections': []  # For compatibility
        }
        
        # Save to scans directory
        scan_filepath = os.path.join(SCANS_DIR, f"trial_{trial_number}.json")
        with open(scan_filepath, 'w') as f:
            json.dump(scan_record, f, indent=2)
        
        return f'''
        <html>
        <head>
            <meta http-equiv="refresh" content="2;url=/">
            <style>
                body {{
                    font-family: Arial;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .message {{
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    text-align: center;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }}
                h1 {{ color: #10b981; }}
            </style>
        </head>
        <body>
            <div class="message">
                <h1>✅ Scan Saved!</h1>
                <p>Trial {trial_number} scan saved successfully! ({crack_count} cracks detected)</p>
                <p>Redirecting to dashboard...</p>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f"Error saving scan: {str(e)}", 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download a session file"""
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return "File not found", 404


@app.route('/download_report/<filename>')
def download_report(filename):
    """Download a scan report"""
    reports_dir = os.path.expanduser("~/crack_data/reports")
    filepath    = os.path.join(reports_dir, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return "Report not found", 404


@app.route('/delete_report/<filename>')
def delete_report(filename):
    """Delete a scan report"""
    reports_dir = os.path.expanduser("~/crack_data/reports")
    filepath    = os.path.join(reports_dir, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        return f"Error deleting: {e}", 500
    from flask import redirect
    return redirect('/')


@app.route('/delete_all_reports')
def delete_all_reports():
    """Delete all scan reports"""
    reports_dir = os.path.expanduser("~/crack_data/reports")
    try:
        for f in os.listdir(reports_dir):
            if f.endswith('.txt'):
                os.remove(os.path.join(reports_dir, f))
    except Exception as e:
        return f"Error: {e}", 500
    from flask import redirect
    return redirect('/')

@app.route('/download_scan/<int:day_number>')
def download_scan(day_number):
    """Download a specific day scan"""
    filepath = os.path.join(SCANS_DIR, f"day_{day_number}.json")
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=f"day_{day_number}_scan.json")
    return "Scan not found", 404

@app.route('/api/comparison')
def api_comparison():
    """API endpoint for comparison data including crack sizes"""
    scans = load_all_scans()
    # Attach extracted size to each scan for API consumers
    for scan in scans:
        scan['crack_size_extracted'] = extract_crack_size(scan)
    analysis = analyze_crack_growth(scans) if len(scans) >= 2 else None
    return jsonify({
        'scans': scans,
        'analysis': analysis
    })

# ========================================
# MAIN
# ========================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("MULTI-DAY CRACK MONITORING ANALYTICS")
    print("="*60)
    print("\n🔍 Features:")
    print("  • Day-by-day comparison (Day 0, 7, 14, 21, 28...)")
    print("  • Smart growth alerts")
    print("  • Downloadable reports")
    print("\nStarting analytics server...")
    print(f"\n🌐 ACCESS DASHBOARD:")
    print(f"  http://192.168.168.111:8080")
    print(f"\n📁 Data directories:")
    print(f"  Sessions: {DATA_DIR}")
    print(f"  Day scans: {SCANS_DIR}")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=8080, debug=False)
