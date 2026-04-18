# 🧠 AXIS-NANA
### Canonical Knowledge Engine for the PureDhamma Corpus

> **Part of the AXIS-NIDDHI Ecosystem** — `@matikamata`

AXIS-NANA (from Pāli: **Ñāṇa** — *knowledge, understanding, wisdom*) is the knowledge retrieval engine for the PureDhamma corpus. It answers questions, explains concepts, generates study paths, and provides canonical citations — all grounded in the CSL (Corpus Source Library) of 748 posts.

## Core Invariant

> *"ÑĀṆA never synthesizes knowledge. It retrieves and cites.*  
> *All answers are grounded in CSL entry IDs."*

This is a fundamental architectural principle: the engine never "makes up" an explanation. Every response points back to a canonical post by its `PD#PN` identifier.

---

## Architecture

```
axis-nana/
├── engine/
│   ├── nana_engine.py       ← AXIS ÑĀṆA Core V2.1 (primary engine)
│   └── oracle_engine.py     ← Oracle Reasoning Engine V1.0 (to be merged into nana)
│
├── data/
│   ├── _oracle_data.json    ← 72KB structured Q&A canonical data
│   ├── source_format.json   ← Source format specification
│   ├── axis_engine.json     ← Engine configuration
│   └── corpus.json          ← Corpus metadata
│
└── cli/
    ├── axis_cli.sh          ← Unified CLI (31KB) for the ecosystem
    └── run_full_pipeline.sh ← Full pipeline orchestrator
```

---

## Engine Modes (ÑĀṆA V2.1)

| Mode | Description |
|---|---|
| `qa` | Question answering with canonical citations |
| `explain` | Deep concept explanation |
| `quiz` | Generate canonical quiz question |
| `study_path` | Suggest learning sequence |
| `cite` | Return raw canonical citations for a concept |
| `concept_map` | Dependency graph for AXIS COSMOS |

---

## Architectural Invariants

```
[ARCH-1] CANON ACCESS RULE
  All application layers must access canonical knowledge
  through AXIS ÑĀṆA. Direct CSL access is prohibited.
  Application → ÑĀṆA → CANON (no shortcuts)

[ARCH-2] CANON VERSIONING RULE
  Canon IDs are immutable. New expansions create new IDs.
  puredhamma-v1 → puredhamma-v2 (never modify v1)

[ARCH-3] SEMANTIC GROWTH RULE
  New concepts require ≥5 CSL citations.
  Concept JSON must include: concept, citations,
  definition, keyword_index.
```

---

## Future Vision

This engine is designed to be **modality-agnostic** — the same core feeds:
- 📖 Text (sKullApp — reading interface)  
- 🎵 Audio (PitiPath — listening interface)
- 🌌 Graph (AXIS COSMOS — visual navigation)
- 🧘 Adaptive (UltraApp — biometric-aware learning, 2222 CE)

---

## Ecosystem

| Repository | Role |
|---|---|
| [axis-niddhi](https://github.com/matikamata/axis-niddhi) | Core SSG — bilingual static site |
| [axis-navigator](https://github.com/matikamata/axis-navigator) | Semantic graph + learning paths |
| **axis-nana** ← you are here | Canonical knowledge engine |
| axis-preservation *(coming soon)* | Integrity seals + IPFS distribution |

---

🌐 **Live:** https://niddhi.netlify.app  
📜 **Source corpus:** https://puredhamma.net (Prof. Lal Dhammajoti, Ph.D.)

*AXIS-NIDDHI Ecosystem — Deadline: 2222 CE* 🛸
