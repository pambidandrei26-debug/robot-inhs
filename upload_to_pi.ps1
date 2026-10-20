# ============================================================
# UPLOAD UPDATED FILES TO RASPBERRY PI
# Run from Windows:  .\upload_to_pi.ps1
# ============================================================

param(
    [string]$PiUser = "pi",
    [string]$PiHost = "192.168.254.109"
)

$ErrorActionPreference = "Stop"
$ROOT = "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM"

$CYAN   = "`e[96m"
$GREEN  = "`e[92m"
$RED    = "`e[91m"
$YELLOW = "`e[93m"
$RESET  = "`e[0m"

function Write-Ok($msg)   { Write-Host "  ${GREEN}[OK]${RESET}  $msg" }
function Write-Fail($msg) { Write-Host "  ${RED}[FAIL]${RESET}  $msg" }
function Write-Info($msg) { Write-Host "  ${CYAN}[INFO]${RESET}  $msg" }

Write-Host ""
Write-Host "${CYAN}============================================================${RESET}"
Write-Host "${CYAN}  UPLOAD TO RASPBERRY PI — $PiUser@$PiHost${RESET}"
Write-Host "${CYAN}============================================================${RESET}"
Write-Host ""

# Check SCP available
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Fail "scp not found. Install OpenSSH client:"
    Write-Host "    Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0"
    exit 1
}

# Files to upload: local source -> remote destination
$FILES = @(
    @{ Src = "$ROOT\raspberry_pi\web_remote_control.py";        Dst = "/home/pi/web_remote_control.py";        Desc = "Web dashboard (crack size panel)" },
    @{ Src = "$ROOT\raspberry_pi\web_data_analytics.py";        Dst = "/home/pi/web_data_analytics.py";        Desc = "Analytics (crack size columns)" },
    @{ Src = "$ROOT\raspberry_pi\fully_autonomous_wall_scanner.py"; Dst = "/home/pi/fully_autonomous_wall_scanner.py"; Desc = "Main scanner v2.0 (optimized sensors)" },
    @{ Src = "$ROOT\raspberry_pi\check_pi_files.sh";            Dst = "/home/pi/check_pi_files.sh";            Desc = "Pi file check script" }
)

Write-Host "Pinging $PiHost ..."
$ping = Test-Connection -ComputerName $PiHost -Count 1 -Quiet
if (-not $ping) {
    Write-Fail "Cannot reach $PiHost — make sure Pi is powered on and on the same WiFi."
    exit 1
}
Write-Ok "Pi is reachable"
Write-Host ""

$uploaded = 0
$failed   = 0

foreach ($f in $FILES) {
    if (-not (Test-Path $f.Src)) {
        Write-Fail "Source not found: $($f.Src)"
        $failed++
        continue
    }

    Write-Host "  Uploading: $([System.IO.Path]::GetFileName($f.Src))"
    Write-Info "  $($f.Desc)"

    try {
        $result = scp "$($f.Src)" "${PiUser}@${PiHost}:$($f.Dst)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Done`n"
            $uploaded++
        } else {
            Write-Fail "scp exited $LASTEXITCODE : $result`n"
            $failed++
        }
    } catch {
        Write-Fail "$($_.Exception.Message)`n"
        $failed++
    }
}

Write-Host "${CYAN}============================================================${RESET}"
Write-Host "  Uploaded: ${GREEN}$uploaded${RESET}   Failed: $(if($failed -gt 0){"${RED}$failed${RESET}"}else{"${GREEN}$failed${RESET}"})"
Write-Host "${CYAN}============================================================${RESET}"
Write-Host ""

if ($uploaded -gt 0) {
    Write-Host "Next steps on the Pi:"
    Write-Host "  1. SSH:          ${CYAN}ssh $PiUser@$PiHost${RESET}"
    Write-Host "  2. Make sh exec: ${CYAN}chmod +x ~/check_pi_files.sh${RESET}"
    Write-Host "  3. Run check:    ${CYAN}bash ~/check_pi_files.sh${RESET}"
    Write-Host "  4. Start web:    ${CYAN}python3 ~/web_remote_control.py${RESET}"
    Write-Host ""

    $ans = Read-Host "SSH into Pi now? (y/n)"
    if ($ans -match '^[Yy]') {
        ssh "${PiUser}@${PiHost}"
    }
}
