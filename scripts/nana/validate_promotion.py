#!/usr/bin/env python3
"""AXIS NANA — Wave 2c.4f — Capsule Promotion Validator.

Validates a NANA static artifact set against all promotion gates
before any copy into the NIDDHI capsule.

This script does NOT copy files. It does NOT call APIs.
It does NOT read credentials. It does NOT run providers.

Usage:
    python3 scripts/nana/validate_promotion.py --source <path>
    python3 scripts/nana/validate_promotion.py --source fixtures/nana/static_bridge_sample_v1/ --dry-run

Exit codes:
    0 — all gates passed
    1 — one or more gates failed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WAVE = "wave2c4f"

# Exact same forbidden marker list as axis-niddhi-production/pipeline/13-ssg/build.py
FORBIDDEN_MARKERS: list[str] = [
    "/home/",
    "/media/",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "gen-lang-client",
    "private_key",
    "BEGIN PRIVATE KEY",
    "api_key",
    "access_token",
    "refresh_token",
    "github_token",
    "deepl_key",
    "wp_password",
    "pipeline/scripts/private",
]

# Chain-of-thought / hidden reasoning markers — never in promoted artifacts
COT_MARKERS: list[str] = [
    "reasoning_trace",
    "hidden_chain",
    "cot_",
    "chain_of_thought",
]


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def _pass(msg: str) -> None:
    print(f"  [PASS] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(f"  [INFO] {msg}")


def _section(title: str) -> None:
    print(f"\n── {title} {'─' * max(0, 60 - len(title))}")


# ---------------------------------------------------------------------------
# Gate implementations
# ---------------------------------------------------------------------------

def gate_source_exists(source: Path) -> bool:
    _section("Gate 1 — Source directory")
    if source.is_dir():
        _pass(f"source directory exists: {source}")
        return True
    _fail(f"source directory not found: {source}")
    return False


def gate_manifest_exists(source: Path) -> tuple[bool, Path | None]:
    _section("Gate 2 — manifest.json presence")
    manifest_path = source / "manifest.json"
    if manifest_path.is_file():
        _pass(f"manifest.json found: {manifest_path}")
        return True, manifest_path
    _fail(f"manifest.json not found: {manifest_path}")
    return False, None


def gate_manifest_parse(manifest_path: Path) -> tuple[bool, dict | None]:
    _section("Gate 3 — manifest.json is valid JSON object")
    try:
        raw = manifest_path.read_bytes().decode("utf-8")
    except Exception as exc:
        _fail(f"manifest.json cannot be decoded as UTF-8: {exc}")
        return False, None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        _fail(f"manifest.json JSON parse error: {exc}")
        return False, None
    if not isinstance(data, dict):
        _fail(f"manifest.json root must be a JSON object, got: {type(data).__name__}")
        return False, None
    _pass("manifest.json is a valid JSON object")
    return True, data


def gate_artifacts_by_concept(manifest: dict) -> tuple[bool, dict]:
    _section("Gate 4 — artifacts_by_concept field")
    abc = manifest.get("artifacts_by_concept")
    if not isinstance(abc, dict):
        _fail(
            "manifest.artifacts_by_concept is missing or not an object "
            f"(got: {type(abc).__name__})"
        )
        return False, {}
    _pass(f"artifacts_by_concept is an object with {len(abc)} concept(s): {list(abc.keys())}")
    return True, abc


def gate_artifact_files(
    source: Path, artifacts_by_concept: dict
) -> tuple[bool, list[tuple[str, Path]]]:
    """Return (all_exist, [(rel_path_str, resolved_path), ...])."""
    _section("Gate 5 — All listed artifact paths exist")
    resolved: list[tuple[str, Path]] = []
    all_ok = True

    for concept_id, paths in artifacts_by_concept.items():
        if not isinstance(paths, dict):
            _fail(f"concept '{concept_id}': expected dict of paths, got {type(paths).__name__}")
            all_ok = False
            continue
        for key, rel in paths.items():
            if not isinstance(rel, str):
                _fail(f"concept '{concept_id}' key '{key}': path must be a string, got {type(rel).__name__}")
                all_ok = False
                continue
            resolved_path = source / rel
            if resolved_path.is_file():
                _pass(f"{concept_id}/{key}: {rel}")
                resolved.append((rel, resolved_path))
            else:
                _fail(f"{concept_id}/{key}: NOT FOUND — {rel}")
                all_ok = False

    return all_ok, resolved


def gate_no_path_traversal(resolved: list[tuple[str, Path]]) -> bool:
    _section("Gate 6 — No path traversal (..) in artifact paths")
    ok = True
    for rel, _ in resolved:
        parts = Path(rel).parts
        if ".." in parts:
            _fail(f"path traversal detected in: {rel}")
            ok = False
        else:
            _pass(f"safe relative path: {rel}")
    return ok


def gate_json_extension(resolved: list[tuple[str, Path]]) -> bool:
    _section("Gate 7 — All listed paths have .json extension")
    ok = True
    for rel, p in resolved:
        if p.suffix.lower() == ".json":
            _pass(f"{rel}")
        else:
            _fail(f"non-.json extension rejected: {rel}")
            ok = False
    return ok


def gate_utf8_decode(resolved: list[tuple[str, Path]]) -> tuple[bool, list[tuple[str, str]]]:
    """Return (all_ok, [(rel, content_str), ...])."""
    _section("Gate 8 — All files decode as UTF-8")
    ok = True
    decoded: list[tuple[str, str]] = []
    for rel, p in resolved:
        try:
            content = p.read_bytes().decode("utf-8")
            _pass(f"{rel}")
            decoded.append((rel, content))
        except Exception as exc:
            _fail(f"{rel}: UTF-8 decode failed — {exc}")
            ok = False
    return ok, decoded


def gate_json_parse(decoded: list[tuple[str, str]]) -> tuple[bool, list[tuple[str, dict]]]:
    """Return (all_ok, [(rel, parsed_object), ...])."""
    _section("Gate 9 — All files parse as valid JSON")
    ok = True
    parsed: list[tuple[str, dict]] = []
    for rel, content in decoded:
        try:
            data = json.loads(content)
            _pass(f"{rel}")
            parsed.append((rel, data))
        except json.JSONDecodeError as exc:
            _fail(f"{rel}: JSON parse error — {exc}")
            ok = False
    return ok, parsed


def gate_object_root(parsed: list[tuple[str, dict]]) -> bool:
    _section("Gate 10 — All artifact roots are JSON objects")
    ok = True
    for rel, data in parsed:
        if isinstance(data, dict):
            _pass(f"{rel}")
        else:
            _fail(f"{rel}: root is {type(data).__name__}, expected object")
            ok = False
    return ok


def gate_forbidden_markers(
    resolved: list[tuple[str, Path]], decoded: list[tuple[str, str]]
) -> bool:
    _section("Gate 11 — No forbidden markers in paths or content")
    content_map = dict(decoded)
    ok = True

    for rel, p in resolved:
        blocked_by: list[str] = []

        # Check relative path string
        for marker in FORBIDDEN_MARKERS:
            if marker in rel:
                blocked_by.append(f"path contains '{marker}'")

        # Check file content
        content = content_map.get(rel, "")
        for marker in FORBIDDEN_MARKERS:
            if marker in content:
                blocked_by.append(f"content contains '{marker}'")

        if blocked_by:
            for reason in blocked_by:
                _fail(f"{rel}: {reason}")
            ok = False
        else:
            _pass(f"{rel}: clean")

    return ok


def gate_cot_markers(decoded: list[tuple[str, str]]) -> bool:
    _section("Gate 12 — No chain-of-thought / hidden reasoning markers")
    ok = True
    for rel, content in decoded:
        blocked_by = [m for m in COT_MARKERS if m in content]
        if blocked_by:
            _fail(f"{rel}: contains CoT markers: {blocked_by}")
            ok = False
        else:
            _pass(f"{rel}: clean")
    return ok


def gate_display_gating(
    parsed: list[tuple[str, dict]], source: Path
) -> bool:
    """
    Gate 13: If an artifact contains answer/raw_answer/simulated_answer,
    verify that the corresponding answer_validation has display_allowed=true.
    Fixture artifacts with display_allowed=false pass as non-displayable fixtures.
    """
    _section("Gate 13 — Display gating for answer text")
    ok = True

    # Build a map of all parsed artifacts for cross-reference
    artifact_map: dict[str, dict] = dict(parsed)

    # Find answer_validation artifacts
    validation_artifacts = {
        rel: data
        for rel, data in artifact_map.items()
        if "answer_validation" in rel and isinstance(data, dict)
    }

    # Find provider artifacts that contain answer text
    answer_fields = {"answer", "raw_answer", "simulated_answer", "answer_text"}

    for rel, data in parsed:
        if not isinstance(data, dict):
            continue

        has_answer_text = any(
            k in data and isinstance(data[k], str) and len(data[k].strip()) > 0
            for k in answer_fields
        )

        if not has_answer_text:
            _pass(f"{rel}: no answer text fields")
            continue

        # Check artifact_status — fixture artifacts with display_allowed=false are accepted
        artifact_status = data.get("artifact_status", "")
        is_fixture = "fixture_only" in str(artifact_status)

        # Find corresponding answer_validation
        display_allowed: bool | None = None
        for val_rel, val_data in validation_artifacts.items():
            display_allowed = val_data.get("display_allowed")
            break  # Use first found (only one set per source currently)

        if display_allowed is True:
            _pass(f"{rel}: has answer text — display_allowed=true in answer_validation")
        elif is_fixture and display_allowed is False:
            _pass(
                f"{rel}: has answer text — fixture_only with display_allowed=false "
                "[non-displayable fixture, allowed]"
            )
        elif display_allowed is False:
            _fail(
                f"{rel}: has answer text but display_allowed=false "
                "and artifact is NOT marked fixture_only — promotion blocked"
            )
            ok = False
        else:
            # display_allowed not found or None
            if is_fixture:
                _pass(
                    f"{rel}: has answer text — fixture_only artifact, "
                    "no answer_validation found [non-displayable by contract]"
                )
            else:
                _fail(
                    f"{rel}: has answer text but no answer_validation artifact found "
                    "— promotion blocked (non-fixture source requires validator)"
                )
                ok = False

    return ok


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_validation(source: Path, dry_run: bool) -> int:
    print("=" * 70)
    print(f"AXIS NANA — Capsule Promotion Validator — {WAVE}")
    print(f"Source : {source.resolve()}")
    print(f"Mode   : {'DRY-RUN (no copy will occur)' if dry_run else 'VALIDATE ONLY (no copy in this wave)'}")
    print("=" * 70)

    counters = {
        "files_checked": 0,
        "files_passed": 0,
        "files_blocked": 0,
        "manifest_paths_checked": 0,
    }
    failures: list[str] = []

    def record_fail(gate_name: str) -> None:
        failures.append(gate_name)

    # Gate 1
    if not gate_source_exists(source):
        record_fail("source_exists")
        _print_summary(counters, failures)
        return 1

    # Gate 2
    manifest_ok, manifest_path = gate_manifest_exists(source)
    if not manifest_ok:
        record_fail("manifest_exists")
        _print_summary(counters, failures)
        return 1

    # Gate 3
    parse_ok, manifest = gate_manifest_parse(manifest_path)
    if not parse_ok:
        record_fail("manifest_parse")
        _print_summary(counters, failures)
        return 1

    # Gate 4
    abc_ok, artifacts_by_concept = gate_artifacts_by_concept(manifest)
    if not abc_ok:
        record_fail("artifacts_by_concept")
        _print_summary(counters, failures)
        return 1

    # Gate 5
    files_ok, resolved = gate_artifact_files(source, artifacts_by_concept)
    counters["manifest_paths_checked"] = len(resolved)
    if not files_ok:
        record_fail("artifact_files_exist")

    # Gate 6
    if resolved and not gate_no_path_traversal(resolved):
        record_fail("no_path_traversal")

    # Gate 7
    if resolved and not gate_json_extension(resolved):
        record_fail("json_extension")

    # Gate 8
    utf8_ok, decoded = gate_utf8_decode(resolved)
    if not utf8_ok:
        record_fail("utf8_decode")

    # Gate 9
    json_ok, parsed = gate_json_parse(decoded)
    if not json_ok:
        record_fail("json_parse")

    # Update file counters
    counters["files_checked"] = len(resolved)

    # Gate 10
    if parsed and not gate_object_root(parsed):
        record_fail("object_root")

    # Gate 11
    if not gate_forbidden_markers(resolved, decoded):
        record_fail("forbidden_markers")

    # Gate 12
    if decoded and not gate_cot_markers(decoded):
        record_fail("cot_markers")

    # Gate 13
    if parsed and not gate_display_gating(parsed, source):
        record_fail("display_gating")

    # Final file counters
    counters["files_blocked"] = len(failures)
    counters["files_passed"] = counters["files_checked"] - max(
        0, len([f for f in failures if f not in (
            "source_exists", "manifest_exists", "manifest_parse",
            "artifacts_by_concept", "artifact_files_exist"
        )])
    )

    _print_summary(counters, failures)

    if failures:
        return 1
    return 0


def _print_summary(counters: dict, failures: list[str]) -> None:
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  manifest_paths_checked : {counters['manifest_paths_checked']}")
    print(f"  files_checked          : {counters['files_checked']}")
    print(f"  gates_failed           : {len(failures)}")
    if failures:
        for f in failures:
            print(f"    - {f}")
    if not failures:
        print("\n  ✅  ALL GATES PASSED — artifact set is valid for promotion")
        print("  (Actual promotion into NIDDHI capsule is a separate future step.)")
    else:
        print("\n  ❌  VALIDATION FAILED — do NOT promote this artifact set")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "AXIS NANA capsule promotion validator — Wave 2c.4f. "
            "Validates a NANA static artifact set before any copy into NIDDHI capsule. "
            "Does NOT copy files. Does NOT call APIs. Does NOT read credentials."
        )
    )
    parser.add_argument(
        "--source",
        metavar="PATH",
        required=True,
        help=(
            "Path to the NANA artifact set to validate. "
            "Examples: fixtures/nana/static_bridge_sample_v1/ "
            "or outputs/nana/<run_id>/"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Explicitly label output as dry-run. Behavior is identical — no files are ever copied.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source = Path(args.source)
    return run_validation(source, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
