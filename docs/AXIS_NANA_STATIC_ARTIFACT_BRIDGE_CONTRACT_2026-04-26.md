# AXIS NANA STATIC ARTIFACT BRIDGE CONTRACT
Date: 2026-04-26

## 1. Purpose
The purpose of this contract is to define the architecture for integrating the local backend LLM execution with the static frontend interface.
- NANA generates local JSON artifacts.
- NIDDHI packages approved JSON artifacts into the static site.
- Navigator reads static JSON only.
- Browser never calls Vertex/OpenAI/Gemini directly.

## 2. Airgap Rule
The system strictly enforces an airgapped separation between execution and presentation.
- No browser-side credentials.
- No `GOOGLE_APPLICATION_CREDENTIALS` in frontend/static output.
- No committed secrets.
- No provider execution during static build.
- No API call during build unless a future architect-approved local operator mode explicitly allows it.
- Static site is a viewer only.

## 3. Directory Contract
All browser fetch paths must be resolved relative to the deployed site asset base. Do not hardcode absolute paths like `/assets/nana/...`.

**Source-side NANA outputs (`axis-nana-lab`):**
```text
outputs/nana/
  manifest.json
  execution/
  provider_runs/
  council/
  answer_validation/
```

**Promoted NIDDHI capsule input (`axis-niddhi-lab`):**
```text
pipeline/capsule/nana/
  manifest.json
  execution/
  provider_runs/
  council/
  answer_validation/
```

**Static output target (`axis-niddhi-lab` -> Cloudflare Pages):**
```text
assets/nana/
  manifest.json
  execution/
  provider_runs/
  council/
  answer_validation/
```

## 4. Manifest-First Rule
`manifest.json` is the stable entrypoint for discovering available artifacts.

It should include at minimum:
- `schema_version`
- `generated_by`
- `generated_at_policy` (deterministic or omitted)
- `artifact_set_id`
- `concepts`
- `artifacts_by_concept`
- artifact paths relative to `assets/nana/`
- SHA-256 hashes for listed artifacts when available
- `artifact_status`
- `provider_run_type`

Navigator should eventually load the manifest first, then locate provider/council/validation artifacts from the manifest.

## 5. Safe UI Fields
The following fields are considered safe for static UI display:
- `concept_id`
- `concept_label`
- `canonical_refs`
- `cited_refs`
- `provider_name`
- `provider_run_id`
- `provider_run_type`
- `artifact_status`
- `llm_called`
- `gate_decision`
- `display_allowed`
- `validation_status`
- `unknown_refs`
- `check_matrix`
- `answer` (text only when validator marks `display_allowed` true)

## 6. Internal / Forbidden Fields
The following fields and artifacts are forbidden from public static outputs:
- credential paths
- env var values
- API keys
- OAuth/service account JSON
- raw provider HTTP request/response logs
- local filesystem paths
- stack traces
- private prompts containing operator notes
- chain-of-thought or hidden reasoning
- unvalidated raw answers marked unsafe

## 7. Build Responsibility Boundary
- `axis-nana-lab` creates/validates artifacts.
- human/operator promotes approved artifacts into `axis-niddhi-lab/pipeline/capsule/nana` later.
- `axis-niddhi` `build.py` may later copy capsule files to static output.
- `build.py` must not execute NANA or providers in this bridge wave.
- Navigator must degrade gracefully if manifest/artifacts are absent.

## 8. Future Wave Breakdown
- **2c.4b:** sample fixture artifact, mock/none only
- **2c.4c:** NIDDHI copy hook, static copy only
- **2c.4d:** Navigator manifest reader, graceful 404
- **2c.4e:** optional local operator export command
- *Future live Vertex execution remains postponed and gated.*

## 9. Explicit Conclusion
This contract authorizes documentation only. It does not authorize provider execution, build integration, frontend integration, or live API calls.
