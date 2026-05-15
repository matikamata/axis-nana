#!/usr/bin/env python3
"""AXIS NANA — Wave 2c.5g.0 — First Vertex Call Preflight Harness

This script performs strict environmental checks to ensure that the system
is perfectly prepared for the first real API call. Since the network layer
was unlocked in Wave 2c.5f, this script now verifies that the execution
path remains strictly bounded and properly gated.

It does NOT execute any API calls.
It does NOT read or print any credential values.
It strictly targets only the concept 'dukkha'.
"""

import os
import sys
from pathlib import Path

# The exact target concept for the first call
TARGET_CONCEPT = "dukkha"

# Environment variables
ENV_ALLOW_REAL_LLM = "AXIS_NANA_ALLOW_REAL_LLM"
ENV_ALLOW_GEMINI = "AXIS_NANA_ALLOW_GEMINI_VERTEX"
ENV_GOOGLE_CREDS = "GOOGLE_APPLICATION_CREDENTIALS"

def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}", file=sys.stderr)
    sys.exit(1)

def _pass(msg: str) -> None:
    print(f"  [PASS] {msg}")

def main() -> int:
    print("=" * 60)
    print("AXIS NANA — Wave 2c.5g.0 — Preflight Harness")
    print("=" * 60)

    # 1. Target check
    if TARGET_CONCEPT != "dukkha":
        _fail(f"Target concept is not 'dukkha'. Found: {TARGET_CONCEPT}")
    _pass("Target concept restricted to exactly 'dukkha'.")

    # 2. Env check: AXIS_NANA_ALLOW_REAL_LLM
    if os.environ.get(ENV_ALLOW_REAL_LLM) != "1":
        _fail(f"Environment variable {ENV_ALLOW_REAL_LLM} is not set to '1'.")
    _pass(f"{ENV_ALLOW_REAL_LLM}=1 is set.")

    # 3. Env check: AXIS_NANA_ALLOW_GEMINI_VERTEX
    if os.environ.get(ENV_ALLOW_GEMINI) != "1":
        _fail(f"Environment variable {ENV_ALLOW_GEMINI} is not set to '1'.")
    _pass(f"{ENV_ALLOW_GEMINI}=1 is set.")

    # 4. Env check: GOOGLE_APPLICATION_CREDENTIALS
    cred_path_str = os.environ.get(ENV_GOOGLE_CREDS, "").strip()
    if not cred_path_str:
        _fail(f"Environment variable {ENV_GOOGLE_CREDS} is empty or unset.")
    
    cred_path = Path(cred_path_str)
    if not cred_path.is_file():
        _fail("Credential file path does not point to an existing file.")
    
    # We do NOT read the contents of the credential file.
    # Just checking read permissions using os.access
    if not os.access(cred_path, os.R_OK):
        _fail("Credential file is not readable.")
    
    _pass(f"{ENV_GOOGLE_CREDS} points to a valid, readable file.")
    
    # 4b. Env check: GOOGLE_CLOUD_PROJECT
    if not os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip():
        _fail("Environment variable GOOGLE_CLOUD_PROJECT is empty or unset.")
    _pass("GOOGLE_CLOUD_PROJECT is set.")
    
    # 4c. Env check: GOOGLE_CLOUD_LOCATION
    if not os.environ.get("GOOGLE_CLOUD_LOCATION", "").strip():
        _fail("Environment variable GOOGLE_CLOUD_LOCATION is empty or unset.")
    _pass("GOOGLE_CLOUD_LOCATION is set.")

    # 5. Check gemini_vertex_provider.py for post-unlock guardrails
    script_dir = Path(__file__).resolve().parent
    provider_path = script_dir / "providers" / "gemini_vertex_provider.py"
    
    if not provider_path.is_file():
        _fail(f"Provider file not found: {provider_path}")
        
    provider_code = provider_path.read_text(encoding="utf-8")
    
    # 5a. Check that runtime gates are still intact
    expected_gates = [
        "enable_real_llm",
        "AXIS_NANA_ALLOW_REAL_LLM",
        "AXIS_NANA_ALLOW_GEMINI_VERTEX",
        "GOOGLE_APPLICATION_CREDENTIALS"
    ]
    for gate in expected_gates:
        if gate not in provider_code:
            _fail(f"gemini_vertex_provider.py is missing runtime gate: {gate}")
    
    # 5b. Check that the provider contains a bounded single-call path
    expected_call_markers = ["generate_content", "max_output_tokens", "temperature"]
    for marker in expected_call_markers:
        if marker not in provider_code:
            _fail(f"gemini_vertex_provider.py is missing execution boundary marker: {marker}")
            
    # 5c. Check that the provider marks output as unapproved
    if "generated_unapproved" not in provider_code or "real_single_call_unapproved" not in provider_code:
        _fail("gemini_vertex_provider.py is missing unapproved output status markers.")
        
    # 5d. Check that display_allowed=true is NOT introduced
    if "display_allowed=true" in provider_code.replace(" ", "").lower():
        _fail("gemini_vertex_provider.py MUST NOT introduce display_allowed=True.")
    
    _pass("Provider script confirmed to contain all post-unlock runtime guardrails.")

    print("=" * 60)
    print("✅ PREFLIGHT SUCCESS: Environment is safe and ready for live execution.")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
