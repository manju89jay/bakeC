# Safety Standards Context

bakeC explores embedded code-generation patterns such as static allocation,
lifecycle functions, calibration-data separation and source traceability. These
patterns can be relevant to development under IEC 61508, IEC 62061, ISO 13849-1
or ISO 26262. This project does not demonstrate compliance with those standards,
qualified tooling, a safety integrity level, a performance level or suitability
for medical-device control.

## Configuration is not safety evidence

The AURIX configuration includes SIL 2/PLd, watchdog, safe-state, EtherCAT and
memory-budget metadata. These fields do not implement watchdog handling,
fieldbus communication, safe-state transitions or resource-budget enforcement.
Likewise, a `SIL2_SAFETY` compile definition does not provide a safety mechanism.
The pipeline does not demonstrate AURIX compilation or hardware execution.

Static allocation does not establish worst-case execution time or bounded stack
usage. Those properties require target-specific analysis and measurement. Desktop
execution and Cortex-M4 cross-compilation provide narrower, distinct evidence.

## MISRA-inspired heuristics

bakeC provides **heuristic checks inspired by selected MISRA C:2012 rules**.
Nine text-pattern checks look for selected allocation calls, direct recursion,
missing return types, else-chain termination, unused parameters, extern declarations,
loop-variable modification, stdio calls and potentially const pointer parameters.

These are incomplete approximations, with false positives and false negatives.
They do not establish MISRA compliance or complete coverage of the referenced
rules. Narrowing-conversion analysis is unsupported: the earlier heuristic based
on variable spelling has been removed. See the individual docstrings in
`src/bakec/checks/misra.py` for limitations.

## Verification evidence

`bakec validate` reports findings from applicable categories and identifies skipped
categories. Regression and API-stability comparisons require an independent valid
baseline; platform constraints require platform configuration. Empty targets and
invalid explicit baselines fail. A clean report is not a safety assessment.

The development pipeline also compiles and executes desktop C tests and generated-C
numerical regressions. These tests exercise selected behavior; they do not prove
correctness for all models, inputs, compilers or hardware. Source hashes establish
provenance, not functional equivalence. Deployment needs its own requirements,
verification and safety process.
