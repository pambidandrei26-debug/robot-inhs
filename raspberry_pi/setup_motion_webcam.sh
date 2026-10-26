#!/bin/bash
# Setup Motion for DV28 USB Webcam - proven solution for cheap Chinese webcams
# Content rephrased for compliance with licensing restrictions

echo "========================================="
echo "Installing Motion for USB Webcam"
echo "========================================="

# Install motion software
sudo apt-get update
sudo apt-get install -y motion

# Backup original config
sudo cp /etc/motion/motion.conf /etc/motion/motion.conf.backup

# Configure motion for USB webcam
sudo tee /etc/motion/motion.conf > /dev/null <<'EOF'
# Motion configuration for DV28 USB webcam
daemon on
process_id_file /var/run/motion/motion.pid

# Device settings
videodevice /dev/video0
v4l2_palette 8
input -1

# Image dimensions
width 640
height 480
framerate 10

# Minimal motion detection (we don't need motion detect, just streaming)
threshold 999999
minimum_motion_frames 1

# Output - disable file saving, we just need stream
output_pictures off
ffmpeg_output_movies off

# Streaming settings
stream_port 8081
stream_quality 85
stream_maxrate 10
stream_localhost off
stream_auth_method 0

# Web control
webcontrol_port 8080
webcontrol_localhost off
webcontrol_parms 0
EOF

# Enable motion daemon
sudo sed -i 's/start_motion_daemon=no/start_motion_daemon=yes/g' /etc/default/motion

# Create required directories
sudo mkdir -p /var/run/motion
sudo chown motion:motion /var/run/motion

echo ""
echo "========================================="
echo "Motion configured successfully!"
echo "========================================="
echo ""
echo "Starting motion service..."
sudo systemctl enable motion
sudo systemctl restart motion

echo ""
echo "Waiting for motion to start..."
sleep 3

echo ""
echo "Motion status:"
sudo systemctl status motion --no-pager

echo ""
echo "========================================="
echo "WEBCAM STREAM AVAILABLE AT:"
echo "http://192.168.168.123:8081"
echo "========================================="
echo ""
echo "You can now integrate this stream into web_remote_control.py"
