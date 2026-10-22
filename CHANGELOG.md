# Changelog

## v0.9.0 (2026-10-22)

### Added
- Native Codex hooks with safe install and uninstall scripts
- Task submission, permission request, tool failure, and task completion notifications for Codex
- Tag-triggered macOS and Windows builds that publish downloadable GitHub Releases

### Changed
- GitHub release downloads now use the `diligentliu/agentwatch` repository

## v0.8.0 (2026-06-03)

### Added
- **PermissionRequest hook** support for real Claude Code "Allow this bash command?" prompts
- **PermissionDenied hook** logging — tracks denied operations
- **Persona Themes**: 总裁版, 少爷版, 大小姐版, 皇上版, 甄嬛版
- **macOS menu bar app**: native Swift + AppKit, full status & actions
- **Windows tray app source**: native C# / .NET 8 WinForms tray app
- **Bark Key configuration**: from CLI, macOS menu bar, or Windows tray
- **Actionable notification mode**: only pushes when user interaction is truly needed
- **Pending approval detection**: logs possible permission waits without false alerts
- **PreToolUse timeout log-only mode**: reduces false positives from long commands
- **ANSI monitor dashboard**: `agentwatch monitor`
- **One-click Mac launchers**: `AgentWatch.command`, `AgentWatch Setup.command`
- **Log redaction**: Bark keys automatically stripped from logs
- **Task boundaries**: set allowed/forbidden paths, detect drift silently

### Changed
- PreToolUse timeout no longer pushes Watch notifications by default (`timeout_watch_notify: false`)
- All real notifications now go through `message_builder` + persona templates
- Doctor now checks six hooks (includes PermissionRequest / PermissionDenied)

### Fixed
- False "needs permission" alerts when Bash commands run longer than 4 seconds
- Hook schema compatibility with Claude Code settings.json v2 format
- Persona theme not applied to pending-check notifications
- Windows hooks script Python path quoting for spaces

### Upgrade
- Users upgrading from older versions must reinstall hooks to enable PermissionRequest / PermissionDenied
