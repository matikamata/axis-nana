#!/usr/bin/env python3
"""AXIS NANA — Capsule Promotion Script (Wave 2c.4g+).

Promotes a validated NANA static artifact set from axis-nana-lab into
the axis-niddhi-lab capsule input directory.

Modes:
  --dry-run   Validate and plan only. No files written. (always safe)
  --execute   Perform the real atomic copy after all guards pass.
              Requires --fixture-only. Requires explicit operator decision.

Usage (dry-run):
    python3 scripts/nana/promote_to_capsule.py \\
        --source /home/sanghop/axis/axis-nana-lab/fixtures/nana/static_bridge_sample_v1/ \\
        --target /home/sanghop/axis/axis-niddhi-lab/pipeline/capsule/nana/ \\
        --fixture-only \\
        --dry-run \\
        [--include-readme]

Usage (real copy — explicit operator approval required):
    python3 scripts/nana/promote_to_capsule.py \\
        --source /home/sanghop/axis/axis-nana-lab/fixtures/nana/static_bridge_sample_v1/ \\
        --target /home/sanghop/axis/axis-niddhi-lab/pipeline/capsule/nana/ \\
        --fixture-only \\
        --execute \\
        [--include-readme]

Hard constraints enforced at runtime (both modes):
  - Exactly one of --dry-run or --execute must be specified
  - Target must be under /home/sanghop/axis/axis-niddhi-lab/pipeline/capsule/
  - Target must NOT contain: niddhi-production, niddhi-published, bengyond-playground
  - Source must be under /home/sanghop/axis/axis-nana-lab/
  - Source under fixtures/ requires --fixture-only
  - Source under outputs/ is refused (no --allow-generated flag yet)
  - All 13 validation gates from validate_promotion.py must pass before any copy
  - build.py is never called
  - No external API calls, no providers

Atomic copy strategy (--execute mode):
  Step 1. Validate source (all 13 gates) → abort if any fails.
  Step 2. tmp_dir = target.parent / "nana.tmp"
          If tmp_dir exists → rmtree(tmp_dir)  [cleanup leftover]
  Step 3. For each approved file:
            dst = tmp_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
          If any copy fails → rmtree(tmp_dir), abort.
  Step 4. Re-validate tmp_dir/manifest.json (JSON parse only).
          If fail → rmtree(tmp_dir), abort.
  Step 5. If target.exists() → shutil.rmtree(target)
  Step 6. tmp_dir.rename(target)
  Step 7. Report: N files copied, target ready.
          Print: "build.py NOT run — operator must approve separately."

  This strategy ensures:
    - The old capsule/nana/ is only removed after the new copy is 100% complete.
    - A process kill leaves old target intact (tmp_dir is the staging area).
    - No stale mixed artifacts can be served.

Exit codes:
  0 — success (dry-run passed or execute completed)
  1 — any guard, path, validation, or copy failure
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve import path so validate_promotion can be imported as a module
# regardless of cwd.
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Import the 13-gate validator directly (no subprocess).
try:
    from validate_promotion import (
        run_validation,
        gate_manifest_exists,
        gate_manifest_parse,
        gate_artifacts_by_concept,
        gate_artifact_files,
    )
    _VALIDATOR_AVAILABLE = True
except ImportError as _imp_err:
    _VALIDATOR_AVAILABLE = False
    _VALIDATOR_IMPORT_ERROR = str(_imp_err)


# ---------------------------------------------------------------------------
# Path contract constants
# ---------------------------------------------------------------------------

# The only directory that may contain the target capsule.
_ALLOWED_TARGET_PARENT = Path("/home/sanghop/axis/axis-niddhi-lab/pipeline/capsule")

# The only directory that may contain the source.
_ALLOWED_SOURCE_ROOT = Path("/home/sanghop/axis/axis-nana-lab")

# Strings that must NEVER appear in the resolved target path.
_FORBIDDEN_TARGET_SUBSTRINGS: list[str] = [
    "niddhi-production",
    "niddhi-published",
    "bengyond-playground",
]

# File types allowed to be copied.
_ALLOWED_EXTENSIONS = {".json"}
_README_NAME = "README.md"

# Files never copied regardless of other rules.
_NEVER_COPY_PATTERNS: list[str] = [
    "__pycache__",
    ".pyc",
    ".log",
    ".env",
    "private_key",
    "credentials",
    ".pem",
    ".key",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _abort(msg: str) -> int:
    print(f"\n[ABORT] {msg}", file=sys.stderr)
    return 1


def _section(title: str) -> None:
    print(f"\n── {title} {'─' * max(0, 60 - len(title))}")


def _info(msg: str) -> None:
    print(f"  [INFO] {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


# ---------------------------------------------------------------------------
# Path guards
# ---------------------------------------------------------------------------

def _guard_target(target: Path) -> tuple[bool, str]:
    """Return (ok, reason). Must be called before any write."""
    resolved = target.resolve()

    # Forbidden substrings — checked against fully resolved path
    resolved_str = str(resolved)
    for forbidden in _FORBIDDEN_TARGET_SUBSTRINGS:
        if forbidden in resolved_str:
            return False, f"target path contains forbidden substring: '{forbidden}'"

    # Must be under the allowed parent (or equal to it)
    try:
        resolved.relative_to(_ALLOWED_TARGET_PARENT)
    except ValueError:
        return False, (
            f"target path is not under allowed parent:\n"
            f"  allowed: {_ALLOWED_TARGET_PARENT}\n"
            f"  got:     {resolved}"
        )

    return True, ""


def _guard_source(source: Path, fixture_only: bool) -> tuple[bool, str]:
    """Return (ok, reason)."""
    resolved = source.resolve()

    # Must be under axis-nana-lab
    try:
        resolved.relative_to(_ALLOWED_SOURCE_ROOT)
    except ValueError:
        return False, (
            f"source path is not under allowed root:\n"
            f"  allowed: {_ALLOWED_SOURCE_ROOT}\n"
            f"  got:     {resolved}"
        )

    source_str = str(resolved)

    # If source is under fixtures/, --fixture-only is required
    if "/fixtures/" in source_str and not fixture_only:
        return False, (
            "source is under fixtures/ but --fixture-only was not specified. "
            "Re-run with --fixture-only to confirm intent."
        )

    # If source is under outputs/ (future generated artifacts), refuse
    if "/outputs/" in source_str:
        return False, (
            "source is under outputs/ (generated artifacts). "
            "Generated artifact promotion is not enabled yet. "
            "A future --allow-generated flag will be required."
        )

    return True, ""


def _is_never_copy(rel_path: str) -> bool:
    for pattern in _NEVER_COPY_PATTERNS:
        if pattern in rel_path:
            return True
    return False


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def _collect_files(
    source: Path,
    manifest_resolved: list[tuple[str, Path]],
    include_readme: bool,
) -> list[tuple[str, Path]]:
    """
    Build the list of (rel_path_str, abs_path) pairs approved for copying.
    Uses the manifest-validated file list as the canonical source of truth.
    Adds README.md only if --include-readme is passed.
    """
    approved: list[tuple[str, Path]] = []

    for rel, abs_path in manifest_resolved:
        rel_path_str = str(Path(rel).as_posix())

        # Path traversal guard (redundant with validator but defence-in-depth)
        if ".." in Path(rel).parts:
            _warn(f"SKIP (path traversal): {rel_path_str}")
            continue

        # Extension guard
        if Path(rel).suffix.lower() not in _ALLOWED_EXTENSIONS:
            _warn(f"SKIP (non-.json extension): {rel_path_str}")
            continue

        # Never-copy pattern guard
        if _is_never_copy(rel_path_str):
            _warn(f"SKIP (forbidden pattern): {rel_path_str}")
            continue

        approved.append((rel_path_str, abs_path))

    # Always include manifest.json (not always listed in artifacts_by_concept)
    manifest_path = source / "manifest.json"
    if manifest_path.is_file():
        manifest_entry = ("manifest.json", manifest_path)
        if manifest_entry not in approved:
            approved.insert(0, manifest_entry)

    # README.md (optional, only with --include-readme)
    if include_readme:
        readme = source / _README_NAME
        if readme.is_file():
            approved.append((_README_NAME, readme))
            _info("README.md included via --include-readme")
        else:
            _warn("--include-readme specified but README.md not found in source")

    return approved


# ---------------------------------------------------------------------------
# Dry-run report
# ---------------------------------------------------------------------------

def _dry_run_report(
    source: Path,
    target: Path,
    approved: list[tuple[str, Path]],
) -> None:
    _section("DRY-RUN PLAN")
    tmp_dir = target.parent / "nana.tmp"

    print(f"\n  Source    : {source.resolve()}")
    print(f"  Target    : {target.resolve()}")
    print(f"  Temp dir  : {tmp_dir}  [would be created]")
    print(f"  Final dir : {target.resolve()}  [would replace existing if present]")
    print()
    print(f"  Planned files ({len(approved)}):")
    for rel, abs_path in approved:
        size = abs_path.stat().st_size if abs_path.exists() else 0
        print(f"    COPY  {rel}  ({size} bytes)")

    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║  DRY RUN ONLY — no files copied, no directories created     ║")
    print("  ║  build.py NOT run — operator must approve separately.       ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")


# ---------------------------------------------------------------------------
# Atomic copy (--execute mode)
# ---------------------------------------------------------------------------

def _execute_copy(
    source: Path,
    target: Path,
    approved: list[tuple[str, Path]],
) -> int:
    """Perform the atomic tmp → rename copy. Returns 0 on success, 1 on failure."""
    tmp_dir = target.parent / "nana.tmp"

    _section("Atomic copy — execute mode")
    print(f"\n  Source    : {source.resolve()}")
    print(f"  Target    : {target.resolve()}")
    print(f"  Temp dir  : {tmp_dir}")
    print(f"  Files     : {len(approved)}")

    # Step 2 — cleanup leftover tmp
    if tmp_dir.exists():
        _info(f"Removing leftover tmp dir: {tmp_dir}")
        shutil.rmtree(tmp_dir)

    # Step 3 — copy to tmp
    _section("Copying files to tmp dir")
    try:
        for rel, src_path in approved:
            dst = tmp_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src_path.read_bytes())
            print(f"  [COPY] {rel}  ({src_path.stat().st_size} bytes)")
    except Exception as exc:  # noqa: BLE001
        _info(f"Copy failed: {exc} — cleaning up tmp dir")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        return _abort(f"Copy failed: {exc}")

    # Step 4 — re-validate tmp manifest (JSON parse)
    _section("Validating tmp/manifest.json")
    tmp_manifest = tmp_dir / "manifest.json"
    try:
        json.loads(tmp_manifest.read_bytes().decode("utf-8"))
        print("  [PASS] tmp/manifest.json is valid JSON")
    except Exception as exc:  # noqa: BLE001
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        return _abort(f"tmp/manifest.json validation failed: {exc}")

    # Step 5+6 — atomic replace
    _section("Atomic replace")
    if target.exists():
        _info(f"Removing existing target: {target}")
        shutil.rmtree(target)
    tmp_dir.rename(target)
    print(f"  [OK] {tmp_dir.name} → {target.name}")

    # Step 7 — final report
    _section("Promotion complete")
    print(f"\n  ✅  {len(approved)} file(s) copied to {target.resolve()}")
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║  build.py NOT run — operator must approve separately.       ║")
    print("  ║  No API calls made. No providers run.                       ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "AXIS NANA — Capsule promotion script (Wave 2c.4g+). "
            "Use --dry-run to validate and plan. "
            "Use --execute to perform the real atomic copy. "
            "Does NOT run build.py. Does NOT call APIs. Does NOT run providers."
        )
    )
    parser.add_argument(
        "--source",
        metavar="PATH",
        required=True,
        help=(
            "Path to the NANA artifact set to promote. "
            "Must be under axis-nana-lab/. "
            "Fixture sources require --fixture-only."
        ),
    )
    parser.add_argument(
        "--target",
        metavar="PATH",
        required=True,
        help=(
            "Destination capsule path. "
            "Must be under axis-niddhi-lab/pipeline/capsule/. "
            "Must NOT contain niddhi-production, niddhi-published, or bengyond-playground."
        ),
    )
    parser.add_argument(
        "--fixture-only",
        action="store_true",
        default=False,
        help="Required when source is under fixtures/. Confirms fixture intent.",
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate and plan only — no files copied, no directories created.",
    )
    mode_group.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help=(
            "Perform the real atomic copy. "
            "Requires explicit operator approval. "
            "All 13 validation gates run first. Fail-closed."
        ),
    )

    parser.add_argument(
        "--include-readme",
        action="store_true",
        default=False,
        help="Also include README.md from source in the planned/copied set.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    mode_label = "DRY-RUN — no writes" if args.dry_run else "EXECUTE — real atomic copy"

    print("=" * 70)
    print("AXIS NANA — Capsule Promotion — wave2c4g+")
    print(f"Mode : {mode_label}")
    print("=" * 70)

    source = Path(args.source)
    target = Path(args.target)

    # --- Guard: validator available ---
    _section("Validator import")
    if not _VALIDATOR_AVAILABLE:
        return _abort(
            f"validate_promotion.py could not be imported: {_VALIDATOR_IMPORT_ERROR}\n"
            "Ensure scripts/nana/validate_promotion.py exists and is importable."
        )
    print("  [PASS] validate_promotion.py imported successfully")

    # --- Guard: target path (before any write) ---
    _section("Target path guard")
    target_ok, target_reason = _guard_target(target)
    if not target_ok:
        return _abort(f"Target path rejected:\n  {target_reason}")
    print(f"  [PASS] target path is safe: {target.resolve()}")

    # --- Guard: source path ---
    _section("Source path guard")
    source_ok, source_reason = _guard_source(source, args.fixture_only)
    if not source_ok:
        return _abort(f"Source path rejected:\n  {source_reason}")
    print(f"  [PASS] source path is safe: {source.resolve()}")
    if args.fixture_only:
        print("  [INFO] --fixture-only flag confirmed")

    # --- Run all 13 validation gates ---
    _section("Running validate_promotion.py (13 gates)")
    print()
    val_exit = run_validation(source, dry_run=True)
    if val_exit != 0:
        return _abort(
            "Validation failed. Promotion aborted. "
            "Fix the artifact set and re-run."
        )

    # --- Collect approved files ---
    _section("Collecting approved files from manifest")
    _, manifest_path = gate_manifest_exists(source)
    _, manifest_data = gate_manifest_parse(manifest_path)
    _, artifacts_by_concept = gate_artifacts_by_concept(manifest_data)
    _, resolved_files = gate_artifact_files(source, artifacts_by_concept)

    approved = _collect_files(source, resolved_files, args.include_readme)

    if not approved:
        return _abort("No approved files found after collection. Nothing to promote.")

    # --- Dispatch to dry-run or execute ---
    if args.dry_run:
        _dry_run_report(source, target, approved)
        print(f"\n  Summary: {len(approved)} file(s) would be copied")
        print("\n  ✅  DRY-RUN PASSED — artifact set is ready for promotion")
        return 0

    # --execute path
    return _execute_copy(source, target, approved)


if __name__ == "__main__":
    raise SystemExit(main())
