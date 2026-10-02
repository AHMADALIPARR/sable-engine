# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""The sparse SUBLEQ core.

One instruction:  d = mem[a] - mem[b] (in the Goldilocks field);
branch taken iff signed(d) <= 0. On a taken branch mem[b] = d and the
reduction body executes. On an untaken branch nothing executes — that
skip is the entire point. Sparsity is not an optimization here; it is
the execution model.

Every lane pays the predicate cost (the subtraction must be evaluated
to know whether the branch takes). Only taken-and-gated lanes pay the
body cost. The energy ledger records both, exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field as _field

from . import energy as _energy  # noqa: F401  (re-exported for convenience)
from .energy import E_EXEC, E_GATED_SKIP, E_PRED, E_UNTaken, EnergyLedger
from .field import P, gf_add, gf_sub, to_signed


@dataclass
class LaneEvent:
    index: int
    taken: bool      # SUBLEQ predicate: signed(a - b) <= 0
    gated: bool      # resonance gate open for this lane
    executed: bool   # taken and gated: the body ran


@dataclass
class SparseResult:
    total: int                 # the sparse reduction result (field element)
    events: list[LaneEvent] = _field(default_factory=list)

    @property
    def n_taken(self) -> int:
        return sum(1 for e in self.events if e.taken)

    @property
    def n_executed(self) -> int:
        return sum(1 for e in self.events if e.executed)

    @property
    def n_gated_skip(self) -> int:
        return sum(1 for e in self.events if e.taken and not e.gated)

    @property
    def n_untaken(self) -> int:
        return sum(1 for e in self.events if not e.taken)


def sparse_reduce(
    xs: list[int],
    threshold: int,
    gate_fn,          # gate_fn(lane_index) -> bool  (resonance gate)
    ledger: EnergyLedger,
    order: list[int] | None = None,
) -> SparseResult:
    """SUBLEQ-gated sparse reduction over xs.

    For each lane i (in `order`, default 0..n-1):
      d = xs[i] - threshold   (field subtraction; the SUBLEQ core)
      taken  = signed(d) <= 0
      gated  = gate_fn(i)
      if taken and gated: total = total + xs[i]; charge E_EXEC
      else: charge the skip cost
    The predicate cost E_PRED is charged for every lane: you cannot
    know the branch outcome without evaluating the subtraction.
    """
    idx = order if order is not None else list(range(len(xs)))
    total = 0
    events: list[LaneEvent] = []
    for i in idx:
        ledger.charge_predicate()
        d = gf_sub(xs[i], threshold)
        taken = to_signed(d) <= 0
        if not taken:
            ledger.charge_skip(E_UNTaken)
            events.append(LaneEvent(i, taken=False, gated=False, executed=False))
            continue
        gated = bool(gate_fn(i))
        if gated:
            total = gf_add(total, xs[i])
            ledger.charge_exec()
            events.append(LaneEvent(i, taken=True, gated=True, executed=True))
        else:
            ledger.charge_skip(E_GATED_SKIP)
            events.append(LaneEvent(i, taken=True, gated=False, executed=False))
    _ = P  # the field prime governs every op above; kept explicit
    return SparseResult(total=total, events=events)
