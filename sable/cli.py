# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""SABLE command line: demo | verify."""

from __future__ import annotations

import argparse
import sys

from . import seal as _seal
from .engine import PassConfig, SableEngine


def cmd_demo(args: argparse.Namespace) -> int:
    eng = SableEngine(workdir=args.workdir)
    cfg = PassConfig(
        name=args.name,
        n=args.n,
        resonance_threshold=args.resonance,
        energy_budget=args.budget,
        seal_log=args.seal_log,
    )
    r = eng.run_pass(cfg)
    print(f"pass:      {cfg.name}")
    print(f"status:    {r.status}")
    print(f"gate:      {'VALID' if r.gate_valid else 'INVALID (veto)'}")
    print(f"checksum:  {'OK' if r.checksum_ok else 'FAILED'}")
    print(f"entropy:   {r.anu_provenance}  nonce={r.anu_nonce}")
    print(f"lanes:     visited={r.lanes_visited} taken={r.pred_taken} "
          f"executed={r.executed} gated_skip={r.gated_skipped} untaken={r.untaken}")
    if r.executed:
        sparsity = 100.0 * (1 - r.executed / r.n)
        print(f"sparsity:  {sparsity:.1f}% of lanes skipped work")
    print(f"result:    {r.result}")
    e = r.energy
    if e:
        print(f"energy:    spent={e['spent_total']:.1f} / budget={e['budget']:.1f} "
              f"(pred={e['spent_predicate']:.1f} exec={e['spent_exec']:.1f} "
              f"skip={e['spent_skip']:.1f} seal={e['spent_seal']:.1f})")
    print(f"seal:      {r.seal}")
    return 0 if r.status == "completed" else 1


def cmd_verify(args: argparse.Namespace) -> int:
    from pathlib import Path
    ok, msg = _seal.verify_chain(Path(args.workdir) / args.seal_log)
    print(f"chain valid: {ok} — {msg}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sable", description="SABLE sparse orbital engine")
    ap.add_argument("--workdir", default=".", help="working directory for the seal log")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo", help="run one sparse orbital pass")
    d.add_argument("--name", default="eclipse-pass-01")
    d.add_argument("--n", type=int, default=1024)
    d.add_argument("--resonance", type=float, default=0.75)
    d.add_argument("--budget", type=float, default=20000.0)
    d.add_argument("--seal-log", default="seals.jsonl")
    d.set_defaults(fn=cmd_demo)

    v = sub.add_parser("verify", help="verify the WORM seal chain")
    v.add_argument("--seal-log", default="seals.jsonl")
    v.set_defaults(fn=cmd_verify)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
