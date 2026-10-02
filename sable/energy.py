# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""The energy ledger: exact accounting of a modeled cost.

Costs are MODEL parameters, stated here and not claimed as silicon
measurements. One unit is defined as the cost of evaluating one SUBLEQ
predicate (one field subtraction + sign test). Everything else is priced
relative to that:

    E_PRED       1.0    every lane pays: the subtraction must run
    E_EXEC       8.0    taken + gated lane: the reduction body runs
    E_GATED_SKIP 0.5    taken but resonance-gated: predicate + gate check
    E_UNTaken    0.25   untaken: predicate only, early out
    E_SEAL       4.0    firing the WORM seal

The ledger's arithmetic is exact; the model's mapping to joules is a
calibration exercise for real hardware, documented in the README and
not claimed here. An orbital pass sets an energy budget; the engine
halts (with a sealed receipt) when the budget is exhausted.
"""

from __future__ import annotations

from dataclasses import dataclass

E_PRED: float = 1.0
E_EXEC: float = 8.0
E_GATED_SKIP: float = 0.5
E_UNTaken: float = 0.25
E_SEAL: float = 4.0


class BudgetExhausted(Exception):
    """Raised when a pass would exceed its energy budget."""


@dataclass
class EnergyLedger:
    budget: float
    spent_pred: float = 0.0
    spent_exec: float = 0.0
    spent_skip: float = 0.0
    spent_seal: float = 0.0

    def _spend(self, amount: float) -> None:
        if self.spent_total + amount > self.budget:
            raise BudgetExhausted(
                f"budget {self.budget} exhausted "
                f"(spent {self.spent_total}, need {amount})"
            )

    @property
    def spent_total(self) -> float:
        return self.spent_pred + self.spent_exec + self.spent_skip + self.spent_seal

    @property
    def remaining(self) -> float:
        return self.budget - self.spent_total

    def charge_predicate(self) -> None:
        self._spend(E_PRED)
        self.spent_pred += E_PRED

    def charge_exec(self) -> None:
        self._spend(E_EXEC)
        self.spent_exec += E_EXEC

    def charge_skip(self, cost: float) -> None:
        self._spend(cost)
        self.spent_skip += cost

    def charge_seal(self) -> None:
        self._spend(E_SEAL)
        self.spent_seal += E_SEAL

    def summary(self) -> dict:
        return {
            "budget": self.budget,
            "spent_predicate": self.spent_pred,
            "spent_exec": self.spent_exec,
            "spent_skip": self.spent_skip,
            "spent_seal": self.spent_seal,
            "spent_total": self.spent_total,
            "remaining": self.remaining,
        }
