# ============================================================
# SCP UPLOAD + VERIFY — Crack Detection Robot
# Uploads files to Pi then SSHes in to confirm each file
# Usage: .\scp_upload_and_verify.ps1
# ============================================================

param(
    [string]$PiUser = "pi",
    [string]$PiHost = "192.168.254.109",
    [string]$PiDest = "/home/pi"
)

$ROOT = "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi"

# ANSI colors
$G = "`e[92m"  # green
$R = "`e[91m"  # red
$Y = "`e[93m"  # yellow
$C = "`e[96m"  # cyan
$W = "`e[97m"  # white
$X = "`e[0m"   # reset

function Banner($txt) {
    Write-Host ""
    Write-Host "${C}============================================================${X}"
    Write-Host "${C}  $txt${X}"
    Write-Host "${C}============================================================${X}"
}

function Ok($msg)   { Write-Host "  ${G}[OK]${X}      $msg" }
function Fail($msg) { Write-Host "  ${R}[FAIL]${X}    $msg" }
function Warn($msg) { Write-Host "  ${Y}[WARN]${X}    $msg" }
function Info($msg) { Write-Host "  ${C}[INFO]${X}    $msg" }

# ── Files to upload ─────────────────────────────────────────
# Each entry: local filename (inside raspberry_pi\) -> description
$FILES = [ordered]@{
    "web_remote_control.py"              = "Web dashboard (port 5000) — crack size panel added"
    "web_data_analytics.py"              = "Analytics dashboard (port 8080) — crack size columns added"
    "fully_autonomous_wall_scanner.py"   = "Main scanner v2.0 — optimized sensor roles"
    "check_pi_files.sh"                  = "Pi file verification script"
}

# ── Version markers to verify after upload ──────────────────
# key = filename, value = string that must exist in the file on Pi
$VERIFY_MARKERS = @{
    "web_remote_control.py"            = "crack_analysis"
    "web_data_analytics.py"            = "extract_crack_size"
    "fully_autonomous_wall_scanner.py" = "v2.0"
    "check_pi_files.sh"                = "CRACK DETECTION ROBOT"
}

# ────────────────────────────────────────────────────────────
Banner "STEP 1 — PING CHECK"

Write-Host ""
Write-Host "  Testing connection to ${W}$PiHost${X} ..."
$ping = Test-Connection -ComputerName $PiHost -Count 2 -Quiet 2>$null
if (-not $ping) {
    Fail "Cannot reach $PiHost"
    Write-Host ""
    Write-Host "  Possible fixes:"
    Write-Host "   • Power on the Raspberry Pi"
    Write-Host "   • Check WiFi — both PC and Pi on same network"
    Write-Host "   • Try:  arp -a | Select-String '192.168'  (find real IP)"
    Write-Host "   • Try:  ping raspberrypi.local"
    Write-Host ""
    exit 1
}
Ok "$PiHost is reachable"

# ── Check SCP ───────────────────────────────────────────────
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Fail "scp not found — install OpenSSH client:"
    Write-Host "    Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0"
    exit 1
}
Ok "scp is available"

# ────────────────────────────────────────────────────────────
Banner "STEP 2 — UPLOAD FILES"
Write-Host ""

$uploaded = 0
$failed   = 0

foreach ($file in $FILES.Keys) {
    $desc    = $FILES[$file]
    $srcPath = Join-Path $ROOT $file
    $dstPath = "$PiDest/$file"

    Write-Host "  ${W}→ $file${X}"
    Info $desc

    if (-not (Test-Path $srcPath)) {
        Fail "Local file not found: $srcPath"
        $failed++
        Write-Host ""
        continue
    }

    $fileSize = [math]::Round((Get-Item $srcPath).Length / 1KB, 1)
    Info "Size: ${fileSize} KB"

    $output = scp "$srcPath" "${PiUser}@${PiHost}:${dstPath}" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Ok "Uploaded successfully"
        $uploaded++
    } else {
        Fail "Upload failed: $output"
        $failed++
    }
    Write-Host ""
}

Write-Host "  Upload summary — ${G}$uploaded uploaded${X}  /  $(if($failed -gt 0){"${R}$failed failed${X}"}else{"${G}$failed failed${X}"})"

# ────────────────────────────────────────────────────────────
Banner "STEP 3 — VERIFY FILES ON PI"
Write-Host ""
Write-Host "  Connecting to Pi to verify each file..."
Write-Host ""

$verifyPassed = 0
$verifyFailed = 0

