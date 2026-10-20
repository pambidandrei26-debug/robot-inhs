# CHECK FILES ON PI — Run these commands ON THE PI

## Copy-paste this entire block into the Pi terminal:

```bash
echo "=== FILES IN /home/pi ===" && ls -lh /home/pi/*.py /home/pi/*.sh 2>/dev/null && echo "" && echo "=== CHECKING KEY VERSIONS ===" && grep -l "v2.0" /home/pi/*.py 2>/dev/null && grep -l "crack_analysis" /home/pi/*.py 2>/dev/null && grep -l "extract_crack_size" /home/pi/*.py 2>/dev/null
```
