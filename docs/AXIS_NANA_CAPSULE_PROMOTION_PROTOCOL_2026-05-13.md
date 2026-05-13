# AXIS NANA — Capsule Promotion Protocol
**Wave 2c.4f | Date: 2026-05-13 | Status: Validation-gate only**

---

## 1. Purpose

This document defines the operator protocol for promoting approved NANA static
JSON artifacts into the NIDDHI capsule input directory, where the NIDDHI static
site generator will pick them up and serve them to the Navigator UI.

**Promotion is validation-first.** No files are copied until all validation gates pass.

---

## 2. Bridge Architecture Summary

```
axis-nana-lab                    axis-niddhi-production           Netlify
─────────────────────            ──────────────────────────────   ─────────
fixtures/nana/<set>/    ──[promotion]──▶  pipeline/capsule/nana/
outputs/nana/<run_id>/  (future)                │
                                               │  (build.py SSG run)
                                               ▼
                                    13-static-site/assets/nana/
                                               │
                                               ▼
                                    assets/nana/manifest.json
                                    assets/nana/provider_runs/*.json
                                    assets/nana/council/*.json
                                    assets/nana/answer_validation/*.json
                                               │
                                               ▼
                                    axis-navigator-lab (browser)
                                    fetches static JSON → read-only viewer
```

---

## 3. What This Wave Implements

Wave 2c.4f adds **only the offline validation gate**:

| Component | Status |
|---|---|
| `scripts/nana/validate_promotion.py` | ✅ Implemented |
| Promotion script (copy files) | ❌ Future wave |
| NIDDHI capsule write | ❌ Future wave |
| Live LLM / provider execution | ❌ Permanently deferred in this wave |

The validator **does NOT copy files**. It does NOT call APIs. It does NOT read
credentials. It does NOT run providers.

---

## 4. Current Safe Source Sets

| Source | Path | Status | Notes |
|---|---|---|---|
| Fixture set v1 | `fixtures/nana/static_bridge_sample_v1/` | ✅ Available | `display_allowed: false`, `artifact_status: fixture_only_not_for_doctrinal_use` |
| Generated outputs | `outputs/nana/<run_id>/` | ❌ Not yet created | Requires live provider run (future wave) |

**For all current testing, use the fixture source only.**

---

## 5. Validation Gates

The validator applies 13 gates in order. All must pass for promotion to proceed.

| Gate | Check | Fail behavior |
|---|---|---|
| 1 | Source directory exists | Abort |
| 2 | `manifest.json` exists | Abort |
| 3 | `manifest.json` is valid JSON object | Abort |
| 4 | `manifest.artifacts_by_concept` exists as object | Abort |
| 5 | Every listed artifact path exists on disk | Continue, record |
| 6 | No path traversal (`..`) in any listed path | Continue, record |
| 7 | Every listed file has `.json` extension | Continue, record |
| 8 | Every file decodes as UTF-8 | Continue, record |
| 9 | Every file parses as valid JSON | Continue, record |
| 10 | Every artifact root is a JSON object | Continue, record |
| 11 | No forbidden security markers in paths or content | Continue, record |
| 12 | No chain-of-thought / hidden reasoning markers | Continue, record |
| 13 | Display gating: if answer text present, `display_allowed` must be `true` or artifact must be `fixture_only` | Continue, record |

### 5.1 Forbidden Security Markers (Gate 11)

```
/home/                         /media/
GOOGLE_APPLICATION_CREDENTIALS gen-lang-client
private_key                    BEGIN PRIVATE KEY
api_key                        access_token
refresh_token                  github_token
deepl_key                      wp_password
pipeline/scripts/private
```

### 5.2 Chain-of-Thought Markers (Gate 12)

```
reasoning_trace    hidden_chain
cot_               chain_of_thought
```

---

## 6. Validation Commands

### Validate the fixture set (safe, read-only):

```bash
cd /home/sanghop/axis/axis-nana-lab

# Syntax check only
python3 -m py_compile scripts/nana/validate_promotion.py

# Full dry-run validation against fixture set
python3 scripts/nana/validate_promotion.py \
  --source fixtures/nana/static_bridge_sample_v1/ \
  --dry-run
```

### Expected exit codes:

| Exit code | Meaning |
|---|---|
| `0` | All 13 gates passed — artifact set is structurally valid |
| `1` | One or more gates failed — do NOT promote |

---

## 7. Future Promotion Steps (Not Yet Implemented)

When a future wave implements the promotion script, it must:

1. **Call this validator first.** Exit immediately if validator returns non-zero.
2. **Create a temporary directory** (`pipeline/capsule/nana.tmp/`) in the target repo.
3. **Copy only validated files** into the tmp dir (same gates applied).
4. **Atomic replace**: delete `capsule/nana/` if it exists, rename `nana.tmp/` → `nana/`.
5. **Commit the result** in `axis-niddhi-production` with a signed commit message referencing the source artifact set ID.
6. **Do NOT run the NIDDHI build** as part of the promotion script. Build is a separate human-initiated step.

---

## 8. Security Posture

| Constraint | Enforcement |
|---|---|
| No credentials in artifacts | Gate 11 (forbidden markers) |
| No raw LLM traces | Gate 12 (CoT markers) |
| No absolute filesystem paths | Gate 11 (`/home/`, `/media/`) |
| No path traversal | Gate 6 (`..` check) |
| Answer text not displayed unless gated | Gate 13 (`display_allowed`) + Navigator UI gate |
| Fixture artifacts labeled | `artifact_status: fixture_only_not_for_doctrinal_use` preserved in JSON |
| NIDDHI build hook double-checks | `build.py` `_copy_nana_static_artifacts()` re-applies forbidden markers |

The NIDDHI build hook provides a **second independent security layer** on top of
this validator. Both must pass for an artifact to reach the static site.

---

## 9. What Must NEVER Be Promoted

- Files containing `raw_answer` or `simulated_answer` fields where `display_allowed` is `false` and the artifact is NOT marked `fixture_only`
- Provider HTTP request/response logs
- Chain-of-thought or hidden reasoning traces
- Any file with an absolute path to the local filesystem
- Any file containing credentials or API tokens
- Non-JSON files (`.log`, `.txt`, `.py`, `.env`, etc.)
- Files whose paths contain `..`

---

## 10. References

| Document | Location |
|---|---|
| NANA Static Bridge Contract | `docs/AXIS_NANA_STATIC_ARTIFACT_BRIDGE_CONTRACT_2026-04-26.md` |
| NIDDHI Copy Hook Doc | `axis-niddhi-production/docs/AXIS_NIDDHI_NANA_STATIC_COPY_HOOK_2026-04-26.md` |
| Fixture set v1 | `fixtures/nana/static_bridge_sample_v1/` |
| Promotion validator | `scripts/nana/validate_promotion.py` |
| NIDDHI build hook | `axis-niddhi-production/pipeline/13-ssg/build.py` → `_copy_nana_static_artifacts()` |
