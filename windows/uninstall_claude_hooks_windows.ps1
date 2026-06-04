# AgentWatch -- uninstall Claude Code hooks for Windows
# Usage: powershell -ExecutionPolicy Bypass -File windows\uninstall_claude_hooks_windows.ps1

$ErrorActionPreference = "Stop"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$SettingsFile = Join-Path $env:USERPROFILE ".claude\settings.json"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $env:USERPROFILE ".claude\settings.json.agentwatch.bak.uninstall.$Timestamp"

if (-not (Test-Path $SettingsFile)) {
    Write-Host "[AgentWatch] No settings.json found. Nothing to uninstall."
    exit 0
}

Copy-Item $SettingsFile $BackupFile
Write-Host "[AgentWatch] Backed up to: $BackupFile"

$settings = Get-Content -Raw $SettingsFile | ConvertFrom-Json
$removed = @()

if ($settings.PSObject.Properties["hooks"]) {
    $hooksToRemove = @()
    foreach ($prop in $settings.hooks.PSObject.Properties) {
        $eventName = $prop.Name
        $entries = $prop.Value
        if (-not $entries) { continue }
        $kept = @()
        $hadRemoval = $false
        foreach ($entry in $entries) {
            $isAw = $false
            if ($entry.PSObject.Properties["hooks"]) {
                $filtered = @()
                foreach ($h in $entry.hooks) {
                    if ($h.PSObject.Properties["command"] -and ($h.command -match "agentwatch")) {
                        $isAw = $true
                        $hadRemoval = $true
                    } else {
                        $filtered += $h
                    }
                }
                if ($filtered.Count -gt 0) {
                    $entry.hooks = $filtered
                    $kept += $entry
                }
            }
            if ($entry.PSObject.Properties["command"] -and ($entry.command -match "agentwatch")) {
                $hadRemoval = $true
            } else {
                $kept += $entry
            }
        }
        if ($hadRemoval) {
            $removed += "$eventName"
            if ($kept.Count -gt 0) {
                $settings.hooks.$eventName = $kept
            } else {
                $hooksToRemove += $eventName
            }
        }
    }
    foreach ($name in $hooksToRemove) {
        $settings.hooks.PSObject.Properties.Remove($name)
    }
}

if ($removed.Count -gt 0) {
    $settings | ConvertTo-Json -Depth 10 | Set-Content $SettingsFile -Encoding UTF8
    Write-Host "[AgentWatch] Removed hooks for: $($removed -join ', ')"
} else {
    Write-Host "[AgentWatch] No AgentWatch hooks found -- nothing removed."
}

Write-Host ""
Write-Host "[AgentWatch] Uninstall complete."
Write-Host "  Backup: $BackupFile"
