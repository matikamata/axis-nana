#!/usr/bin/env python3
"""
AXIS-NIDDHI — nana_engine.py
AXIS ÑĀṆA — Core Understanding Engine V2.1

ARCHITECTURAL INVARIANTS (Cognitive Phase):

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

ARCHITECTURE:
  Modality-agnostic. Returns structured NanaResponse.
  The same engine feeds: text (sKullApp), audio (PitiPath), graph (Cosmos).

MODES:
  qa            — question answering with canonical citations
  explain       — deep concept explanation
  quiz          — generate canonical quiz question
  study_path    — suggest learning sequence
  cite          — return raw canonical citations for a concept
  concept_map   — dependency graph for AXIS COSMOS

KNOWLEDGE SOURCE:
  - semantic/concepts/*.json   (11 canonical concepts)
  - navigator/query_index.json (CSL entry index)
  - CSL (748 entries via slug_map)

INVARIANT:
  ÑĀṆA never synthesizes knowledge. It retrieves and cites.
  All answers are grounded in CSL entry IDs.
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ── Resolve paths ─────────────────────────────────────────────────────────────
_SELF = Path(__file__).resolve()

def _resolve_base() -> Path:
    env = os.environ.get("BENG_BASE")
    if env:
        return Path(env)
    for candidate in [_SELF.parent, _SELF.parent.parent,
                      _SELF.parent.parent.parent]:
        if (candidate / "semantic").is_dir():
            return candidate
    return Path.cwd()

BASE = _resolve_base()

# ── ÑĀṆA data structures ────────────────────────────────────────────────────
@dataclass
class CanonicalCitation:
    pdpn:    str          # e.g. "DS.FF.002"
    title:   str          # human-readable slug title
    concept: str          # which concept this supports
    score:   int = 5      # relevance score

@dataclass
class ConceptMatch:
    slug:        str
    pali:        str
    label_en:    str
    type_:       str
    description: str
    related:     list[str]
    confidence:  float    # 0–1

@dataclass
class StudyPath:
    id:          str
    title:       str
    level:       str
    sequence:    list[str]

@dataclass
class QuizItem:
    question:    str
    options:     list[str]
    answer:      str
    explanation: str
    citation:    str       # PDPN ID

@dataclass
class ConceptMapNode:
    """Single node in a concept dependency graph for AXIS COSMOS."""
    slug:         str
    pali:         str
    label_en:     str
    type_:        str
    depth:        int           # 0 = core, 1 = direct deps, 2 = extended
    edges:        list[str]     # slugs this node depends on / relates to

@dataclass
class NanaResponse:
    """
    Modality-agnostic ÑĀṆA output — text / audio / graph.
    Renderers (text / audio / graph) consume this struct.
    """
    mode:             str
    query:            str
    concepts:         list[ConceptMatch]
    citations:        list[CanonicalCitation]
    study_paths:      list[StudyPath]
    quiz:             Optional[QuizItem]
    prompt:           str           # LLM-ready prompt with canonical context
    context_json:     dict          # machine-readable context for downstream
    warnings:         list[str]
    confidence_score: float = 0.0   # 0–1 aggregate detection confidence
    citation_count:   int   = 0     # total CSL citations retrieved
    concept_depth:    int   = 0     # max depth of detected concept graph (0–2)
    concept_graph:    Optional[list] = None  # list[ConceptMapNode] for concept_map mode

    def to_dict(self) -> dict:
        return asdict(self)

    def to_audio_hint(self) -> dict:
        """Stripped output for audio/TTS rendering."""
        return {
            "mode":      self.mode,
            "query":     self.query,
            "concepts":  [{"pali": c.pali, "label": c.label_en}
                          for c in self.concepts],
            "citations": [{"id": c.pdpn, "title": c.title}
                          for c in self.citations[:3]],
            "paths":     [{"id": p.id, "level": p.level}
                          for p in self.study_paths],
        }

    def to_graph_hint(self) -> dict:
        """Node/edge output for AXIS COSMOS graph rendering."""
        if self.concept_graph:
            # Full concept_map mode — rich graph
            nodes = [{"id": n.slug, "label": n.pali, "type": n.type_,
                      "depth": n.depth, "citation_count": len(n.edges) + 2}
                     for n in self.concept_graph]
            edges = [{"from": n.slug, "to": r, "weight": 1 if n.depth == 0 else 0.5}
                     for n in self.concept_graph for r in n.edges]
        else:
            # Inline graph from detected concepts
            nodes = [{"id": c.slug, "label": c.pali, "type": c.type_,
                      "depth": 0, "citation_count": len(c.related) + 2}
                     for c in self.concepts]
            edges = [{"from": c.slug, "to": r, "weight": 1}
                     for c in self.concepts for r in c.related]
        return {
            "schema":         "AXIS-COSMOS-GRAPH-V1",
            "nodes":          nodes,
            "edges":          edges,
            "citations":      [c.pdpn for c in self.citations],
            "confidence":     self.confidence_score,
        }


# ── Knowledge base ─────────────────────────────────────────────────────────────
class NanaKnowledgeBase:
    """Loads and indexes the AXIS canon knowledge base."""

    STUDY_PATHS = [
        StudyPath("BEGINNER_PATH", "Three Marks of Existence", "beginner",
                  ["dukkha","anicca","anatta","tilakkhana"]),
        StudyPath("DEPENDENT_ORIGINATION_PATH", "Dependent Origination", "intermediate",
                  ["avijja","sankhara","tanha","paticca_samuppada"]),
        StudyPath("LIBERATION_PATH", "Path to Liberation", "advanced",
                  ["magga","phala","nibbana"]),
    ]

    def __init__(self):
        self.concepts:      dict = {}
        self.csl_index:     dict = {}   # concept → [{pdpn, title, score}]
        self.keyword_index: dict = {}   # term → {concept_slug: weight}
        self.slug_map:      dict = {}
        self._load()

    def _load(self):
        # 1. Load concepts from semantic/concepts/*.json
        concept_dir = BASE / "semantic" / "concepts"
        if concept_dir.is_dir():
            for f in concept_dir.glob("*.json"):
                try:
                    c = json.loads(f.read_text(encoding="utf-8"))
                    self.concepts[c["concept"]] = c
                except Exception:
                    pass

        # 2. Load slug_map
        slug_map_path = BASE / "09-csl" / "slug_map.json"
        if not slug_map_path.exists():
            # Try metadata dir
            slug_map_path = BASE / "metadata" / "slug_map.json"
        if slug_map_path.exists():
            self.slug_map = json.loads(slug_map_path.read_text(encoding="utf-8"))

        # 3. Load query_index from navigator
        query_path = BASE / "navigator" / "query_index.json"
        if query_path.exists():
            qi = json.loads(query_path.read_text(encoding="utf-8"))
            for concept_slug, data in qi.get("concepts", {}).items():
                entries = data.get("csl_entries", [])
                self.csl_index[concept_slug] = [
                    {"pdpn": e.get("pdpn",""), "title": e.get("slug",""), "score": 5}
                    for e in entries
                ]

        # 4. Build keyword detection index
        self._build_keyword_index()

        # 5. Populate CSL titles from slug_map
        self._enrich_csl_titles()

    def _build_keyword_index(self):
        """Build inverted keyword → concept index for question parsing."""
        def add(term: str, slug: str, weight: int):
            t = term.lower().strip(".,;:()'\"")
            if len(t) < 3:
                return
            if t not in self.keyword_index:
                self.keyword_index[t] = {}
            self.keyword_index[t][slug] = max(
                self.keyword_index[t].get(slug, 0), weight
            )

        KEY_PHRASES = {
            "dukkha":            ["suffering","unsatisfactoriness","pain","stress",
                                  "first noble truth","dukkha"],
            "anicca":            ["impermanence","impermanent","change","arising",
                                  "passing away","transient","anicca"],
            "anatta":            ["non-self","no-self","not-self","selfless","no self",
                                  "no permanent self","anatta","anattā"],
            "tilakkhana":        ["three marks","three characteristics","three signs",
                                  "marks of existence","tilakkhana"],
            "avijja":            ["ignorance","delusion","not knowing","root cause",
                                  "root condition","avijja","avijjā"],
            "sankhara":          ["formations","volitional","kamma","intention",
                                  "conditioned","sankhara","saṅkhāra"],
            "tanha":             ["craving","desire","thirst","longing","attachment",
                                  "cause of suffering","origin of suffering",
                                  "second noble truth","tanha","taṇhā"],
            "paticca_samuppada": ["dependent origination","dependent arising",
                                  "twelve links","nidana","conditioned arising",
                                  "paticca samuppada","paṭicca samuppāda"],
            "magga":             ["eightfold path","noble path","right view",
                                  "right intention","practice","fourth noble truth",
                                  "magga","path"],
            "phala":             ["fruition","attainment","fruit","stages of awakening",
                                  "four stages","phala","sotapatti","arahant"],
            "nibbana":           ["nirvana","liberation","cessation","freedom",
                                  "unconditioned","extinguishing","release",
                                  "nibbana","nibbāna","enlightenment"],
        }

        for slug, c in self.concepts.items():
            add(slug, slug, 10)
            add(c.get("pali","").lower(), slug, 10)
            add(c.get("translations",{}).get("en",""), slug, 9)
            for phrase in KEY_PHRASES.get(slug, []):
                add(phrase, slug, 8)
            for ref in c.get("glossary_refs", []):
                add(ref, slug, 7)

    def _enrich_csl_titles(self):
        for slug, entries in self.csl_index.items():
            for e in entries:
                pdpn = e.get("pdpn","")
                if pdpn in self.slug_map and not e.get("title"):
                    e["title"] = self.slug_map[pdpn].replace("-"," ").title()

    def detect_concepts(self, text: str) -> list[ConceptMatch]:
        """Detect canonical concepts mentioned in a text string."""
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for term, concept_weights in self.keyword_index.items():
            if term in text_lower:
                for slug, weight in concept_weights.items():
                    scores[slug] = scores.get(slug, 0) + weight

        if not scores:
            return []

        max_score = max(scores.values())
        results = []
        for slug, score in sorted(scores.items(), key=lambda x: -x[1]):
            c = self.concepts.get(slug)
            if not c:
                continue
            results.append(ConceptMatch(
                slug        = slug,
                pali        = c.get("pali",""),
                label_en    = c.get("translations",{}).get("en",""),
                type_       = c.get("type",""),
                description = c.get("description",""),
                related     = c.get("related",[]),
                confidence  = round(score / max_score, 2),
            ))
        return results[:5]

    def get_citations(self, concept_slugs: list[str],
                      max_per_concept: int = 4) -> list[CanonicalCitation]:
        """Return top canonical citations for a set of concepts."""
        seen: set = set()
        citations: list[CanonicalCitation] = []

        for slug in concept_slugs:
            entries = self.csl_index.get(slug, [])
            count = 0
            for e in sorted(entries, key=lambda x: -x.get("score",5)):
                pdpn = e.get("pdpn","")
                if pdpn in seen or not pdpn:
                    continue
                seen.add(pdpn)
                title = e.get("title") or self.slug_map.get(pdpn,"")
                citations.append(CanonicalCitation(
                    pdpn    = pdpn,
                    title   = title.replace("-"," ").title() if title else pdpn,
                    concept = slug,
                    score   = e.get("score", 5),
                ))
                count += 1
                if count >= max_per_concept:
                    break
        return citations

    def suggest_paths(self, concept_slugs: list[str]) -> list[StudyPath]:
        """Suggest study paths that cover the detected concepts."""
        slug_set = set(concept_slugs)
        scored = []
        for path in self.STUDY_PATHS:
            overlap = len(slug_set & set(path.sequence))
            if overlap > 0:
                scored.append((overlap, path))
        scored.sort(key=lambda x: -x[0])
        return [p for _, p in scored]

    def build_concept_map(self, core_slugs: list[str],
                          depth: int = 2) -> list:
        """
        Build a concept dependency graph for AXIS COSMOS.
        depth=0: core concepts only
        depth=1: core + direct related
        depth=2: core + related + extended
        Returns list[ConceptMapNode].
        """
        seen:  dict[str, int] = {}  # slug → depth assigned
        queue: list[tuple[str, int]] = [(s, 0) for s in core_slugs]
        nodes: list = []

        while queue:
            slug, d = queue.pop(0)
            if slug in seen or d > depth:
                continue
            seen[slug] = d
            c = self.concepts.get(slug)
            if not c:
                continue
            related = c.get("related", [])
            nodes.append(_ConceptMapNode(
                slug     = slug,
                pali     = c.get("pali", slug),
                label_en = c.get("translations", {}).get("en", ""),
                type_    = c.get("type", ""),
                depth    = d,
                edges    = [r for r in related if r in self.concepts],
            ))
            if d < depth:
                for r in related:
                    if r not in seen:
                        queue.append((r, d + 1))

        return nodes

    def get_quiz(self, concept_slug: str) -> Optional[QuizItem]:
        """Generate a canonical quiz question for a concept."""
        QUIZZES = {
            "dukkha": QuizItem(
                question   = "According to the Buddha's teaching, which of the following best describes dukkha?",
                options    = ["A pleasant mental state", "The unsatisfactoriness inherent in all conditioned existence",
                              "A type of meditation practice", "The cessation of craving"],
                answer     = "The unsatisfactoriness inherent in all conditioned existence",
                explanation= "Dukkha is the First Noble Truth — all conditioned existence is unsatisfactory because it is impermanent (anicca) and arises dependent on causes and conditions.",
                citation   = "BD.AA.009",
            ),
            "tanha": QuizItem(
                question   = "What does the Second Noble Truth identify as the origin of suffering?",
                options    = ["Ignorance (avijjā)", "Craving (taṇhā)", "Volitional formations (saṅkhāra)", "Non-self (anattā)"],
                answer     = "Craving (taṇhā)",
                explanation= "The Second Noble Truth states that craving (taṇhā) — for sensual pleasure, for existence, or for non-existence — is the proximate origin of suffering.",
                citation   = "DS.FF.002",
            ),
            "avijja": QuizItem(
                question   = "In paṭicca samuppāda, what is the first and root condition?",
                options    = ["Taṇhā (craving)", "Saṅkhāra (formations)", "Avijjā (ignorance)", "Phassa (contact)"],
                answer     = "Avijjā (ignorance)",
                explanation= "Avijjā — ignorance of the Four Noble Truths and the three characteristics — is the first nidāna. Its cessation leads to the cessation of the entire chain.",
                citation   = "PS.II.004",
            ),
            "nibbana": QuizItem(
                question   = "How does the Canon describe Nibbāna?",
                options    = ["A heavenly realm", "Annihilation of the self", "The unconditioned cessation of craving and ignorance",
                              "A deep meditative state"],
                answer     = "The unconditioned cessation of craving and ignorance",
                explanation= "Nibbāna is not a place or annihilation. It is the unconditioned — the permanent cessation of suffering, craving, and ignorance, realized at the moment of phala.",
                citation   = "BD.HH.007",
            ),
            "magga": QuizItem(
                question   = "The Noble Eightfold Path is which of the Four Noble Truths?",
                options    = ["The First — the truth of suffering",
                              "The Second — the truth of the origin of suffering",
                              "The Third — the truth of cessation",
                              "The Fourth — the truth of the path"],
                answer     = "The Fourth — the truth of the path",
                explanation= "The Fourth Noble Truth identifies the Noble Eightfold Path (magga) as the practical method leading to the cessation of suffering.",
                citation   = "TL.BB.006",
            ),
        }
        return QUIZZES.get(concept_slug)


# Internal alias — KB builds these before dataclass is in scope
_ConceptMapNode = ConceptMapNode

# ── ÑĀṆA engine ──────────────────────────────────────────────────────────────
class NanaEngine:
    """
    AXIS ÑĀṆA — modality-agnostic reasoning engine.
    Produces NanaResponse from natural language queries.
    """

    def __init__(self):
        self.kb = NanaKnowledgeBase()

    def ask(self, question: str, mode: str = "qa") -> NanaResponse:
        """
        Main entry point.
        mode: qa | explain | quiz | study_path | cite | concept_map
        """
        concepts  = self.kb.detect_concepts(question)
        slugs     = [c.slug for c in concepts]
        citations = self.kb.get_citations(slugs, max_per_concept=4)
        paths     = self.kb.suggest_paths(slugs)
        quiz      = self.kb.get_quiz(slugs[0]) if slugs else None
        prompt    = self._build_prompt(question, concepts, citations, mode)

        # Confidence score — weighted mean of top concept confidences
        confidence = round(
            sum(c.confidence for c in concepts[:3]) / max(len(concepts[:3]), 1), 2
        ) if concepts else 0.0

        # Concept graph — always built; deep in concept_map mode
        graph_depth    = 2 if mode == "concept_map" else 1
        concept_graph  = self.kb.build_concept_map(slugs, depth=graph_depth)

        return NanaResponse(
            mode             = mode,
            query            = question,
            concepts         = concepts,
            citations        = citations,
            study_paths      = paths,
            quiz             = quiz,
            prompt           = prompt,
            context_json     = self._build_context(question, concepts, citations),
            warnings         = self._warnings(concepts, citations),
            confidence_score = confidence,
            citation_count   = len(citations),
            concept_depth    = max((n.depth for n in concept_graph), default=0),
            concept_graph    = concept_graph,
        )

    def _build_prompt(self, question: str,
                      concepts: list[ConceptMatch],
                      citations: list[CanonicalCitation],
                      mode: str) -> str:
        """Build LLM-ready prompt grounded in canonical context."""

        concept_block = "\n".join(
            f"  [{c.pali} / {c.label_en}]\n  {c.description}"
            for c in concepts[:3]
        ) or "  No canonical concepts detected."

        citation_block = "\n".join(
            f"  [{c.pdpn}] {c.title}"
            for c in citations[:6]
        ) or "  No canonical CSL entries found."

        related_block = ", ".join(
            sorted({r for c in concepts for r in c.related[:3]})
        ) or "none"

        MODE_INSTRUCTIONS = {
            "qa": (
                "Answer the question using ONLY the canonical context provided. "
                "Cite CSL IDs (e.g. [DS.FF.002]) inline for every claim. "
                "Do not speculate beyond what the canon states."
            ),
            "explain": (
                "Provide a thorough explanation of the detected concepts using ONLY "
                "the canonical definitions provided. Structure: (1) Pāli term and "
                "meaning, (2) canonical definition, (3) relationship to other concepts, "
                "(4) CSL citations. Cite all CSL IDs inline."
            ),
            "quiz": (
                "Generate one canonical quiz question about the primary concept. "
                "Format: Question / Four options (A–D) / Correct answer / "
                "Explanation citing CSL IDs."
            ),
            "study_path": (
                "Suggest a structured learning sequence for this topic. "
                "Start from foundational concepts and progress to advanced ones. "
                "Reference only the canonical study paths and cite CSL IDs."
            ),
            "cite": (
                "Return the canonical citations relevant to this topic. "
                "For each CSL entry: ID, title, and which concept it supports."
            ),
            "concept_map": (
                "Describe the canonical concept dependency structure. "
                "For each detected concept: (1) Pāli term and type, "
                "(2) direct canonical dependencies (what it requires to be understood), "
                "(3) dependent concepts (what depends on it), "
                "(4) key CSL citations. "
                "Format suitable for knowledge graph visualization."
            ),
        }

        instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["qa"])

        return f"""You are AXIS ÑĀṆA — a canonical question-answering engine for the PureDhamma corpus.
