"""Bounded draw-window polling; reuse the existing scraper and all safety gates.

No website markup, source rules or credentials are changed by this orchestrator.
Publishing is allowed only in the existing GitHub Actions environment.
"""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from results_http import fresh_request
MYT = timezone(timedelta(hours=8))
GENERATED = ["results.json", "index.html", "sitemap.xml"] + [
    f"{route}/index.html" for route in (
        "magnum-4d-results", "sports-toto-4d-results", "da-ma-cai-results",
        "sabah-88-4d-results", "special-cash-sweep-results", "sandakan-stc-4d-results",
        "west-malaysia-4d-results", "east-malaysia-4d-results", "ms",
    )
]
REQUIRED = {"damacai", "magnum", "toto", "totoextra", "damacai13d", "singapore",
            "sabah88", "sandakan", "cashsweep", "gd4d", "nine"}


def now_myt():
    return datetime.now(MYT)


def in_window(now):
    # Daily, including special draw dates; each source still controls its actual dates.
    return (18, 45) <= (now.hour, now.minute) < (23, 0)


def run(*args, capture=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    result = subprocess.run(args, cwd=ROOT, env=env, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None, timeout=300)
    return result.stdout.strip() if capture else ""


def git(*args, capture=False):
    # http.sslBackend is a Windows-only switch; Linux git (the Actions robot) aborts every fetch/push with it.
    ssl = ("-c", "http.sslBackend=openssl") if os.name == "nt" else ()
    return run("git", *ssl, *args, capture=capture)


def assert_clean():
    if git("status", "--porcelain", capture=True):
        raise RuntimeError("Dirty checkout: refusing to overwrite or publish unrelated files")


def backup():
    # Outside the checkout, never included in a commit.
    base = Path(os.environ.get("RUNNER_TEMP", str(ROOT.parent / "release-backups")))
    target = base / "my4d-result-backups" / now_myt().strftime("%Y%m%d-%H%M%S-%f-MYT")
    for name in GENERATED:
        source = ROOT / name
        if source.is_file():
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    return target


def require_complete(candidate, baseline):
    cards = candidate.get("providers", {})
    previous = baseline.get("providers", {})
    if not REQUIRED <= cards.keys():
        raise RuntimeError("Incomplete configured provider set")
    for key, old in previous.items():
        card = cards.get(key, {})
        for field in ("first", "second", "third"):
            if field in old:
                width = len(re.sub(r"\s", "", str(old[field])))
                value = re.sub(r"\s", "", str(card.get(field, "")))
                if not value.isdigit() or len(value) != width:
                    raise RuntimeError(f"Incomplete {key} {field}")
        for field in ("special", "consolation", "fiveD", "sixD"):
            if field in old:
                def prizes(values):
                    return [re.sub(r"\s", "", str(v)) for v in values if re.search(r"\d", str(v))]
                expected = prizes(old[field])
                actual = prizes(card.get(field, []))
                if len(actual) != len(expected) or any(
                    len(a) != len(b) or not re.fullmatch(r"[0-9*]+", a)
                    for a, b in zip(actual, expected)
                ):
                    raise RuntimeError(f"Incomplete {key} {field}")
        if key == "totoextra":
            games = card.get("lotto", [])
            if len(games) != len(old.get("lotto", [])) or any(
                len(game.get("balls", [])) != 6 or any(not str(ball).isdigit() for ball in game["balls"])
                for game in games
            ):
                raise RuntimeError("Incomplete Toto lotto balls")


def validate():
    require_complete(json.loads((ROOT / "results.json").read_text(encoding="utf-8")),
                     json.loads(git("show", "HEAD:results.json", capture=True)))
    run("node", "scripts/prerender-home.mjs")
    run(sys.executable, "scripts/prerender_supporting_pages.py")
    run("node", "scripts/prerender-home.mjs", "--check")
    run("node", "--test", *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "scripts").glob("*.test.mjs"))])
    run(sys.executable, "scripts/prerender_supporting_pages.py", "--check")
    run(sys.executable, "-m", "unittest", "discover", "-s", "scripts", "-p", "test_*.py", "-v")
    git("-c", "core.whitespace=cr-at-eol", "diff", "--check")


def publish():
    changed = set(git("diff", "--name-only", capture=True).splitlines())
    staged = git("diff", "--cached", "--name-only", capture=True)
    untracked = git("ls-files", "--others", "--exclude-standard", capture=True)
    if changed - set(GENERATED) or staged or untracked:
        raise RuntimeError("Unexpected files: refusing result publication")
    if not changed:
        return
    git("config", "user.name", "4D VIP results bot")
    git("config", "user.email", "actions@github.com")
    git("add", "--", *GENERATED)
    snapshot = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    git("commit", "-m", "Update verified results " + snapshot["drawDate"])
    # Never force or rebase: competing changes cause a safe failure.
    git("push", "origin", "HEAD:main")
    git("fetch", "origin", "main")
    if git("rev-parse", "HEAD", capture=True) != git("rev-parse", "origin/main", capture=True):
        raise RuntimeError("Remote-main verification failed")
    verify_live(snapshot)


def read_public(url):
    with urllib.request.urlopen(fresh_request(url, "my4d-release-verifier/1.0"), timeout=20) as response:
        return response.read().decode("utf-8", "replace")


def verify_live(snapshot):
    deadline = time.monotonic() + 240
    while True:
        try:
            current = json.loads(read_public("https://my4d.co/results.json"))
            html = read_public("https://my4d.co/")
            marker = 'data-results-updated="' + snapshot["updated"] + '"'
            if current == snapshot and marker in html and all(
                'id="card-' + key + '"' in html for key in REQUIRED
            ):
                print("Live JSON and raw homepage verified for " + snapshot["drawDate"], flush=True)
                return
        except Exception:
            # Retry transient deploy/cache/network failures; never claim success from a push alone.
            pass
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("Result pushed, but live JSON/raw homepage deployment was not verified")
        time.sleep(min(15, remaining))


def all_current(now):
    snapshot = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    cards = snapshot.get("providers", {})
    today = now.strftime("%d-%m-%Y")
    return snapshot.get("drawDate") == today and REQUIRED <= cards.keys() and all(
        cards[key].get("drawDate") == today for key in REQUIRED)


def cycle(publishing):
    assert_clean()
    if publishing:
        git("fetch", "origin", "main")
        git("merge", "--ff-only", "origin/main")
    previous = (ROOT / "results.json").read_bytes()
    saved = backup()
    try:
        run(sys.executable, "scrape.py")
        if (ROOT / "results.json").read_bytes() == previous:
            return False
        validate()
        if publishing:
            publish()
        return True
    except Exception:
        # Preserve the exact last verified generated files after a failed gate.
        # A failed push may leave a local commit but cannot force remote changes.
        for name in GENERATED:
            if (saved / name).is_file():
                shutil.copy2(saved / name, ROOT / name)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.publish and os.environ.get("GITHUB_ACTIONS") != "true":
        parser.error("--publish requires the existing GitHub Actions runner")
    # Maximum 20 minutes per job. Active polling survives missed later cron ticks.
    deadline = time.monotonic() + 20 * 60
    while True:
        cycle(args.publish)
        now = now_myt()
        if args.once or not args.publish or not in_window(now) or all_current(now):
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(60, remaining))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
