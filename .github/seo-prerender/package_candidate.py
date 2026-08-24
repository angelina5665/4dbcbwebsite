#!/usr/bin/env python3
"""Package a changed result snapshot for review without mutating the checkout."""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import build_site
import prerender_results as pre


TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parents[1]
MAX_FILES = 25
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 5 * 1024 * 1024
METADATA_PATHS = {
    "results.json",
    "manifest.json",
    "publication-blockers.json",
    "changes.patch",
    "checksums.sha256",
    "READY",
}


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def derive_staging_policy(policy: dict[str, Any]) -> dict[str, Any]:
    staged = copy.deepcopy(policy)
    staged["releaseApproval"] = {
        "status": "staging-only",
        "approvalId": None,
        "approvedAt": None,
        "resultsSha256": None,
        "evidence": "A candidate artifact requires separate explicit live approval.",
        "reason": "Review only; no publication authorization is recorded.",
    }
    for source in staged.get("sources", []):
        if isinstance(source, dict):
            source["publicationAllowed"] = False
    return staged


def relative_generated_path(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise pre.ValidationError("generated plan contains a path outside the repository") from exc
    return relative.as_posix()


def validate_candidate_boundary(candidate: dict[str, Any], baseline: dict[str, Any]) -> None:
    provenance = candidate.get("provenance")
    if not isinstance(provenance, dict):
        raise pre.ValidationError("candidate provenance is missing")
    if provenance.get("snapshotVerificationIds") not in (None, []):
        raise pre.ValidationError("candidate carries snapshot-specific verification IDs")
    source_hashes = provenance.get("sourcePayloadSha256")
    expected_source_ids = set(pre.EXPECTED_SOURCE_MAP.values())
    if not isinstance(source_hashes, dict) or set(source_hashes) != expected_source_ids:
        raise pre.ValidationError("candidate source payload hashes are missing or incomplete")
    if any(
        not isinstance(value, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None
        for value in source_hashes.values()
    ):
        raise pre.ValidationError("candidate source payload hash is invalid")

    candidate_global = pre.parse_draw_date(candidate.get("drawDate"))
    baseline_global = pre.parse_draw_date(baseline.get("drawDate"))
    if candidate_global.date() < baseline_global.date():
        raise pre.ValidationError("candidate global draw date regresses the baseline")
    candidate_providers = candidate.get("providers", {})
    baseline_providers = baseline.get("providers", {})
    for provider_key in pre.REQUIRED_PROVIDERS:
        candidate_date = pre.parse_draw_date(candidate_providers.get(provider_key, {}).get("drawDate"))
        baseline_date = pre.parse_draw_date(baseline_providers.get(provider_key, {}).get("drawDate"))
        if candidate_date.date() < baseline_date.date():
            raise pre.ValidationError(f"candidate provider {provider_key} draw date regresses the baseline")
    if pre.parse_updated(candidate.get("updated")) < pre.parse_updated(baseline.get("updated")):
        raise pre.ValidationError("candidate update timestamp regresses the baseline")


def exact_patch(candidate: dict[str, Any], planned: dict[Path, str]) -> tuple[str, list[str]]:
    proposed: dict[str, str] = {
        "results.json": json.dumps(candidate, ensure_ascii=False, indent=1) + "\n"
    }
    proposed.update({relative_generated_path(path): content for path, content in planned.items()})
    patch_parts: list[str] = []
    changed_paths: list[str] = []
    for relative, proposed_text in sorted(proposed.items()):
        baseline_path = REPO_ROOT / relative
        baseline_text = baseline_path.read_text(encoding="utf-8") if baseline_path.exists() else ""
        if baseline_text == proposed_text:
            continue
        changed_paths.append(relative)
        patch_parts.extend(
            difflib.unified_diff(
                baseline_text.splitlines(keepends=True),
                proposed_text.splitlines(keepends=True),
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
                lineterm="\n",
            )
        )
    return "".join(patch_parts), changed_paths


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def validate_artifact(root: Path, expected_paths: set[str]) -> dict[str, Any]:
    observed: dict[str, Path] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise pre.ValidationError(f"artifact contains a symlink: {path.relative_to(root)}")
        if path.is_file():
            observed[path.relative_to(root).as_posix()] = path
    if set(observed) != expected_paths:
        missing = sorted(expected_paths - set(observed))
        extra = sorted(set(observed) - expected_paths)
        raise pre.ValidationError(f"artifact allowlist mismatch; missing={missing}; extra={extra}")
    if len(observed) > MAX_FILES:
        raise pre.ValidationError(f"artifact has more than {MAX_FILES} files")
    sizes = {name: path.stat().st_size for name, path in observed.items()}
    oversized = sorted(name for name, size in sizes.items() if size > MAX_FILE_BYTES)
    if oversized:
        raise pre.ValidationError(f"artifact file exceeds {MAX_FILE_BYTES} bytes: {oversized}")
    if sum(sizes.values()) > MAX_TOTAL_BYTES:
        raise pre.ValidationError(f"artifact exceeds {MAX_TOTAL_BYTES} total bytes")

    checksum_lines = (root / "checksums.sha256").read_text(encoding="utf-8").splitlines()
    expected_checksum_names = sorted(expected_paths - {"checksums.sha256"})
    if len(checksum_lines) != len(expected_checksum_names):
        raise pre.ValidationError("checksum manifest entry count is incorrect")
    for line, expected_name in zip(checksum_lines, expected_checksum_names):
        expected_hash, separator, observed_name = line.partition("  ")
        if separator != "  " or observed_name != expected_name:
            raise pre.ValidationError("checksum manifest path ordering is invalid")
        if expected_hash != sha256_bytes(observed[observed_name].read_bytes()):
            raise pre.ValidationError(f"checksum mismatch for {observed_name}")
    return {
        "fileCount": len(observed),
        "totalBytes": sum(sizes.values()),
        "largestFileBytes": max(sizes.values(), default=0),
    }


def package_candidate(
    *,
    candidate_path: Path,
    baseline_path: Path,
    policy_path: Path,
    output_root: Path,
    base_commit: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    candidate_path = candidate_path.resolve()
    baseline_path = baseline_path.resolve()
    policy_path = policy_path.resolve()
    output_root = output_root.resolve()
    if baseline_path != (REPO_ROOT / "results.json").resolve():
        raise pre.ValidationError("baseline must be the checked-in results.json")
    if policy_path != (TOOL_DIR / "provenance-policy.json").resolve():
        raise pre.ValidationError("policy must be the checked-in provenance policy")
    if path_is_within(candidate_path, REPO_ROOT) or path_is_within(output_root, REPO_ROOT):
        raise pre.ValidationError("candidate input and artifact output must be outside the repository")
    if candidate_path.is_symlink() or not candidate_path.is_file():
        raise pre.ValidationError("candidate input must be a regular file")
    if candidate_path.stat().st_size > MAX_FILE_BYTES:
        raise pre.ValidationError("candidate input is too large")
    if output_root.exists():
        raise pre.ValidationError("artifact output must not already exist")
    if not re.fullmatch(r"[0-9a-f]{40}", base_commit):
        raise pre.ValidationError("base commit must be a full 40-character SHA-1")

    candidate = pre.read_json(candidate_path)
    baseline = pre.read_json(baseline_path)
    policy = pre.read_json(policy_path)
    reference_now = now or datetime.now(pre.MYT)
    pre.validate_results_shape(candidate, now=reference_now)
    validate_candidate_boundary(candidate, baseline)
    baseline_digest = pre.result_facts_digest(baseline)
    candidate_digest = pre.result_facts_digest(candidate)
    if baseline_digest == candidate_digest:
        raise pre.ValidationError("candidate has no factual result change")

    staged_policy = derive_staging_policy(policy)
    staging_blockers = pre.policy_blockers(
        staged_policy,
        candidate,
        mode="staging",
        now=reference_now,
    )
    if staging_blockers:
        raise pre.ValidationError("STAGING_BLOCKED: " + "; ".join(staging_blockers))
    publication_blockers = pre.policy_blockers(
        staged_policy,
        candidate,
        mode="publication",
        now=reference_now,
    )
    if not publication_blockers:
        raise pre.ValidationError("candidate unexpectedly passes publication policy")

    planned = build_site.build(candidate, staged_policy, mode="staging", now=reference_now)
    if len(planned) != 14:
        raise pre.ValidationError(f"candidate build produced {len(planned)} files instead of 14")
    generated = {
        f"preview/{relative_generated_path(path)}": content.encode("utf-8")
        for path, content in planned.items()
    }
    patch, changed_paths = exact_patch(candidate, planned)
    if not changed_paths or "results.json" not in changed_paths:
        raise pre.ValidationError("candidate review patch does not contain results.json")

    manifest = {
        "schemaVersion": 1,
        "artifactType": "4dvip88-result-review-candidate",
        "state": "staged-not-approved-for-publication",
        "baseCommit": base_commit,
        "drawDate": candidate.get("drawDate"),
        "candidateVerifiedAt": candidate.get("provenance", {}).get("verifiedAt"),
        "baselineFactsSha256": baseline_digest,
        "candidateFactsSha256": candidate_digest,
        "candidateSnapshotSha256": pre.results_snapshot_digest(candidate),
        "sourcePayloadSha256": candidate["provenance"]["sourcePayloadSha256"],
        "publicationApproved": False,
        "changedPaths": changed_paths,
        "previewPaths": sorted(generated),
    }
    files: dict[str, bytes] = {
        "results.json": (json.dumps(candidate, ensure_ascii=False, indent=1) + "\n").encode("utf-8"),
        "manifest.json": stable_json(manifest).encode("utf-8"),
        "publication-blockers.json": stable_json(
            {
                "schemaVersion": 1,
                "mode": "publication",
                "status": "blocked",
                "blockers": publication_blockers,
            }
        ).encode("utf-8"),
        "changes.patch": patch.encode("utf-8"),
        **generated,
    }
    manifest_sha = sha256_bytes(files["manifest.json"])
    files["READY"] = (
        "STAGED_REVIEW_ARTIFACT\n"
        "publicationApproved=false\n"
        f"manifestSha256=sha256:{manifest_sha}\n"
    ).encode("utf-8")
    expected_without_checksums = METADATA_PATHS - {"checksums.sha256"}
    expected_without_checksums.update(generated)
    if set(files) != expected_without_checksums:
        raise pre.ValidationError("candidate package content does not match the strict allowlist")
    checksums = "".join(
        f"{sha256_bytes(files[name])}  {name}\n"
        for name in sorted(files)
    ).encode("utf-8")
    files["checksums.sha256"] = checksums

    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(
        tempfile.mkdtemp(prefix=output_root.name + ".", suffix=".tmp", dir=output_root.parent)
    )
    try:
        for relative, payload in sorted(files.items()):
            if relative != "READY":
                atomic_write(staging_root / relative, payload)
        atomic_write(staging_root / "READY", files["READY"])
        qa = validate_artifact(staging_root, set(files))
        os.replace(staging_root, output_root)
    except Exception:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise
    return {**manifest, **qa, "artifactRoot": str(output_root)}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    return parser.parse_args(argv)


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        summary = package_candidate(
            candidate_path=args.candidate,
            baseline_path=args.baseline,
            policy_path=args.policy,
            output_root=args.output,
            base_commit=args.base_commit,
        )
        print(stable_json(summary), end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, pre.ValidationError) as exc:
        print(f"CANDIDATE_PACKAGE_BLOCKED: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
