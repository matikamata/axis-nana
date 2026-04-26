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
