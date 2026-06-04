# AgentWatch Windows -- build the system tray app
# Usage: powershell -ExecutionPolicy Bypass -File windows\build_app.ps1

$ErrorActionPreference = "Stop"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$BuildDir   = Join-Path $ProjectDir "build\windows\AgentWatchTray"

Write-Host "============================================"
Write-Host "  AgentWatch -- Building Windows Tray App"
Write-Host "============================================"
Write-Host ""

# Check dotnet
$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet) {
    Write-Host "[ERROR] dotnet SDK not found. Install .NET 8 SDK from https://dotnet.microsoft.com"
    exit 1
}
Write-Host "[1/4] dotnet SDK: $($dotnet.Source)"

# Build
$Csproj = Join-Path $ScriptDir "AgentWatchTray\AgentWatchTray.csproj"
Write-Host "[2/4] Building release (win-x64, framework-dependent)..."
Push-Location $ScriptDir
dotnet publish $Csproj -c Release -r win-x64 --self-contained false -o "$BuildDir" 2>&1
Pop-Location
Write-Host "      Done."

# Verify
$ExePath = Join-Path $BuildDir "AgentWatchTray.exe"
if (Test-Path $ExePath) {
    Write-Host "[3/4] Executable: $ExePath"
} else {
    Write-Host "[ERROR] Build succeeded but .exe not found. Check output above."
    exit 1
}

Write-Host "[4/4] Verifying..."
Write-Host ""

Write-Host "============================================"
Write-Host "  Build Complete"
Write-Host "============================================"
Write-Host ""
Write-Host "  App:  $ExePath"
Write-Host ""
Write-Host "  To launch:"
Write-Host "    $ExePath"
Write-Host "    or double-click 'Open AgentWatch Windows App.bat'"
Write-Host ""
Write-Host "  The app runs in the system tray (bottom-right)."
Write-Host "  Right-click the icon to open the menu."
