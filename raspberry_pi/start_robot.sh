#!/bin/bash
# Startup script for Robot Controller

echo "======================================"
echo "  Starting Robot Controller System"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "⚠️  Warning: Running as root is not recommended"
fi

# Check Python version
python3 --version

# Check required packages
echo ""
echo "Checking dependencies..."

packages=("picamera2" "opencv-python" "pyserial" "adafruit-circuitpython-mlx90640")

for pkg in "${packages[@]}"; do
    python3 -c "import ${pkg//-/_}" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ $pkg installed"
    else
        echo "❌ $pkg NOT installed"
        echo "   Install with: pip3 install $pkg"
    fi
done

echo ""
echo "Starting main controller..."
echo ""

# Run the main controller
python3 main_controller.py

echo ""
echo "Robot controller stopped"
