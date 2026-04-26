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
