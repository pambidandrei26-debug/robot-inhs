#!/usr/bin/env python3
"""
Simple Web Viewer for Crack Detection Results with Multi-Day Comparison
Access from browser: http://raspberrypi.local:8080
"""

from flask import Flask, render_template_string, send_from_directory, request, redirect, jsonify
import os
import json
import glob
from datetime import datetime

app = Flask(__name__)

DATA_DIR = "/home/pi/crack_data"
SCANS_DIR = os.path.join(DATA_DIR, "day_scans")
os.makedirs(SCANS_DIR, exist_ok=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>INHS Crack Detection System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f7fa;
            min-height: 100vh;
            padding: 0;
        }
        
        /* Header with INHS DepEd colors */
        .header-bar {
            background: linear-gradient(135deg, #0038a8 0%, #0056d6 100%);
            padding: 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            padding: 15px 30px;
            gap: 20px;
        }
        
        .logo-container {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo {
            width: 70px;
            height: 70px;
            background: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            padding: 5px;
        }
        
        .logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        .header-text {
            color: white;
        }
        
        .header-title {
            font-size: 1.8em;
            font-weight: 600;
            margin-bottom: 3px;
            letter-spacing: -0.5px;
        }
        
        .header-subtitle {
            font-size: 0.9em;
            opacity: 0.9;
            font-weight: 300;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
        }
        
        /* Stats cards with INHS colors */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid #0038a8;
            transition: all 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,56,168,0.15);
        }
        
        .stat-card:nth-child(2) {
            border-left-color: #ffc107;
        }
        
        .stat-card:nth-child(3) {
            border-left-color: #28a745;
        }
        
        .stat-card:nth-child(4) {
            border-left-color: #dc3545;
        }
        
        .stat-number {
            font-size: 3em;
            font-weight: 700;
            color: #0038a8;
            margin-bottom: 10px;
            line-height: 1;
        }
        
        .stat-label {
            color: #666;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }
        
        .section {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 30px;
        }
        
        h2 {
            color: #0038a8;
            margin-bottom: 25px;
            font-size: 1.6em;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .report-list {
            list-style: none;
        }
        
        .report-item {
            padding: 20px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
        }
        
        .report-item:hover {
            background: linear-gradient(90deg, #f8f9ff 0%, #ffffff 100%);
            padding-left: 25px;
        }
        
        .report-item:last-child {
            border-bottom: none;
        }
        
        .report-name {
            font-weight: 600;
            color: #0038a8;
            margin-bottom: 5px;
        }
        
        .report-date {
            color: #666;
            font-size: 0.85em;
        }
        
        .btn {
            background: #0038a8;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s;
            font-weight: 500;
            font-size: 0.9em;
        }
        
        .btn:hover {
            background: #0056d6;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,56,168,0.3);
        }
        
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
            margin-top: 10px;
        }
        
        .image-card {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.3s;
            border: 2px solid #f0f0f0;
        }
        
        .image-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 8px 24px rgba(0,56,168,0.2);
            border-color: #ffc107;
        }
        
        .image-card img {
            width: 100%;
            height: 220px;
            object-fit: cover;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .image-info {
            padding: 18px;
            background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
        }
        
        .image-name {
            font-weight: 600;
            color: #0038a8;
            margin-bottom: 8px;
            font-size: 0.9em;
        }
        
        .image-date {
            color: #666;
            font-size: 0.85em;
        }
        
        .no-data {
            text-align: center;
            color: #999;
            padding: 50px 20px;
            font-size: 1.1em;
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border-radius: 8px;
            border: 2px dashed #e0e0e0;
        }
        
        .status-good {
            color: #28a745;
            font-weight: 700;
        }
        
        .status-warning {
            color: #ffc107;
            font-weight: 700;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        /* Multi-Day Comparison */
        .alert-toast {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 30px;
            border-left: 6px solid;
            animation: slideIn 0.5s ease;
        }
        @keyframes slideIn {
            from {
                transform: translateX(-20px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        .alert-toast.good {
            border-color: #28a745;
        }
        .alert-toast.warning {
            border-color: #ffc107;
        }
        .alert-toast.critical {
            border-color: #dc3545;
        }
        .alert-icon {
            font-size: 36px;
            display: inline-block;
            margin-right: 15px;
            vertical-align: middle;
        }
        .alert-content {
            display: inline-block;
            vertical-align: middle;
        }
        .alert-status {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .alert-status.good { color: #28a745; }
        .alert-status.warning { color: #ffc107; }
        .alert-status.critical { color: #dc3545; }
        .alert-message {
            color: #666;
            font-size: 14px;
        }
        .alert-details {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 13px;
        }
        
        .comparison-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .comparison-table th {
            background: #0038a8;
            color: white;
            padding: 12px;
            text-align: center;
            font-weight: 600;
        }
        .comparison-table td {
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
            text-align: center;
        }
        .comparison-table tr:hover {
            background: #f8f9ff;
        }
        .day-label {
            font-weight: bold;
            color: #0038a8;
            font-size: 16px;
        }
        .crack-count-cell {
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }
        .growth-indicator {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
        }
        .growth-positive {
            background: #fef3c7;
            color: #d97706;
        }
        .growth-negative {
            background: #d1fae5;
            color: #059669;
        }
        
        .save-scan-form {
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            padding: 25px;
            border-radius: 8px;
            border: 2px dashed #e0e0e0;
            margin-top: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #0038a8;
            font-weight: 600;
            font-size: 14px;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #0038a8;
        }
        .btn-submit {
            background: #28a745;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-submit:hover {
            background: #218838;
        }
        .btn-delete {
            background: #dc3545;
            color: white;
            padding: 6px 12px;
            border: none;
            border-radius: 5px;
            font-weight: 600;
            cursor: pointer;
            font-size: 12px;
        }
        .btn-delete:hover {
            background: #c82333;
        }
        .btn-delete-all {
            background: #6c757d;
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-delete-all:hover {
            background: #5a6268;
        }
        .info-note {
            background: #e7f3ff;
            border-left: 4px solid #0038a8;
            padding: 12px;
            margin-top: 15px;
            border-radius: 5px;
            color: #004085;
            font-size: 13px;
        }
        
        /* Charts Section */
        .charts-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .chart-title {
            color: #0038a8;
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 15px;
            text-align: center;
        }
        .chart-canvas {
            max-height: 300px;
        }
        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }
        }
        
        footer {
            text-align: center;
            padding: 40px 20px 30px;
            color: #666;
            font-size: 0.9em;
        }
        
        footer a {
            color: #0038a8;
            text-decoration: none;
            font-weight: 500;
        }
        
        footer a:hover {
            color: #ffc107;
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 1.8em; }
            .stat-number { font-size: 2em; }
            .stats { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <!-- ISU Header Bar -->
    <div class="header-bar">
        <div class="header-content">
            <div class="logo-container">
                <div class="logo"><img src="/static/logo.jpg" alt="INHS Logo"></div>
                <div class="header-text">
                    <div class="header-title">Isabela National High School</div>
                    <div class="header-subtitle">Crack Detection System - Autonomous Robot Dashboard</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="container">
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ total_scans }}</div>
                <div class="stat-label">Total Scans</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_images }}</div>
                <div class="stat-label">Images Captured</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ crack_count }}</div>
                <div class="stat-label">Cracks Detected</div>
            </div>
            <div class="stat-card">
                <div class="stat-number status-{{ system_status }}">{{ system_text }}</div>
                <div class="stat-label">System Status</div>
            </div>
        </div>
        
        {% if analysis %}
        <div class="alert-toast {{ analysis.level }}">
            <span class="alert-icon">
                {% if analysis.level == 'good' %}✅{% endif %}
                {% if analysis.level == 'warning' %}⚠️{% endif %}
                {% if analysis.level == 'critical' %}🚨{% endif %}
            </span>
            <div class="alert-content">
                <div class="alert-status {{ analysis.level }}">{{ analysis.status }}</div>
                <div class="alert-message">{{ analysis.message }}</div>
                <div class="alert-details">
                    Day {{ analysis.baseline_day }} → Day {{ analysis.latest_day }} ({{ analysis.days_elapsed }} days elapsed) | 
                    Growth: {{ "%.1f"|format(analysis.growth_percent) }}% | 
                    Cracks: {{ analysis.baseline_count }} → {{ analysis.latest_count }}
                </div>
            </div>
        </div>
        {% endif %}
        
        {% if day_scans|length >= 2 %}
        <div class="section">
            <h2>📊 Crack Growth Analytics</h2>
            <p style="color: #666; margin-bottom: 15px;">Showing comparison of {{ day_scans|length }} scans</p>
            <div class="charts-grid">
                <div class="chart-container">
                    <div class="chart-title">Crack Count Over Time</div>
                    <canvas id="crackTrendChart" class="chart-canvas"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">Growth Rate (%)</div>
                    <canvas id="growthRateChart" class="chart-canvas"></canvas>
                </div>
            </div>
            <div class="chart-container" style="margin-top: 20px;">
                <div class="chart-title">Day-by-Day Comparison</div>
                <canvas id="comparisonBarChart" class="chart-canvas"></canvas>
            </div>
        </div>
        {% elif day_scans|length == 1 %}
        <div class="section">
            <h2>📊 Crack Growth Analytics</h2>
            <div class="no-data">
                📈 You have 1 saved scan. Save at least one more scan to see growth charts!
            </div>
        </div>
        {% else %}
        <div class="section">
            <h2>📊 Crack Growth Analytics</h2>
            <div class="no-data">
                📊 No saved scans yet. Scroll down to "💾 Save Current Scan" to start tracking crack growth over time!
            </div>
        </div>
        {% endif %}
        
        <div class="section">
            <h2>📅 Multi-Day Comparison</h2>
            {% if day_scans %}
            <div style="text-align: right; margin-bottom: 15px;">
                <button onclick="if(confirm('Delete ALL day scans? This cannot be undone!')) window.location.href='/delete_all_scans'" class="btn-delete-all">🗑️ Delete All Scans</button>
            </div>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Trial</th>
                        <th>Date</th>
                        <th>Cracks Detected</th>
                        <th>Location</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for scan in day_scans %}
                    <tr>
                        <td><span class="day-label">Trial {{ scan.day_number }}</span></td>
                        <td>{{ scan.scan_date }}</td>
                        <td><span class="crack-count-cell">{{ scan.crack_count }}</span></td>
                        <td>{{ scan.location|default('Not specified', true) }}</td>
                        <td>
                            {% if loop.index > 1 %}
                                {% if day_scans[loop.index-2].crack_count < scan.crack_count %}
                                <span class="growth-indicator growth-positive">▲ Growth</span>
                                {% else %}
                                <span class="growth-indicator growth-negative">✓ Stable</span>
                                {% endif %}
                            {% else %}
                            <span class="growth-indicator growth-negative">✓ Baseline</span>
                            {% endif %}
                        </td>
                        <td>
                            <button onclick="if(confirm('Delete Day {{ scan.day_number }} scan?')) window.location.href='/delete_scan/{{ scan.day_number }}'" class="btn-delete">🗑️ Delete</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="no-data">No day scans saved yet. Use the form below to save your first scan!</div>
            {% endif %}
            
            <div class="save-scan-form">
                <h3 style="color: #0038a8; margin-bottom: 15px;">💾 Save Current Scan for Trial Comparison</h3>
                <form action="/save_day_scan" method="POST">
                    <div class="form-group">
                        <label>Trial Number (1, 2, 3, 4...)</label>
                        <input type="number" name="day_number" required placeholder="e.g., 1">
                    </div>
                    <div class="form-group">
                        <label>Location (e.g., Column A-03)</label>
                        <input type="text" name="location" placeholder="e.g., Column A-03, Wall Section B">
                    </div>
                    <div class="form-group">
                        <label>Select Scan Report to use</label>
                        <select name="report_file" required style="width:100%;padding:10px;border:2px solid #e5e7eb;border-radius:8px;font-size:14px">
                            <option value="">-- Select the scan report for this trial --</option>
                            {% for r in reports %}
                            <option value="{{ r.name }}">{{ r.name }}  ({{ r.date }})</option>
                            {% endfor %}
                        </select>
                        <small style="color:#666;margin-top:4px;display:block">
                            Select the report from your AUTO SCAN. Crack width, length and thermal data will be read automatically.
                        </small>
                    </div>
                    <button type="submit" class="btn-submit">💾 Save Scan for Trial Comparison</button>
                </form>

                <div class="info-note">
                    <strong>How to use:</strong> After each AUTO SCAN (Trial 1, 2, 3, 4...),
                    select the scan report, set the trial number and location, then click Save.
                    The system reads crack measurements automatically from the report file.
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Scan Reports</h2>
            {% if reports %}
            <div style="text-align: right; margin-bottom: 15px;">
                <button onclick="if(confirm('Delete ALL scan reports? This cannot be undone!')) window.location.href='/delete_all_reports'" class="btn-delete-all">🗑️ Delete All Reports</button>
            </div>
            <ul class="report-list">
                {% for report in reports %}
                <li class="report-item">
                    <div>
                        <div class="report-name">{{ report.name }}</div>
                        <div class="report-date">{{ report.date }}</div>
                    </div>
                    <div>
                        <a href="/reports/{{ report.name }}" class="btn" download style="margin-right: 8px;">📥 Download</a>
                        <button onclick="if(confirm('Delete {{ report.name }}?')) window.location.href='/delete_report/{{ report.name }}'" class="btn-delete">🗑️ Delete</button>
                    </div>
                </li>
                {% endfor %}
            </ul>
            {% else %}
            <div class="no-data">No scan reports yet. Run a scan to generate reports!</div>
            {% endif %}
        </div>
        
        <!-- RESEARCH TABLES -->
        <div class="section">
            <h2>📊 Crack Growth Monitoring Tables</h2>

            <h3 style="margin:20px 0 10px;color:#0038a8">Table 1 — Inspection Period Mean Change</h3>
            <table style="width:100%;border-collapse:collapse;margin-bottom:25px">
                <thead>
                    <tr style="background:#0038a8;color:white">
                        <th style="padding:12px;text-align:left;border:1px solid #ddd">Inspection Period</th>
                        <th style="padding:12px;text-align:center;border:1px solid #ddd">Mean Width Change</th>
                        <th style="padding:12px;text-align:center;border:1px solid #ddd">Mean Length Change</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in research.period_rows %}
                    <tr style="background:{% if loop.index is odd %}#f8f9ff{% else %}white{% endif %}">
                        <td style="padding:10px 12px;border:1px solid #ddd;font-weight:600">{{ row.period }}</td>
                        <td style="padding:10px 12px;border:1px solid #ddd;text-align:center">{{ row.width }}</td>
                        <td style="padding:10px 12px;border:1px solid #ddd;text-align:center">{{ row.length }}</td>
                    </tr>
                    {% endfor %}
                    <tr style="background:#e8f0ff;font-weight:bold">
                        <td style="padding:10px 12px;border:1px solid #ddd">Overall Mean Weekly Change</td>
                        <td style="padding:10px 12px;border:1px solid #ddd;text-align:center">{{ research.mean_width }}</td>
                        <td style="padding:10px 12px;border:1px solid #ddd;text-align:center">{{ research.mean_length }}</td>
                    </tr>
                    <tr style="background:#fff3cd">
                        <td colspan="3" style="padding:10px 12px;border:1px solid #ddd;font-weight:bold">
                            Screening Classification: <span style="color:{% if research.classification == 'High Priority' %}#dc3545{% elif research.classification == 'Moderate Priority' %}#fd7e14{% else %}#28a745{% endif %}">{{ research.classification }}</span>
                        </td>
                    </tr>
                </tbody>
            </table>

            <h3 style="margin:20px 0 10px;color:#0038a8">Table 2 — Trial Summary (Trial 1 → 5)</h3>
            <table style="width:100%;border-collapse:collapse;margin-bottom:10px">
                <thead>
                    <tr style="background:#0038a8;color:white">
                        <th style="padding:12px;text-align:left;border:1px solid #ddd">Trial</th>
                        <th style="padding:12px;text-align:left;border:1px solid #ddd">Location</th>
                        <th style="padding:12px;text-align:center;border:1px solid #ddd">Crack Width</th>
                        <th style="padding:12px;text-align:center;border:1px solid #ddd">Crack Length</th>
                        <th style="padding:12px;text-align:center;border:1px solid #ddd">Thermal Anomaly</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in research.trial_rows %}
                    <tr style="background:{% if loop.index is odd %}#f8f9ff{% else %}white{% endif %}">
                        <td style="padding:10px 12px;border:1px solid #ddd;font-weight:600">{{ row.day }}</td>
                        <td style="padding:10px 12px;border:1px solid #ddd">{{ row.location }}</td>
                        <td style="padding:10px 12px;border:1px solid #ddd;text-align:center">{{ row.width }}</td>
                        <td style="padding:10px 12px;border:1px solid #ddd;text-align:center">{{ row.length }}</td>
                        <td style="padding:10px 12px;border:1px solid #ddd;text-align:center">
                            <span style="color:{% if row.thermal == 'Detected' %}#dc3545{% else %}#28a745{% endif %};font-weight:bold">
                                {{ row.thermal }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            <p style="color:#666;font-size:12px;margin-top:8px">
                Data auto-populated from scan records. Use "Save Scan for Trial Comparison" to add measurements for each trial.
            </p>
        </div>

        <div class="section">
            <h2>📸 Recent Images</h2>
            {% if images %}
            <div style="text-align: right; margin-bottom: 15px;">
                <button onclick="if(confirm('Delete ALL scan images? This cannot be undone!')) window.location.href='/delete_all_images'" class="btn-delete-all">🗑️ Delete All Images</button>
            </div>
            <div class="image-grid">
                {% for img in images %}
                <div class="image-card">
                    <img src="/scans/{{ img.name }}" alt="{{ img.name }}">
                    <div class="image-info">
                        <div class="image-name">{{ img.name }}</div>
                        <div class="image-date">{{ img.date }}</div>
                        <button onclick="if(confirm('Delete {{ img.name }}?')) window.location.href='/delete_image/{{ img.name }}'" class="btn-delete" style="margin-top: 8px; width: 100%;">🗑️ Delete</button>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="no-data">No images yet. Start scanning to capture images!</div>
            {% endif %}
        </div>
        
        {% if cracks %}
        <div class="section">
            <h2>🚨 Detected Cracks</h2>
            <div style="text-align: right; margin-bottom: 15px;">
                <button onclick="if(confirm('Delete ALL crack images? This cannot be undone!')) window.location.href='/delete_all_cracks'" class="btn-delete-all">🗑️ Delete All Cracks</button>
            </div>
            <div class="image-grid">
                {% for crack in cracks %}
                <div class="image-card">
                    <img src="/cracks/{{ crack.name }}" alt="{{ crack.name }}">
                    <div class="image-info">
                        <div class="image-name">{{ crack.name }}</div>
                        <div class="image-date">{{ crack.date }}</div>
                        <button onclick="if(confirm('Delete {{ crack.name }}?')) window.location.href='/delete_crack/{{ crack.name }}'" class="btn-delete" style="margin-top: 8px; width: 100%;">🗑️ Delete</button>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
    
    <footer>
        <p>Isabela National High School - Crack Detection System • Powered by Raspberry Pi 3 B+ • <a href="#" onclick="location.reload()">🔄 Refresh</a></p>
    </footer>
    
    {% if day_scans|length >= 2 %}
    <script>
        // Prepare data from backend
        const dayScans = {{ day_scans|tojson }};
        
        const dayLabels = dayScans.map(scan => 'Day ' + scan.day_number);
        const crackCounts = dayScans.map(scan => scan.crack_count);
        
        // Calculate growth rates
        const growthRates = crackCounts.map((count, idx) => {
            if (idx === 0) return 0;
            const prevCount = crackCounts[idx - 1];
            if (prevCount === 0) return count > 0 ? 100 : 0;
            return ((count - prevCount) / prevCount * 100).toFixed(1);
        });
        
        // Color scheme
        const primaryColor = '#0038a8';
        const warningColor = '#ffc107';
        const dangerColor = '#dc3545';
        const successColor = '#28a745';
        
        // Chart 1: Line Chart - Crack Trend
        const ctx1 = document.getElementById('crackTrendChart').getContext('2d');
        new Chart(ctx1, {
            type: 'line',
            data: {
                labels: dayLabels,
                datasets: [{
                    label: 'Crack Count',
                    data: crackCounts,
                    borderColor: primaryColor,
                    backgroundColor: 'rgba(0, 56, 168, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: primaryColor,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            font: { size: 12 }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        ticks: {
                            font: { size: 12, weight: 'bold' }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
        
        // Chart 2: Growth Rate Line Chart
        const ctx2 = document.getElementById('growthRateChart').getContext('2d');
        const growthColors = growthRates.map(rate => {
            if (rate < 5) return successColor;
            if (rate < 15) return warningColor;
            return dangerColor;
        });
        
        new Chart(ctx2, {
            type: 'line',
            data: {
                labels: dayLabels,
                datasets: [{
                    label: 'Growth Rate (%)',
                    data: growthRates,
                    borderColor: warningColor,
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: growthColors,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        callbacks: {
                            label: function(context) {
                                return 'Growth: ' + context.parsed.y + '%';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            },
                            font: { size: 12 }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        ticks: {
                            font: { size: 12, weight: 'bold' }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
        
        // Chart 3: Bar Chart Comparison
        const ctx3 = document.getElementById('comparisonBarChart').getContext('2d');
        const barColors = crackCounts.map((count, idx) => {
            if (idx === 0) return primaryColor;
            const prevCount = crackCounts[idx - 1];
            if (count > prevCount) return dangerColor;
            if (count === prevCount) return successColor;
            return warningColor;
        });
        
        new Chart(ctx3, {
            type: 'bar',
            data: {
                labels: dayLabels,
                datasets: [{
                    label: 'Cracks Detected',
                    data: crackCounts,
                    backgroundColor: barColors,
                    borderColor: barColors.map(c => c),
                    borderWidth: 2,
                    borderRadius: 8,
                    barThickness: 50
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        callbacks: {
                            afterLabel: function(context) {
                                if (context.dataIndex === 0) return 'Baseline';
                                const idx = context.dataIndex;
                                const current = crackCounts[idx];
                                const prev = crackCounts[idx - 1];
                                const diff = current - prev;
                                if (diff > 0) return '▲ +' + diff + ' cracks';
                                if (diff < 0) return '▼ ' + diff + ' cracks';
                                return '● No change';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            font: { size: 12 }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        ticks: {
                            font: { size: 12, weight: 'bold' }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    </script>
    {% endif %}
</body>
</html>
"""

def get_files_info(directory):
    """Get list of files with info"""
    files = []
    if not os.path.exists(directory):
        return files

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append({
                'name':  filename,
                'date':  datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'size':  stat.st_size,
                'mtime': stat.st_mtime,
            })

    # Sort newest first by actual modification time — reliable regardless of filename
    return sorted(files, key=lambda x: x['mtime'], reverse=True)

def load_all_day_scans():
    """Load all saved day scans"""
    scans = []
    pattern = os.path.join(SCANS_DIR, "day_*.json")
    
    for filepath in sorted(glob.glob(pattern)):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                data['filepath'] = filepath
                scans.append(data)
        except:
            pass
    
    return sorted(scans, key=lambda x: x.get('day_number', 0))

def analyze_crack_growth(scans):
    """Analyze crack growth between scans"""
    if len(scans) < 2:
        return None
    
    baseline = scans[0]
    latest = scans[-1]
    
    baseline_count = baseline.get('crack_count', 0)
    latest_count = latest.get('crack_count', 0)
    
    # Calculate growth percentage
    if baseline_count > 0:
        growth_percent = ((latest_count - baseline_count) / baseline_count) * 100
    else:
        growth_percent = 0 if latest_count == 0 else 100
    
    # Determine alert level
    if growth_percent < 5:
        status = "OK"
        level = "good"
        message = "No significant crack growth detected. Continue monitoring."
    elif growth_percent < 15:
        status = "MONITOR"
        level = "warning"
        message = "Slight crack growth detected. Monitor closely in next inspection."
    else:
        status = "ACTION NEEDED"
        level = "critical"
        message = "Significant crack growth detected! Immediate action recommended."
    
    return {
        'baseline_day': baseline.get('day_number', 0),
        'latest_day': latest.get('day_number', 0),
        'baseline_count': baseline_count,
        'latest_count': latest_count,
        'growth_percent': growth_percent,
        'status': status,
        'level': level,
        'message': message,
        'days_elapsed': latest.get('day_number', 0) - baseline.get('day_number', 0)
    }

def compute_research_tables(reports_dir, data_dir):
    """
    Build the two research tables from actual scan report files.
    
    Table 1 - Inspection Period: Mean width/length change per 7-day period
    Table 2 - Trial Table: Day 0,7,14,21,28 with crack measurements
    
    Reads report .txt files, extracts crack measurements by day.
    """
    DAYS = [1, 2, 3, 4, 5]

    # Collect measurements per day
    day_data = {}   # {day_number: {width_cm, length_cm, location, thermal, scan_date}}

    # Load from day_scans JSON files
    scans_dir_json = os.path.join(data_dir, 'day_scans')
    for filepath in glob.glob(os.path.join(scans_dir_json, 'day_*.json')):
        try:
            with open(filepath) as f:
                rec = json.load(f)
            d = rec.get('day_number', -1)
            if d in DAYS:
                day_data[d] = {
                    'day':      d,
                    'location': rec.get('location', '—'),
                    'width':    rec.get('crack_width_cm',  rec.get('width_cm',  0.0)),
                    'length':   rec.get('crack_length_cm', rec.get('length_cm', 0.0)),
                    'thermal':  'Detected' if rec.get('thermal_anomaly') or rec.get('crack_count', 0) > 0
                                else 'Not Detected',
                    'date':     rec.get('scan_date', ''),
                }
        except:
            pass

    # Also try to read from txt report files as fallback
    for filepath in sorted(glob.glob(os.path.join(reports_dir, '*.txt')),
                           key=lambda p: os.stat(p).st_mtime):
        try:
            with open(filepath, 'r', errors='ignore') as f:
                content = f.read()
            # Look for day number hint in filename or content
            fname = os.path.basename(filepath)
            day_hint = None
            for d in DAYS:
                if f'day_{d}' in fname.lower() or f'day {d}' in content.lower():
                    day_hint = d
                    break
            if day_hint is None:
                continue
            # Extract measurements
            width = 0.0; length = 0.0; thermal = 'Not Detected'
            for line in content.splitlines():
                if 'Crack Width' in line or 'crack_width' in line.lower():
                    try: width = float(line.split(':')[1].strip().split()[0])
                    except: pass
                if 'Crack Length' in line or 'crack_length' in line.lower():
                    try: length = float(line.split(':')[1].strip().split()[0])
                    except: pass
                if 'Thermal' in line and ('Detected' in line or 'anomaly' in line.lower()):
                    thermal = 'Detected'
            if day_hint not in day_data:
                day_data[day_hint] = {
                    'day': day_hint, 'location': '—',
                    'width': width, 'length': length,
                    'thermal': thermal, 'date': '',
                }
        except:
            pass

    # --- TABLE 2: Trial table (Trial 1/2/3/4/5) ---
    trial_rows = []
    for d in DAYS:
        row = day_data.get(d)
        if row:
            trial_rows.append({
                'day':      f'Trial {d}',
                'location': row['location'],
                'width':    f"{row['width']:.2f} cm" if row['width'] else '—',
                'length':   f"{row['length']:.2f} cm" if row['length'] else '—',
                'thermal':  row['thermal'],
            })
        else:
            trial_rows.append({
                'day': f'Trial {d}', 'location': '—',
                'width': '—', 'length': '—', 'thermal': '—',
            })

    # --- TABLE 1: Inspection Period changes ---
    period_rows = []
    period_labels = [('Trial 1-2',   1,  2),
                     ('Trial 2-3',   2,  3),
                     ('Trial 3-4',   3,  4),
                     ('Trial 4-5',   4,  5)]

    width_changes  = []
    length_changes = []

    for label, d_start, d_end in period_labels:
        s = day_data.get(d_start)
        e = day_data.get(d_end)
        if s and e:
            dw = round(e['width']  - s['width'],  2)
            dl = round(e['length'] - s['length'], 2)
        else:
            dw = None
            dl = None

        period_rows.append({
            'period':  label,
            'width':   f'{dw:+.2f} cm' if dw is not None else '—',
            'length':  f'{dl:+.2f} cm' if dl is not None else '—',
        })

        if dw is not None: width_changes.append(dw)
        if dl is not None: length_changes.append(dl)

    # Overall mean
    mean_w = round(sum(width_changes)  / len(width_changes),  2) if width_changes  else None
    mean_l = round(sum(length_changes) / len(length_changes), 2) if length_changes else None

    # Screening classification
    if mean_l is not None:
        if mean_l < 0.2:
            classification = 'Low Priority'
        elif mean_l < 0.5:
            classification = 'Moderate Priority'
        else:
            classification = 'High Priority'
    else:
        classification = 'Insufficient Data'

    return {
        'trial_rows':      trial_rows,
        'period_rows':     period_rows,
        'mean_width':      f'{mean_w:+.2f} cm' if mean_w is not None else '—',
        'mean_length':     f'{mean_l:+.2f} cm' if mean_l is not None else '—',
        'classification':  classification,
    }


@app.route('/')
def index():
    """Main dashboard page"""

    # Get reports
    reports_dir = os.path.join(DATA_DIR, 'reports')
    reports = get_files_info(reports_dir)

    # Get scan images
    scans_dir = os.path.join(DATA_DIR, 'scans')
    images = get_files_info(scans_dir)[:12]

    # Get crack images
    cracks_dir = os.path.join(DATA_DIR, 'cracks')
    cracks = get_files_info(cracks_dir)

    # Calculate stats
    total_scans  = len(reports)
    total_images = len(get_files_info(scans_dir))
    crack_count  = len(cracks)

    # Day scans and growth analysis
    day_scans = load_all_day_scans()
    analysis  = analyze_crack_growth(day_scans) if len(day_scans) >= 2 else None

    # Research tables
    research = compute_research_tables(reports_dir, DATA_DIR)

    # System status
    if crack_count == 0:
        system_status = 'good';  system_text = 'OK'
    elif crack_count < 5:
        system_status = 'warning'; system_text = 'ALERT'
    else:
        system_status = 'warning'; system_text = 'CRITICAL'

    return render_template_string(
        HTML_TEMPLATE,
        reports=reports,
        images=images,
        cracks=cracks,
        day_scans=day_scans,
        analysis=analysis,
        research=research,
        total_scans=total_scans,
        total_images=total_images,
        crack_count=crack_count,
        system_status=system_status,
        system_text=system_text
    )


@app.route('/save_day_scan', methods=['POST'])
def save_day_scan():
    """Save a day scan — reads measurements from selected report file"""
    try:
        day_number  = int(request.form.get('day_number', 0))
        location    = request.form.get('location', '')
        report_file = request.form.get('report_file', '')

        # Default values
        crack_count  = 0
        crack_width  = 0.0
        crack_length = 0.0
        thermal      = False
        positions    = 0

        # Auto-read measurements from selected report file
        if report_file:
            rpath = os.path.join(DATA_DIR, 'reports', report_file)
            if os.path.exists(rpath):
                try:
                    with open(rpath, 'r', errors='ignore') as f:
                        for line in f:
                            line = line.strip()
                            if ':' not in line:
                                continue
                            key = line.split(':')[0].strip()
                            val = line.split(':')[1].strip()
                            if key in ('Cracks Detected', 'Cracks detected'):
                                try: crack_count = int(val)
                                except: pass
                            if key in ('Total Positions', 'Positions scanned'):
                                try: positions = int(val)
                                except: pass
                            if key == 'Crack Length':
                                try: crack_length = float(val.split()[0])
                                except: pass
                            if key == 'Crack Width':
                                try: crack_width = float(val.split()[0])
                                except: pass
                            if 'Thermal' in key and 'anomaly' in line.lower():
                                thermal = True
                            if crack_count > 0:
                                thermal = True
                except:
                    pass

        # Create day scan record
        scan_record = {
            'day_number':     day_number,
            'scan_date':      datetime.now().strftime('%Y-%m-%d %H:%M'),
            'location':       location,
            'crack_count':    crack_count,
            'crack_width_cm': crack_width,
            'crack_length_cm': crack_length,
            'thermal_anomaly': thermal,
            'positions':      positions,
            'source_report':  report_file,
        }

        scan_filepath = os.path.join(SCANS_DIR, f"day_{day_number}.json")
        os.makedirs(SCANS_DIR, exist_ok=True)
        with open(scan_filepath, 'w') as f:
            json.dump(scan_record, f, indent=2)

        return redirect('/')
    except Exception as e:
        return f"Error saving scan: {str(e)}", 500

@app.route('/delete_scan/<int:day_number>')
def delete_scan(day_number):
    """Delete a specific day scan"""
    try:
        scan_filepath = os.path.join(SCANS_DIR, f"day_{day_number}.json")
        if os.path.exists(scan_filepath):
            os.remove(scan_filepath)
        return redirect('/')
    except Exception as e:
        return f"Error deleting scan: {str(e)}", 500

@app.route('/delete_all_scans')
def delete_all_scans():
    """Delete all day scans"""
    try:
        pattern = os.path.join(SCANS_DIR, "day_*.json")
        for filepath in glob.glob(pattern):
            os.remove(filepath)
        return redirect('/')
    except Exception as e:
        return f"Error deleting scans: {str(e)}", 500

@app.route('/delete_report/<path:filename>')
def delete_report(filename):
    """Delete a specific report file"""
    try:
        reports_dir = os.path.join(DATA_DIR, 'reports')
        filepath = os.path.join(reports_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        return redirect('/')
    except Exception as e:
        return f"Error deleting report: {str(e)}", 500

@app.route('/delete_all_reports')
def delete_all_reports():
    """Delete all report files"""
    try:
        reports_dir = os.path.join(DATA_DIR, 'reports')
        if os.path.exists(reports_dir):
            for filename in os.listdir(reports_dir):
                filepath = os.path.join(reports_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        return redirect('/')
    except Exception as e:
        return f"Error deleting reports: {str(e)}", 500

@app.route('/delete_image/<path:filename>')
def delete_image(filename):
    """Delete a specific scan image"""
    try:
        scans_dir = os.path.join(DATA_DIR, 'scans')
        filepath = os.path.join(scans_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        return redirect('/')
    except Exception as e:
        return f"Error deleting image: {str(e)}", 500

@app.route('/delete_all_images')
def delete_all_images():
    """Delete all scan images"""
    try:
        scans_dir = os.path.join(DATA_DIR, 'scans')
        if os.path.exists(scans_dir):
            for filename in os.listdir(scans_dir):
                filepath = os.path.join(scans_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        return redirect('/')
    except Exception as e:
        return f"Error deleting images: {str(e)}", 500

@app.route('/delete_crack/<path:filename>')
def delete_crack(filename):
    """Delete a specific crack image"""
    try:
        cracks_dir = os.path.join(DATA_DIR, 'cracks')
        filepath = os.path.join(cracks_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        return redirect('/')
    except Exception as e:
        return f"Error deleting crack image: {str(e)}", 500

@app.route('/delete_all_cracks')
def delete_all_cracks():
    """Delete all crack images"""
    try:
        cracks_dir = os.path.join(DATA_DIR, 'cracks')
        if os.path.exists(cracks_dir):
            for filename in os.listdir(cracks_dir):
                filepath = os.path.join(cracks_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        return redirect('/')
    except Exception as e:
        return f"Error deleting crack images: {str(e)}", 500

@app.route('/reports/<path:filename>')
def serve_report(filename):
    """Serve report file"""
    return send_from_directory(os.path.join(DATA_DIR, 'reports'), filename)

@app.route('/scans/<path:filename>')
def serve_scan(filename):
    """Serve scan image"""
    return send_from_directory(os.path.join(DATA_DIR, 'scans'), filename)

@app.route('/cracks/<path:filename>')
def serve_crack(filename):
    """Serve crack image"""
    return send_from_directory(os.path.join(DATA_DIR, 'cracks'), filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files like logo"""
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, filename)

if __name__ == '__main__':
    print("="*70)
    print("🌐 Starting Web Viewer...")
    print("="*70)
    print(f"\n📂 Data directory: {DATA_DIR}")
    print(f"\n🌍 Access from:")
    print(f"   • Local:  http://localhost:8080")
    print(f"   • Network: http://raspberrypi.local:8080")
    print(f"   • Or use Raspberry Pi IP address")
    print(f"\n⌨️  Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=8080, debug=False)
