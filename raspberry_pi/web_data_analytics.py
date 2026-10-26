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
                    if 'trial_number' not in data:
                        data['trial_number'] = data.get('day_number', 0)
                    scans.append(data)
            except:
                pass
    seen = set()
    unique = []
    for s in scans:
        if s['filepath'] not in seen:
            seen.add(s['filepath'])
            unique.append(s)
    return sorted(unique, key=lambda x: x.get('trial_number', x.get('day_number', 0)))

def extract_crack_size(scan):
    """Pull crack size from a scan record."""
    cs = scan.get('crack_size') or scan.get('thermal_data', {}).get('crack_size') or {}
    length = cs.get('estimated_length_cm') or cs.get('crack_length_cm') or 0
    width  = cs.get('estimated_width_cm')  or cs.get('crack_width_cm')  or 0
    area   = cs.get('estimated_area_cm2')  or cs.get('crack_area_cm2')  or 0
    depth  = (scan.get('thermal_data') or scan).get('estimated_depth_cm', 0)
    if not length: length = scan.get('crack_length_cm', 0)
    if not width:  width  = scan.get('crack_width_cm', 0)
    if not area:   area   = scan.get('crack_area_cm2', 0)
    if not depth:  depth  = scan.get('crack_depth_cm', 0)
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

app.jinja_env.filters['extract_size'] = extract_crack_size


def analyze_crack_growth(scans):
    """Analyze crack growth between scans."""
    if len(scans) < 2:
        return None

    baseline = scans[0]
    latest   = scans[-1]
    b_size = extract_crack_size(baseline)
    l_size = extract_crack_size(latest)
    baseline_cracks = baseline.get('detections', [])
    latest_cracks   = latest.get('detections', [])

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
        'baseline_size': b_size,
        'latest_size':   l_size,
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
    for filepath in glob.glob(os.path.join(DATA_DIR, "session_*.json")):
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
    for filepath in glob.glob(os.path.join(DATA_DIR, "distance_log_*.csv")):
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
    """Load all scan reports from ~/crack_data/reports/ sorted newest first."""
    reports_dir = os.path.expanduser("~/crack_data/reports")
    os.makedirs(reports_dir, exist_ok=True)
    reports = []
    for filepath in glob.glob(os.path.join(reports_dir, "*.txt")):
        try:
            stat  = os.stat(filepath)
            name  = os.path.basename(filepath)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            size  = stat.st_size
            building = 'Scan Report'
            parts = name.replace('.txt', '').split('_')
            if not name.startswith('scan_report_'):
                date_idx = None
                for i, p in enumerate(parts):
                    if len(p) == 10 and p.count('-') == 2:
                        date_idx = i
                        break
                if date_idx is not None:
                    building = ' '.join(parts[:date_idx]).replace('_', ' ')
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
                'name':      name,
                'path':      filepath,
                'building':  building,
                'scan_date': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                'mtime':     stat.st_mtime,
                'size_kb':   round(size / 1024, 1),
                'cracks':    crack_count,
                'positions': positions,
            })
        except:
            pass
    return sorted(reports, key=lambda x: x['mtime'], reverse=True)