foreach ($file in $FILES.Keys) {
    $dstPath = "$PiDest/$file"
    $marker  = $VERIFY_MARKERS[$file]

    Write-Host "  ${W}Checking: $file${X}"

    # Check file exists + get size and modification time
    $statCmd = "stat -c '%s bytes | modified: %y' $dstPath 2>/dev/null && echo EXISTS || echo MISSING"
    $statOut = ssh "${PiUser}@${PiHost}" $statCmd 2>&1

    if ($statOut -match "MISSING" -or $LASTEXITCODE -ne 0) {
        Fail "File NOT found on Pi: $dstPath"
        $verifyFailed++
        Write-Host ""
        continue
    }

    # Extract stat info (first line)
    $statLine = ($statOut -split "`n")[0]
    Ok "EXISTS  — $statLine"

    # Check version marker
    if ($marker) {
        $grepCmd = "grep -c '$marker' $dstPath 2>/dev/null || echo 0"
        $grepOut = ssh "${PiUser}@${PiHost}" $grepCmd 2>&1
        $hits    = [int]($grepOut -replace '\D','')

        if ($hits -gt 0) {
            Ok "Marker found: '$marker' ($hits line(s)) ✅"
            $verifyPassed++
        } else {
            Warn "Marker '$marker' NOT found — file may be the OLD version"
            $verifyFailed++
        }
    } else {
        $verifyPassed++
    }
    Write-Host ""
}

# ────────────────────────────────────────────────────────────
Banner "STEP 4 — QUICK PI STATUS"
Write-Host ""

# Run a one-liner on the Pi: IP, Python version, running processes
$statusCmd = @"
echo '--- IP ---' && hostname -I | awk '{print \$1}' &&
echo '--- Python ---' && python3 --version &&
echo '--- Running ---' && ps aux | grep -E 'web_remote|web_data|wall_scanner|crack_detect' | grep -v grep | awk '{print \$11}' || echo none &&
echo '--- Ports ---' && ss -tlnp 2>/dev/null | grep -E '5000|8080' | awk '{print \$4}' || echo none &&
echo '--- Disk ---' && df -h / | tail -1 | awk '{print "Used: "\$3"  Free: "\$4"  (""\$5" used)"}'
"@

$status = ssh "${PiUser}@${PiHost}" $statusCmd 2>&1

if ($LASTEXITCODE -eq 0) {
    $lines  = $status -split "`n"
    $ip     = ($lines | Select-String -Pattern '^\d+\.\d+' | Select-Object -First 1).ToString().Trim()
    $pyver  = ($lines | Select-String -Pattern 'Python').ToString().Trim()
    $disk   = ($lines | Select-String -Pattern 'Used:').ToString().Trim()

    if ($ip)    { Ok "Pi IP:      $ip" }
    if ($pyver) { Ok "Python:     $pyver" }
    if ($disk)  { Ok "Disk:       $disk" }

    # Running services
    $running = $lines | Where-Object { $_ -match '\.py$' }
    if ($running) {
        foreach ($r in $running) { Ok "Running:    $($r.Trim())" }
    } else {
        Info "No scanner/web services currently running"
    }

    # Open ports
    $ports = $lines | Where-Object { $_ -match '5000|8080' }
    if ($ports) {
        foreach ($p in $ports) { Ok "Port open:  $($p.Trim())" }
    } else {
        Info "Ports 5000/8080 not yet open (services not started)"
    }
} else {
    Warn "Could not get Pi status — SSH may need password"
}

# ────────────────────────────────────────────────────────────
Banner "DONE"
Write-Host ""
Write-Host "  Upload:  ${G}$uploaded OK${X}  /  $(if($failed -gt 0){"${R}$failed FAILED${X}"}else{"${G}0 FAILED${X}"})"
Write-Host "  Verify:  ${G}$verifyPassed OK${X}  /  $(if($verifyFailed -gt 0){"${Y}$verifyFailed WARN${X}"}else{"${G}0 WARN${X}"})"
Write-Host ""

if ($ip) {
    Write-Host "  ${C}To start the web dashboard on Pi:${X}"
    Write-Host "    ssh ${PiUser}@${PiHost} 'nohup python3 ~/web_remote_control.py > ~/web.log 2>&1 &'"
    Write-Host ""
    Write-Host "  ${C}To start analytics on Pi:${X}"
    Write-Host "    ssh ${PiUser}@${PiHost} 'nohup python3 ~/web_data_analytics.py > ~/analytics.log 2>&1 &'"
    Write-Host ""
    Write-Host "  ${C}To run the file check script on Pi:${X}"
    Write-Host "    ssh ${PiUser}@${PiHost} 'bash ~/check_pi_files.sh'"
    Write-Host ""
    Write-Host "  ${C}Then open browser:${X}"
    Write-Host "    http://${ip}:5000   (Robot control + crack size)"
    Write-Host "    http://${ip}:8080   (Analytics + growth table)"
}
Write-Host ""
