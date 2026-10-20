# PowerShell Script to Upload ENHANCED Thermal Detection

$separator = "=" * 70

Write-Host $separator
Write-Host "UPLOADING THERMAL UPGRADE - Maximum Detection Power" -ForegroundColor Green
Write-Host $separator

# Step 1: Upload enhanced autonomous scanner
Write-Host ""
Write-Host "[1/2] Uploading enhanced fully_autonomous_wall_scanner.py..." -ForegroundColor Cyan
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\fully_autonomous_wall_scanner.py" pi@192.168.168.127:/home/pi/fully_autonomous_wall_scanner.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Upload successful!" -ForegroundColor Green
} else {
    Write-Host "  Upload failed!" -ForegroundColor Red
    exit 1
}

# Step 2: Upload thermal_analyzer module
Write-Host ""
Write-Host "[2/2] Uploading thermal_analyzer.py module..." -ForegroundColor Cyan
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\thermal_analyzer.py" pi@192.168.168.127:/home/pi/thermal_analyzer.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Upload successful!" -ForegroundColor Green
} else {
    Write-Host "  Upload failed!" -ForegroundColor Red
    exit 1
}

# Step 3: Copy to crack_detector folder
Write-Host ""
Write-Host "[3/3] Copying files to /home/pi/crack_detector/..." -ForegroundColor Cyan
ssh pi@192.168.168.127 "cp /home/pi/fully_autonomous_wall_scanner.py /home/pi/crack_detector/ && cp /home/pi/thermal_analyzer.py /home/pi/crack_detector/"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Files copied!" -ForegroundColor Green
} else {
    Write-Host "  Copy failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host $separator
Write-Host "THERMAL UPGRADE COMPLETE!" -ForegroundColor Green
Write-Host $separator

Write-Host ""
Write-Host "NEW CAPABILITIES:" -ForegroundColor Yellow
Write-Host "  - 4-algorithm detection (variance, gradient, cluster, edge)"
Write-Host "  - Severity scoring (0-100 instead of yes/no)"
Write-Host "  - Crack classification (cold_crack, hot_crack, surface_crack)"
Write-Host "  - Improved depth estimation"
Write-Host "  - Automatic fallback to basic if module unavailable"

Write-Host ""
Write-Host "TEST COMMAND:" -ForegroundColor Yellow
Write-Host "  ssh pi@192.168.168.127"
Write-Host "  cd /home/pi/crack_detector"
Write-Host "  python3 fully_autonomous_wall_scanner.py"

Write-Host ""
Write-Host "Maximum thermal power activated!" -ForegroundColor Green
