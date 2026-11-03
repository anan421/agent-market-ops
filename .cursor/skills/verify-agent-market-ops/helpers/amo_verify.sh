#!/usr/bin/env bash
# Verification helper for agent-market-ops CLI demos.
# Usage:
#   amo_verify.sh doctor
#   RUN_ID=... amo_verify.sh drive <feature-id>
#   RUN_ID=... amo_verify.sh cleanup
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  . .venv/bin/activate
fi

EVID_ROOT="/workspace/verify-evidence/agent-market-ops"
SCRATCH_ROOT="/tmp/amo-verify-${RUN_ID:-unset}"

die() { echo "ERROR: $*" >&2; exit 1; }

cmd_doctor() {
  python -c "import pipeline.brief_check_demo, pipeline.fees, pipeline.reconcile_demo, pipeline.fetch_prices_demo, markets" \
    || die "imports failed — run: pip install -e '.[dev]'"
  out="$(python -m pipeline.brief_check_demo examples/brief.md)" || die "examples/brief.md lint failed"
  [[ "$out" == "OK" ]] || die "expected OK, got: $out"
  python -m pipeline.brief_check_demo --help >/dev/null
  echo "DOCTOR_OK root=$ROOT"
}

ensure_run() {
  [[ -n "${RUN_ID:-}" ]] || die "set RUN_ID (e.g. export RUN_ID=\$(date +%Y%m%d-%H%M%S))"
  mkdir -p "$SCRATCH_ROOT" "$EVID_ROOT/$RUN_ID"
}

stamp_meta() {
  local feature="$1" entry="$2" dest="$3"
  {
    echo "feature_id=$feature"
    echo "entry_point=$entry"
    echo "run_id=$RUN_ID"
    echo "repo_root=$ROOT"
    echo "time_asia_shanghai=$(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S %Z')"
  } >"$dest/META.txt"
}

drive_brief_lint() {
  local dest="$EVID_ROOT/$RUN_ID/brief-lint"
  mkdir -p "$dest"
  stamp_meta brief-lint "python -m pipeline.brief_check_demo" "$dest"
  {
    echo "== OK cash =="
    set +e
    python -m pipeline.brief_check_demo examples/brief.md >"$dest/ok.stdout" 2>"$dest/ok.stderr"
    echo "exit=$?" | tee "$dest/ok.exit"
    set -e
    cat "$dest/ok.stdout"
    [[ "$(cat "$dest/ok.exit")" == "exit=0" ]] || die "ok cash expected exit 0"
    [[ "$(cat "$dest/ok.stdout")" == "OK" ]] || die "ok cash expected OK"

    cat >"$SCRATCH_ROOT/bad_picks.md" <<'MD'
```action
动作: 今天不做
```

```picks
DEMO01 | 关注 | note
```
MD
    echo "== reject picks =="
    set +e
    python -m pipeline.brief_check_demo "$SCRATCH_ROOT/bad_picks.md" >"$dest/bad.stdout" 2>"$dest/bad.stderr"
    echo "exit=$?" | tee "$dest/bad.exit"
    set -e
    cat "$dest/bad.stderr"
    [[ "$(cat "$dest/bad.exit")" == "exit=1" ]] || die "bad picks expected exit 1"
    grep -q "今天不做" "$dest/bad.stderr" || die "stderr missing 今天不做"

    echo "# no action here" >"$SCRATCH_ROOT/missing.md"
    echo "== missing action =="
    set +e
    python -m pipeline.brief_check_demo "$SCRATCH_ROOT/missing.md" >"$dest/missing.stdout" 2>"$dest/missing.stderr"
    echo "exit=$?" | tee "$dest/missing.exit"
    set -e
    [[ "$(cat "$dest/missing.exit")" == "exit=1" ]] || die "missing action expected exit 1"

    echo "BRIEF_LINT_PROOF_OK" | tee "$dest/RESULT.txt"
  } | tee "$dest/transcript.txt"
}

