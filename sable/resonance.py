# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Resonance gating, driven by the APL machine.

The APL reduction engine's sovereign vector (SovVec) carries six
components, each with a truth value and a resonance weight:

    ⊙ origin    1.00      ▦ ledger  0.90      ○ oracle  0.80
    ◇ policy    0.70      △ consensus 0.85    ⬡ mesh    0.75

Lane i of the sparse reduction is assigned component (i mod 6). The
resonance gate opens for lane i iff that component's resonance meets
the threshold. Resonance is therefore the execution policy: the APL
machine we built decides what the SUBLEQ core is allowed to run.

The AND-fold veto is preserved: if any component's truth is 0, the
vector is INVALID and the engine must not execute at all.
"""

from __future__ import annotations

from . import _aplre

_aplre.ensure_aplre()

from aplre.components import DEFAULT_RESONANCE, SOVEREIGN_ORDER, compose, make_components  # noqa: E402


class ResonanceGate:
    def __init__(
        self,
        truths: list[int] | None = None,
        resonances: dict[str, float] | None = None,
        threshold: float = 0.75,
    ) -> None:
        self.components = make_components(truths, resonances)
        self.vec = compose(self.components)
        self.threshold = threshold

    @property
    def valid(self) -> bool:
        """The ∧-fold: True iff every component's truth is 1."""
        return self.vec.truth

    @property
    def total_resonance(self) -> float:
        """The +/⊗ sum-fold: total resonance of the sovereign vector."""
        return sum(self.vec.resonances)

    def lane_glyph(self, i: int) -> str:
        return SOVEREIGN_ORDER[i % 6][0]

    def lane_resonance(self, i: int) -> float:
        return self.vec.members[i % 6].resonance

    def fires(self, i: int) -> bool:
        """The gate: open iff the lane's component resonates at threshold."""
        return self.lane_resonance(i) >= self.threshold

    def open_lanes(self, n: int) -> list[int]:
        """Lane indices whose gates are open, highest resonance first.

        Energy-aware scheduling: when the budget runs out mid-pass, the
        work that mattered most already ran.
        """
        lanes = [i for i in range(n) if self.fires(i)]
        lanes.sort(key=self.lane_resonance, reverse=True)
        return lanes

    def component_table(self) -> list[dict]:
        return [
            {
                "glyph": c.glyph,
                "name": c.name,
                "truth": c.truth,
                "resonance": c.resonance,
                "gate_open": c.resonance >= self.threshold,
            }
            for c in self.vec.members
        ]


def default_resonance() -> dict[str, float]:
    return dict(DEFAULT_RESONANCE)
