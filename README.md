# SABLE — Sparse APL-Branch Ledger Engine

*(working title — renameable)*

A quantum-seeded, energy-aware execution engine in **C** — no Python
anywhere in this stack, by explicit directive. The hot path is
`-O3` C11; the only runtime needs are a C library and `curl`.

It is built from three machines we already proved:

- the **SUBLEQ reduction core** from the reduction-algebra benchmark
  (Goldilocks field `p = 2⁶⁴−2³²+1`, branch-if-≤0, canonical checksum
  `1388262917130611548`)
- the **APL reduction engine**: its sovereign-vector **resonances** are
  the gating policy and its WORM seal log is the receipt format
  (vendored as data + reimplemented byte-compatibly, not imported)
- **Wolfram's Quantum Framework**: the lane sampler expressed as a
  real WL program (`quantum/sparse_sampler.wl`) — written, not executed
  here (no Wolfram Engine on this host)

## The idea

SUBLEQ's branch predicate is a natural sparsity gate: work happens only
on taken branches. SABLE makes that the execution model, adds a second
gate — the APL machine's resonance — and keeps an exact energy ledger:

```
ANU quantum entropy ──► lane visit order (quantum shuffle) + seal nonce
                              │
APL resonances ──► gate: lane i fires iff resonance(i mod 6) ≥ threshold
│  ⊙ 1.00  ▦ 0.90  ○ 0.80  ◇ 0.70  △ 0.85  ⬡ 0.75 (vendored, documented)
                              │
SUBLEQ core ──► per lane: d = x[i] − threshold; taken iff signed(d) ≤ 0
                              │
                    taken AND gated ──► execute body, charge E_EXEC
                    otherwise         ──► skip, charge the skip cost
                              │
Energy ledger ──► budget per orbital pass; exhausted → halt + receipt
                              │
WORM seal ──► completed passes sealed; chain verifies with `sable verify`
              (byte-compatible with the APL machine's own log format —
              verified once against aplre's verifier during development)
```

**Orbital** is the deployment frame: a pass is a compute window with a
fixed energy budget — the way a spacecraft's eclipse pass is. Lanes run
highest-resonance-first inside the quantum shuffle, so a depleted budget
still did the work that mattered most. The AND-fold veto is preserved:
any component truth 0 → INVALID, the pass halts before executing
anything, and the seal is withheld.

**Wolfram Q** is the sampler's quantum expression: `quantum/`
amplitude-encodes the resonance weights into a qudit and measures in
the computational basis. The C engine's ANU-shuffle sampler is a
classical sampler with quantum entropy, not that circuit — the two are
not claimed equivalent; what the cross-check pins is everything
downstream of the order.

## Honesty notes

- **Energy is modeled, not measured.** One unit = one SUBLEQ predicate
  evaluation by definition; E_EXEC=8, skips < 1. The ledger's arithmetic
  is exact; mapping units to joules needs silicon calibration, which is
  future work, not claimed here.
- **Entropy is provenance-tagged.** Every run records `quantum` (values
  fetched live from `qrng.anu.edu.au`) or `fallback-csprng` (local
  `/dev/urandom`, 2s timeout). A run never claims quantum entropy it
  didn't fetch.
- **Verify-before-record.** The SplitMix64 stream must reproduce the
  canonical checksum before any pass executes — the same gate as the
  benchmark.
- **The reference oracle is gone.** A Python implementation defined
  truth during development and verified this C port bit-for-bit
  (result `9198698438492148246`, executed 426, taken 510 — identical),
  then left the stack per the Python-free directive. The C self-test
  and `tests/test_crosscheck.sh` (pure sh) carry the verification now.

## Usage

```bash
cd c && make                      # gcc -O3 -std=c11 -Wall -Wextra
./sable --selftest                # field, checksum, sha256, float repr

# live quantum pass (16 ANU words; falls back honestly if unreachable)
read HEX PROV < <(./fetch-anu.sh 16)
./sable --entropy-hex "$HEX" --entropy-provenance "$PROV" \
      --n 4096 --budget 60000 --seal-log seals.jsonl --name eclipse-pass-01
./sable verify --seal-log seals.jsonl

sh ../tests/test_crosscheck.sh    # determinism, expected values, tamper rejection
```

Example run (live ANU fetch, `provenance: quantum`):

```
pass:      eclipse-pass-quantum
status:    completed
gate:      VALID
checksum:  OK
entropy:   quantum  nonce=cba94a5337096bfe
lanes:     visited=4096 taken=2069 executed=1743 gated_skip=326 untaken=2027
sparsity:  57.4% of lanes skipped work
result:    7899349274895355111
energy:    spent=18713.8 / budget=60000.0 (pred=4096.0 exec=13944.0 skip=669.8 seal=4.0)
seal:      73a43944…
chain valid: True - 2 seal(s) verified, chain intact
```

## Layout

```
c/
  sable.c       the engine: gate → checksum → sparse run → seal | verify | --selftest
  field.h       Goldilocks arithmetic (mirrors the benchmark substrate)
  splitmix.h    SplitMix64, counter-increment threading
  sha256.h/.c   self-contained SHA-256 (no crypto dependency)
  jsoncanon.h/.c canonical JSON: sorted keys, compact separators,
                CPython-compatible float repr, raw UTF-8
  fetch-anu.sh  ANU QRNG fetch with provenance tag (sh + curl, no Python)
  Makefile      -O3 -std=c11 -Wall -Wextra
quantum/
  sparse_sampler.wl  Wolfram Quantum Framework sampler (written, unexecuted)
tests/
  test_crosscheck.sh pure-sh verification suite
```

## License

AGPL-3.0-or-later. Copyright (C) 2026 SnapKitty Collective. See LICENSE.
Every source file carries the SPDX header.
