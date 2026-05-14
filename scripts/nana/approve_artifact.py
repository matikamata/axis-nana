#!/usr/bin/env python3
"""AXIS NANA — Human Approval Script (Wave 2c.5b).

Converts an unapproved offline NANA artifact bundle into an approved
static-preview bundle by flipping display_allowed to true after explicit
human validation via CLI flags.

Does NOT mutate the source bundle. Creates an approved copy.
Does NOT call APIs.
Does NOT touch NIDDHI or production.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

FORBIDDEN_PATH_MARKERS = [
    "production", "published", "rescue", "private", "secrets", ".."
]

FORBIDDEN_CONTENT_MARKERS = [
    "GOOGLE_APPLICATION_CREDENTIALS", "private_key", "client_email",
    "github_token", "deepl_key", "wp_password", "/home/", "/media/",
    "BEGIN PRIVATE KEY", "chain.of.thought", "hidden reasoning"
]

def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True)

def _guard_path(p: Path, is_output: bool = False) -> None:
    p_str = str(p.resolve())
    for m in FORBIDDEN_PATH_MARKERS:
        if m in p_str:
            print(f"[ABORT] Path '{p}' contains forbidden marker '{m}'", file=sys.stderr)
            sys.exit(1)
    if not is_output and not p.exists():
        print(f"[ABORT] Source path does not exist: {p}", file=sys.stderr)
        sys.exit(1)

def _scan_content(content: str, rel_path: str) -> None:
    for m in FORBIDDEN_CONTENT_MARKERS:
        if m in content:
            print(f"[ABORT] Forbidden marker '{m}' found in generated content for {rel_path}", file=sys.stderr)
            sys.exit(1)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Unapproved source bundle directory")
    parser.add_argument("--output", required=True, help="New directory for the approved bundle copy")
    parser.add_argument("--operator-id", required=True, help="ID of human operator approving")
    parser.add_argument("--approval-note", required=True, help="Mandatory approval rationale")
    parser.add_argument("--i-reviewed-answer", action="store_true", required=True)
    parser.add_argument("--i-reviewed-sources", action="store_true", required=True)
    parser.add_argument("--approve-display", action="store_true", required=True)

    args = parser.parse_args()

    source_dir = Path(args.source)
    out_dir = Path(args.output)

    _guard_path(source_dir, is_output=False)
    _guard_path(out_dir, is_output=True)

    if out_dir.exists():
        print(f"[ABORT] Output directory already exists: {out_dir}", file=sys.stderr)
        return 1

    manifest_path = source_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"[ABORT] manifest.json not found in {source_dir}", file=sys.stderr)
        return 1

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ABORT] Could not parse manifest.json: {e}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True)
    
    # Track files for marker scanning
    output_files = {}

    abc = manifest.get("artifacts_by_concept", {})
    for concept_id, paths in abc.items():
        for art_type, rel_path in paths.items():
            src_file = source_dir / rel_path
            dst_file = out_dir / rel_path
            
            if not src_file.exists():
                print(f"[ABORT] Missing artifact file: {src_file}", file=sys.stderr)
                shutil.rmtree(out_dir)
                return 1

            try:
                data = json.loads(src_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                print(f"[ABORT] Invalid JSON in {src_file}: {e}", file=sys.stderr)
                shutil.rmtree(out_dir)
                return 1

            # Apply approval mutations
            if art_type == "answer_validation":
                data["display_allowed"] = True
                data["artifact_status"] = "human_approved_static_preview"
                data["approval_metadata"] = {
                    "approved_by": args.operator_id,
                    "approved_at_policy": "operator_supplied_or_omitted",
                    "approval_note": args.approval_note,
                    "approval_scope": "static_preview_only",
                    "canonical_status": "non_canonical",
                    "doctrinal_authority": "none"
                }
            elif art_type == "provider_run":
                data["artifact_status"] = "human_approved_static_preview"
                data["canonical_status"] = "non_canonical"

            dst_file.parent.mkdir(parents=True, exist_ok=True)
            output_content = _canonical_json(data)
            _scan_content(output_content, rel_path)
            output_files[dst_file] = output_content

    # Copy manifest as is
    manifest_content = _canonical_json(manifest)
    _scan_content(manifest_content, "manifest.json")
    output_files[out_dir / "manifest.json"] = manifest_content

    # All checks passed, write to disk
    for path, content in output_files.items():
        path.write_text(content, encoding="utf-8")

    print(f"[OK] Human-approved bundle created at: {out_dir}")
    print(f"     Artifact status: human_approved_static_preview")
    print(f"     Canonical status: non_canonical (static preview only)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
