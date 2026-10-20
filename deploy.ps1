# deploy.ps1 - Upload updated files to Pi and restart
# Usage: .\deploy.ps1

$PI   = "pi@192.168.168.127"
$ROOT = "C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi"
$OPT  = "-o StrictHostKeyChecking=no -o ConnectTimeout=15"

$FILES = @(
    "web_remote_control.py",
    "fully_autonomous_wall_scanner.py",
    "web_data_analytics.py",
    "run_scan.sh"
)

Write-Host ""
Write-Host "=== UPLOADING TO RASPBERRY PI ===" -ForegroundColor Cyan
Write-Host ""

$ok   = 0
$fail = 0

foreach ($f in $FILES) {
    $src = Join-Path $ROOT $f
    if (Test-Path $src) {
        Write-Host "Uploading $f ..." -NoNewline
        $proc = Start-Process -FilePath "scp" -ArgumentList "$OPT `"$src`" `"${PI}:/home/pi/$f`"" -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -eq 0) {
            Write-Host " OK" -ForegroundColor Green
            $ok++
        } else {
            Write-Host " FAILED" -ForegroundColor Red
            $fail++
        }
    } else {
        Write-Host "SKIP $f (not found)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Uploaded: $ok  Failed: $fail" -ForegroundColor Cyan

if ($fail -gt 0) {
    Write-Host "Some uploads failed. Check connection." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Restarting web dashboard on Pi..." -ForegroundColor Cyan
$restartCmd = "pkill -9 -f python3; sleep 2; chmod +x /home/pi/run_scan.sh; nohup python3 /home/pi/web_remote_control.py > /home/pi/web.log 2>&1 &"
$proc2 = Start-Process -FilePath "ssh" -ArgumentList "$OPT $PI `"$restartCmd`"" -Wait -PassThru -NoNewWindow

Start-Sleep 3

Write-Host "Checking if running..." -NoNewline
$checkCmd = "pgrep -f web_remote_control.py"
$proc3 = Start-Process -FilePath "ssh" -ArgumentList "$OPT $PI `"$checkCmd`"" -Wait -PassThru -NoNewWindow
if ($proc3.ExitCode -eq 0) {
    Write-Host " RUNNING" -ForegroundColor Green
} else {
    Write-Host " NOT RUNNING - check /home/pi/web.log" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Cyan
Write-Host "Open: http://192.168.168.127:5000" -ForegroundColor White
Write-Host "Then press Ctrl+Shift+R in browser" -ForegroundColor White
Write-Host ""
