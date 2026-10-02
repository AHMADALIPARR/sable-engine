# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""WORM sealing, via the APL machine's seal backend.

Completed passes are sealed with aplre's SHA-256 append-only log:
each entry links the previous digest, so the receipt chain is
tamper-evident. Verification recomputes every digest and link.
"""

from __future__ import annotations

from pathlib import Path

from . import _aplre

_aplre.ensure_aplre()

from aplre.seal import build_payload, fire_seal, verify_log  # noqa: E402


def seal_pass(
    receipt: dict,
    components: list[dict],
    omega_truth: bool,
    and_value: bool,
    resonance_total: float,
    log_path: Path | str,
) -> str:
    payload = build_payload(
        meta="sable-pass",
        components=components,
        omega_truth=omega_truth,
        and_value=and_value,
        resonance_total=resonance_total,
    )
    payload["sable_receipt"] = receipt
    return fire_seal(payload, log_path)


def verify_chain(log_path: Path | str) -> tuple[bool, str]:
    return verify_log(log_path)
