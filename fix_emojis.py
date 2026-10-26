import re

f = r'c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_data_analytics.py'
with open(f, 'rb') as fh:
    raw = fh.read()

# Double-encoded UTF-8 bytes for each emoji (with \r\n line endings)
replacements = [
    # success ✅  (U+2705)
    (b'\xc3\xa2\xc5\x93\xe2\x80\xa6', b'&#x2705;'),
    # warning ⚠️  (U+26A0 U+FE0F)
    (b'\xc3\xa2\xc5\xa1\xc2\xa0\xc3\xaf\xc2\xb8\xc2\x8f', b'&#x26A0;&#xFE0F;'),
    # danger 🚨  (U+1F6A8)
    (b'\xc3\xb0\xc5\xb8\xc5\xa1\xc2\xa8', b'&#x1F6A8;'),
]

for bad, good in replacements:
    count = raw.count(bad)
    raw = raw.replace(bad, good)
    print(f'Replaced {count}x: {bad!r} -> {good!r}')

with open(f, 'wb') as fh:
    fh.write(raw)
print('Done')
