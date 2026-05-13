# Initialize OpenClaw Environment for Windows
Write-Host "Starting UI Audit..." -ForegroundColor Cyan

# Execute OpenClaw command
$task = @"
Audit the MES AI Design-Time client Unit of Measure (UoM) CRUD editor.
Stack: MES server on http://localhost:8081, DT-CLIENT on http://localhost:5177.

1. Verify both URLs respond before opening the browser.
2. Navigate to http://localhost:5177/uom and confirm the 'Units of Measure' heading is visible.
3. Run the full pytest suite and report results:
   cd c:\dev\mes_ai && .venv\Scripts\python.exe -m pytest SQA/modules/SQA-DT/test_uom_crud.py -v --tb=short 2>&1
4. For any failing test: capture a screenshot, classify the bug (UI/API/data), and append a findings entry to SQA/HEARTBEAT.md.
5. If all tests pass, append a green-pass entry to SQA/HEARTBEAT.md with the timestamp and test count.
"@

openclaw agent --agent main --local --message $task

# Optional: Keep the window open if there is an error
if ($LASTEXITCODE -ne 0) {
    Write-Host "Audit failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Pause
}