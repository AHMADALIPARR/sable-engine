# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Quantum entropy, fetched from ANU.

Primary source: the ANU Quantum Random Number Generator
(https://qrng.anu.edu.au/API/jsonI.php?length=<n>&type=uint16),
vacuum-fluctuation quantum randomness served as JSON:
{"type":"uint16","length":4,"data":[...],"success":true}.

Every fetch is provenance-tagged: "quantum" when the values came from
ANU, "fallback-csprng" when the API was unreachable and the local
CSPRNG (secrets) stood in. The tag travels with the run receipt and
into the seal payload — a run never claims quantum entropy it did not
fetch. Timeout is short (2s): ANU is a gift, not a dependency.
"""

from __future__ import annotations

import json
import secrets
import urllib.request

ANU_URL = "https://qrng.anu.edu.au/API/jsonI.php"
TIMEOUT_S = 2.0
MAX_LEN = 1024


def fetch_quantum(n: int = 16, timeout: float = TIMEOUT_S) -> tuple[list[int], str]:
    """Fetch n uint16 values. Returns (values, provenance)."""
    if not 1 <= n <= MAX_LEN:
        raise ValueError(f"n must be 1..{MAX_LEN}, got {n}")
    try:
        url = f"{ANU_URL}?length={n}&type=uint16"
        req = urllib.request.Request(url, headers={"User-Agent": "SABLE/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if not body.get("success") or body.get("type") != "uint16":
            raise ValueError(f"ANU error response: {body!r}")
        data = [int(v) & 0xFFFF for v in body["data"]]
        if len(data) != n:
            raise ValueError(f"ANU returned {len(data)} values, asked {n}")
        return data, "quantum"
    except Exception:
        return [secrets.randbelow(65536) for _ in range(n)], "fallback-csprng"


def quantum_shuffle(order: list[int], entropy: list[int]) -> list[int]:
    """Fisher-Yates shuffle of `order`, driven by quantum uint16 values.

    Deterministic given the entropy: the same ANU draw shuffles the
    same way. This is the sparse sampler — the lane visit order of a
    pass is quantum-driven, not PRNG-driven.
    """
    order = list(order)
    e = 0
    for i in range(len(order) - 1, 0, -1):
        j = entropy[e % len(entropy)] % (i + 1)
        e += 1
        order[i], order[j] = order[j], order[i]
    return order


def derive_nonce(entropy: list[int]) -> str:
    """A 64-bit hex nonce from four uint16 draws, for seal payloads."""
    v = 0
    for x in entropy[:4]:
        v = ((v << 16) | (x & 0xFFFF)) & 0xFFFFFFFFFFFFFFFF
    return f"{v:016x}"
