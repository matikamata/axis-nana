# AXIS NANA One-Call Preflight Protocol

**Date:** 2026-05-14
**Scope:** Strict environmental validation for Wave 2c.5e.

## Purpose
Before unlocking the Vertex API network layer, the execution environment must be rigorously verified. The preflight harness guarantees that the local environment holds all necessary tokens and configurations to make a call, while actively preventing the call from occurring.

## Preflight Harness Checks
The script `scripts/nana/preflight_first_vertex_call.py` verifies the following invariants:
1. **Target Lock:** The script statically asserts that only the concept `dukkha` can be requested.
2. **Environmental Gates:**
   - `AXIS_NANA_ALLOW_REAL_LLM=1` must be present.
   - `AXIS_NANA_ALLOW_GEMINI_VERTEX=1` must be present.
3. **Credential Integrity:**
   - `GOOGLE_APPLICATION_CREDENTIALS` must be present and point to an existing, readable JSON file.
   - The contents of this file are **never read** by the preflight script, preventing any accidental logging or printing of secret material.
4. **Network Blocker:**
   - The script performs a static inspection of `gemini_vertex_provider.py` to ensure the `NotImplementedError` network blocker is still present. This confirms the codebase has not been prematurely unlocked.

## Operational Outcomes
- If any check fails, the preflight harness exits with code `1`.
- If all checks pass, the environment is confirmed ready for Wave 2c.5f (the actual network unlock and output bundle execution), but remains completely isolated from the internet.
