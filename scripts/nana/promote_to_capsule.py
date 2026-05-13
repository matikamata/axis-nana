#!/usr/bin/env python3
"""AXIS NANA — Wave 2c.4g — Fixture-Only Capsule Promotion Script.

Promotes a validated NANA static artifact set from axis-nana-lab into
the axis-niddhi-lab capsule input directory.

THIS WAVE: --dry-run is required. No actual files are written.

Future wave (explicit human approval required):
  Omitting --dry-run will execute the atomic copy described in the
  ATOMIC COPY STRATEGY section below.

Usage (dry-run — this wave):
    python3 scripts/nana/promote_to_capsule.py \\
        --source /home/sanghop/axis/axis-nana-lab/fixtures/nana/static_bridge_sample_v1/ \\
        --target /home/sanghop/axis/axis-niddhi-lab/pipeline/capsule/nana/ \\
        --fixture-only \\
        --dry-run \\
        [--include-readme]

Hard constraints enforced at runtime:
  - Target must be under /home/sanghop/axis/axis-niddhi-lab/pipeline/capsule/
  - Target must NOT contain: niddhi-production, niddhi-published, bengyond-playground
  - Source must be under /home/sanghop/axis/axis-nana-lab/
  - Source under fixtures/ requires --fixture-only
  - All 13 validation gates from validate_promotion.py must pass before any copy
  - build.py is never called

Exit codes:
  0 — dry-run passed all checks (this wave)
  1 — any guard, path, or validation failure
"""

from __future__ import annotations

import argparse
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
        gate_source_exists,
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


def _plan(msg: str) -> None:
    print(f"  [PLAN] {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


# ---------------------------------------------------------------------------
# Path guards
# ---------------------------------------------------------------------------

def _guard_target(target: Path) -> tuple[bool, str]:
    """Return (ok, reason). Must be called before any write."""
    resolved = target.resolve()

    # Forbidden substrings
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

    # If source is under fixtures/, --fixture-only is required
    source_str = str(resolved)
    if "/fixtures/" in source_str and not fixture_only:
        return False, (
            "source is under fixtures/ but --fixture-only was not specified. "
            "Re-run with --fixture-only to confirm intent."
        )

    # If source is under outputs/ (future generated artifacts), refuse unless explicitly flagged
    if "/outputs/" in source_str:
        return False, (
            "source is under outputs/ (generated artifacts). "
            "Generated artifact promotion is not enabled in this wave. "
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

    # Also include manifest.json itself (not always listed in artifacts_by_concept)
    manifest_path = source / "manifest.json"
    if manifest_path.is_file():
        manifest_entry = ("manifest.json", manifest_path)
        if manifest_entry not in approved:
            approved.insert(0, manifest_entry)

    # README.md (optional)
    if include_readme:
        readme = source / _README_NAME
        if readme.is_file():
            approved.append((_README_NAME, readme))
            _info(f"README.md included via --include-readme")
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
    print("  ║  No writes to axis-niddhi-lab in this wave.                 ║")
    print("  ║  build.py NOT run — operator must approve separately.       ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")


# ---------------------------------------------------------------------------
# ATOMIC COPY STRATEGY (future wave — not executed here)
# ---------------------------------------------------------------------------
#
# When --dry-run is absent (future human approval required), the script will:
#
# Step 1. Validate source (all 13 gates) → abort if any fails.
# Step 2. tmp_dir = target.parent / "nana.tmp"
#         If tmp_dir exists → rmtree(tmp_dir)  [cleanup leftover]
# Step 3. For each approved file:
#           dst = tmp_dir / rel_path
#           dst.parent.mkdir(parents=True, exist_ok=True)
#           dst.write_bytes(src.read_bytes())
#         If any copy fails → rmtree(tmp_dir), abort.
# Step 4. Re-validate tmp_dir/manifest.json (JSON parse only).
#         If fail → rmtree(tmp_dir), abort.
# Step 5. If target.exists() → shutil.rmtree(target)
# Step 6. tmp_dir.rename(target)
# Step 7. Report: N files copied, target ready.
#         Print: "build.py NOT run — operator must approve separately."
#
# This strategy ensures:
#   - The old capsule/nana/ is only removed after the new copy is 100% complete.
#   - A process kill leaves target intact (tmp_dir is the staging area).
#   - No stale mixed artifacts can be served.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "AXIS NANA Wave 2c.4g — Fixture-only capsule promotion script. "
            "In this wave, --dry-run is required. No files are written. "
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help=(
            "Required in Wave 2c.4g. Validate and plan only — "
            "no files copied, no directories created."
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

    print("=" * 70)
    print("AXIS NANA — Fixture-Only Capsule Promotion — wave2c4g")
    print(f"Mode : {'DRY-RUN — no writes' if args.dry_run else '⚠ LIVE MODE — writes enabled'}")
    print("=" * 70)

    # --- Wave 2c.4g enforcement: --dry-run required ---
    if not args.dry_run:
        return _abort(
            "--dry-run is required in Wave 2c.4g. "
            "Real promotion (without --dry-run) requires explicit approval in a future wave."
        )

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

    # --- Guard: target path ---
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
            "Validation failed. Promotion plan aborted. "
            "Fix the artifact set and re-run."
        )

    # --- Collect approved files ---
    _section("Collecting approved files from manifest")

    # Re-parse manifest to get resolved file list (gates already passed above)
    _, manifest_path = gate_manifest_exists(source)
    _, manifest_data = gate_manifest_parse(manifest_path)
    _, artifacts_by_concept = gate_artifacts_by_concept(manifest_data)
    _, resolved_files = gate_artifact_files(source, artifacts_by_concept)

    approved = _collect_files(source, resolved_files, args.include_readme)

    if not approved:
        return _abort("No approved files found after collection. Nothing to promote.")

    # --- Dry-run report ---
    _dry_run_report(source, target, approved)

    print(f"\n  Summary: {len(approved)} file(s) would be copied")
    print("\n  ✅  DRY-RUN PASSED — artifact set is ready for future fixture promotion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
