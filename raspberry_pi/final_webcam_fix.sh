#!/bin/bash
# Final attempt: Use Motion in snapshot mode instead of streaming

sudo pkill -9 motion
sleep 2

# Configure Motion for snapshot mode
sudo tee /etc/motion/motion.conf > /dev/null <<'EOF'
# Motion snapshot configuration
daemon off
process_id_file /var/run/motion/motion.pid

# Video device
videodevice /dev/video0
v4l2_palette 17
width 640
height 480
framerate 5

# Disable motion detection
threshold 999999

# Save latest snapshot continuously
picture_output on
picture_filename latest
snapshot_interval 1
snapshot_filename snapshot
target_dir /tmp/motion

# Disable streaming (it's broken)
stream_port 0
webcontrol_port 0
movie_output off
EOF

# Create snapshot directory
sudo mkdir -p /tmp/motion
sudo chmod 777 /tmp/motion

echo "Starting Motion in snapshot mode..."
sudo motion -c /etc/motion/motion.conf &
sleep 3

echo "Motion should be saving to /tmp/motion/"
ls -lh /tmp/motion/
