# AXIS NANA — Fixture Promotion Protocol
**Wave 2c.4g | Date: 2026-05-13 | Status: Dry-run only**

---

## 1. Purpose

This document defines the operator protocol for promoting the NANA fixture
artifact set into the AXIS-NIDDHI integration lab capsule.

**This is dry-run-first.** No files are written until an explicit real-copy wave
is approved by the operator.

---

## 2. Source and Target Contract

```
SOURCE (fixture set):
  /home/sanghop/axis/axis-nana-lab/fixtures/nana/static_bridge_sample_v1/

TARGET (lab capsule input):
  /home/sanghop/axis/axis-niddhi-lab/pipeline/capsule/nana/

FORBIDDEN TARGET (production — never use):
  /home/sanghop/axis/axis-niddhi-production/pipeline/capsule/nana/
```

The script enforces these paths at runtime via path guards. Any target path
containing `niddhi-production`, `niddhi-published`, or `bengyond-playground`
is rejected with a hard abort before any file operation.

---

## 3. Production Is Off-Limits

> **`axis-niddhi-production` must never be used as a promotion target.**

Fixture promotion, capsule tests, and integration experiments belong
exclusively in `axis-niddhi-lab`.

The production pipeline (`build.py` in `axis-niddhi-production`) reads from its
own `pipeline/capsule/nana/` — a separate path that must only receive artifacts
via the production-approved workflow, which does not exist yet.

---

## 4. Fixture-Only Mode

The fixture set `static_bridge_sample_v1/` carries:
- `artifact_status: "fixture_only_not_for_doctrinal_use"`
- `display_allowed: false`

These are **not canonical doctrine**. They exist to test the bridge plumbing
end-to-end without real LLM output.

The `--fixture-only` flag is required when the source path is under `fixtures/`.
This prevents accidental fixture promotion being confused for real artifact promotion.

---

## 5. Dry-Run-First Policy

In Wave 2c.4g, `--dry-run` is **required**. The script aborts immediately if
`--dry-run` is absent.

`--dry-run` mode:
- Runs all 13 validation gates
- Prints source, target, planned temp dir, planned final dir, planned file list
- Does NOT create `nana.tmp/`, does NOT write, does NOT rename
- Prints: `DRY RUN ONLY — no files copied`

Future real-copy wave (requires explicit human approval):
- Remove `--dry-run` flag
- Script will execute the atomic copy strategy described in Section 7

---

## 6. Validator Reuse

`promote_to_capsule.py` imports `validate_promotion.py` directly (no subprocess).
All 13 gates from Wave 2c.4f run before any file operation is planned or executed.
If validation fails → abort immediately, touch nothing.

---

## 7. Atomic Copy Strategy (Future Wave — Not Executed Here)

When real-copy mode is approved in a future wave:

```
Step 1 — VALIDATE SOURCE
  All 13 gates must pass. Abort if any fail.

Step 2 — CLEANUP LEFTOVER
  tmp_dir = pipeline/capsule/nana.tmp/
  If nana.tmp/ exists → rmtree(nana.tmp/)  [leftover from interrupted run]

Step 3 — COPY TO TEMP
  For each approved file (JSON + optional README.md):
    dst = nana.tmp/<rel_path>
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
  If any copy fails → rmtree(nana.tmp/), abort.

Step 4 — VALIDATE TEMP
  Re-parse nana.tmp/manifest.json (JSON parse only).
  If fail → rmtree(nana.tmp/), abort.

Step 5 — ATOMIC REPLACE
  If pipeline/capsule/nana/ exists → rmtree(nana/)
  nana.tmp/.rename(nana/)

Step 6 — REPORT
  N files copied. Target ready.
  "build.py NOT run — operator must approve separately."
```

**Why atomic?**
- The old `capsule/nana/` is only deleted after the new copy is 100% complete.
- A process kill leaves the old target intact.
- No stale mixed artifacts can reach the SSG.

---

## 8. What Is Never Copied

```
__pycache__/           *.pyc
*.log                  *.env
private_key            credentials
*.pem                  *.key
provider traces        chain-of-thought files
files with /home/      files with /media/
files with GOOGLE_APPLICATION_CREDENTIALS
files with api_key     files with access_token
files with paths containing ".."
```

---

## 9. No Build, No Providers, No APIs

The promotion script:
- Does NOT run `build.py` in any mode
- Does NOT call Vertex AI, Gemini, OpenAI, or any external API
- Does NOT run providers or LLMs
- Does NOT read credentials
- Does NOT inspect secrets

After promotion, the operator must separately and explicitly approve a build run.

---

## 10. No Doctrinal Authority

Fixture artifacts promoted via this script carry no doctrinal authority.
The `artifact_status: fixture_only_not_for_doctrinal_use` field is preserved
verbatim in all promoted JSON files.

The Navigator UI renders a `[⚠ FIXTURE ONLY — not doctrinal]` badge for
any artifact with `fixture_only` in its `artifact_status`.

The NIDDHI build hook re-validates all promoted artifacts via its own
`forbidden_markers` check before copying them to the static site output.

---

## 11. Usage Reference

### Dry-run (this wave):
```bash
cd /home/sanghop/axis/axis-nana-lab

python3 scripts/nana/promote_to_capsule.py \
  --source /home/sanghop/axis/axis-nana-lab/fixtures/nana/static_bridge_sample_v1/ \
  --target /home/sanghop/axis/axis-niddhi-lab/pipeline/capsule/nana/ \
  --fixture-only \
  --dry-run \
  --include-readme
```

### Real copy (future wave — explicit approval required):
```bash
# Only after human approval of a future "Wave 2c.4g real copy" prompt.
# Remove --dry-run. All other flags remain required.
python3 scripts/nana/promote_to_capsule.py \
  --source /home/sanghop/axis/axis-nana-lab/fixtures/nana/static_bridge_sample_v1/ \
  --target /home/sanghop/axis/axis-niddhi-lab/pipeline/capsule/nana/ \
  --fixture-only \
  --include-readme
```

---

## 12. References

| Document | Location |
|---|---|
| Validation gates | `scripts/nana/validate_promotion.py` |
| Capsule promotion protocol (Wave 2c.4f) | `docs/AXIS_NANA_CAPSULE_PROMOTION_PROTOCOL_2026-05-13.md` |
| NIDDHI copy hook doc | `axis-niddhi-lab/docs/AXIS_NIDDHI_NANA_STATIC_COPY_HOOK_2026-04-26.md` |
| NIDDHI copy hook code | `axis-niddhi-lab/pipeline/13-ssg/build.py` → `_copy_nana_static_artifacts()` |
| Fixture set | `fixtures/nana/static_bridge_sample_v1/` |
