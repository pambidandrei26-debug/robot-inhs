#!/bin/bash
# Setup mjpg-streamer for DV28 USB webcam

echo "Installing mjpg-streamer..."
sudo apt-get install -y cmake libjpeg-dev gcc g++

cd /tmp
git clone https://github.com/jacksonliam/mjpg-streamer.git
cd mjpg-streamer/mjpg-streamer-experimental
make
sudo make install

echo "Starting mjpg-streamer..."
mjpg_streamer -i "input_uvc.so -d /dev/video0 -r 640x480 -f 10" -o "output_http.so -p 8090 -w /usr/local/share/mjpg-streamer/www"

echo "Stream available at: http://192.168.168.123:8090/?action=stream"
