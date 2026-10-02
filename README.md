# SABLE — Sparse APL-Branch Ledger Engine

*(working title — renameable)*

A quantum-seeded, energy-aware execution engine built from two machines
we already proved:

- the **SUBLEQ reduction core** from the reduction-algebra benchmark
  (Goldilocks field, branch-if-≤0, canonical checksum `1388262917130611548`)
- the **APL reduction engine** (`aplre`): its evaluator stack is the
  execution substrate, its sovereign-vector **resonances** are the gating
  policy, its WORM seal log is the receipt chain

## The idea

SUBLEQ's branch predicate is a natural sparsity gate: work happens only
on taken branches. SABLE makes that the execution model, adds a second
gate — the APL machine's resonance — and keeps an exact energy ledger:

```
ANU quantum entropy ──► lane visit order (quantum shuffle) + seal nonce
                              │
APL SovVec resonances ──► gate: lane i fires iff resonance(i mod 6) ≥ threshold
                              │
SUBLEQ core ──► per lane: d = x[i] − threshold; taken iff signed(d) ≤ 0
                              │
                    taken AND gated ──► execute body, charge E_EXEC
                    otherwise         ──► skip, charge the skip cost
                              │
Energy ledger ──► budget per orbital pass; exhausted → halt + receipt
                              │
WORM seal ──► completed passes sealed (aplre SHA-256 chain); veto/invalid
              passes execute nothing and no seal fires
```

**Orbital** is the deployment frame: a pass is a compute window with a
fixed energy budget — the way a spacecraft's eclipse pass is. Lanes run
highest-resonance-first inside the quantum shuffle, so a depleted budget
still did the work that mattered most.

**Resonance** is literal, not metaphor: lane *i* is assigned sovereign
component *(i mod 6)* — ⊙ 1.00, ▦ 0.90, ○ 0.80, ◇ 0.70, △ 0.85, ⬡ 0.75 —
and the gate opens iff that component's resonance meets the threshold.
The AND-fold veto is preserved: any component truth 0 → INVALID, the
pass halts before executing anything, and the seal is withheld.

## Honesty notes

- **Energy is modeled, not measured.** One unit = one SUBLEQ predicate
  evaluation by definition; E_EXEC=8, skips < 1. The ledger's arithmetic
  is exact; mapping units to joules needs silicon calibration, which is
  future work, not claimed here.
- **Entropy is provenance-tagged.** Every run records `quantum` (values
  fetched live from `qrng.anu.edu.au`) or `fallback-csprng` (local
  `secrets`, 2s timeout). A run never claims quantum entropy it didn't fetch.
- **Verify-before-record.** The SplitMix64 stream must reproduce the
  canonical checksum before any pass executes — the same gate as the
  benchmark, so both machines provably draw from the same source.
- **Wolfram Q integration is pending** — the component is not yet
  specified; nothing is fabricated in its place.

## Usage

```bash
cd ~/workspace/sable-engine
python3 -m sable.cli --workdir ./runs demo --n 1024 --budget 20000
python3 -m sable.cli --workdir ./runs verify
python3 -m tests.test_sable     # 15/15, stdlib only (no pytest on this host)
```

Example run (live ANU fetch):

```
pass:      eclipse-pass-01
status:    completed
gate:      VALID
checksum:  OK
entropy:   quantum  nonce=7450e69088c66b5c
lanes:     visited=1024 taken=510 executed=426 gated_skip=84 untaken=514
sparsity:  58.4% of lanes skipped work
result:    9198698438492148246
energy:    spent=4606.5 / budget=20000.0 (pred=1024.0 exec=3408.0 skip=170.5 seal=4.0)
seal:      1ea889b1…
```

## Layout

```
sable/
  field.py      Goldilocks arithmetic (vendored from the benchmark substrate)
  stream.py     SplitMix64 + canonical checksum gate
  subleq.py     sparse SUBLEQ core: taken/gated/executed lane events
  resonance.py  APL SovVec gating via aplre (the stack substrate lives there)
  energy.py     exact ledger over modeled costs + budget enforcement
  anu.py        ANU QRNG fetch w/ provenance + quantum shuffle + nonces
  seal.py       WORM sealing via aplre.seal
  engine.py     the orbital pass: gate → checksum → sparse run → seal
  cli.py        demo | verify
tests/
  test_sable.py stdlib-only suite, 15/15 green
```

## License

AGPL-3.0-or-later. Copyright (C) 2026 SnapKitty Collective. See LICENSE.
Every source file carries the SPDX header.
