# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Goldilocks field arithmetic: p = 2**64 - 2**32 + 1.

Vendored from the reduction-algebra-bench substrate
(~/workspace/reduction-algebra-bench/substrate/), whose correctness suite
pins these identities. Vendored rather than imported so SABLE stays a
single self-contained package; the provenance is recorded here, not hidden.
"""

from __future__ import annotations

P: int = 2**64 - 2**32 + 1
MASK64: int = 2**64 - 1
HALF64: int = 2**63


def gf_add(a: int, b: int) -> int:
    """Carry-free addition mod P (verified against the Chapel oracle)."""
    s = a + b
    return s - P if s >= P else s


def gf_sub(a: int, b: int) -> int:
    """Subtraction mod P."""
    return a - b if a >= b else a - b + P


def gf_mul(a: int, b: int) -> int:
    """Multiplication mod P."""
    return (a * b) % P


def to_signed(x: int) -> int:
    """Interpret a 64-bit representative as signed (the SUBLEQ test domain)."""
    return x - 2**64 if x >= HALF64 else x
