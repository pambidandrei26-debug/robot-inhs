#!/bin/bash
# Last attempt: Try different YUYV variants and color conversions

sudo pkill -9 motion
sleep 2

echo "Testing different pixel formats..."

# Test 1: Try UYVY instead of YUYV
echo ""
echo "=== Test 1: UYVY format ==="
v4l2-ctl -d /dev/video0 --set-fmt-video=width=640,height=480,pixelformat=UYVY
fswebcam -d /dev/video0 -r 640x480 --no-banner /tmp/test_uyvy.jpg
if [ -f /tmp/test_uyvy.jpg ]; then
    echo "UYVY test image saved"
    file /tmp/test_uyvy.jpg
fi

# Test 2: Try YU12 (YUV420)
echo ""
echo "=== Test 2: YU12 format ==="
v4l2-ctl -d /dev/video0 --set-fmt-video=width=640,height=480,pixelformat=YU12
fswebcam -d /dev/video0 -r 640x480 --no-banner /tmp/test_yu12.jpg
if [ -f /tmp/test_yu12.jpg ]; then
    echo "YU12 test image saved"
    file /tmp/test_yu12.jpg
fi

# Test 3: Try RGB24
echo ""
echo "=== Test 3: RGB24 format ==="
v4l2-ctl -d /dev/video0 --set-fmt-video=width=640,height=480,pixelformat=RGB3
fswebcam -d /dev/video0 -r 640x480 --no-banner /tmp/test_rgb24.jpg
if [ -f /tmp/test_rgb24.jpg ]; then
    echo "RGB24 test image saved"
    file /tmp/test_rgb24.jpg
fi

# Test 4: Try GREY (grayscale - should definitely work)
echo ""
echo "=== Test 4: GREY format ==="
v4l2-ctl -d /dev/video0 --set-fmt-video=width=640,height=480,pixelformat=GREY
fswebcam -d /dev/video0 -r 640x480 --no-banner /tmp/test_grey.jpg
if [ -f /tmp/test_grey.jpg ]; then
    echo "GREY test image saved"
    file /tmp/test_grey.jpg
fi

echo ""
echo "========================================="
echo "Test images saved to /tmp/"
echo "Check which one looks correct:"
ls -lh /tmp/test_*.jpg
echo "========================================="
