#!/usr/bin/env bash
# End-to-end test for GCN reproduction.
#
# Prerequisites (set up by ops/demo track, not this script):
#   ~/.scideer/cache/pygcn/                — official pygcn repo cloned
#   ~/.scideer/cache/torch_geometric/Cora/ — Planetoid Cora downloaded
#   pdfplumber installed (for download_paper.py)
#   torch + torch_geometric installed (for the cached pygcn or Tier 3 skeleton)
#
# This script does NOT mount sandbox paths; it runs the 5 scripts as if the
# agent would, against /tmp, and verifies the contract.
#
# Usage:
#   bash test_e2e_gcn.sh                          # uses defaults
#   bash test_e2e_gcn.sh 1609.02907 "custom target"

set -euo pipefail

ARXIV_ID="${1:-1609.02907}"
TARGET="${2:-Table 2 GCN/Cora row, expected ~81.5%}"

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WS="/tmp/test-pr-$ARXIV_ID-$$"
OUT="/tmp/test-pr-out-$ARXIV_ID-$$"

trap "rm -rf $WS $OUT" EXIT

rm -rf "$WS" "$OUT"
mkdir -p "$WS" "$OUT"

echo "=== Step 1: download_paper.py ==="
python "$SKILL_DIR/scripts/download_paper.py" "$ARXIV_ID" --workspace "$WS"

echo "=== Step 2: extract_method.py ==="
python "$SKILL_DIR/scripts/extract_method.py" \
    --workspace "$WS" --target "$TARGET" --arxiv-id "$ARXIV_ID"

echo "=== Step 3: scale_down.py ==="
python "$SKILL_DIR/scripts/scale_down.py" --workspace "$WS"

echo "=== Step 4: run_experiment.py ==="
SCIDEER_CACHE_DIR="$HOME/.scideer/cache" \
    python "$SKILL_DIR/scripts/run_experiment.py" --workspace "$WS" --timeout 240

echo "=== Step 5: comparator.py ==="
python "$SKILL_DIR/scripts/comparator.py" --workspace "$WS" --output "$OUT"

echo "=== Verifying contract ==="
test -f "$OUT/report.md" || { echo "FAIL: report.md missing"; exit 1; }
test -f "$OUT/comparison.json" || { echo "FAIL: comparison.json missing"; exit 1; }

VERDICT="$(python -c "import json; print(json.load(open('$OUT/comparison.json'))['verdict'])")"
OUR_VAL="$(python -c "import json; print(json.load(open('$OUT/comparison.json'))['our_value'])")"

echo "verdict: $VERDICT"
echo "our_value: $OUR_VAL"

if [ "$VERDICT" = "within_tolerance" ]; then
    echo "PASS: E2E test passed (verdict=within_tolerance, our_value=$OUR_VAL)"
else
    echo "FAIL: E2E test failed (verdict=$VERDICT, our_value=$OUR_VAL)"
    echo "--- Top of report.md ---"
    head -50 "$OUT/report.md"
    exit 1
fi
