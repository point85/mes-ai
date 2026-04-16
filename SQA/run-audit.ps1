# Initialize OpenClaw Environment for Windows
Write-Host "Starting UI Audit..." -ForegroundColor Cyan

# Execute OpenClaw command
# We use the '--' to ensure arguments are passed correctly through the PowerShell parser
openclaw run ui-auditor "Audit the latest build. Focus on the abstract timeline icons and verify the 2026-01 modern design requirements."

# Optional: Keep the window open if there is an error
if ($LASTEXITCODE -ne 0) {
    Write-Host "Audit failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Pause
}