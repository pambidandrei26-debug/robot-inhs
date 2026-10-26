"""
Fix double-encoded UTF-8 in web_data_analytics.py.
Reads the file as latin-1, re-encodes the garbled sequences back to UTF-8,
then saves as clean UTF-8.
"""

f = r'c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_data_analytics.py'

with open(f, 'rb') as fh:
    raw = fh.read()

# The bytes were saved as UTF-8 but read as latin-1 and re-encoded as UTF-8 twice.
# Decode as latin-1 to undo one layer, then re-encode as UTF-8.
try:
    text = raw.decode('utf-8')
    # Now fix the double-encoded chars: decode as latin-1, re-read as utf-8
    fixed = text.encode('latin-1', errors='replace').decode('utf-8', errors='replace')
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(fixed)
    print('Fixed via latin-1 round-trip')
except Exception as e:
    print('Error:', e)