Your only source of knowledge is the AXIS Canon (748 CSL entries). You do not speculate.
Every statement must be grounded in the canonical context below and cited with a CSL ID.

═══════════════════════════════════════════════════════
CANONICAL CONTEXT
═══════════════════════════════════════════════════════

QUESTION:
{question}

DETECTED CONCEPTS:
{concept_block}

RELATED CONCEPTS: {related_block}

CANONICAL CSL ENTRIES:
{citation_block}

═══════════════════════════════════════════════════════
INSTRUCTION ({mode.upper()}):
{instruction}

CITATION FORMAT: cite as [PDPN] e.g. [DS.FF.002] inline.
If no canonical source supports a claim, state: "Not found in canon."
═══════════════════════════════════════════════════════"""

    def _build_context(self, question: str,
                       concepts: list[ConceptMatch],
                       citations: list[CanonicalCitation]) -> dict:
        return {
            "question":  question,
            "concepts":  [{"slug": c.slug, "pali": c.pali,
                           "confidence": c.confidence} for c in concepts],
            "citations": [{"pdpn": c.pdpn, "title": c.title,
                           "concept": c.concept} for c in citations],
            "corpus":    "puredhamma",
            "csl_total": 748,
        }

    def _warnings(self, concepts: list[ConceptMatch],
                  citations: list[CanonicalCitation]) -> list[str]:
        w = []
        if not concepts:
            w.append("No canonical concepts detected — answer may be limited")
        if not citations:
            w.append("No CSL citations found for detected concepts")
        low = [c.slug for c in concepts if c.confidence < 0.3]
        if low:
            w.append(f"Low confidence detection: {', '.join(low)}")
        return w


# ── Convenience API ────────────────────────────────────────────────────────────
_engine: Optional[NanaEngine] = None

def get_engine() -> NanaEngine:
    global _engine
    if _engine is None:
        _engine = NanaEngine()
    return _engine

def ask(question: str, mode: str = "qa") -> NanaResponse:
    return get_engine().ask(question, mode)

def ask_dict(question: str, mode: str = "qa") -> dict:
    return ask(question, mode).to_dict()


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is dukkha?"
    r = ask(q)
    print(f"\nQuery      : {r.query}")
    print(f"Mode       : {r.mode}")
    print(f"Confidence : {r.confidence_score}")
    print(f"Concepts   : {[c.pali for c in r.concepts]}")
    print(f"Citations  ({len(r.citations)}):")
    for c in r.citations:
        print(f"  [{c.pdpn}] {c.title}")
    print(f"Paths      : {[p.id for p in r.study_paths]}")
    if r.concept_graph:
        print(f"Graph      : {len(r.concept_graph)} nodes")
        for n in r.concept_graph[:4]:
            print(f"  depth={n.depth} {n.pali} → {n.edges[:3]}")
    print(f"Warnings   : {r.warnings}")
    print(f"\nPrompt ({len(r.prompt)} chars) ↓")
    print(r.prompt[:500] + "...")
