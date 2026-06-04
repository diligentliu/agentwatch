# AgentWatch Windows -- first-time setup
# Usage: powershell -ExecutionPolicy Bypass -File windows\setup_windows.ps1

$ErrorActionPreference = "Stop"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Write-Host "============================================"
Write-Host "  AgentWatch -- Windows First-Time Setup"
Write-Host "============================================"
Write-Host ""

# 1. .venv
$VenvPath = Join-Path $ProjectDir ".venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "[1/5] Creating virtual environment ..."
    python -m venv $VenvPath
    Write-Host "      .venv created."
} else {
    Write-Host "[1/5] Virtual environment already exists -- skipping."
}

# 2. pip install
Write-Host "[2/5] Installing agentwatch ..."
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
& $PythonExe -m pip install -q --upgrade pip setuptools 2>$null
& $PythonExe -m pip install -q -e $ProjectDir
Write-Host "      Done."

# 3. agentwatch init
Write-Host "[3/5] Initialising config and logs ..."
$AgentWatchExe = Join-Path $VenvPath "Scripts\agentwatch.exe"
& $AgentWatchExe init
Write-Host ""

# 4. agentwatch doctor
Write-Host "[4/5] Running health check ..."
& $AgentWatchExe doctor

# 5. Next steps
Write-Host ""
Write-Host "============================================"
Write-Host "  Next Steps"
Write-Host "============================================"
Write-Host ""
Write-Host "  1. Configure Bark:"
Write-Host "     .\.venv\Scripts\agentwatch.exe config bark"
Write-Host ""
Write-Host "  2. Test notifications:"
Write-Host "     .\.venv\Scripts\agentwatch.exe config test"
Write-Host ""
Write-Host "  3. Build Windows tray app:"
Write-Host "     powershell -ExecutionPolicy Bypass -File windows\build_app.ps1"
Write-Host ""
Write-Host "  4. Install Claude Code hooks (optional but recommended):"
Write-Host "     powershell -ExecutionPolicy Bypass -File windows\install_claude_hooks_windows.ps1"
Write-Host ""
Write-Host "  5. Launch the tray app:"
Write-Host "     build\windows\AgentWatchTray\AgentWatchTray.exe"
Write-Host "     or double-click 'Open AgentWatch Windows App.bat'"
Write-Host ""

Read-Host "Press Enter to exit..."
