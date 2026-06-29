#!/usr/bin/env bash
# =============================================================================
#  PyAutoFlow — Shell Script Wrapper
#  Convenience script for running common pipeline workflows from Bash/Zsh.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }

# ── Sanity check ──────────────────────────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
    echo "Python interpreter not found. Set the PYTHON env variable." >&2
    exit 1
fi

# ── Usage ─────────────────────────────────────────────────────────────────────
usage() {
cat <<EOF
PyAutoFlow Shell Wrapper

Usage: ./run.sh <command> [options]

Commands:
  csv       Process the sample CSV file
  json      Process the sample JSON file
  api       Fetch live data from the demo REST API
  test      Run all unit tests with pytest
  full      Full demo: CSV + group aggregation + all report formats
  help      Show this message

Environment:
  PYTHON              Python interpreter (default: python3)
  PYAUTOFLOW_API_KEY  Optional Bearer token for API auth
EOF
}

# ── Commands ──────────────────────────────────────────────────────────────────
cmd_csv() {
    info "Running CSV pipeline…"
    "$PYTHON" -m pyautoflow.cli \
        --input data/sample_input.csv \
        --group-by region category \
        --agg revenue:sum units:mean \
        --outlier-col revenue \
        --formats csv json txt
    success "CSV pipeline complete. Reports in output/"
}

cmd_json() {
    info "Running JSON pipeline…"
    "$PYTHON" -m pyautoflow.cli \
        --input data/sample_input.json \
        --group-by region \
        --agg revenue:sum units:sum \
        --formats csv json txt
    success "JSON pipeline complete. Reports in output/"
}

cmd_api() {
    info "Fetching live data from API…"
    "$PYTHON" -m pyautoflow.cli \
        --source api \
        --api-endpoint posts \
        --api-limit 50 \
        --formats csv txt
    success "API pipeline complete. Reports in output/"
}

cmd_test() {
    info "Running test suite…"
    "$PYTHON" -m pytest tests/ -v --tb=short --cov=pyautoflow --cov-report=term-missing
    success "All tests passed."
}

cmd_full() {
    info "Running full demo pipeline…"
    "$PYTHON" -m pyautoflow.cli \
        --input data/sample_input.csv \
        --filter "units > 5" "revenue > 0" \
        --derive "profit=revenue - cost" "margin_pct=profit / revenue * 100" \
        --group-by region category \
        --agg revenue:sum cost:sum units:mean \
        --rolling-col revenue \
        --rolling-window 5 \
        --outlier-col revenue \
        --outlier-multiplier 1.5 \
        --formats csv json txt \
        --label demo_run
    success "Full demo complete. Reports in output/"
}

# ── Dispatcher ────────────────────────────────────────────────────────────────
COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    csv)  cmd_csv  "$@" ;;
    json) cmd_json "$@" ;;
    api)  cmd_api  "$@" ;;
    test) cmd_test "$@" ;;
    full) cmd_full "$@" ;;
    help|--help|-h) usage ;;
    *) warn "Unknown command: '$COMMAND'"; usage; exit 1 ;;
esac
