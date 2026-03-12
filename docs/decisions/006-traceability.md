# ADR-006: End-to-End Traceability in Generated Code

## Status
Accepted

## Context
Safety standards (IEC 61508, ISO 26262, IEC 62304) require traceability
from requirements through design to implementation. For generated code,
this means every output file and function must be traceable back to the
model and generator that produced it. MATLAB Embedded Coder embeds model
paths, block names, and version info in generated comments.

## Decision
Every generated file includes:
1. **Provenance banner** — generator version, model path, platform path,
   SHA-256 hashes of input files, generation timestamp, and "DO NOT EDIT"
   warning.
2. **@trace tags** — each non-static function has a doc comment linking
   to the model YAML path and block name that produced it.
3. **Content hash** — SHA-256 of the input files, enabling detection of
   regeneration from modified sources.

These are enforced by TRACE-001 through TRACE-005 in the validation
pipeline.

## Consequences
- Auditors can verify that generated code matches a specific model
  version by checking the embedded hashes.
- @trace tags create a bidirectional link: code → model (in comments)
  and model → code (via grep).
- The banner adds ~10 lines of overhead per file, which is negligible
  for the traceability benefit.
