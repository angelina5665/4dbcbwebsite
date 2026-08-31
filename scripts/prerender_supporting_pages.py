#!/usr/bin/env python3
"""Keep all current crawlable result pages aligned with results.json."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from html.parser import HTMLParser
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = SCRIPT_ROOT.parent
SEO_TOOL_DIR = DEFAULT_REPO_ROOT / ".github" / "seo-prerender"
sys.path.insert(0, str(SEO_TOOL_DIR))

import build_site as site  # noqa: E402


PROVIDER_CONFIGS = {config["slug"]: config for config in site.PROVIDER_PAGES}
REGION_CONFIGS = {config["slug"]: config for config in site.REGION_PAGES}
PROVIDER_PATHS = tuple(f"{slug}/index.html" for slug in PROVIDER_CONFIGS)
REGION_PATHS = tuple(f"{slug}/index.html" for slug in REGION_CONFIGS)
MALAY_PATH = "ms/index.html"
TARGET_PATHS = PROVIDER_PATHS + REGION_PATHS + (MALAY_PATH,)


class SupportingPageError(RuntimeError):
    """Raised before any file is written when a generation guard fails."""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    return parser.parse_args(argv)


def normalize_eol(value: str) -> str:
    return value.replace("\r\n", "\n")


def result_region_pattern(relative_path: str) -> re.Pattern[str]:
    if relative_path in PROVIDER_PATHS:
        pattern = (
            r'<section class="content-card"><h2>Latest completed result</h2>.*?</section>'
            r'(?=<section class="content-card"><h2>What this result page covers</h2>)'
        )
    elif relative_path in REGION_PATHS:
        pattern = (
            r'<section class="content-card"><h2>Provider comparison</h2>.*?</section>'
            r'(?=<section class="content-card"><h2>What this regional page covers</h2>)'
        )
    elif relative_path == MALAY_PATH:
        pattern = (
            r'<div class="status-box">.*?</div>\s*'
            r'<div class="results-grid">.*?</div>\s*'
            r'(?=<h2>Cara membaca keputusan</h2>)'
        )
    else:
        raise SupportingPageError(f"no generated-region guard for {relative_path}")
    return re.compile(pattern, re.S)


def result_region(document: str, relative_path: str) -> str:
    matches = result_region_pattern(relative_path).findall(normalize_eol(document))
    if len(matches) != 1:
        raise SupportingPageError(f"expected one generated result region in {relative_path}, found {len(matches)}")
    return matches[0]


def mask_result_region(document: str, relative_path: str) -> str:
    pattern = result_region_pattern(relative_path)
    masked, count = pattern.subn("__GENERATED_RESULT_REGION__", normalize_eol(document))
    if count != 1:
        raise SupportingPageError(f"expected one generated result region in {relative_path}, found {count}")
    return masked


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[tuple[str, str, tuple[tuple[str, str], ...]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        stable_attrs = tuple(sorted((name, value or "") for name, value in attrs))
        self.tokens.append(("start", tag, stable_attrs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        stable_attrs = tuple(sorted((name, value or "") for name, value in attrs))
        self.tokens.append(("startend", tag, stable_attrs))

    def handle_endtag(self, tag: str) -> None:
        self.tokens.append(("end", tag, ()))


def result_structure(document: str, relative_path: str) -> list[tuple[str, str, tuple[tuple[str, str], ...]]]:
    parser = StructureParser()
    parser.feed(result_region(document, relative_path))
    parser.close()
    return parser.tokens


def require_unchanged_shell(current: str, generated: str, relative_path: str) -> None:
    if mask_result_region(current, relative_path) != mask_result_region(generated, relative_path):
        raise SupportingPageError(
            f"non-result HTML drift detected in {relative_path}; refusing to alter design or page structure"
        )
    if result_structure(current, relative_path) != result_structure(generated, relative_path):
        raise SupportingPageError(
            f"result-card structure drift detected in {relative_path}; refusing to alter layout"
        )
    if current.count("<h1") != 1 or generated.count("<h1") != 1:
        raise SupportingPageError(f"{relative_path} must keep exactly one H1")
    current_styles = re.findall(r'<link\s+rel="stylesheet"[^>]*>', current)
    generated_styles = re.findall(r'<link\s+rel="stylesheet"[^>]*>', generated)
    if current_styles != generated_styles:
        raise SupportingPageError(f"stylesheet references changed in {relative_path}")


def validate_target_results(results: dict[str, Any]) -> None:
    site.pre.validate_results_shape(results)


def render_targets(results: dict[str, Any]) -> dict[str, str]:
    validate_target_results(results)
    rendered: dict[str, str] = {}
    for slug, config in PROVIDER_CONFIGS.items():
        rendered[f"{slug}/index.html"] = site.provider_page(results, config)
    for slug, config in REGION_CONFIGS.items():
        rendered[f"{slug}/index.html"] = site.region_page(results, config)
    rendered[MALAY_PATH] = site.malay_page(results)
    return rendered


def replace_sitemap_lastmods(sitemap: str, lastmod: str) -> str:
    updated = sitemap
    for relative_path in TARGET_PATHS:
        route = "/" + relative_path.removesuffix("index.html")
        canonical = re.escape(site.BASE_URL + route)
        pattern = re.compile(rf"(<loc>{canonical}</loc>\s*<lastmod>)[^<]+(</lastmod>)")
        updated, count = pattern.subn(rf"\g<1>{lastmod}\g<2>", updated)
        if count != 1:
            raise SupportingPageError(f"expected one sitemap entry for {route}, found {count}")
    return updated


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        results = json.loads((repo / "results.json").read_text(encoding="utf-8"))
        generated = render_targets(results)
        planned: dict[Path, str] = {}
        for relative_path, content in generated.items():
            target = repo / relative_path
            current = target.read_text(encoding="utf-8")
            require_unchanged_shell(current, content, relative_path)
            planned[target] = content

        updated = site.pre.parse_updated(results["updated"])
        sitemap_path = repo / "sitemap.xml"
        sitemap = sitemap_path.read_text(encoding="utf-8")
        planned[sitemap_path] = replace_sitemap_lastmods(sitemap, updated.strftime("%Y-%m-%d"))

        stale = [path for path, content in planned.items() if normalize_eol(path.read_text(encoding="utf-8")) != normalize_eol(content)]
        if args.check:
            if stale:
                print("Generated supporting pages are stale: " + ", ".join(str(path.relative_to(repo)) for path in stale), file=sys.stderr)
                return 1
            print(f"Supporting-page check passed for {len(generated)} pages")
            return 0

        for path in stale:
            atomic_write(path, planned[path])
        if stale:
            print("Updated " + ", ".join(str(path.relative_to(repo)) for path in stale))
        else:
            print("Supporting pages are already current")
        return 0
    except (OSError, ValueError, site.pre.ValidationError, SupportingPageError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
