# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""SABLE test suite — stdlib only (no pytest on this host).

Run:  python3 -m tests.test_sable   (from the project root)
Every claim the engine makes, pinned. Any failure raises AssertionError.
"""

from __future__ import annotations

import random
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sable import anu, energy, field, stream  # noqa: E402
from sable import seal as _seal  # noqa: E402
from sable.engine import PassConfig, SableEngine  # noqa: E402
from sable.energy import BudgetExhausted, EnergyLedger  # noqa: E402
from sable.resonance import ResonanceGate  # noqa: E402
from sable.subleq import sparse_reduce  # noqa: E402

PASS = []


def check(name):
    def deco(fn):
        PASS.append((name, fn))
        return fn
    return deco


@check("field identities")
def t_field_identities():
    assert field.gf_add(field.P - 1, 1) == 0
    assert field.gf_add(0, 0) == 0
    assert field.gf_sub(0, 1) == field.P - 1
    assert field.gf_mul(2, field.P - 1) == field.P - 2
    assert field.to_signed(2**64 - 1) == -1
    assert field.to_signed(2**63 - 1) == 2**63 - 1


@check("field matches % P (200 random)")
def t_field_matches_mod():
    rng = random.Random(42)
    for _ in range(200):
        a, b = rng.randrange(field.P), rng.randrange(field.P)
        assert field.gf_add(a, b) == (a + b) % field.P
        assert field.gf_sub(a, b) == (a - b) % field.P
        assert field.gf_mul(a, b) == (a * b) % field.P


@check("canonical checksum gate")
def t_canonical_checksum():
    assert stream.verify_canonical()
    assert stream.stream_checksum() == 1388262917130611548


@check("sparse reduction is deterministic and genuinely sparse")
def t_sparse_deterministic():
    xs = stream.splitmix64_stream(stream.SEED, 256)
    l1, l2 = EnergyLedger(10**9), EnergyLedger(10**9)
    r1 = sparse_reduce(xs, field.P // 2, lambda i: True, l1)
    r2 = sparse_reduce(xs, field.P // 2, lambda i: True, l2)
    assert r1.total == r2.total
    assert r1.n_executed == r2.n_executed
    assert 0 < r1.n_executed < 256


@check("sparse matches dense when gate fully open")
def t_sparse_matches_dense():
    xs = stream.splitmix64_stream(stream.SEED, 128)
    ledger = EnergyLedger(10**9)
    r = sparse_reduce(xs, field.P // 2, lambda i: True, ledger)
    dense = 0
    for x in xs:
        if field.to_signed(field.gf_sub(x, field.P // 2)) <= 0:
            dense = field.gf_add(dense, x)
    assert r.total == dense


@check("energy accounting is exact")
def t_energy_accounting_exact():
    xs = stream.splitmix64_stream(stream.SEED, 64)
    ledger = EnergyLedger(10**9)
    r = sparse_reduce(xs, field.P // 2, lambda i: True, ledger)
    assert ledger.spent_pred == 64 * energy.E_PRED
    assert ledger.spent_exec == r.n_executed * energy.E_EXEC
    assert abs(ledger.spent_total - (
        64 * energy.E_PRED + r.n_executed * energy.E_EXEC
        + r.n_untaken * energy.E_UNTaken)) < 1e-9


@check("resonance threshold gates lanes")
def t_resonance_threshold():
    g = ResonanceGate(threshold=1.0)
    assert g.fires(0)       # ⊙ resonance 1.00
    assert not g.fires(1)   # ▦ resonance 0.90 < 1.0
    assert g.lane_glyph(6) == "⊙"


@check("resonance veto (AND-fold)")
def t_resonance_veto():
    g = ResonanceGate(truths=[1, 1, 1, 0, 1, 1])
    assert not g.valid


@check("open lanes sorted by resonance desc")
def t_open_lanes_sorted():
    g = ResonanceGate(threshold=0.0)
    lanes = g.open_lanes(12)
    res = [g.lane_resonance(i) for i in lanes]
    assert res == sorted(res, reverse=True)


@check("ANU fallback provenance (network blocked)")
def t_anu_fallback():
    real = urllib.request.urlopen

    def boom(*a, **k):
        raise OSError("no network")
    urllib.request.urlopen = boom
    try:
        vals, prov = anu.fetch_quantum(4)
    finally:
        urllib.request.urlopen = real
    assert prov == "fallback-csprng"
    assert len(vals) == 4 and all(0 <= v < 65536 for v in vals)


@check("quantum shuffle deterministic + permutation")
def t_quantum_shuffle():
    e = [1, 2, 3, 4, 5, 6, 7, 8]
    a = anu.quantum_shuffle([0, 1, 2, 3], e)
    b = anu.quantum_shuffle([0, 1, 2, 3], e)
    assert a == b and sorted(a) == [0, 1, 2, 3]


@check("pass completes, seals, chain verifies")
def t_pass_completes_and_seals():
    with tempfile.TemporaryDirectory() as td:
        eng = SableEngine(workdir=td)
        cfg = PassConfig(n=128, energy_budget=10**9,
                         entropy_override=[7] * 16, seal_log="s.jsonl")
        r = eng.run_pass(cfg)
        assert r.status == "completed", r.status
        assert r.checksum_ok and r.gate_valid
        assert r.seal is not None
        ok, _ = _seal.verify_chain(Path(td) / "s.jsonl")
        assert ok


@check("veto halts pass: no execution, no seal")
def t_pass_veto_halts():
    with tempfile.TemporaryDirectory() as td:
        eng = SableEngine(workdir=td)
        cfg = PassConfig(n=128, truths=[1, 1, 1, 0, 1, 1],
                         entropy_override=[7] * 16, seal_log="s.jsonl")
        r = eng.run_pass(cfg)
        assert r.status == "invalid-gate"
        assert r.executed == 0 and r.seal is None
        assert not (Path(td) / "s.jsonl").exists()


@check("budget exhaustion halts pass")
def t_pass_budget_exhaustion():
    with tempfile.TemporaryDirectory() as td:
        eng = SableEngine(workdir=td)
        cfg = PassConfig(n=1024, energy_budget=10.0,
                         entropy_override=[7] * 16, seal_log="s.jsonl")
        r = eng.run_pass(cfg)
        assert r.status == "budget-exhausted"
        assert r.seal is None


@check("ledger raises BudgetExhausted")
def t_budget_ledger_raises():
    l = EnergyLedger(budget=1.0)
    l.charge_predicate()
    try:
        l.charge_predicate()
    except BudgetExhausted:
        return
    raise AssertionError("expected BudgetExhausted")


def main() -> int:
    failed = 0
    for name, fn in PASS:
        try:
            fn()
        except Exception as e:
            failed += 1
            print(f"FAIL {name}: {e!r}")
        else:
            print(f"ok   {name}")
    print(f"\n{len(PASS) - failed}/{len(PASS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
