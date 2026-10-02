# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""SABLE — the sparse orbital pass.

One pass:
  1. Fetch quantum entropy from ANU (provenance-tagged; CSPRNG fallback).
  2. Compose the APL sovereign vector; AND-fold the gate.
     INVALID (any truth 0) -> halt, no execution, seal withheld.
  3. Verify-before-record: the SplitMix64 stream must reproduce the
     canonical checksum, or the pass refuses to run.
  4. Sparse SUBLEQ reduction over n lanes, resonance-gated, in
     quantum-shuffled lane order, highest-resonance-first, against
     the energy budget. Budget exhausted -> halt with a receipt.
  5. Fire the WORM seal on a completed pass.

"Orbital" is the deployment frame: a pass is a compute window with a
fixed energy budget, the way a spacecraft's eclipse pass is. The
engine does the most resonant work first, so a depleted budget still
did the work that mattered.
"""

from __future__ import annotations

from dataclasses import dataclass, field as _field
from pathlib import Path

from . import anu, seal as _seal
from .energy import BudgetExhausted, EnergyLedger
from .field import P
from .resonance import ResonanceGate
from .stream import SEED, verify_canonical, splitmix64_stream
from .subleq import sparse_reduce


@dataclass
class PassConfig:
    name: str = "eclipse-pass-01"
    n: int = 1024
    threshold: int = P // 2          # SUBLEQ comparison point (~half take)
    resonance_threshold: float = 0.75
    energy_budget: float = 20000.0
    truths: list[int] | None = None  # six 0/1; any 0 vetoes the pass
    resonances: dict[str, float] | None = None
    anu_words: int = 16
    seal_log: str = "seals.jsonl"
    entropy_override: list[int] | None = None  # tests: deterministic entropy


@dataclass
class RunReceipt:
    status: str                      # completed | budget-exhausted | invalid-gate | checksum-failed
    n: int
    lanes_visited: int
    pred_taken: int
    executed: int
    gated_skipped: int
    untaken: int
    result: int | None
    energy: dict = _field(default_factory=dict)
    checksum_ok: bool = False
    anu_provenance: str = "unknown"
    anu_nonce: str = ""
    seal: str | None = None
    gate_valid: bool = False
    resonance_total: float = 0.0


class SableEngine:
    def __init__(self, workdir: str | Path = ".") -> None:
        self.workdir = Path(workdir)

    def run_pass(self, cfg: PassConfig) -> RunReceipt:
        # 1. Quantum entropy (provenance-tagged).
        if cfg.entropy_override is not None:
            entropy, provenance = list(cfg.entropy_override), "test-override"
        else:
            entropy, provenance = anu.fetch_quantum(cfg.anu_words)
        nonce = anu.derive_nonce(entropy)

        # 2. The APL gate: compose, AND-fold, veto check.
        gate = ResonanceGate(
            truths=cfg.truths,
            resonances=cfg.resonances,
            threshold=cfg.resonance_threshold,
        )
        receipt = RunReceipt(
            status="started",
            n=cfg.n,
            lanes_visited=0,
            pred_taken=0,
            executed=0,
            gated_skipped=0,
            untaken=0,
            result=None,
            anu_provenance=provenance,
            anu_nonce=nonce,
            gate_valid=gate.valid,
            resonance_total=gate.total_resonance,
        )
        if not gate.valid:
            receipt.status = "invalid-gate"   # seal withheld, nothing executed
            return receipt

        # 3. Verify-before-record.
        receipt.checksum_ok = verify_canonical()
        if not receipt.checksum_ok:
            receipt.status = "checksum-failed"
            return receipt

        # 4. The sparse pass.
        ledger = EnergyLedger(budget=cfg.energy_budget)
        xs = splitmix64_stream(SEED, cfg.n)
        lane_order = list(range(cfg.n))
        lane_order = anu.quantum_shuffle(lane_order, entropy)
        # Highest-resonance-first within the quantum order: stable sort by
        # descending resonance keeps the quantum permutation inside each
        # resonance class.
        lane_order.sort(key=gate.lane_resonance, reverse=True)
        try:
            sres = sparse_reduce(xs, cfg.threshold, gate.fires, ledger, order=lane_order)
        except BudgetExhausted:
            receipt.status = "budget-exhausted"
            receipt.energy = ledger.summary()
            return receipt

        receipt.status = "completed"
        receipt.lanes_visited = len(sres.events)
        receipt.pred_taken = sres.n_taken
        receipt.executed = sres.n_executed
        receipt.gated_skipped = sres.n_gated_skip
        receipt.untaken = sres.n_untaken
        receipt.result = sres.total
        receipt.energy = ledger.summary()

        # 5. Seal the completed pass.
        ledger.charge_seal()
        receipt.energy = ledger.summary()
        seal_payload_receipt = {
            "pass": cfg.name,
            "status": receipt.status,
            "n": receipt.n,
            "executed": receipt.executed,
            "pred_taken": receipt.pred_taken,
            "result": receipt.result,
            "energy": receipt.energy,
            "anu_provenance": provenance,
            "anu_nonce": nonce,
        }
        receipt.seal = _seal.seal_pass(
            seal_payload_receipt,
            gate.component_table(),
            omega_truth=gate.valid,
            and_value=gate.valid,
            resonance_total=gate.total_resonance,
            log_path=self.workdir / cfg.seal_log,
        )
        return receipt
