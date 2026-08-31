#!/usr/bin/env python3
"""Validate result provenance and render crawlable, last-known-good HTML.

Staging and publication are deliberately separate modes. Staging requires
confirmed reuse rights and dated accuracy evidence. Publication additionally
requires a separate live-release approval in provenance-policy.json.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


TOOL_DIR = Path(__file__).resolve().parent
FIXTURE_ROOT = (TOOL_DIR / "tests" / "fixtures").resolve()
GENERATED_ROOT = (TOOL_DIR / "generated").resolve()
SYNTHETIC_ROOT = (TOOL_DIR / "tests" / "generated").resolve()
SYNTHETIC_WATERMARK = "SYNTHETIC TEST DATA - NOT FOR PUBLICATION"
MYT = timezone(timedelta(hours=8))
POLICY_SCHEMA_VERSION = 5
VERIFICATION_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{7,127}")

REQUIRED_PROVIDERS = (
    "damacai",
    "magnum",
    "toto",
    "totoextra",
    "damacai13d",
    "singapore",
    "sabah88",
    "sandakan",
    "cashsweep",
    "gd4d",
)
CLASSIC_PROVIDERS = set(REQUIRED_PROVIDERS) - {"totoextra"}
FOUR_DIGIT_PROVIDERS = {
    "damacai", "magnum", "toto", "singapore", "sabah88", "sandakan", "cashsweep", "gd4d"
}
SIX_DIGIT_PROVIDERS = {"damacai13d"}
MAX_RESULT_AGE_DAYS = 7
MAX_CLOCK_SKEW = timedelta(minutes=5)
EXPECTED_CROSS_CHECKS = {
    "4dmoon-feedwest": {"magnum", "damacai", "damacai13d", "toto", "totoextra"}
}
EXPECTED_SOURCE_MAP = {
    "damacai": "4d4d-co",
    "magnum": "4d4d-co",
    "toto": "4d4d-co",
    "totoextra": "4d4d-co",
    "damacai13d": "4d4d-co",
    "singapore": "4d4d-co",
    "sabah88": "4d4d-co",
    "sandakan": "4d4d-co",
    "cashsweep": "4d4d-co",
    "gd4d": "4dmoon-feedwest",
}
PROVIDER_LINKS = {
    "magnum": "/magnum-4d-results/",
    "toto": "/sports-toto-4d-results/",
    "totoextra": "/sports-toto-4d-results/",
    "damacai": "/da-ma-cai-results/",
    "damacai13d": "/da-ma-cai-results/",
    "sabah88": "/sabah-88-4d-results/",
    "sandakan": "/sandakan-stc-4d-results/",
    "cashsweep": "/special-cash-sweep-results/",
}
DISPLAY_NAMES = {
    "damacai": "Da Ma Cai 4D",
    "magnum": "Magnum 4D",
    "toto": "Sports Toto 4D",
    "totoextra": "Sports Toto 5D, 6D and Lotto",
    "damacai13d": "Da Ma Cai 1+3D",
    "singapore": "Singapore Pools 4D",
    "sabah88": "Sabah 88 4D",
    "sandakan": "Sandakan Turf Club 4D",
    "cashsweep": "Special Cash Sweep 4D",
    "gd4d": "Grand Dragon 4D",
}


class ValidationError(ValueError):
    """A fail-closed validation error suitable for CLI output."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"expected a JSON object in {path}")
    return value


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def valid_iso_datetime(value: Any) -> bool:
    return parse_iso_datetime(value) is not None


def parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def provider_result_digest(provider_key: str, provider: Any) -> str:
    """Bind a dated manual check to one exact provider result object."""
    payload = json.dumps(
        {"provider": provider_key, "result": provider},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def result_facts_digest(results: dict[str, Any]) -> str:
    """Hash user-visible result facts without volatile provenance timestamps."""
    payload = json.dumps(
        {
            "drawDate": results.get("drawDate"),
            "drawDay": results.get("drawDay"),
            "recentDates": results.get("recentDates"),
            "providers": results.get("providers"),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def results_snapshot_digest(results: dict[str, Any]) -> str:
    """Bind live approval to every field of one exact validated snapshot."""
    payload = json.dumps(
        results,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def parse_draw_date(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValidationError("draw date is not a string")
    try:
        return datetime.strptime(value, "%d-%m-%Y").replace(tzinfo=MYT)
    except ValueError as exc:
        raise ValidationError(f"invalid draw date {value!r}") from exc


def parse_updated(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValidationError("updated timestamp is not a string")
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M MYT").replace(tzinfo=MYT)
    except ValueError as exc:
        raise ValidationError(f"invalid updated timestamp {value!r}") from exc


def valid_result_token(value: Any, *, minimum_digits: int = 3) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9* -]+", value.strip()):
        return False
    return len(re.sub(r"\D", "", value)) >= minimum_digits


def meaningful_numbers(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and re.search(r"\d", value)]


def validate_weekday(draw_date: datetime, value: Any, *, label: str) -> None:
    expected = draw_date.strftime("%a")
    if value != expected:
        raise ValidationError(f"{label} drawDay {value!r} does not match {expected!r}")


def validate_number_list(provider_key: str, provider: dict[str, Any], field: str, pattern: str) -> None:
    numbers = meaningful_numbers(provider.get(field))
    if len(numbers) != 10:
        raise ValidationError(f"provider {provider_key!r} must contain exactly ten {field} numbers")
    if any(re.fullmatch(pattern, value.strip()) is None for value in numbers):
        raise ValidationError(f"provider {provider_key!r} has malformed {field} numbers")


def validate_totoextra(provider: dict[str, Any]) -> None:
    five_d = provider.get("fiveD")
    five_patterns = (r"\d{5}", r"\d{4}", r"\d{5}", r"\d{3}", r"\d{5}", r"\d{2}")
    if not isinstance(five_d, list) or len(five_d) != len(five_patterns):
        raise ValidationError("totoextra fiveD must contain six values")
    if any(not isinstance(value, str) or re.fullmatch(pattern, value) is None for value, pattern in zip(five_d, five_patterns)):
        raise ValidationError("totoextra fiveD values have invalid formats")

    six_d = provider.get("sixD")
    six_patterns = (
        r"\d{6}", r"\d{5}\*", r"\*\d{5}", r"\d{4}\*{2}", r"\*{2}\d{4}",
        r"\d{3}\*{3}", r"\*{3}\d{3}", r"\d{2}\*{4}", r"\*{4}\d{2}",
    )
    if not isinstance(six_d, list) or len(six_d) != len(six_patterns):
        raise ValidationError("totoextra sixD must contain nine values")
    if any(not isinstance(value, str) or re.fullmatch(pattern, value) is None for value, pattern in zip(six_d, six_patterns)):
        raise ValidationError("totoextra sixD values have invalid formats")

    lotto = provider.get("lotto")
    expected = {
        "Star Toto 6/50": {"maximum": 50, "jackpots": ("Jackpot 1", "Jackpot 2"), "bonus": True},
        "Power Toto 6/55": {"maximum": 55, "jackpots": ("Jackpot",), "bonus": False},
        "Supreme Toto 6/58": {"maximum": 58, "jackpots": ("Jackpot",), "bonus": False},
    }
    if not isinstance(lotto, list) or len(lotto) != len(expected):
        raise ValidationError("totoextra lotto must contain the three reviewed games")
    by_title = {entry.get("title"): entry for entry in lotto if isinstance(entry, dict)}
    if set(by_title) != set(expected):
        raise ValidationError("totoextra lotto titles do not match the reviewed games")
    for title, rules in expected.items():
        entry = by_title[title]
        balls = entry.get("balls")
        if not isinstance(balls, list) or len(balls) != 6 or any(not isinstance(ball, str) or not ball.isdigit() for ball in balls):
            raise ValidationError(f"totoextra {title} must contain six numeric balls")
        ball_values = [int(ball) for ball in balls]
        if len(set(ball_values)) != 6 or any(value < 1 or value > rules["maximum"] for value in ball_values):
            raise ValidationError(f"totoextra {title} balls are duplicated or out of range")
        bonus = entry.get("bonus")
        if rules["bonus"]:
            if not isinstance(bonus, str) or not bonus.isdigit() or not 1 <= int(bonus) <= rules["maximum"]:
                raise ValidationError(f"totoextra {title} bonus is missing or invalid")
        elif bonus not in (None, ""):
            raise ValidationError(f"totoextra {title} has an unexpected bonus")
        jackpots = entry.get("jackpots")
        if not isinstance(jackpots, list) or len(jackpots) != len(rules["jackpots"]):
            raise ValidationError(f"totoextra {title} jackpot fields are incomplete")
        for row, expected_label in zip(jackpots, rules["jackpots"]):
            if not isinstance(row, list) or len(row) != 2 or row[0] != expected_label:
                raise ValidationError(f"totoextra {title} jackpot label is invalid")
            if not isinstance(row[1], str) or re.fullmatch(r"(?:RM\s*)?[\d,]+(?:\.\d{2})?", row[1]) is None:
                raise ValidationError(f"totoextra {title} jackpot amount is invalid")


def validate_results_shape(
    results: dict[str, Any],
    *,
    synthetic: bool = False,
    now: datetime | None = None,
) -> None:
    required_strings = ("drawDate", "drawDay", "updated")
    missing = [key for key in required_strings if not isinstance(results.get(key), str) or not results[key].strip()]
    if missing:
        raise ValidationError("results missing non-empty fields: " + ", ".join(missing))

    providers = results.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ValidationError("results.providers must be a non-empty object")

    if synthetic:
        fixture = results.get("_fixture")
        if not isinstance(fixture, dict) or fixture.get("synthetic") is not True:
            raise ValidationError("synthetic fixture marker is missing")
        if fixture.get("watermark") != SYNTHETIC_WATERMARK:
            raise ValidationError("synthetic fixture watermark is missing or incorrect")
        provider_keys: Iterable[str] = providers.keys()
    else:
        actual = set(providers)
        expected = set(REQUIRED_PROVIDERS)
        if actual != expected:
            missing_keys = sorted(expected - actual)
            extra_keys = sorted(actual - expected)
            raise ValidationError(
                "provider set mismatch; missing=" + ",".join(missing_keys or ["none"])
                + "; extra=" + ",".join(extra_keys or ["none"])
            )
        provider_keys = REQUIRED_PROVIDERS

    reference_now = now or datetime.now(MYT)
    if reference_now.tzinfo is None or reference_now.utcoffset() is None:
        reference_now = reference_now.replace(tzinfo=MYT)
    provider_dates: dict[str, datetime] = {}
    for provider_key in provider_keys:
        provider = providers.get(provider_key)
        if not isinstance(provider, dict):
            raise ValidationError(f"provider {provider_key!r} is not an object")
        if not isinstance(provider.get("name"), str) or not provider["name"].strip():
            raise ValidationError(f"provider {provider_key!r} missing name")

        if synthetic:
            if not all(isinstance(provider.get(field), str) and provider[field] for field in ("first", "second", "third")):
                raise ValidationError("synthetic provider top results are incomplete")
            continue

        provider_date = parse_draw_date(provider.get("drawDate"))
        provider_dates[provider_key] = provider_date
        validate_weekday(provider_date, provider.get("drawDay"), label=f"provider {provider_key!r}")
        if provider_key != "gd4d" and (not isinstance(provider.get("drawNo"), str) or not provider["drawNo"].strip()):
            raise ValidationError(f"provider {provider_key!r} missing drawNo")

        if provider_key == "totoextra":
            validate_totoextra(provider)
            continue

        number_pattern = r"\d{4}" if provider_key in FOUR_DIGIT_PROVIDERS else r"\d{3}\s\d{3}"
        for field in ("first", "second", "third"):
            value = provider.get(field)
            if not isinstance(value, str) or re.fullmatch(number_pattern, value.strip()) is None:
                raise ValidationError(f"provider {provider_key!r} has invalid {field} result")
        validate_number_list(provider_key, provider, "special", number_pattern)
        validate_number_list(provider_key, provider, "consolation", number_pattern)

        if provider_key == "sabah88":
            three_d = provider.get("threeD")
            if not isinstance(three_d, dict) or any(
                not isinstance(three_d.get(field), str) or re.fullmatch(r"\d{3}", three_d[field]) is None
                for field in ("first", "second", "third")
            ):
                raise ValidationError("sabah88 threeD results are incomplete or malformed")
        if provider_key == "damacai13d":
            rows = provider.get("d3rows")
            if not isinstance(rows, list) or len(rows) != 3:
                raise ValidationError("damacai13d d3rows must contain three entries")
            for index, row in enumerate(rows):
                if not isinstance(row, dict) or row.get("value") != provider[("first", "second", "third")[index]]:
                    raise ValidationError("damacai13d d3rows do not match the top results")
                if not isinstance(row.get("zodiac"), str) or re.fullmatch(r"[A-Z ]+", row["zodiac"]) is None:
                    raise ValidationError("damacai13d zodiac value is invalid")
                if not isinstance(row.get("bonus"), str) or re.fullmatch(r"RM\s[\d,]+\.\d{2}", row["bonus"]) is None:
                    raise ValidationError("damacai13d bonus value is invalid")

    if synthetic:
        return

    latest = max(provider_dates.values())
    global_date = parse_draw_date(results["drawDate"])
    validate_weekday(global_date, results.get("drawDay"), label="global")
    if global_date.date() != latest.date():
        raise ValidationError("global drawDate is not the newest provider draw date")
    for provider_key, provider_date in provider_dates.items():
        age = reference_now.date() - provider_date.date()
        if age.days < 0:
            raise ValidationError(f"provider {provider_key!r} has a future draw date")
        if age.days > MAX_RESULT_AGE_DAYS:
            raise ValidationError(f"provider {provider_key!r} result is more than {MAX_RESULT_AGE_DAYS} days old")
    if provider_dates["toto"].date() != provider_dates["totoextra"].date():
        raise ValidationError("Sports Toto 4D and extended result dates do not match")
    if providers["toto"].get("drawNo") != providers["totoextra"].get("drawNo"):
        raise ValidationError("Sports Toto 4D and extended draw numbers do not match")
    if provider_dates["damacai"].date() != provider_dates["damacai13d"].date():
        raise ValidationError("Da Ma Cai 4D and 1+3D result dates do not match")
    if providers["damacai"].get("drawNo") != providers["damacai13d"].get("drawNo"):
        raise ValidationError("Da Ma Cai 4D and 1+3D draw numbers do not match")

    updated = parse_updated(results["updated"])
    if updated > reference_now.astimezone(MYT) + MAX_CLOCK_SKEW:
        raise ValidationError("updated timestamp is in the future")
    if updated.date() < latest.date():
        raise ValidationError("updated timestamp predates the newest provider result")

    recent_dates = results.get("recentDates")
    if not isinstance(recent_dates, list) or not recent_dates:
        raise ValidationError("recentDates must be a non-empty list")
    parsed_recent: list[datetime] = []
    for entry in recent_dates:
        match = re.fullmatch(r"(\d{2}-\d{2}-\d{4}) \(([A-Z][a-z]{2})\)", str(entry))
        if not match:
            raise ValidationError(f"invalid recentDates entry {entry!r}")
        parsed = parse_draw_date(match.group(1))
        validate_weekday(parsed, match.group(2), label="recentDates")
        if parsed.date() > reference_now.date():
            raise ValidationError("recentDates contains a future date")
        parsed_recent.append(parsed)
    if len({entry.date() for entry in parsed_recent}) != len(parsed_recent):
        raise ValidationError("recentDates contains duplicates")
    if parsed_recent != sorted(parsed_recent, reverse=True):
        raise ValidationError("recentDates is not newest first")
    if parsed_recent[0].date() != global_date.date():
        raise ValidationError("recentDates newest entry does not match global drawDate")


def policy_blockers(
    policy: dict[str, Any],
    results: dict[str, Any],
    *,
    mode: str,
    now: datetime | None = None,
) -> list[str]:
    blockers: list[str] = []
    reference_now = now or datetime.now(MYT)
    if reference_now.tzinfo is None or reference_now.utcoffset() is None:
        reference_now = reference_now.replace(tzinfo=MYT)
    if policy.get("schemaVersion") != POLICY_SCHEMA_VERSION:
        blockers.append(f"policy schemaVersion must be {POLICY_SCHEMA_VERSION}")
    rights = policy.get("rightsApproval")
    accuracy = policy.get("accuracyReview")
    release = policy.get("releaseApproval")

    if not isinstance(rights, dict) or rights.get("status") != "confirmed":
        blockers.append("reuse rights are not confirmed")
        rights = {}
    for field in ("approvalId", "evidence"):
        if not isinstance(rights.get(field), str) or not rights[field].strip():
            blockers.append(f"rightsApproval {field} is missing")
    rights_time = parse_iso_datetime(rights.get("confirmedAt"))
    if rights_time is None:
        blockers.append("rightsApproval confirmedAt is missing or invalid")
    elif rights_time > reference_now + MAX_CLOCK_SKEW:
        blockers.append("rightsApproval confirmedAt is in the future")

    if not isinstance(accuracy, dict) or accuracy.get("status") != "cross-checked":
        blockers.append("accuracy review is not cross-checked")
        accuracy = {}
    accuracy_time = parse_iso_datetime(accuracy.get("reviewedAt"))
    if accuracy_time is None:
        blockers.append("accuracyReview reviewedAt is missing or invalid")
    elif accuracy_time > reference_now + MAX_CLOCK_SKEW:
        blockers.append("accuracyReview reviewedAt is in the future")
    if not isinstance(accuracy.get("evidence"), str) or not accuracy["evidence"].strip():
        blockers.append("accuracyReview evidence is missing")

    snapshot_verifications = accuracy.get("snapshotVerifications", {})
    if not isinstance(snapshot_verifications, dict):
        blockers.append("accuracyReview snapshotVerifications is not an object")
        snapshot_verifications = {}
    else:
        for verification_id, verification in snapshot_verifications.items():
            if not isinstance(verification_id, str) or not VERIFICATION_ID_PATTERN.fullmatch(verification_id):
                blockers.append("accuracyReview contains an invalid snapshot verification ID")
            if not isinstance(verification, dict):
                blockers.append(f"snapshot verification {verification_id!r} is not an object")

    sources = policy.get("sources")
    if not isinstance(sources, list) or not sources:
        blockers.append("source policy entries are missing")
        sources = []
    approved_sources: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("sourceId"), str):
            blockers.append("a source policy entry is invalid")
            continue
        source_id = source["sourceId"]
        if source.get("verificationStatus") != "cross-checked":
            blockers.append(f"source {source_id} has not been cross-checked")
        if source.get("reusePermission") != "confirmed":
            blockers.append(f"source {source_id} reuse permission is not confirmed")
        if source.get("stagingAllowed") is not True:
            blockers.append(f"source {source_id} is not approved for staging")
        if mode == "publication" and source.get("publicationAllowed") is not True:
            blockers.append(f"source {source_id} is not approved for live publication")
        approved_sources[source_id] = source

    provenance = results.get("provenance")
    if not isinstance(provenance, dict):
        blockers.append("results provenance object is missing")
        return blockers
    if mode == "publication" and provenance.get("snapshotVerificationIds"):
        blockers.append(
            "results snapshotVerificationIds is not permitted for release-scoped publication"
        )
    if provenance.get("approvalId") != rights.get("approvalId"):
        blockers.append("results approvalId does not match the rights approval")
    verified_at = parse_iso_datetime(provenance.get("verifiedAt"))
    if verified_at is None:
        blockers.append("results verifiedAt is missing or invalid")
    elif verified_at > reference_now + MAX_CLOCK_SKEW:
        blockers.append("results verifiedAt is in the future")
    else:
        try:
            updated_at = parse_updated(results.get("updated"))
        except ValidationError:
            blockers.append("results updated timestamp is invalid")
        else:
            if abs((verified_at.astimezone(MYT) - updated_at).total_seconds()) > 600:
                blockers.append("results verifiedAt does not match the result update window")
    provider_sources = provenance.get("providerSources")
    if not isinstance(provider_sources, dict):
        blockers.append("results providerSources map is missing")
    else:
        if provider_sources != EXPECTED_SOURCE_MAP:
            blockers.append("results providerSources map does not match the reviewed mapping")
        for source_id in provider_sources.values():
            if source_id not in approved_sources:
                blockers.append(f"results map to unknown source {source_id}")

    cross_checks = provenance.get("crossChecks")
    independently_checked: set[str] = set()
    if not isinstance(cross_checks, dict) or set(cross_checks) != set(EXPECTED_CROSS_CHECKS):
        blockers.append("results crossChecks map does not match the reviewed automated sources")
        cross_checks = {}
    else:
        for source_id, expected_providers in EXPECTED_CROSS_CHECKS.items():
            observed = cross_checks.get(source_id)
            if not isinstance(observed, list) or set(observed) != expected_providers or len(observed) != len(expected_providers):
                blockers.append(f"results crossChecks for {source_id} do not match the reviewed provider set")
            else:
                independently_checked.update(expected_providers)

    verification_reference = "results"
    requested_verification_ids = provenance.get("snapshotVerificationIds", [])
    if mode == "publication":
        verification_reference = "releaseApproval"
        requested_verification_ids = (
            release.get("snapshotVerificationIds") if isinstance(release, dict) else None
        )
    if not isinstance(requested_verification_ids, list) or any(
        not isinstance(value, str) or not VERIFICATION_ID_PATTERN.fullmatch(value)
        for value in requested_verification_ids
    ) or (mode == "publication" and not requested_verification_ids):
        blockers.append(f"{verification_reference} snapshotVerificationIds is not a valid ID list")
        requested_verification_ids = []
    elif len(requested_verification_ids) != len(set(requested_verification_ids)):
        blockers.append(f"{verification_reference} snapshotVerificationIds contains duplicates")
        requested_verification_ids = []

    verified_snapshot_providers: set[str] = set()
    latest_verification_time: datetime | None = None
    for verification_id in requested_verification_ids:
        verification = snapshot_verifications.get(verification_id)
        if not isinstance(verification, dict):
            blockers.append(
                f"{verification_reference} references unknown snapshot verification {verification_id}"
            )
            continue
        verification_valid = True
        checked_at = parse_iso_datetime(verification.get("checkedAt"))
        if checked_at is None:
            blockers.append(f"snapshot verification {verification_id} checkedAt is missing or invalid")
            verification_valid = False
        elif checked_at > reference_now + MAX_CLOCK_SKEW:
            blockers.append(f"snapshot verification {verification_id} checkedAt is in the future")
            verification_valid = False
        else:
            if latest_verification_time is None or checked_at > latest_verification_time:
                latest_verification_time = checked_at
            if accuracy_time is not None and checked_at > accuracy_time:
                blockers.append(
                    f"snapshot verification {verification_id} postdates the accuracy review"
                )
                verification_valid = False

        if verification.get("method") not in {
            "provider-owned-plus-independent",
            "operator-family-plus-independent",
            "multi-domain-independent",
        }:
            blockers.append(f"snapshot verification {verification_id} method is invalid")
            verification_valid = False
        if not isinstance(verification.get("evidence"), str) or not verification["evidence"].strip():
            blockers.append(f"snapshot verification {verification_id} evidence is missing")
            verification_valid = False

        verified_providers = verification.get("providers")
        if not isinstance(verified_providers, dict) or not verified_providers:
            blockers.append(f"snapshot verification {verification_id} providers are missing")
            continue
        local_verified: set[str] = set()
        for provider_key, binding in verified_providers.items():
            provider_valid = True
            if provider_key not in REQUIRED_PROVIDERS or not isinstance(binding, dict):
                blockers.append(f"snapshot verification {verification_id} has an invalid provider binding")
                verification_valid = False
                continue
            if provider_key in verified_snapshot_providers or provider_key in local_verified:
                blockers.append(f"snapshot verification provider {provider_key} is duplicated")
                provider_valid = False

            provider = results.get("providers", {}).get(provider_key)
            if not isinstance(provider, dict):
                blockers.append(f"snapshot verification {verification_id} provider result is missing")
                provider_valid = False
            else:
                if binding.get("drawDate") != provider.get("drawDate"):
                    blockers.append(f"snapshot verification {verification_id} draw date does not match {provider_key}")
                    provider_valid = False
                if binding.get("drawNo") != provider.get("drawNo"):
                    blockers.append(f"snapshot verification {verification_id} draw number does not match {provider_key}")
                    provider_valid = False
                if binding.get("resultSha256") != provider_result_digest(provider_key, provider):
                    blockers.append(f"snapshot verification {verification_id} digest does not match {provider_key}")
                    provider_valid = False
                if checked_at is not None:
                    try:
                        provider_draw_date = parse_draw_date(provider.get("drawDate"))
                    except ValidationError:
                        provider_valid = False
                    else:
                        if checked_at.astimezone(MYT).date() < provider_draw_date.date():
                            blockers.append(
                                f"snapshot verification {verification_id} predates the {provider_key} draw"
                            )
                            provider_valid = False

            evidence_sources = binding.get("evidenceSources")
            source_urls: set[str] = set()
            publisher_roles: dict[str, str] = {}
            if not isinstance(evidence_sources, list) or len(evidence_sources) < 2:
                blockers.append(f"snapshot verification {verification_id} needs two evidence sources for {provider_key}")
                provider_valid = False
            else:
                for evidence_source in evidence_sources:
                    if not isinstance(evidence_source, dict):
                        blockers.append(f"snapshot verification {verification_id} has malformed evidence for {provider_key}")
                        provider_valid = False
                        continue
                    source_url = evidence_source.get("url")
                    publisher_id = evidence_source.get("publisherId")
                    source_role = evidence_source.get("role")
                    if not isinstance(source_url, str) or not source_url.strip() or source_url in source_urls:
                        blockers.append(f"snapshot verification {verification_id} has a duplicate or invalid URL for {provider_key}")
                        provider_valid = False
                        continue
                    source_urls.add(source_url)
                    parsed_url = urlparse(source_url)
                    if parsed_url is None or parsed_url.scheme != "https" or not parsed_url.hostname:
                        blockers.append(f"snapshot verification {verification_id} has an invalid source URL for {provider_key}")
                        provider_valid = False
                        continue
                    if (
                        not isinstance(publisher_id, str)
                        or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", publisher_id)
                        or source_role not in {"provider-owned", "operator-family", "independent-publisher"}
                    ):
                        blockers.append(f"snapshot verification {verification_id} has invalid publisher evidence for {provider_key}")
                        provider_valid = False
                        continue
                    prior_role = publisher_roles.get(publisher_id)
                    if prior_role is not None and prior_role != source_role:
                        blockers.append(f"snapshot verification {verification_id} gives conflicting roles to {publisher_id}")
                        provider_valid = False
                        continue
                    publisher_roles[publisher_id] = source_role

                method = verification.get("method")
                roles = set(publisher_roles.values())
                required_roles = {
                    "provider-owned-plus-independent": {"provider-owned", "independent-publisher"},
                    "operator-family-plus-independent": {"operator-family", "independent-publisher"},
                    "multi-domain-independent": {"independent-publisher"},
                }.get(method, set())
                if not required_roles.issubset(roles):
                    blockers.append(f"snapshot verification {verification_id} lacks required source roles for {provider_key}")
                    provider_valid = False
                if method == "multi-domain-independent":
                    independent_publishers = {
                        publisher_id for publisher_id, role in publisher_roles.items()
                        if role == "independent-publisher"
                    }
                    if len(independent_publishers) < 2:
                        blockers.append(f"snapshot verification {verification_id} lacks two independent publishers for {provider_key}")
                        provider_valid = False
                if len(publisher_roles) < 2:
                    blockers.append(f"snapshot verification {verification_id} lacks separate publishers for {provider_key}")
                    provider_valid = False

            if provider_valid:
                local_verified.add(provider_key)

        if verification_valid and len(local_verified) == len(verified_providers):
            verified_snapshot_providers.update(local_verified)

    independently_checked.update(verified_snapshot_providers)

    if mode == "publication":
        missing_publication_checks = set(REQUIRED_PROVIDERS) - independently_checked
        if missing_publication_checks:
            blockers.append(
                "live publication lacks an independent cross-check for: "
                + ", ".join(sorted(missing_publication_checks))
            )
        if not isinstance(release, dict) or release.get("status") != "approved":
            blockers.append("live release approval is not approved")
            release = {}
        for field in ("approvalId", "evidence"):
            if not isinstance(release.get(field), str) or not release[field].strip():
                blockers.append(f"releaseApproval {field} is missing")
        expected_snapshot_digest = release.get("resultsSha256")
        if not isinstance(expected_snapshot_digest, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", expected_snapshot_digest) is None:
            blockers.append("releaseApproval resultsSha256 is missing or invalid")
        elif expected_snapshot_digest != results_snapshot_digest(results):
            blockers.append("releaseApproval resultsSha256 does not match the result snapshot")
        release_time = parse_iso_datetime(release.get("approvedAt"))
        if release_time is None:
            blockers.append("releaseApproval approvedAt is missing or invalid")
        elif release_time > reference_now + MAX_CLOCK_SKEW:
            blockers.append("releaseApproval approvedAt is in the future")
        else:
            try:
                updated_at = parse_updated(results.get("updated"))
            except ValidationError:
                pass
            else:
                snapshot_time = updated_at
                if verified_at is not None:
                    snapshot_time = max(snapshot_time, verified_at.astimezone(MYT))
                if latest_verification_time is not None:
                    snapshot_time = max(snapshot_time, latest_verification_time.astimezone(MYT))
                if accuracy_time is not None:
                    snapshot_time = max(snapshot_time, accuracy_time.astimezone(MYT))
                if release_time.astimezone(MYT) < snapshot_time:
                    blockers.append("releaseApproval predates the result snapshot")
    elif mode == "staging" and isinstance(release, dict) and release.get("status") not in ("staging-only", "approved"):
        blockers.append("releaseApproval does not permit staging")

    return blockers


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def render_number_list(title: str, values: Any) -> str:
    numbers = meaningful_numbers(values)
    if not numbers:
        return ""
    items = "".join(f"<li>{esc(value)}</li>" for value in numbers)
    return f'<div class="number-group"><strong>{esc(title)}</strong><ul class="number-list">{items}</ul></div>'


def render_result_card(provider_key: str, provider: dict[str, Any]) -> str:
    display_name = DISPLAY_NAMES.get(provider_key, provider.get("name", provider_key))
    link = PROVIDER_LINKS.get(provider_key)
    heading = esc(display_name)
    if link:
        heading = f'<a href="{esc(link)}">{heading}</a>'
    draw_no = f' · Draw {esc(provider.get("drawNo"))}' if provider.get("drawNo") else ""
    lines = [
        f'<article class="outerbox result-card" data-provider="{esc(provider_key)}">',
        f'  <h3 class="provider-title">{heading}</h3>',
        f'  <p class="result-meta">Draw date: {esc(provider.get("drawDate"))} ({esc(provider.get("drawDay"))}){draw_no}</p>',
    ]
    if provider_key == "totoextra":
        lines.append('<div class="extended-results">')
        lines.append(f'<p><strong>5D:</strong> {esc(", ".join(provider.get("fiveD", [])))}</p>')
        lines.append(f'<p><strong>6D:</strong> {esc(", ".join(provider.get("sixD", [])))}</p>')
        for lotto in provider.get("lotto", []):
            if not isinstance(lotto, dict):
                continue
            balls = ", ".join(str(value) for value in lotto.get("balls", []))
            bonus = f' · Bonus {esc(lotto.get("bonus"))}' if lotto.get("bonus") else ""
            lines.append(f'<p><strong>{esc(lotto.get("title", "Lotto"))}:</strong> {esc(balls)}{bonus}</p>')
        lines.append('</div>')
    else:
        lines.extend(
            [
                f'  <table class="top-prizes"><caption class="sr-only">Top prizes for {esc(display_name)}</caption><thead><tr><th scope="col">1st prize</th><th scope="col">2nd prize</th><th scope="col">3rd prize</th></tr></thead>',
                f'  <tbody><tr><td>{esc(provider.get("first"))}</td><td>{esc(provider.get("second"))}</td><td>{esc(provider.get("third"))}</td></tr></tbody></table>',
                render_number_list("Special", provider.get("special")),
                render_number_list("Consolation", provider.get("consolation")),
            ]
        )
        if provider_key == "sabah88":
            three_d = provider.get("threeD", {})
            lines.extend(
                [
                    '  <table class="top-prizes"><caption class="sr-only">Sabah 88 3D top prizes</caption><thead><tr><th scope="col">3D 1st prize</th><th scope="col">3D 2nd prize</th><th scope="col">3D 3rd prize</th></tr></thead>',
                    f'  <tbody><tr><td>{esc(three_d.get("first"))}</td><td>{esc(three_d.get("second"))}</td><td>{esc(three_d.get("third"))}</td></tr></tbody></table>',
                ]
            )
    lines.append('</article>')
    return "\n".join(line for line in lines if line)


def render_cards(results: dict[str, Any], provider_keys: Iterable[str]) -> str:
    providers = results["providers"]
    return "\n".join(render_result_card(key, providers[key]) for key in provider_keys)


def render_results_fragment(results: dict[str, Any]) -> str:
    groups = (
        ("Malaysia 4D results", ("gd4d", "damacai", "magnum", "toto", "totoextra", "damacai13d")),
        ("Sabah and Sarawak 4D results", ("sabah88", "sandakan", "cashsweep")),
        ("Additional result reference", ("singapore",)),
    )
    lines = ['<section class="prerendered-results" aria-labelledby="results-heading">']
    lines.append('  <h2 id="results-heading">Latest Malaysia 4D results</h2>')
    lines.append(
        f'  <p class="result-status">Most recent recorded draw date: {esc(results["drawDate"])}. '
        f'Data file updated {esc(results["updated"])}. Verify important results with the relevant provider.</p>'
    )
    rendered_keys: set[str] = set()
    for title, keys in groups:
        available = tuple(key for key in keys if key in results["providers"])
        if not available:
            continue
        rendered_keys.update(available)
        lines.append(f'  <div class="section-bar"><h2>{esc(title)}</h2></div>')
        lines.append('  <div class="row">')
        lines.append(render_cards(results, available))
        lines.append('  </div>')
    extra = tuple(key for key in results["providers"] if key not in rendered_keys)
    if extra:
        lines.append('  <div class="section-bar"><h2>Test result data</h2></div>')
        lines.append('  <div class="row">')
        lines.append(render_cards(results, extra))
        lines.append('  </div>')
    lines.append('</section>')
    return "\n".join(lines) + "\n"


def wrap_preview(fragment: str, *, synthetic: bool) -> str:
    robots = '<meta name="robots" content="noindex,nofollow,noarchive">' if synthetic else ""
    watermark = f'<p role="status">{SYNTHETIC_WATERMARK}</p>' if synthetic else ""
    return (
        '<!doctype html><html lang="en-MY"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'{robots}<title>4D results prerender preview</title></head><body>{watermark}{fragment}</body></html>\n'
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("staging", "publication", "synthetic"))
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--policy", type=Path, default=TOOL_DIR / "provenance-policy.json")
    return parser.parse_args(argv)


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    output = args.output.resolve()
    try:
        results = read_json(args.results.resolve())
        if args.mode == "synthetic":
            if not is_within(args.results.resolve(), FIXTURE_ROOT) or not is_within(output, SYNTHETIC_ROOT):
                raise ValidationError("synthetic input/output must remain in hidden test directories")
            validate_results_shape(results, synthetic=True)
            rendered = wrap_preview(render_results_fragment(results), synthetic=True)
        else:
            if not is_within(output, GENERATED_ROOT):
                raise ValidationError("preview output must remain inside the hidden generated directory")
            validate_results_shape(results)
            policy = read_json(args.policy.resolve())
            blockers = policy_blockers(policy, results, mode=args.mode)
            if blockers:
                raise ValidationError(args.mode.upper() + "_BLOCKED: " + "; ".join(blockers))
            rendered = wrap_preview(render_results_fragment(results), synthetic=False)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"WROTE {output}")
        return 0
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
