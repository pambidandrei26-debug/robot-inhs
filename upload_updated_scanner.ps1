# ============================================================================
# UPLOAD UPDATED SCANNER TO RASPBERRY PI
# Uploads the refactored fully_autonomous_wall_scanner.py with new architecture
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "UPLOADING UPDATED SCANNER TO RASPBERRY PI" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Configuration
$PI_USER = "pi"
$PI_HOST = "192.168.254.109"  # Update if different
$PI_DEST = "/home/pi"

# Files to upload
$FILES = @(
    "raspberry_pi\fully_autonomous_wall_scanner.py",
    "SENSOR_ROLES_UPDATED.md"
)

Write-Host "Target: $PI_USER@$PI_HOST`:$PI_DEST" -ForegroundColor Yellow
Write-Host ""

# Check if scp is available
try {
    $null = Get-Command scp -ErrorAction Stop
    Write-Host "[OK] SCP found" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] SCP not found!" -ForegroundColor Red
    Write-Host "Install OpenSSH client or use PuTTY's pscp.exe" -ForegroundColor Yellow
    exit 1
}

# Upload each file
foreach ($file in $FILES) {
    $fullPath = Join-Path $PSScriptRoot $file
    
    if (Test-Path $fullPath) {
        Write-Host "Uploading: $file" -ForegroundColor Cyan
        
        try {
            scp $fullPath "${PI_USER}@${PI_HOST}:${PI_DEST}/"
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Uploaded successfully`n" -ForegroundColor Green
            } else {
                Write-Host "  [ERROR] Upload failed (exit code: $LASTEXITCODE)`n" -ForegroundColor Red
            }
        } catch {
            Write-Host "  [ERROR] $($_.Exception.Message)`n" -ForegroundColor Red
        }
    } else {
        Write-Host "[SKIP] File not found: $file" -ForegroundColor Yellow
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "UPLOAD COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Next steps on Raspberry Pi:" -ForegroundColor Yellow
Write-Host "1. SSH to Pi: ssh $PI_USER@$PI_HOST" -ForegroundColor White
Write-Host "2. Make executable: chmod +x fully_autonomous_wall_scanner.py" -ForegroundColor White
Write-Host "3. Test run: python3 fully_autonomous_wall_scanner.py" -ForegroundColor White
Write-Host ""

# Offer to SSH automatically
$response = Read-Host "Connect to Pi via SSH now? (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "`nConnecting to $PI_USER@$PI_HOST..." -ForegroundColor Cyan
    ssh "${PI_USER}@${PI_HOST}"
}
