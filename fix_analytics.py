#!/usr/bin/env python3
"""Fix web_data_analytics.py - add sorted reports section"""
import os

path = os.path.join(os.path.dirname(__file__), 'raspberry_pi', 'web_data_analytics.py')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the Raw Session Data section (has unicode replacement char \ufffd)
old_marker = 'Raw Session Data'
idx = content.find(old_marker)
if idx < 0:
    print("ERROR: Could not find 'Raw Session Data'")
    exit(1)

# Find the div start before it
div_start = content.rfind('<div class="files-section">', 0, idx)
if div_start < 0:
    print("ERROR: Could not find files-section div")
    exit(1)

old_section = content[div_start:div_start + 80]
print("Found section at", div_start)
print("Old:", repr(old_section[:80]))

# The new reports section + preserved raw session section
new_section = '''        <div class="files-section">
            <h2>Scan Reports</h2>
            {% if reports %}
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
            <h2>Raw Session Data</h2>'''

# Find the end of the h2 tag after 'Raw Session Data'
h2_end = content.find('</h2>', idx)
old_to_replace = content[div_start:h2_end + 5]
print("Replacing", len(old_to_replace), "chars")

content = content[:div_start] + new_section + content[h2_end + 5:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("OK - web_data_analytics.py updated")
