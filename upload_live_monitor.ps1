# ============================================================================
# UPLOAD LIVE MONITOR ENHANCEMENT
# ============================================================================

$PI_IP = "192.168.168.127"
$PI_USER = "pi"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " UPLOADING LIVE MONITOR ENHANCEMENT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# File to upload
$LOCAL_FILE = "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\fully_autonomous_wall_scanner.py"
$REMOTE_FILE = "/home/pi/fully_autonomous_wall_scanner.py"
$DEST_DIR = "/home/pi/crack_detector"

Write-Host "[1/3] Uploading enhanced scanner to Pi..." -ForegroundColor Yellow
scp "$LOCAL_FILE" "${PI_USER}@${PI_IP}:${REMOTE_FILE}"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Success: Upload complete" -ForegroundColor Green
} else {
    Write-Host "  Error: Upload failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/3] Moving to crack_detector directory..." -ForegroundColor Yellow
ssh "${PI_USER}@${PI_IP}" "cp ${REMOTE_FILE} ${DEST_DIR}/"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Success: File moved" -ForegroundColor Green
} else {
    Write-Host "  Error: Move failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3/3] Verifying installation..." -ForegroundColor Yellow
ssh "${PI_USER}@${PI_IP}" "ls -lh ${DEST_DIR}/fully_autonomous_wall_scanner.py"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Success: Verification complete" -ForegroundColor Green
} else {
    Write-Host "  Error: Verification failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " LIVE MONITOR ENHANCEMENT DEPLOYED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "FEATURES ADDED:" -ForegroundColor Yellow
Write-Host "  - Real-time logging to ~/scan_output.log" -ForegroundColor Green
Write-Host "  - Timestamps for every action" -ForegroundColor Green
Write-Host "  - Detailed position tracking" -ForegroundColor Green
Write-Host "  - Distance readings logged" -ForegroundColor Green
Write-Host "  - Thermal analysis results" -ForegroundColor Green
Write-Host "  - Movement commands logged" -ForegroundColor Green
Write-Host "  - Crack detection with details" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. Run autonomous scan from web dashboard" -ForegroundColor White
Write-Host "  2. Open LIVE SCAN MONITOR section" -ForegroundColor White
Write-Host "  3. Watch detailed real-time progress!" -ForegroundColor White
Write-Host ""
Write-Host "Web Dashboard: http://${PI_IP}:5000" -ForegroundColor Cyan
Write-Host ""
