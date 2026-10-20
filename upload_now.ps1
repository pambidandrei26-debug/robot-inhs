# UPLOAD FILES TO RASPBERRY PI
# Run this on Windows: .\upload_now.ps1

$PiUser = "pi"
$PiHost = "192.168.168.127"
$ROOT   = "C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi"

$FILES = @(
    "web_remote_control.py",
    "web_data_analytics.py",
    "fully_autonomous_wall_scanner.py",
    "thermal_analyzer_enhanced.py",
    "autonomous_crack_detector.py",
    "crack_detector.py",
    "crack_detector_enhanced.py",
    "thermal_crack_tracker.py",
    "scan_patterns.py",
    "acoustic_analyzer.py",
    "calibrate_rotation.py",
    "manual_calibration.py",
    "test_robot_nocam.py",
    "test_thermal.py",
    "check_pi_files.sh",
    "start_robot.sh",
    "start_web_remote.sh"
)

Write-Host ""
Write-Host "====================================================="
Write-Host "  UPLOADING FILES TO $PiUser@$PiHost"
Write-Host "====================================================="
Write-Host ""

# Ping check
Write-Host "Checking connection to Pi..."
$ping = Test-Connection -ComputerName $PiHost -Count 1 -Quiet
if (-not $ping) {
    Write-Host "ERROR: Cannot reach $PiHost - check Pi is on and connected"
    exit 1
}
Write-Host "Pi is reachable!"
Write-Host ""

# Upload each file
$ok   = 0
$fail = 0
$skip = 0

foreach ($file in $FILES) {
    $src = Join-Path $ROOT $file
    $dst = "${PiUser}@${PiHost}:/home/pi/$file"

    if (-not (Test-Path $src)) {
        Write-Host "[SKIP]   $file (not in local folder)"
        $skip++
        continue
    }

    Write-Host "[UPLOAD] $file ..."
    scp "$src" "$dst"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK]     $file uploaded"
        $ok++
    } else {
        Write-Host "[FAIL]   $file upload failed"
        $fail++
    }
}

Write-Host ""
Write-Host "====================================================="
Write-Host "  UPLOAD DONE: $ok uploaded, $fail failed, $skip skipped"
Write-Host "====================================================="
Write-Host ""

if ($fail -gt 0) {
    Write-Host "Some files failed. Check your SSH/SCP connection."
    Write-Host ""
}

# Now verify what's on Pi
Write-Host "====================================================="
Write-Host "  VERIFYING FILES ON PI..."
Write-Host "====================================================="
Write-Host ""

$checkCmd = "echo '--- FILES ON PI ---' && ls -lh /home/pi/*.py /home/pi/*.sh 2>/dev/null && echo '' && echo '--- VERSION CHECK ---' && grep -l 'crack_analysis' /home/pi/web_remote_control.py 2>/dev/null && echo 'web_remote_control OK' && grep -l 'extract_crack_size' /home/pi/web_data_analytics.py 2>/dev/null && echo 'web_data_analytics OK' && grep -l 'v2.0' /home/pi/fully_autonomous_wall_scanner.py 2>/dev/null && echo 'wall_scanner v2.0 OK'"

ssh "${PiUser}@${PiHost}" $checkCmd

Write-Host ""
Write-Host "====================================================="
Write-Host "  CHECK COMPLETE"
Write-Host "====================================================="
Write-Host ""
Write-Host "To start web dashboard on Pi:"
Write-Host "  ssh pi@$PiHost"
Write-Host "  python3 ~/web_remote_control.py"
Write-Host ""
