(* ::Package:: *)

(* SABLE sparse sampler — Wolfram Quantum Framework program.
 *
 * STATUS: WRITTEN, NOT EXECUTED. This host has no Wolfram Engine /
 * wolframscript (cf. reduction-algebra-bench wolfram/exp02: the same
 * standing rule — no results claimed until executed). Run in
 * Wolfram Engine 14+ with the QuantumFramework paclet.
 *
 * What it does: the SABLE sparse pass visits lanes in an order drawn
 * from quantum measurement. This program expresses that sampler as a
 * quantum circuit: an amplitude-encoded qudit over lane indices,
 * weighted by the APL machine's resonance table, measured in the
 * computational ("Z") basis. The classical SUBLEQ execution consumes
 * the sampled order; the quantum part is the sampler only (hybrid
 * design, stated plainly).
 *
 * API usage below follows the wolframresearch/quantumframework
 * reference docs: QuantumState[vector], QuantumMeasurementOperator["Z"],
 * ["SimulatedMeasurement"], QuditBasis["Z"]["Names"]. *)

Needs["Wolfram`QuantumFramework`"];

(* --- resonance table: vendored from the APL machine's DEFAULT_RESONANCE,
 * documented as such; the six sovereign components in canonical order --- *)
$components = {"origin", "ledger", "oracle", "policy", "consensus", "mesh"};
$resonance = <|"origin" -> 1.00, "ledger" -> 0.90, "oracle" -> 0.80,
               "policy" -> 0.70, "consensus" -> 0.85, "mesh" -> 0.75|>;
laneResonance[i_Integer] := $resonance[$components[[Mod[i, 6] + 1]]];

(* --- amplitude-encoded sampler state: |psi> = Sum_i sqrt(r_i / R) |i> ---
 * A qudit of dimension n; QuantumState[vector] is the documented
 * constructor (cf. QuantumState[{0,0,1}] for a qutrit in the QF docs). *)
sableSamplerState[n_Integer?Positive] := Module[{amps, rtot},
  amps = Table[laneResonance[i], {i, 0, n - 1}];
  rtot = Total[amps];
  QuantumState[Sqrt[amps/rtot]]
];

(* --- one measurement shot in the computational basis ---
 * QuantumMeasurementOperator["Z"][state]["SimulatedMeasurement"] is the
 * documented simulated-measurement accessor (cf. the QF BB84 example). *)
sableShot[state_QuantumState] :=
  QuantumMeasurementOperator["Z"][state]["SimulatedMeasurement"];

(* --- visit order: first-occurrence order over `shots` measurement shots ---
 * Outcome labels follow QuditBasis["Z"]["Names"] ordering, i.e. lane index
 * order 0..n-1, so the sampled order is a permutation prefix over lanes. *)
sableVisitOrder[n_Integer?Positive, shots_Integer?Positive] := Module[
  {state, raw, names, idx},
  state = sableSamplerState[n];
  names = QuditBasis["Z"]["Names"];
  raw = Table[sableShot[state], {shots}];
  idx = raw /. Thread[names -> Range[0, n - 1]];
  DeleteDuplicates[idx]
];

(* --- interface contract with the C engine (c/sable.c) ---
 * The C engine consumes a lane visit order. In production that order is
 * produced here, by measurement. In this repository the C engine draws
 * its shuffle from ANU QRNG uint16s through a Fisher-Yates pass
 * (c/fetch-anu.sh), which is a classical sampler with quantum entropy,
 * not this circuit. The two samplers are not claimed equivalent; the
 * execution semantics downstream of the order (SUBLEQ predicate,
 * resonance gating, energy ledger) are identical by construction and
 * are what the cross-check pins. *)

(* Example (Wolfram Engine only):
 *   order = sableVisitOrder[1024, 4096];
 *   Export["/tmp/sable-q-order.json", order, "JSON"];
 *)
