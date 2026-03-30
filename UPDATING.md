# How to Update unified-context

The MCP server is installed from GitHub as an editable package (`pip install -e .`). When new features are added, you can pull the latest and reinstall.

---

## Quick Update (if already installed)

### Using `uv` (Recommended)
```bash
uv tool upgrade unified-context
```

This automatically pulls the latest from GitHub and reinstalls.

### Using `pip`

**If you installed with pip:**
```bash
pip install --upgrade git+https://github.com/anilcelexsa/unified-context.git
```

**If you cloned the repo and installed with `pip install -e .`:**
```bash
cd /path/to/unified-context
git pull origin main
pip install --upgrade -e .
```

---

## Verify the Update

After updating, verify both the CLI and MCP server are working:

```bash
# Check CLI version
uctx --version

# Check MCP server is runnable
uctx-mcp --version        # or just run it and hit Ctrl+C

# Test a tool call (requires .uctx/ to exist)
uctx stats
```

---

## Update the IDE Config (if MCP binary path changed)

If the installer moved the `uctx-mcp` binary to a new location, you may need to re-run the IDE setup command:

```bash
cd /path/to/your/project

# Regenerate MCP config for your IDEs
uctx setup claude-code
uctx setup cursor
uctx setup vscode
# etc.
```

This updates the MCP config files (`.claude/mcp.json`, `.cursor/mcp.json`, etc.) with the new binary path.

**Verify the config was updated:**
```bash
cat .claude/mcp.json | grep command
```

The path should point to the new `uctx-mcp` location.

---

## Troubleshooting Update Issues

### "uctx-mcp: command not found"
The binary isn't on your PATH. Run:

```bash
# Find the new location
which uctx-mcp          # macOS/Linux
where uctx-mcp          # Windows

# If empty, reinstall
pip install --upgrade --force-reinstall git+https://github.com/anilcelexsa/unified-context.git

# Add to PATH if needed
# On macOS/Linux: add ~/.local/bin to ~/.bashrc or ~/.zshrc
# On Windows: use Settings → Environment Variables
```

### "MCP connection failed" in IDE
The IDE still has the old binary path cached. Fix by:

1. Closing the IDE completely
2. Re-running `uctx setup <ide-name>`
3. Restarting the IDE

### ".uctx/ directory issues"
New versions sometimes change the context store structure. Rebuild the index:

```bash
uctx index              # rebuilds .uctx/INDEX.md
uctx stats              # verify store integrity
```

---

## What's New? Check the Changelog

After updating, check what changed:

```bash
cd /path/to/unified-context
git log --oneline main -10
```

Or check the GitHub releases page: https://github.com/anilcelexsa/unified-context/releases

---

## Staying Up to Date

### Option 1: Manual checks (simplest)
Every month, run:
```bash
uv tool upgrade unified-context
```

### Option 2: Automated checks (if available)
If the project sets up GitHub Actions, check for release notifications on the repo.

### Option 3: Watch the repo on GitHub
Go to https://github.com/anilcelexsa/unified-context → "Watch" → select "Releases" to get email notifications.

---

## Breaking Changes

New versions are backward-compatible with existing `.uctx/` stores. If a version introduces a breaking change, the release notes will clearly state it and provide migration instructions.

Common migration scenarios:
- **Field added to task schema:** Old tasks still work; new field is optional.
- **New tool added:** Existing tools unchanged; just ignore the new tool if you don't need it.
- **Tool parameter added:** Old calls still work; new parameter is optional.

---

## Reporting Issues After Update

If an update breaks something:

1. Note the version before and after: `uctx --version`
2. Run `uctx stats` to confirm `.uctx/` is intact
3. Try: `uctx index` (rebuild the index)
4. If still broken, check GitHub issues: https://github.com/anilcelexsa/unified-context/issues
5. If not reported, open a new issue with:
   - Your Python version: `python --version`
   - Your OS and shell
   - The exact error message
   - Steps to reproduce

---

## For Developers (Local Testing)

If you're developing the MCP server locally:

```bash
cd /path/to/unified-context

# Install in development mode (editable)
pip install -e ".[dev]"

# Run tests (if available)
pytest

# Test the MCP server directly
python -m unified_context.mcp_server

# Reinstall after making changes
pip install -e .

# For your IDE to see changes, restart it or re-run:
uctx setup <ide-name>
```

---

## Summary

| Task | Command |
|------|---------|
| Update to latest | `uv tool upgrade unified-context` |
| Verify update | `uctx --version && uctx stats` |
| Update IDE config | `uctx setup <ide-name>` |
| Rebuild context index | `uctx index` |
| Check changelog | `git log --oneline main -10` (from repo) |
| Report bug | https://github.com/anilcelexsa/unified-context/issues |