drive_fetch_prices() {
  local dest="$EVID_ROOT/$RUN_ID/fetch-prices"
  mkdir -p "$dest"
  stamp_meta fetch-prices "python -m pipeline.fetch_prices_demo" "$dest"
  python -m pipeline.fetch_prices_demo --symbol DEMO01 --days 5 --start 2026-10-14 \
    -o "$SCRATCH_ROOT/prices.json"
  python -m pipeline.fetch_prices_demo --symbol DEMO01 --days 5 --start 2026-10-14 \
    --format csv -o "$SCRATCH_ROOT/prices.csv"
  cp "$SCRATCH_ROOT/prices.json" "$SCRATCH_ROOT/prices.csv" "$dest/"
  python - <<'PY' "$dest/prices.json"
import json, sys
rows = json.load(open(sys.argv[1]))
assert len(rows) == 5 and all(r.get("synthetic") is True for r in rows)
print("json_ok", len(rows))
PY
  head -1 "$dest/prices.csv" | grep -q "date,symbol,open,high,low,close,volume,synthetic"
  echo "FETCH_PRICES_PROOF_OK" | tee "$dest/RESULT.txt"
}

drive_reconcile_html() {
  local dest="$EVID_ROOT/$RUN_ID/reconcile-html"
  mkdir -p "$dest"
  stamp_meta reconcile-html "python -m pipeline.reconcile_demo" "$dest"
  python -m pipeline.reconcile_demo --date 2026-10-21 -o "$SCRATCH_ROOT/reconcile.html"
  cp "$SCRATCH_ROOT/reconcile.html" "$dest/"
  grep -q "Paper reconcile 2026-10-21" "$dest/reconcile.html"
  grep -q "今天不做" "$dest/reconcile.html"
  grep -q "Demo data only. Not investment advice" "$dest/reconcile.html"
  echo "RECONCILE_HTML_PROOF_OK" | tee "$dest/RESULT.txt"
}

drive_fees() {
  local dest="$EVID_ROOT/$RUN_ID/fees"
  mkdir -p "$dest"
  stamp_meta fees "python -c pipeline.fees" "$dest"
  python - <<'PY' | tee "$dest/fees_out.txt"
from pipeline.fees import fee_breakdown, round_trip_cost_pct
b = fee_breakdown(100_000, "buy")
s = fee_breakdown(100_000, "sell")
assert b["stamp_duty"] == 0.0
assert s["stamp_duty"] > 0
assert abs(b["total"] - sum(v for k, v in b.items() if k != "total")) < 1e-9
pct = round_trip_cost_pct()
assert 0.0025 < pct < 0.0035
print("buy", b)
print("sell", s)
print("round_trip", pct)
print("FEES_PROOF_OK")
PY
  cp "$dest/fees_out.txt" "$dest/RESULT.txt"
}

drive_schema_validate() {
  local dest="$EVID_ROOT/$RUN_ID/schema-validate"
  mkdir -p "$dest"
  stamp_meta schema-validate "python scripts/validate_demo.py" "$dest"
  set +e
  python scripts/validate_demo.py >"$dest/transcript.txt" 2>&1
  ec=$?
  set -e
  echo "exit=$ec" | tee "$dest/exit.txt"
  [[ $ec -eq 0 ]] || die "validate_demo failed"
  grep -q "^OK$" "$dest/transcript.txt" || die "expected OK"
  echo "SCHEMA_VALIDATE_PROOF_OK" | tee "$dest/RESULT.txt"
}

cmd_drive() {
  local feature="${1:-}"
  [[ -n "$feature" ]] || die "drive needs feature-id"
  ensure_run
  case "$feature" in
    brief-lint) drive_brief_lint ;;
    fetch-prices) drive_fetch_prices ;;
    reconcile-html) drive_reconcile_html ;;
    fees) drive_fees ;;
    schema-validate) drive_schema_validate ;;
    *) die "unknown feature: $feature (see features/README.md)" ;;
  esac
}

cmd_cleanup() {
  ensure_run
  if [[ -d "$SCRATCH_ROOT" ]]; then
    rm -rf "$SCRATCH_ROOT"
    echo "removed $SCRATCH_ROOT"
  else
    echo "no scratch at $SCRATCH_ROOT"
  fi
  echo "evidence kept at $EVID_ROOT/$RUN_ID"
}

case "${1:-}" in
  doctor) cmd_doctor ;;
  drive) shift; cmd_drive "$@" ;;
  cleanup) cmd_cleanup ;;
  *) echo "usage: $0 doctor|drive <feature>|cleanup" >&2; exit 2 ;;
esac
