# AXIS NANA Retrieval Skeleton

This directory contains the first local-only retrieval skeleton for AXIS NANA.

## Scope

- registry-based concept lookup
- deterministic context pack generation
- strict context pack validation
- deterministic source-bound prompt package generation
- strict prompt package validation
- deterministic provider adapter runs
- strict provider result validation

## Safety posture

- local only
- no API keys required
- no external calls
- no LLM output
- no LLM calls
- no semantic search
- no embeddings
- no canonical mutation

## Retrieval principle

Retrieve cited canonical context first.
Do not interpret, answer, or paraphrase doctrine here.

## Example commands

```bash
python3 scripts/nana/retrieve_concept.py --concept dukkha --dry-run
python3 scripts/nana/retrieve_concept.py --concept anicca --output outputs/nana/context-pack-anicca-bootstrap-v1.json
python3 scripts/nana/validate_context_pack.py outputs/nana/*.json
python3 scripts/nana/build_source_bound_prompt.py --context-pack outputs/nana/context-pack-dukkha-bootstrap-v1.json --question "What causes suffering?" --output outputs/nana/prompts/prompt-dukkha-bootstrap-v1.json
python3 scripts/nana/validate_prompt_package.py outputs/nana/prompts/*.json
python3 scripts/nana/run_provider_adapter.py --execution outputs/nana/execution/execution-dukkha-bootstrap-v1.json --provider none --output outputs/nana/provider_runs/provider-dukkha-none-bootstrap-v1.json
python3 scripts/nana/validate_provider_result.py outputs/nana/provider_runs/*.json
```

## Wave 2c.2 — Safe Runtime Wrapper

Added in `feat/nana-wave2c2-runtime-wrapper-20260426`.

### New files

- `scripts/nana/providers/router.py` — selects `NoneProvider` or `MockProvider` only; rejects all other provider names
- `scripts/nana/execute_llm_safe_mode.py` — CLI wrapper; produces deterministic execution + optional provider result

### Safety guarantees

- No real LLM provider accepted (`gemini`, `openai`, `vertex`, etc. all rejected)
- No network imports, no cloud SDK imports, no credential/env requirements
- All IDs and hashes are deterministic sha256 over canonical JSON input
- `llm_called` is hard-coded `False`; `enable_real_llm` is hard-coded `False`

### Example (dry-run, no output written)

```bash
python3 scripts/nana/execute_llm_safe_mode.py \
  --concept-id dukkha \
  --question "What causes suffering?" \
  --provider none \
  --dry-run

python3 scripts/nana/execute_llm_safe_mode.py \
  --concept-id dukkha \
  --question "What causes suffering?" \
  --provider mock \
  --run-provider \
  --dry-run
```

## Wave 2c.3 — Guarded Gemini/Vertex Provider Adapter

Added in `feat/nana-wave2c3-gemini-vertex-guarded-20260426`.

### New files

- `scripts/nana/providers/gemini_vertex_provider.py` — guarded adapter skeleton; blocked at wave level

### Modified files

- `scripts/nana/providers/base_provider.py` — `ProviderResult` extended with traceability fields
- `scripts/nana/providers/mock_provider.py` — populates new schema fields
- `scripts/nana/providers/none_provider.py` — populates new schema fields
- `scripts/nana/providers/router.py` — adds `_REAL_PROVIDERS` registry; `allow_real` gate
- `scripts/nana/providers/__init__.py` — exports `GeminiVertexProvider`
- `scripts/nana/execute_llm_safe_mode.py` — adds `--allow-real-provider` flag

### Safety guarantees

- **No real API calls in this wave** — `REAL_CALLS_ENABLED_IN_THIS_WAVE = False` is a compile-time constant; the real call path is physically unreachable
- **Default provider unchanged** — `DEFAULT_PROVIDER = "none"`
- **Real providers require explicit `allow_real=True`** — never reached by default
- **6-condition gate** — all must be true for any future real call
- **No secrets in repo** — credential path never hardcoded; env var names only
- **Lazy SDK import** — `vertexai` not required at module import time
- **mock/none regression baseline unchanged**

### Env vars (values never committed)

| Variable | Purpose |
|---|---|
| `AXIS_NANA_ALLOW_REAL_LLM` | Must be `"1"` to allow real LLM routing |
| `AXIS_NANA_ALLOW_GEMINI_VERTEX` | Must be `"1"` to allow Gemini/Vertex |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON (external only) |
| `AXIS_NANA_GEMINI_MODEL` | Model override (default: `gemini-2.0-flash`) |

### Future live smoke test

Real API call activation requires a separate, explicitly authorised wave.
Do not set `REAL_CALLS_ENABLED_IN_THIS_WAVE = True` without a new guarded PR.
