# v3.8.1 — Windows/Hermes/GBrain v0.42 Compatibility

## Fixes

### Windows Compatibility
- **Python interpreter resolver** — `python3` → `python` → `py -3` fallback chain across all scripts
- **Windows Hermes home** — auto-detects `~/AppData/Local/hermes` when `~/.hermes` doesn't exist
- **MSYS path normalization** — `cygpath -w` converts Git Bash paths for native Python
- **Symlink fallback** — `os.symlink()` → `shutil.copytree` when Windows lacks Developer Mode

### Profile Generation (`generate-profile.py`)
- **Model inheritance** — profiles now inherit the active default model + provider instead of hardcoded broken `deepseek-v4-flash/custom`
- **GBrain MCP** — uses `gbrain serve` (not deprecated `mcp` command), resolves executable path including Windows Bun installs
- **`.env` merge** — `--force` no longer destroys existing platform credentials
- **`--force` actually works** — now overwrites config.yaml and SOUL.md as intended
- **Project-manager type** — added Gorobei profile with `projects` gbrain source

### GBrain Init (`init-gbrain.sh`)
- **v0.42 compatibility** — uses committed `README.md` instead of empty git commit (no longer accepted)
- **JSON source detection** — `sources list --json` instead of fragile `grep`
- **Federation persistence** — `sources federate shared` + `sources unfederate default` survive session restarts

### Cron Wiring (`wire-crons.py`)
- **Profile-scoped** — all cron jobs use `hermes -p <profile> cron create` to prevent cross-profile contamination
- **Non-zero exit** — surface real failures instead of silent `warn()`
- **Path resolution** — `~/.hermes` in cron prompts resolves to the correct Windows AppData path

### Verification (`verify-install.sh`)
- **Fixed fatal errors** — undefined `info()`, top-level `local`, stray `target` command
- **Nested skill support** — `check_skill` accepts 2nd arg for skills under `crm/` subdirectory
- **Script syntax validation** — uses resolved Python interpreter on Windows paths
- **GBrain MCP test** — tests connectivity via `hermes -p <profile> mcp test`

### Installer (`install.sh`)
- **Proper profile existence check** — `hermes profile show` instead of swallowing errors
- **Deploy status tracking** — accurate pass/fail counts instead of blanket "All profiles deployed"

## Tests
- 15 new tests covering Windows profile generation, gbrain federation, and profile-scoped cron wiring
- All passing: `python -m unittest discover -s tests -v`

## Full Changelog
https://github.com/limcheehow/shogun-os/compare/v3.8.0...v3.8.1