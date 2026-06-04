# AgentWatch -- install Claude Code hooks for Windows
# Usage: powershell -ExecutionPolicy Bypass -File windows\install_claude_hooks_windows.ps1

$ErrorActionPreference = "Stop"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$SettingsFile = Join-Path $env:USERPROFILE ".claude\settings.json"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $env:USERPROFILE ".claude\settings.json.agentwatch.bak.$Timestamp"
$PythonBin = Join-Path $ProjectDir ".venv\Scripts\python.exe"
# Quote path for spaces: \"C:\path with spaces\python.exe\"
$QuotedPythonBin = "`"$PythonBin`""
$HookCommandPrefix = "$QuotedPythonBin -m agentwatch.cli hook"

Write-Host "[AgentWatch] Project: $ProjectDir"
Write-Host "[AgentWatch] Settings: $SettingsFile"
Write-Host "[AgentWatch] Python: $PythonBin"

# Backup
if (Test-Path $SettingsFile) {
    Copy-Item $SettingsFile $BackupFile
    Write-Host "[AgentWatch] Backed up to: $BackupFile"
} else {
    Write-Host "[AgentWatch] No existing settings.json -- creating fresh."
}

# Read existing or create empty
$settings = @{}
if (Test-Path $SettingsFile) {
    try {
        $raw = Get-Content -Raw $SettingsFile | ConvertFrom-Json
        $settings = $raw | ConvertTo-Json -Depth 10 | ConvertFrom-Json
    } catch {
        Write-Host "[AgentWatch] WARNING: Could not parse existing settings.json. Starting fresh."
    }
}

# Ensure hooks property exists
if (-not $settings.PSObject.Properties["hooks"]) {
    $settings | Add-Member -MemberType NoteProperty -Name "hooks" -Value @{}
}

# Define agentwatch hooks in correct schema format.
# Hook commands use quoted Python path to handle spaces in directory names.
$hookDefs = @{
    "PreToolUse" = @(
        @{
            hooks = @(
                @{
                    type = "command"
                    command = "$HookCommandPrefix --event PreToolUse"
                    timeout = 15
                }
            )
        }
    )
    "PostToolUse" = @(
        @{
            hooks = @(
                @{
                    type = "command"
                    command = "$HookCommandPrefix --event PostToolUse"
                    timeout = 15
                }
            )
        }
    )
    "Notification" = @(
        @{
            hooks = @(
                @{
                    type = "command"
                    command = "$HookCommandPrefix --event Notification"
                    timeout = 15
                }
            )
        }
    )
    "Stop" = @(
        @{
            hooks = @(
                @{
                    type = "command"
                    command = "$HookCommandPrefix --event Stop"
                    timeout = 15
                }
            )
        }
    )
    "PermissionRequest" = @(
        @{
            hooks = @(
                @{
                    type = "command"
                    command = "$HookCommandPrefix --event PermissionRequest"
                    timeout = 15
                }
            )
        }
    )
    "PermissionDenied" = @(
        @{
            hooks = @(
                @{
                    type = "command"
                    command = "$HookCommandPrefix --event PermissionDenied"
                    timeout = 15
                }
            )
        }
    )
}

$modified = @()
foreach ($eventName in $hookDefs.Keys) {
    $existing = @()
    try { $existing = $settings.hooks.$eventName } catch {}
    if (-not $existing) { $existing = @() }

    # Clean out old agentwatch entries
    $cleaned = @()
    foreach ($entry in $existing) {
        $hasAw = $false
        if ($entry.PSObject.Properties["hooks"]) {
            foreach ($h in $entry.hooks) {
                if ($h.PSObject.Properties["command"]) {
                    if ($h.command -match "agentwatch") { $hasAw = $true }
                }
            }
        }
        if ($entry.PSObject.Properties["command"]) {
            if ($entry.command -match "agentwatch") { $hasAw = $true }
        }
        if (-not $hasAw) { $cleaned += $entry }
    }

    $merged = $cleaned + $hookDefs[$eventName]
    $settings.hooks | Add-Member -MemberType NoteProperty -Name $eventName -Value $merged -Force
    $modified += $eventName
}

# Write back
$settings | ConvertTo-Json -Depth 10 | Set-Content $SettingsFile -Encoding UTF8

Write-Host "[AgentWatch] Hooks installed for: $($modified -join ', ')"
Write-Host "[AgentWatch] Settings written to: $SettingsFile"
Write-Host ""
Write-Host "[AgentWatch] Done!"
Write-Host "  Backup: $BackupFile"
Write-Host "  To test: .\.venv\Scripts\agentwatch.exe simulate danger"
Write-Host "  To uninstall: powershell -ExecutionPolicy Bypass -File windows\uninstall_claude_hooks_windows.ps1"