# ========================================
# HTML TEMPLATE
# ========================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Crack Analytics</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg:      #060d1a;
            --card:    #0c1526;
            --card2:   #101d30;
            --border:  #1a2d4a;
            --border2: #223556;
            --accent:  #3b82f6;
            --accent2: #60a5fa;
            --green:   #22c55e;
            --red:     #ef4444;
            --orange:  #f97316;
            --yellow:  #eab308;
            --text:    #e2e8f0;
            --muted:   #64748b;
            --muted2:  #94a3b8;
            --r:       12px;
            --rs:      8px;
        }
        *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; font-size:14px; }

        /* TOPBAR */
        .topbar {
            position:sticky; top:0; z-index:100;
            height:56px; background:rgba(6,13,26,.92);
            backdrop-filter:blur(12px);
            border-bottom:1px solid var(--border);
            display:flex; align-items:center; justify-content:space-between;
            padding:0 20px;
        }
        .brand { display:flex; align-items:center; gap:10px; }
        .brand-icon {
            width:34px; height:34px;
            background:linear-gradient(135deg,#1d4ed8,#3b82f6);
            border-radius:8px; display:flex; align-items:center; justify-content:center;
            font-size:18px; box-shadow:0 0 16px rgba(59,130,246,.4);
        }
        .brand-name { font-size:15px; font-weight:800; color:white; letter-spacing:-.4px; }
        .brand-sub  { font-size:10px; color:var(--muted2); margin-top:1px; }
        .nav-links  { display:flex; gap:8px; }
        .nav-btn {
            padding:6px 14px; border-radius:6px; font-size:12px; font-weight:600;
            text-decoration:none; border:1px solid var(--border2);
            color:var(--muted2); background:var(--card); transition:all .15s;
        }
        .nav-btn:hover { color:var(--accent2); border-color:var(--accent); }
        .nav-btn.primary { background:rgba(59,130,246,.12); color:var(--accent2); border-color:rgba(59,130,246,.3); }

        /* WRAP */
        .wrap { max-width:1360px; margin:0 auto; padding:16px; }

        /* CARD */
        .card { background:var(--card); border:1px solid var(--border); border-radius:var(--r); overflow:hidden; margin-bottom:14px; }
        .card-head {
            padding:11px 16px; border-bottom:1px solid var(--border);
            background:var(--card2); display:flex; align-items:center; gap:8px;
        }
        .card-title { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:1.4px; color:var(--muted2); }
        .card-body  { padding:16px; }

        /* ALERT */
        .alert {
            border-radius:var(--r); padding:16px 20px;
            display:flex; align-items:flex-start; gap:16px; margin-bottom:14px;
        }
        .alert-icon   { font-size:32px; flex-shrink:0; }
        .alert-status { font-size:18px; font-weight:800; margin-bottom:4px; }
        .alert-msg    { font-size:13px; color:var(--muted2); }
        .alert-details{ font-size:11px; color:var(--muted); margin-top:8px; }
        .alert.success{ background:rgba(34,197,94,.07);  border:1px solid rgba(34,197,94,.2); }
        .alert.warning{ background:rgba(249,115,22,.07); border:1px solid rgba(249,115,22,.2); }
        .alert.danger { background:rgba(239,68,68,.07);  border:1px solid rgba(239,68,68,.2); }
        .alert.success .alert-status { color:var(--green); }
        .alert.warning .alert-status { color:var(--orange); }
        .alert.danger  .alert-status { color:var(--red); }

        /* SIZE COMPARISON */
        .size-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px; }
        .size-card { background:var(--card2); border:1px solid var(--border); border-radius:var(--rs); padding:14px; }
        .size-card-title { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:10px; font-weight:600; }
        .size-row { display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid var(--border); font-size:12px; }
        .size-row:last-child { border-bottom:none; }
        .size-lbl { color:var(--muted2); }
        .size-val { font-weight:700; font-family:'JetBrains Mono',monospace; }
        .size-val.growing { color:var(--red); }
        .size-val.stable  { color:var(--green); }

        /* GROWTH METRICS */
        .growth-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
        .growth-card { background:var(--card2); border:1px solid var(--border); border-radius:var(--rs); padding:12px 8px; text-align:center; }
        .g-lbl { font-size:9px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; }
        .g-val { font-size:18px; font-weight:700; font-family:'JetBrains Mono',monospace; margin:5px 0 2px; }
        .g-val.pos { color:var(--red); }
        .g-val.neg { color:var(--green); }
        .g-pct { font-size:11px; color:var(--muted); }

        /* CHARTS */
        .charts-2col { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px; }
        .chart-wrap  { background:var(--card2); border:1px solid var(--border); border-radius:var(--rs); padding:14px; }
        .chart-lbl   { font-size:11px; font-weight:700; color:var(--muted2); text-align:center; margin-bottom:10px; text-transform:uppercase; letter-spacing:1px; }
        .chart-canvas{ max-height:240px; }
        @media(max-width:768px){ .charts-2col{ grid-template-columns:1fr; } }

        /* TABLES */
        .tbl { width:100%; border-collapse:collapse; font-size:12px; }
        .tbl th { padding:9px 12px; background:var(--card2); border:1px solid var(--border); color:var(--muted); font-weight:600; text-transform:uppercase; letter-spacing:.7px; font-size:10px; text-align:center; }
        .tbl th:first-child { text-align:left; }
        .tbl td { padding:9px 12px; border:1px solid var(--border); text-align:center; }
        .tbl td:first-child { text-align:left; }
        .tbl tr:hover td { background:rgba(59,130,246,.04); }
        .tbl-overall  { background:rgba(59,130,246,.05); font-weight:700; }
        .tbl-screening{ background:rgba(234,179,8,.04); }

        .day-lbl  { font-weight:700; color:var(--accent2); font-family:'JetBrains Mono',monospace; font-size:13px; }
        .crack-num{ font-size:18px; font-weight:700; font-family:'JetBrains Mono',monospace; }

        .badge { display:inline-block; padding:3px 10px; border-radius:12px; font-weight:700; font-size:11px; }
        .badge-baseline{ background:rgba(34,197,94,.1);  color:var(--green);  border:1px solid rgba(34,197,94,.25); }
        .badge-growth  { background:rgba(249,115,22,.1); color:var(--orange); border:1px solid rgba(249,115,22,.25); }
        .badge-stable  { background:rgba(34,197,94,.1);  color:var(--green);  border:1px solid rgba(34,197,94,.25); }

        .dl-btn { display:inline-block; padding:5px 12px; border-radius:6px; background:rgba(34,197,94,.1); color:var(--green); border:1px solid rgba(34,197,94,.25); text-decoration:none; font-size:11px; font-weight:600; transition:all .15s; }
        .dl-btn:hover { background:rgba(34,197,94,.2); }
        .dl-btn.danger{ background:rgba(239,68,68,.1); color:var(--red); border-color:rgba(239,68,68,.25); }
        .dl-btn.danger:hover{ background:rgba(239,68,68,.2); }

        /* FORM */
        .form-group { margin-bottom:14px; }
        .form-group label { display:block; font-size:11px; color:var(--muted2); margin-bottom:5px; font-weight:600; text-transform:uppercase; letter-spacing:.8px; }
        .form-group input,
        .form-group select { width:100%; padding:9px 12px; background:var(--card2); border:1px solid var(--border2); border-radius:var(--rs); color:var(--text); font-size:13px; font-family:'Inter',sans-serif; transition:border-color .2s; }
        .form-group input:focus,
        .form-group select:focus { outline:none; border-color:var(--accent); }
        .form-group select option { background:var(--card2); }
        .btn-submit { padding:10px 24px; border-radius:var(--rs); border:none; background:linear-gradient(135deg,#1d4ed8,#3b82f6); color:white; font-size:13px; font-weight:700; cursor:pointer; transition:all .15s; box-shadow:0 4px 14px rgba(59,130,246,.3); }
        .btn-submit:hover { transform:translateY(-1px); box-shadow:0 6px 20px rgba(59,130,246,.45); }

        .info-note { background:rgba(59,130,246,.07); border:1px solid rgba(59,130,246,.2); border-radius:var(--rs); padding:12px 14px; font-size:12px; color:var(--muted2); margin-top:14px; line-height:1.6; }
        .info-note b { color:var(--accent2); }
        .no-data { text-align:center; padding:32px; color:var(--muted); font-size:13px; }

        ::-webkit-scrollbar { width:3px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:var(--border2); border-radius:4px; }

        @media(max-width:900px){
            .size-grid   { grid-template-columns:1fr; }
            .growth-grid { grid-template-columns:repeat(2,1fr); }
        }
        @media(max-width:600px){
            .growth-grid { grid-template-columns:1fr 1fr; }
            .nav-links   { display:none; }
        }
    </style>
</head>
<body>

    <header class="topbar">
        <div class="brand">
            <div class="brand-icon">&#x1F4CA;</div>
            <div>
                <div class="brand-name">CrackBot Analytics</div>
                <div class="brand-sub">Multi-Trial Crack Monitoring</div>
            </div>
        </div>
        <div class="nav-links">
            <a href="http://192.168.168.111:5000" class="nav-btn">&#x1F3AE; Robot Control</a>
            <a href="/" class="nav-btn primary">&#x1F504; Refresh</a>
        </div>
    </header>

    <div class="wrap">

        {% if analysis %}
        <div class="alert {{ analysis.level }}">
            <div class="alert-icon">
                {% if analysis.level == 'success' %}&#x2705;{% endif %}
                {% if analysis.level == 'warning' %}&#x26A0;&#xFE0F;{% endif %}
                {% if analysis.level == 'danger' %}&#x1F6A8;{% endif %}
            </div>
            <div>
                <div class="alert-status">{{ analysis.status }}</div>
                <div class="alert-msg">{{ analysis.message }}</div>
                <div class="alert-details">
                    Trial {{ analysis.baseline_day }} &rarr; Trial {{ analysis.latest_day }}
                    &nbsp;&middot;&nbsp; {{ analysis.days_elapsed }} trials elapsed
                    &nbsp;&middot;&nbsp; Max growth: <b>{{ analysis.growth_percent }}%</b>
                    &nbsp;&middot;&nbsp; Cracks: {{ analysis.baseline_count }} &rarr; {{ analysis.latest_count }}
                </div>
            </div>
        </div>

        <div class="size-grid">
            <div class="size-card">
                <div class="size-card-title">&#x1F4CF; Baseline &mdash; Trial {{ analysis.baseline_day }}</div>
                <div class="size-row"><span class="size-lbl">Length</span><span class="size-val">{{ analysis.baseline_size.length_cm }} cm</span></div>
                <div class="size-row"><span class="size-lbl">Width</span> <span class="size-val">{{ analysis.baseline_size.width_cm }} cm</span></div>
                <div class="size-row"><span class="size-lbl">Area</span>  <span class="size-val">{{ analysis.baseline_size.area_cm2 }} cm&sup2;</span></div>
                <div class="size-row"><span class="size-lbl">Depth</span> <span class="size-val">{{ analysis.baseline_size.depth_cm }} cm</span></div>
            </div>
            <div class="size-card">
                <div class="size-card-title">&#x1F4CF; Latest &mdash; Trial {{ analysis.latest_day }}</div>
                <div class="size-row"><span class="size-lbl">Length</span><span class="size-val {% if analysis.length_growth_cm > 0 %}growing{% else %}stable{% endif %}">{{ analysis.latest_size.length_cm }} cm</span></div>
                <div class="size-row"><span class="size-lbl">Width</span> <span class="size-val {% if analysis.width_growth_cm > 0 %}growing{% else %}stable{% endif %}">{{ analysis.latest_size.width_cm }} cm</span></div>
                <div class="size-row"><span class="size-lbl">Area</span>  <span class="size-val {% if analysis.area_growth_cm2 > 0 %}growing{% else %}stable{% endif %}">{{ analysis.latest_size.area_cm2 }} cm&sup2;</span></div>
                <div class="size-row"><span class="size-lbl">Depth</span> <span class="size-val {% if analysis.depth_change_cm > 0 %}growing{% else %}stable{% endif %}">{{ analysis.latest_size.depth_cm }} cm</span></div>
            </div>
        </div>
        <div class="growth-grid" style="margin-bottom:14px;">
            <div class="growth-card">
                <div class="g-lbl">Length &Delta;</div>
                <div class="g-val {% if analysis.length_growth_cm > 0 %}pos{% else %}neg{% endif %}">{{ '%+.1f'|format(analysis.length_growth_cm) }} cm</div>
                <div class="g-pct">{{ '%+.1f'|format(analysis.length_growth_pct) }}%</div>
            </div>
            <div class="growth-card">
                <div class="g-lbl">Width &Delta;</div>
                <div class="g-val {% if analysis.width_growth_cm > 0 %}pos{% else %}neg{% endif %}">{{ '%+.1f'|format(analysis.width_growth_cm) }} cm</div>
                <div class="g-pct">{{ '%+.1f'|format(analysis.width_growth_pct) }}%</div>
            </div>
            <div class="growth-card">
                <div class="g-lbl">Area &Delta;</div>
                <div class="g-val {% if analysis.area_growth_cm2 > 0 %}pos{% else %}neg{% endif %}">{{ '%+.1f'|format(analysis.area_growth_cm2) }} cm&sup2;</div>
                <div class="g-pct">{{ '%+.1f'|format(analysis.area_growth_pct) }}%</div>
            </div>
            <div class="growth-card">
                <div class="g-lbl">Depth &Delta;</div>
                <div class="g-val {% if analysis.depth_change_cm > 0 %}pos{% else %}neg{% endif %}">{{ '%+.1f'|format(analysis.depth_change_cm) }} cm</div>
                <div class="g-pct">&nbsp;</div>
            </div>
        </div>
        {% endif %}

        {% if scans|length >= 2 %}
        <div class="card">
            <div class="card-head"><span>&#x1F4C8;</span><span class="card-title">Crack Growth Analytics &mdash; {{ scans|length }} Trials</span></div>
            <div class="card-body">
                <div class="charts-2col">
                    <div class="chart-wrap">
                        <div class="chart-lbl">Crack Count Over Trials</div>
                        <canvas id="crackTrendChart" class="chart-canvas"></canvas>
                    </div>
                    <div class="chart-wrap">
                        <div class="chart-lbl">Growth Rate (%)</div>
                        <canvas id="growthRateChart" class="chart-canvas"></canvas>
                    </div>
                </div>
                <div class="chart-wrap" style="margin-top:12px;">
                    <div class="chart-lbl">Trial-by-Trial Comparison</div>
                    <canvas id="comparisonBarChart" class="chart-canvas"></canvas>
                </div>
            </div>
        </div>
        {% elif scans|length == 1 %}
        <div class="card">
            <div class="card-head"><span>&#x1F4C8;</span><span class="card-title">Crack Growth Analytics</span></div>
            <div class="card-body"><div class="no-data">Save at least 2 trials to see growth charts.</div></div>
        </div>
        {% endif %}

        {% if scans %}
        <div class="card">
            <div class="card-head"><span>&#x1F4CA;</span><span class="card-title">Table 1 &mdash; Trial Period Mean Change</span></div>
            <div class="card-body" style="overflow-x:auto;">
                <table class="tbl">
                    <thead><tr><th>Trial Period</th><th>Mean Width Change</th><th>Mean Length Change</th></tr></thead>
                    <tbody>
                        {% set ns = namespace(prev=none) %}
                        {% for scan in scans %}
                        {% if ns.prev %}
                        {% set prev_sz = ns.prev | extract_size %}
                        {% set curr_sz = scan | extract_size %}
                        {% set dw = curr_sz.width_cm - prev_sz.width_cm %}
                        {% set dl = curr_sz.length_cm - prev_sz.length_cm %}
                        <tr>
                            <td>Trial {{ ns.prev.trial_number if ns.prev.trial_number else ns.prev.day_number }} &rarr; {{ scan.trial_number if scan.trial_number else scan.day_number }}</td>
                            <td style="color:{% if dw > 0 %}var(--red){% else %}var(--green){% endif %};font-weight:600;font-family:'JetBrains Mono',monospace;">{{ '%+.2f'|format(dw) }} cm</td>
                            <td style="color:{% if dl > 0 %}var(--red){% else %}var(--green){% endif %};font-weight:600;font-family:'JetBrains Mono',monospace;">{{ '%+.2f'|format(dl) }} cm</td>
                        </tr>
                        {% endif %}
                        {% set ns.prev = scan %}
                        {% endfor %}
                        {% if scans|length >= 2 %}
                        {% set first_sz = scans[0] | extract_size %}
                        {% set last_sz  = scans[-1] | extract_size %}
                        {% set total_w = last_sz.width_cm  - first_sz.width_cm %}
                        {% set total_l = last_sz.length_cm - first_sz.length_cm %}
                        <tr class="tbl-overall">
                            <td>Overall Mean Change</td>
                            <td style="color:{% if total_w > 0 %}var(--red){% else %}var(--green){% endif %};font-family:'JetBrains Mono',monospace;">{{ '%+.2f'|format(total_w) }} cm</td>
                            <td style="color:{% if total_l > 0 %}var(--red){% else %}var(--green){% endif %};font-family:'JetBrains Mono',monospace;">{{ '%+.2f'|format(total_l) }} cm</td>
                        </tr>
                        {% set max_change = [total_w, total_l] | max %}
                        <tr class="tbl-screening">
                            <td colspan="3" style="padding:10px 12px;">
                                <strong>Screening Classification:</strong>&nbsp;
                                {% if scans|length < 2 %}<span style="color:var(--yellow)">Insufficient Data</span>
                                {% elif max_change < 0.2 %}<span style="color:var(--green)">&#x2705; Low Priority</span>
                                {% elif max_change < 0.5 %}<span style="color:var(--orange)">&#x26A0;&#xFE0F; Moderate Priority</span>
                                {% else %}<span style="color:var(--red)">&#x1F6A8; High Priority</span>{% endif %}
                            </td>
                        </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <div class="card-head"><span>&#x1F4CB;</span><span class="card-title">Table 2 &mdash; Trial Summary (Trial 1 &rarr; {{ scans|length }})</span></div>
            <div class="card-body" style="overflow-x:auto;">
                <table class="tbl">
                    <thead><tr><th>Trial</th><th>Location</th><th>Crack Width</th><th>Crack Length</th><th>Thermal Anomaly</th></tr></thead>
                    <tbody>
                        {% for scan in scans %}
                        {% set sz = scan | extract_size %}
                        <tr>
                            <td><span class="day-lbl">Trial {{ scan.trial_number if scan.trial_number else scan.day_number }}</span></td>
                            <td>{{ scan.location if scan.location else '&mdash;' }}</td>
                            <td>{{ sz.width_cm ~ ' cm' if sz.width_cm > 0 else '&mdash;' }}</td>
                            <td>{{ sz.length_cm ~ ' cm' if sz.length_cm > 0 else '&mdash;' }}</td>
                            <td>
                                {% if scan.thermal_anomaly %}
                                <span style="color:var(--red);font-weight:600">&mdash; Detected</span>
                                {% else %}
                                <span style="color:var(--green)">&mdash; Not Detected</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <div class="card-head"><span>&#x1F4CB;</span><span class="card-title">Multi-Trial Comparison</span></div>
            <div class="card-body" style="overflow-x:auto;">
                <table class="tbl">
                    <thead><tr><th>Trial</th><th>Date</th><th>Cracks</th><th>Length (cm)</th><th>Width (cm)</th><th>Area (cm&sup2;)</th><th>Depth (cm)</th><th>Status</th><th>Download</th></tr></thead>
                    <tbody>
                        {% for scan in scans %}
                        {% set sz = scan | extract_size %}
                        <tr>
                            <td><span class="day-lbl">Trial {{ scan.trial_number if scan.trial_number else scan.day_number }}</span></td>
                            <td style="font-size:11px;color:var(--muted2);">{{ scan.scan_date }}</td>
                            <td><span class="crack-num">{{ scan.crack_count if scan.crack_count else scan.detections|length }}</span></td>
                            <td style="font-family:'JetBrains Mono',monospace;">{{ sz.length_cm if sz.length_cm > 0 else '&mdash;' }}</td>
                            <td style="font-family:'JetBrains Mono',monospace;">{{ sz.width_cm if sz.width_cm > 0 else '&mdash;' }}</td>
                            <td style="font-family:'JetBrains Mono',monospace;">{{ sz.area_cm2 if sz.area_cm2 > 0 else '&mdash;' }}</td>
                            <td style="font-family:'JetBrains Mono',monospace;">{{ sz.depth_cm if sz.depth_cm > 0 else '&mdash;' }}</td>
                            <td>
                                {% if loop.index > 1 %}
                                    {% set prev_c = scans[loop.index-2].crack_count if scans[loop.index-2].crack_count else scans[loop.index-2].detections|length %}
                                    {% set curr_c = scan.crack_count if scan.crack_count else scan.detections|length %}
                                    {% if prev_c < curr_c %}<span class="badge badge-growth">&#x25B2; Growth</span>
                                    {% else %}<span class="badge badge-stable">&#x2713; Stable</span>{% endif %}
                                {% else %}<span class="badge badge-baseline">&#x2713; Baseline</span>{% endif %}
                            </td>
                            <td><a href="/download_scan/{{ scan.day_number }}" class="dl-btn">&#x1F4E5; Download</a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        <div class="card">
            <div class="card-head"><span>&#x1F4BE;</span><span class="card-title">Save Current Scan for Trial Comparison</span></div>
            <div class="card-body">
                <form action="/save_scan" method="POST">
                    <div class="form-group">
                        <label>Trial Number (1, 2, 3 ...)</label>
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
                                <option value="">No reports found &mdash; run a scan first</option>
                            {% endif %}
                        </select>
                    </div>
                    <button type="submit" class="btn-submit">&#x1F4BE; Save Scan</button>
                </form>
                <div class="info-note">
                    <b>How to use:</b> After each inspection (Trial 1, 2, 3 ...), save the scan data here.
                    The system will automatically compare and alert you about crack growth.
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-head">
                <span>&#x1F4C4;</span><span class="card-title">Scan Reports</span>
                {% if reports %}
                <a href="/delete_all_reports" class="dl-btn danger" style="margin-left:auto;font-size:10px;"
                   onclick="return confirm('Delete ALL {{ reports|length }} reports?')">Delete All</a>
                {% endif %}
            </div>
            <div class="card-body" style="overflow-x:auto;">
                {% if reports %}
                <table class="tbl">
                    <thead><tr><th>Building</th><th>Date &amp; Time</th><th>Positions</th><th>Cracks</th><th>Size</th><th>Actions</th></tr></thead>
                    <tbody>
                        {% for r in reports %}
                        <tr>
                            <td>
                                <div style="font-weight:600;">{{ r.building }}</div>
                                <div style="font-size:10px;color:var(--muted);">{{ r.name }}</div>
                            </td>
                            <td style="font-size:11px;color:var(--muted2);">{{ r.scan_date }}</td>
                            <td>{{ r.positions }}</td>
                            <td>{% if r.cracks > 0 %}<span style="color:var(--red);font-weight:700;">{{ r.cracks }}</span>{% else %}<span style="color:var(--green);">None</span>{% endif %}</td>
                            <td style="font-size:11px;color:var(--muted2);">{{ r.size_kb }} KB</td>
                            <td>
                                <a href="/download_report/{{ r.name }}" class="dl-btn" style="margin-right:4px;">Download</a>
                                <a href="/delete_report/{{ r.name }}" class="dl-btn danger" onclick="return confirm('Delete this report?')">Delete</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="no-data">No scan reports yet. Run AUTO SCAN to generate.</div>
                {% endif %}
            </div>
        </div>

        <div class="card">
            <div class="card-head"><span>&#x1F5C2;&#xFE0F;</span><span class="card-title">Raw Session Data</span></div>
            <div class="card-body" style="overflow-x:auto;">
                {% if json_files %}
                <table class="tbl">
                    <thead><tr><th>Filename</th><th>Size</th><th>Date Modified</th><th>Action</th></tr></thead>
                    <tbody>
                        {% for file in json_files %}
                        <tr>
                            <td style="font-family:'JetBrains Mono',monospace;font-size:11px;">{{ file.name }}</td>
                            <td style="color:var(--muted2);">{{ "%.2f"|format(file.size / 1024) }} KB</td>
                            <td style="color:var(--muted2);font-size:11px;">{{ file.modified.split('T')[0] }} {{ file.modified.split('T')[1].split('.')[0] }}</td>
                            <td><a href="/download/{{ file.name }}" class="dl-btn">&#x1F4E5; Download</a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="no-data">No session files yet. Start scanning to generate data.</div>
                {% endif %}
            </div>
        </div>

    </div>

    {% if scans|length >= 2 %}
    <script>
        const scanData    = {{ scans|tojson }};
        const trialLabels = scanData.map(s => 'Trial ' + (s.trial_number || s.day_number));
        const crackCounts = scanData.map(s => s.crack_count || 0);
        const growthRates = crackCounts.map((count, idx) => {
            if (idx === 0) return 0;
            const prev = crackCounts[idx - 1];
            if (prev === 0) return count > 0 ? 100 : 0;
            return parseFloat(((count - prev) / prev * 100).toFixed(1));
        });
        const PRIMARY = '#3b82f6', WARN = '#f97316', DANGER = '#ef4444', SUCCESS = '#22c55e';
        const GRID  = 'rgba(26,45,74,.6)', TICK = '#64748b';
        const base = {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: GRID }, ticks: { color: TICK } },
                y: { grid: { color: GRID }, ticks: { color: TICK }, beginAtZero: true }
            }
        };
        new Chart(document.getElementById('crackTrendChart'), {
            type: 'line',
            data: { labels: trialLabels, datasets: [{ label:'Crack Count', data: crackCounts, borderColor: PRIMARY, backgroundColor:'rgba(59,130,246,.08)', borderWidth:2.5, fill:true, tension:0.4, pointRadius:5, pointHoverRadius:7, pointBackgroundColor:PRIMARY, pointBorderColor:'#060d1a', pointBorderWidth:2 }] },
            options: { ...base }
        });
        new Chart(document.getElementById('growthRateChart'), {
            type: 'line',
            data: { labels: trialLabels, datasets: [{ label:'Growth Rate', data: growthRates, borderColor:WARN, backgroundColor:'rgba(249,115,22,.08)', borderWidth:2.5, fill:true, tension:0.4, pointRadius:5, pointHoverRadius:7, pointBackgroundColor:growthRates.map(r=>r<5?SUCCESS:r<15?WARN:DANGER), pointBorderColor:'#060d1a', pointBorderWidth:2 }] },
            options: { ...base }
        });
        const barColors = crackCounts.map((c,i) => i===0?PRIMARY:c>crackCounts[i-1]?DANGER:c<crackCounts[i-1]?SUCCESS:WARN);
        new Chart(document.getElementById('comparisonBarChart'), {
            type: 'bar',
            data: { labels: trialLabels, datasets: [{ label:'Cracks', data: crackCounts, backgroundColor: barColors.map(c=>c+'33'), borderColor: barColors, borderWidth:2, borderRadius:6 }] },
            options: { ...base, plugins: { legend:{display:false}, tooltip:{ callbacks:{ afterLabel: function(ctx){ if(ctx.dataIndex===0) return 'Baseline'; const d=crackCounts[ctx.dataIndex]-crackCounts[ctx.dataIndex-1]; return d>0?'+'+d+' cracks':d<0?d+' cracks':'No change'; } } } } }
        });
    </script>
    {% endif %}

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
        location     = request.form.get('location', '')
        report_file  = request.form.get('report_file', '')
        report_path  = os.path.join(os.path.expanduser("~/crack_data/reports"), report_file)
        crack_count  = 0
        positions    = 0
        crack_width  = 0.0
        crack_length = 0.0
        crack_area   = 0.0
        crack_depth  = 0.0
        thermal      = False
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
        scan_record = {
            'trial_number':  trial_number,
            'day_number':    trial_number,
            'scan_date':     datetime.now().strftime('%Y-%m-%d %H:%M'),
            'location':      location,
            'crack_count':   crack_count,
            'positions':     positions,
            'crack_width_cm':  crack_width,
            'crack_length_cm': crack_length,
            'crack_area_cm2':  crack_area,
            'crack_depth_cm':  crack_depth,
            'thermal_anomaly': thermal,
            'report_file':   report_file,
            'detections':    []
        }
        scan_filepath = os.path.join(SCANS_DIR, f"trial_{trial_number}.json")
        with open(scan_filepath, 'w') as f:
            json.dump(scan_record, f, indent=2)
        return f'''
        <html>
        <head>
            <meta http-equiv="refresh" content="2;url=/">
            <style>
                body {{ font-family:Arial; display:flex; justify-content:center; align-items:center; height:100vh; background:#060d1a; }}
                .msg {{ background:#0c1526; border:1px solid #1a2d4a; padding:40px; border-radius:15px; text-align:center; color:#e2e8f0; }}
                h1 {{ color:#22c55e; margin-bottom:12px; }}
            </style>
        </head>
        <body>
            <div class="msg">
                <h1>&#x2705; Scan Saved!</h1>
                <p>Trial {trial_number} saved successfully! ({crack_count} cracks detected)</p>
                <p style="color:#64748b;margin-top:8px;">Redirecting to dashboard...</p>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f"Error saving scan: {str(e)}", 500

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return "File not found", 404

@app.route('/download_report/<filename>')
def download_report(filename):
    reports_dir = os.path.expanduser("~/crack_data/reports")
    filepath    = os.path.join(reports_dir, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return "Report not found", 404

@app.route('/delete_report/<filename>')
def delete_report(filename):
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
    filepath = os.path.join(SCANS_DIR, f"day_{day_number}.json")
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=f"day_{day_number}_scan.json")
    return "Scan not found", 404

@app.route('/api/comparison')
def api_comparison():
    scans = load_all_scans()
    for scan in scans:
        scan['crack_size_extracted'] = extract_crack_size(scan)
    analysis = analyze_crack_growth(scans) if len(scans) >= 2 else None
    return jsonify({'scans': scans, 'analysis': analysis})

# ========================================
# MAIN
# ========================================

@app.route('/api/scans')
def api_scans():
    """Return all saved scans as JSON for web dashboard trial table"""
    scans = load_all_scans()
    return jsonify(scans)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("MULTI-DAY CRACK MONITORING ANALYTICS")
    print("="*60)
    print("\nFeatures:")
    print("  - Day-by-day comparison")
    print("  - Smart growth alerts")
    print("  - Downloadable reports")
    print("\nStarting analytics server...")
    print(f"\nACCESS DASHBOARD:")
    print(f"  http://192.168.168.111:8080")
    print(f"\nData directories:")
    print(f"  Sessions: {DATA_DIR}")
    print(f"  Day scans: {SCANS_DIR}")
    print("\nPress Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=8080, debug=False)
