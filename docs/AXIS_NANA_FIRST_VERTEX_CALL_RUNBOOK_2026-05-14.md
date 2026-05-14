# AXIS NANA First Vertex Call Runbook

**Date:** 2026-05-14
**Scope:** Planning the first real Gemini/Vertex API execution.

## 1. Current Safety State
- **Promotion Pipeline:** 13-gate validation enforces strict criteria before any artifact can enter the NIDDHI capsule.
- **Gate 13 Guard:** Unapproved artifacts are generated with `display_allowed: false` and are fundamentally blocked from promotion.
- **Human Approval Loop:** `approve_artifact.py` exists to mandate explicit operator intervention to flip the `display_allowed` flag, generating an approved static preview bundle.
- **Provider Status:** `REAL_CALLS_ENABLED_IN_THIS_WAVE` remains `False` in `gemini_vertex_provider.py`. The system is air-gapped from live APIs by compile-time constants.

## 2. Exact Prerequisites Before First Real Call
Before network calls are unlocked, the following requirements must be verified:
1. `REAL_CALLS_ENABLED_IN_THIS_WAVE` must be updated to `True` via a specific implementation patch.
2. The orchestrator must be capable of feeding real CSL source context (not fixtures) to the model.
3. The orchestrator must seamlessly convert the provider output into the exact directory shape (`manifest.json`, `execution/`, `provider_runs/`, `council/`, `answer_validation/`) expected by `validate_promotion.py`.
4. Outputs must cleanly default to `display_allowed: false` and `artifact_status: generated_unapproved`.

## 3. Required Environment Variables
To authenticate and execute a real call, the environment must contain:
- `GOOGLE_APPLICATION_CREDENTIALS`
- `AXIS_NANA_ALLOW_REAL_LLM`
- `AXIS_NANA_ALLOW_GEMINI_VERTEX`
*(Names only; values must never be documented or logged).*

## 4. Credential Handling Rule
- **Verify File:** Check that the path provided by `GOOGLE_APPLICATION_CREDENTIALS` exists and is readable.
- **Never Print:** Never print the contents of the credential file to stdout/stderr.
- **Never Commit:** Never stage or commit the credential file, its path, or its contents to Git.

## 5. Minimal First-Call Scope
The inaugural API execution must be strictly constrained:
- **Concept Limit:** One concept only (`dukkha`).
- **Provider Limit:** One provider only (`gemini_vertex`).
- **Identifier:** A single, unique `artifact_set_id`.
- **Target:** Artifacts will be written to the local output dir only. **NO PROMOTION TO NIDDHI** will be performed in the execution wave.

## 6. Cost Guard
- **Execution Limit:** Exactly **one** call.
- **No Loops/Batches:** Automation loops, batch requests, or multi-concept execution are strictly forbidden.
- **Fail-Fast:** The script must abort immediately if more than one concept or provider is requested.

## 7. Output Path
All resulting payload files must reside safely inside:
`outputs/nana/<artifact_set_id>/`

## 8. Mandatory Post-Call Gates
Once the provider returns its raw result, the following steps are mandatory:
1. Validate the raw provider result.
2. Generate the unapproved 13-gate bundle (defaults to `display_allowed: false`).
3. Operator performs the formal Human Approval review (`approve_artifact.py`).
4. Validate the approved bundle using `validate_promotion.py`.
5. **No `promote_to_capsule`** until a separate explicit approval decision is rendered.

## 9. Stop Conditions
Execution must halt instantly if any of the following occur:
- Missing required environment variables.
- Missing or unreadable credentials.
- Any provider-side error or timeout.
- The generated answer contains hidden reasoning or chain-of-thought markers.
- The generated answer fails to cite canonical refs.
- The 13-gate validator fails unexpectedly.
- `display_allowed` is not explicitly approved by a human operator.

## 10. Future Implementation Waves
This runbook maps out the trajectory for live integration:
- **Wave 2c.5d:** Enable provider real calls behind strict environment gates.
- **Wave 2c.5e:** Implement a one-call, dry-operator CLI orchestrator.
- **Wave 2c.5f:** Perform real execution and output bundle review.
- **Wave 2c.5g:** Execute the Human Approval script on the live bundle.
- **Wave 2c.5h:** Optional lab capsule promotion (operator gated).
