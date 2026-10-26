#!/bin/bash
# Enable Raspberry Pi Camera Module

echo "========================================="
echo "Enabling Raspberry Pi Camera"
echo "========================================="

# Stop Motion (uses USB camera)
sudo pkill -9 motion

# Enable camera interface if not already enabled
echo "Enabling camera interface..."
sudo raspi-config nonint do_camera 0

# Load camera module
echo "Loading camera modules..."
sudo modprobe bcm2835-v4l2

# Verify camera is detected
echo ""
echo "Checking if camera is detected..."
vcgencmd get_camera

echo ""
echo "Listing video devices..."
v4l2-ctl --list-devices

echo ""
echo "Testing camera with raspistill..."
raspistill -o /tmp/test_picam.jpg -t 1000 -w 640 -h 480

if [ -f /tmp/test_picam.jpg ]; then
    echo ""
    echo "✓ Pi Camera is working!"
    ls -lh /tmp/test_picam.jpg
    echo ""
    echo "Now update web_remote_control.py to use Pi Camera"
else
    echo ""
    echo "✗ Pi Camera test failed"
    echo "Make sure the camera ribbon cable is properly connected"
fi

echo ""
echo "========================================="
echo "Camera setup complete!"
echo "========================================="
