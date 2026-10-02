# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Locate the APL reduction engine (aplre) without touching system packages.

The engine lives at ~/workspace/apl-reduction-engine. If it is importable
already (pip-installed), use it. Otherwise prepend its directory to
sys.path. This keeps SABLE self-contained: no PEP 668 system modification.
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_aplre() -> None:
    try:
        import aplre  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    cand = Path.home() / "workspace" / "apl-reduction-engine"
    if (cand / "aplre" / "__init__.py").exists():
        sys.path.insert(0, str(cand))
        import aplre  # noqa: F401
        return
    raise ModuleNotFoundError(
        "aplre (the APL reduction engine) not found: expected at "
        f"{cand}. It is required as SABLE's stack substrate and seal backend."
    )
