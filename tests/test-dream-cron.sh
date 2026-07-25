#!/usr/bin/env bash
# test-dream-cron.sh — Verify gbrain dream cycle cron script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPT="$REPO_DIR/scripts/gbrain-dream-cron.sh"

pass=0
fail=0

pass_one() {
  echo "  ✅ $1"
  pass=$((pass + 1))
}

fail_one() {
  echo "  ❌ $1"
  fail=$((fail + 1))
}

check_file() {
  local label="$1"
  shift
  if test "$@"; then
    pass_one "$label"
  else
    fail_one "$label"
  fi
}

echo "═══════════════════════════════════════════════════════════════"
echo "Test: gbrain-dream-cron.sh"
echo "═══════════════════════════════════════════════════════════════"

# Read script content once
SCRIPT_CONTENT=$(cat "$SCRIPT")

# 1) Script exists
check_file "Script file exists" -f "$SCRIPT"

# 2) Script is executable
check_file "Script is executable" -x "$SCRIPT"

# 3) Script has proper shebang
shebang=$(head -1 "$SCRIPT")
if [ "$shebang" = "#!/usr/bin/env bash" ]; then
  pass_one "Script has proper shebang"
else
  fail_one "Script has proper shebang (got: $shebang)"
fi

# 4) Script references all 3 phases
if grep -q 'consolidate' <<<"$SCRIPT_CONTENT"; then pass_one "References 'consolidate' phase"; else fail_one "References 'consolidate' phase"; fi
if grep -q 'synthesize'  <<<"$SCRIPT_CONTENT"; then pass_one "References 'synthesize' phase";   else fail_one "References 'synthesize' phase"; fi
if grep -q 'patterns'    <<<"$SCRIPT_CONTENT"; then pass_one "References 'patterns' phase";     else fail_one "References 'patterns' phase"; fi

# 5) Script creates log directory if missing
if grep -q 'mkdir -p' <<<"$SCRIPT_CONTENT"; then
  pass_one "Creates log directory (~/.gbrain/logs)"
else
  fail_one "Creates log directory (~/.gbrain/logs)"
fi

# 6) Script uses set -euo pipefail
if grep -q 'set -euo pipefail' <<<"$SCRIPT_CONTENT"; then
  pass_one "Uses set -euo pipefail"
else
  fail_one "Uses set -euo pipefail"
fi

# 7) Script does NOT exit on individual phase failure
if grep -qE '(exit code|return 1)' <<<"$SCRIPT_CONTENT"; then
  pass_one "Handles phase failure gracefully"
else
  fail_one "Handles phase failure gracefully"
fi

# 8) Script has timestamped logging
if grep -q 'date +%Y%m%d' <<<"$SCRIPT_CONTENT"; then
  pass_one "Uses date in log filename"
else
  fail_one "Uses date in log filename"
fi

# 9) Syntax check with bash -n (execution-level verification)
echo ""
echo "--- Execution-level verification ---"
if bash -n "$SCRIPT" 2>/dev/null; then
  pass_one "bash -n syntax check passed"
else
  fail_one "bash -n syntax check FAILED"
fi

# 10) Script has || true or equivalent failure continuation (C1 bug prevention)
echo ""
echo "--- Failure continuation verification ---"
if grep -qF '|| true' <<<"$SCRIPT_CONTENT"; then
  pass_one "Script uses '|| true' continuation for failure resilience"
elif grep -qF '|| :' <<<"$SCRIPT_CONTENT"; then
  pass_one "Script uses '|| :' continuation for failure resilience"
elif grep -qE '\|\| *[A-Z_]+=' <<<"$SCRIPT_CONTENT"; then
  pass_one "Script uses '|| VAR=' pattern to track failures without exiting"
elif grep -qE '(set \+e|set -e.*set \+e|trap.*EXIT)' <<<"$SCRIPT_CONTENT"; then
  pass_one "Script handles failure via explicit error management"
else
  fail_one "Script lacks failure continuation (|| true, || :, || VAR=, or set +e)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Results: $pass passed, $fail failed"
echo "═══════════════════════════════════════════════════════════════"

if [ "$fail" -gt 0 ]; then
  exit 1
fi