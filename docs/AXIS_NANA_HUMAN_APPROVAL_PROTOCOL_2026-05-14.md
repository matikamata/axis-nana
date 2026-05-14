# AXIS NANA Human Approval Protocol

**Date:** 2026-05-14
**Scope:** Static Preview Only

## Purpose
This document defines the strict manual protocol required to transition a generated offline NANA artifact bundle from `generated_unapproved` to `human_approved_static_preview`.

## Core Principle
AI models generate *candidates*. Only humans grant *display authority*. 
No artifact will ever be promoted into the NIDDHI capsule without explicit human sign-off flipping the `display_allowed` flag to `true`.

## The Approval Script
The script `scripts/nana/approve_artifact.py` requires an operator to supply explicit, required arguments:
- `--operator-id`: Identity of the human performing the review.
- `--approval-note`: Mandatory textual rationale for why the artifact is acceptable.
- `--i-reviewed-answer`: Explicit confirmation that the raw generated answer was reviewed.
- `--i-reviewed-sources`: Explicit confirmation that the cited CSL sources were reviewed.
- `--approve-display`: Final explicit boolean flip.

## What Approval Means
- **IT DOES MEAN:** The artifact is safe, non-hallucinated, and accurate enough to be statically previewed in the Navigator UI.
- **IT DOES NOT MEAN:** The artifact holds any doctrinal authority. The resulting canonical status is strictly `non_canonical`.

## What the Script Does
1. Creates a deep copy of the unapproved bundle into a new output directory.
2. Intercepts the `answer_validation` JSON and injects `display_allowed: true` along with the `approval_metadata`.
3. Upgrades the `artifact_status` to `human_approved_static_preview`.
4. Scans the outgoing payload for forbidden secrets and path traversal before writing to disk.

This ensures Gate 13 of the promotion validator can be passed safely and traceably.
