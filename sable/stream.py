# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""SplitMix64 with counter-increment state threading — the canonical stream.

seed = 0x00BEEFCAFE, n = 1024  ==>  sum(stream) mod P = 1388262917130611548

This is the verify-before-record gate: no SABLE pass executes until the
stream reproduces the canonical checksum. Same construction as the
reduction-algebra-bench substrate; the checksum is the cross-project
proof that both machines draw from the same source.
"""

from __future__ import annotations

from .field import MASK64, P

SEED: int = 0x00BEEFCAFE
CANONICAL_N: int = 1024
CANONICAL_CHECKSUM: int = 1388262917130611548

_GAMMA: int = 0x9E3779B97F4A7C15
_M1: int = 0xBF58476D1CE4E5B9
_M2: int = 0x94D049BB133111EB


def splitmix64_stream(seed: int, n: int) -> list[int]:
    """Draw n 64-bit values. State increments BEFORE mixing (the k+1 rule)."""
    state = seed & MASK64
    out: list[int] = []
    for _ in range(n):
        state = (state + _GAMMA) & MASK64
        z = state
        z = ((z ^ (z >> 30)) * _M1) & MASK64
        z = ((z ^ (z >> 27)) * _M2) & MASK64
        out.append(z ^ (z >> 31))
    return out


def stream_checksum(seed: int = SEED, n: int = CANONICAL_N) -> int:
    """Sum of the stream mod the Goldilocks prime."""
    return sum(splitmix64_stream(seed, n)) % P


def verify_canonical() -> bool:
    """The gate: True iff the stream reproduces the canonical checksum."""
    return stream_checksum() == CANONICAL_CHECKSUM
