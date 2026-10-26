#!/bin/bash
# Webcam diagnostic script for Jieli "WEBCAM HD FULL"

echo "========================================="
echo "WEBCAM DIAGNOSTICS"
echo "========================================="

echo ""
echo "1. Listing all video devices:"
v4l2-ctl --list-devices

echo ""
echo "2. Checking /dev/video0 formats:"
v4l2-ctl -d /dev/video0 --list-formats-ext

echo ""
echo "3. Current camera settings:"
v4l2-ctl -d /dev/video0 --all

echo ""
echo "4. Testing with fswebcam (320x240 YUYV):"
fswebcam -r 320x240 -p YUYV --no-banner --jpeg 90 -S 3 --skip 10 /tmp/test_320.jpg
if [ -f /tmp/test_320.jpg ]; then
    echo "✓ 320x240 capture successful"
    ls -lh /tmp/test_320.jpg
else
    echo "✗ 320x240 capture failed"
fi

echo ""
echo "5. Testing with fswebcam (640x480 YUYV):"
fswebcam -r 640x480 -p YUYV --no-banner --jpeg 90 -S 3 --skip 10 /tmp/test_640.jpg
if [ -f /tmp/test_640.jpg ]; then
    echo "✓ 640x480 capture successful"
    ls -lh /tmp/test_640.jpg
else
    echo "✗ 640x480 capture failed"
fi

echo ""
echo "6. Testing with ffmpeg (640x480):"
timeout 10 ffmpeg -f v4l2 -video_size 640x480 -i /dev/video0 -frames:v 1 /tmp/test_ffmpeg.jpg -y 2>&1 | tail -20

if [ -f /tmp/test_ffmpeg.jpg ]; then
    echo "✓ ffmpeg capture successful"
    ls -lh /tmp/test_ffmpeg.jpg
else
    echo "✗ ffmpeg capture failed"
fi

echo ""
echo "7. USB device info:"
lsusb | grep -i "camera\|webcam\|video"

echo ""
echo "========================================="
echo "DIAGNOSTIC COMPLETE"
echo "========================================="
