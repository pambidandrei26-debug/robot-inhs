#!/bin/bash
# Fix Motion configuration for DV28 camera

echo "Stopping Motion service..."
sudo systemctl stop motion

echo "Creating proper Motion configuration..."
sudo tee /etc/motion/motion.conf > /dev/null <<'EOF'
# Minimal Motion configuration for streaming only
daemon off
process_id_file /var/run/motion/motion.pid
log_level 6

# Video device
videodevice /dev/video0
v4l2_palette 8
input -1
norm 0
frequency 0
rotate 0
width 640
height 480
framerate 10
minimum_frame_time 0
auto_brightness off

# Motion detection (disabled - we just want streaming)
threshold 999999
noise_level 32

# Output control (disable all file outputs)
picture_output off
movie_output off

# Live stream settings
stream_port 8081
stream_quality 85
stream_motion off
stream_maxrate 10
stream_localhost off
stream_limit 0
stream_auth_method 0

# Disable webcontrol to avoid port conflicts
webcontrol_port 0
webcontrol_localhost on
EOF

echo "Setting permissions..."
sudo mkdir -p /var/run/motion
sudo chown motion:motion /var/run/motion
sudo mkdir -p /var/log/motion
sudo chown motion:motion /var/log/motion

echo ""
echo "Starting Motion in foreground mode for testing..."
echo "Press Ctrl+C to stop, then we'll run as daemon"
echo ""
sudo motion -n -c /etc/motion/motion.conf
