# Contributing

## Development Setup

```bash
cd ~/Projects/agentwatch
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
agentwatch init
```

## Running Tests

```bash
# Health check
agentwatch doctor

# Notification tests (requires Bark key in config.json)
agentwatch simulate permission-request
agentwatch simulate permission-denied
agentwatch simulate permission
agentwatch simulate done
agentwatch simulate danger
agentwatch simulate approval-pending
agentwatch simulate auto-exec

# Persona tests
agentwatch persona set emperor
agentwatch persona test permission
agentwatch persona test done
agentwatch persona off

# View logs
agentwatch logs --tail 20
agentwatch monitor
```

## Building the macOS App

```bash
bash macos/build_app.sh
open build/AgentWatch.app
```

Requires Xcode or Command Line Tools (`swift build`).

## Building the Windows App

```powershell
powershell -ExecutionPolicy Bypass -File windows\build_app.ps1
build\windows\AgentWatchTray\AgentWatchTray.exe
```

Requires .NET 8 SDK.

## Release Builds

Pushing any new Git tag starts the macOS and Windows build jobs. When both builds succeed, GitHub Actions creates a release for that tag and attaches `AgentWatch-macOS-arm64.zip` and `AgentWatch-Windows-x64.zip`.

## Pull Request Guidelines

- Do **not** include `config.json`, `logs/`, `.venv/`, `diagnostics/`, or `build/` output.
- Do **not** include real Bark keys in test output, code comments, or documentation.
- Do **not** include personal file paths (use `$HOME`, `~`, or `%USERPROFILE%`).
- Do **not** auto-install hooks in tests or PRs.
- Run `agentwatch doctor` and confirm `Status: Ready` before submitting.
- Update `CHANGELOG.md` under an `Unreleased` section.
- For Windows-specific changes, test on Windows. For macOS-specific changes, test on macOS. Python core changes should be tested on both if possible.

## Code Style

- Python: follow PEP 8. Use `pathlib` for paths. Use `urllib.request` for HTTP. Avoid external dependencies.
- Swift: follow standard Swift conventions. Use `@MainActor` for UI code.
- C#: follow standard C# conventions. Target `net8.0-windows`.
