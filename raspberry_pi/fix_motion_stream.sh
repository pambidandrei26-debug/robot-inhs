#!/bin/bash
# Fix Motion streaming issues

echo "Checking Motion status..."
sudo systemctl status motion --no-pager | head -20

echo ""
echo "Checking if Motion is listening on port 8081..."
sudo netstat -tlnp | grep 8081

echo ""
echo "Checking Motion logs..."
sudo tail -30 /var/log/motion/motion.log

echo ""
echo "Testing if we can access Motion stream locally..."
curl -I http://localhost:8081 2>&1 | head -5

echo ""
echo "Current Motion config (stream settings)..."
grep -E "stream_port|stream_localhost|stream_quality" /etc/motion/motion.conf

echo ""
echo "Restarting Motion with verbose logging..."
sudo systemctl restart motion
sleep 3

echo ""
echo "Motion status after restart:"
sudo systemctl status motion --no-pager | head -15

echo ""
echo "Checking ports again..."
sudo netstat -tlnp | grep motion
