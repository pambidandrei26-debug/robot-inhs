#!/bin/bash
# Initialize DV28 USB Camera with proper settings

echo "Initializing DV28 USB Camera..."

# Reset camera
v4l2-ctl -d /dev/video0 --set-fmt-video=width=640,height=480,pixelformat=MJPG

# Set optimal controls
v4l2-ctl -d /dev/video0 --set-ctrl=brightness=128
v4l2-ctl -d /dev/video0 --set-ctrl=contrast=21
v4l2-ctl -d /dev/video0 --set-ctrl=saturation=450
v4l2-ctl -d /dev/video0 --set-ctrl=gain=21
v4l2-ctl -d /dev/video0 --set-ctrl=power_line_frequency=1  # 50Hz
v4l2-ctl -d /dev/video0 --set-ctrl=white_balance_temperature_auto=1
v4l2-ctl -d /dev/video0 --set-ctrl=backlight_compensation=0

# Verify settings
echo "Camera settings applied:"
v4l2-ctl -d /dev/video0 --get-fmt-video

echo "Camera initialized successfully!"
