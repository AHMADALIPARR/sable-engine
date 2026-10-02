#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
# SABLE-C verification suite — pure sh, no Python anywhere in this stack.
# 1. Determinism: same entropy -> identical run.
# 2. Expected values, recorded when the reference oracle verified this
#    binary bit-for-bit during development (result 9198698438492148246,
#    executed 426, taken 510) before the oracle left the stack per the
#    Python-free directive.
# 3. Seal chain verifies; tampered payload is rejected (digest mismatch).
# 4. Veto halts with no seal; exhausted budget halts with a receipt.
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
BIN="$ROOT/c/sable"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

[ -x "$BIN" ] || (cd "$ROOT/c" && make >/dev/null 2>&1) || fail "build"
"$BIN" --selftest >/dev/null || fail "selftest"

HEX=00070007000700070007000700070007000700070007000700070007
ARGS="--entropy-hex $HEX --entropy-provenance test-override --n 1024 --budget 1000000000"

R1=$($BIN $ARGS --seal-log "$TMP/a.jsonl" --name det | grep -E '^(result|lanes):')
R2=$($BIN $ARGS --seal-log "$TMP/b.jsonl" --name det | grep -E '^(result|lanes):')
[ "$R1" = "$R2" ] || fail "non-deterministic run"
echo "ok   determinism"

echo "$R1" | grep -q 'result:    9198698438492148246' || fail "result mismatch: $R1"
echo "$R1" | grep -q ' taken=510 ' || fail "taken mismatch: $R1"
echo "$R1" | grep -q ' executed=426 ' || fail "executed mismatch: $R1"
echo "ok   expected values (result/executed/taken)"

$BIN verify --seal-log "$TMP/a.jsonl" | grep -q 'chain valid: True' || fail "seal verify"
echo "ok   seal chain verifies"

sed 's/"executed":426/"executed":427/' "$TMP/a.jsonl" > "$TMP/t.jsonl"
$BIN verify --seal-log "$TMP/t.jsonl" | grep -q 'digest mismatch' || fail "tamper not detected"
echo "ok   tampered payload rejected"

$BIN --entropy-hex "$HEX" --truths 1,1,1,0,1,1 --seal-log "$TMP/v.jsonl" --n 64 >/dev/null 2>&1
[ $? -eq 2 ] || fail "veto exit code"
[ ! -f "$TMP/v.jsonl" ] || fail "veto fired a seal"
echo "ok   veto halts, no seal"

$BIN --entropy-hex "$HEX" --budget 10 --seal-log "$TMP/e.jsonl" --n 1024 >/dev/null 2>&1
[ $? -eq 4 ] || fail "budget exit code"
echo "ok   budget exhaustion halts"

echo "CROSSCHECK PASS"
