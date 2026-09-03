"""Adds one job posting to your personal JD corpus (corpus/jds/user/).

Usage:
    python scripts/add_jd.py
    python scripts/add_jd.py --title "AI Engineer" --company "Acme" --url "https://..." --file posting.txt

With no --file, paste the posting text and finish with Ctrl-D (Ctrl-Z on Windows).
Run scripts/build_user_corpus.py afterward to fold it into the taxonomy and digest.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "corpus" / "jds" / "user"


def _slug(title: str, company: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", f"{company}-{title}".lower()).strip("-") or "posting"
    slug, n = base, 2
    while (OUT_DIR / f"{slug}.json").exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", help="Job title as posted")
    parser.add_argument("--company", default="", help="Company name")
    parser.add_argument("--url", default="", help="Source URL")
    parser.add_argument("--file", help="Read the posting text from this file instead of stdin")
    args = parser.parse_args()

    title = args.title or input("Title (as posted): ").strip()
    if not title:
        sys.exit("A title is required -- it feeds target-title alignment downstream.")
    company = args.company if args.company or args.file else input("Company (optional): ").strip()
    url = args.url if args.url or args.file else input("Source URL (optional): ").strip()

    if args.file:
        raw_text = Path(args.file).read_text(encoding="utf-8")
    else:
        print("Paste the posting text, then press Ctrl-D (Ctrl-Z on Windows) when done:")
        raw_text = sys.stdin.read()

    raw_text = raw_text.strip()
    if not raw_text:
        sys.exit("No posting text -- nothing to add.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slug(title, company)
    path = OUT_DIR / f"{slug}.json"
    path.write_text(json.dumps({
        "title": title,
        "company": company,
        "source_url": url,
        "date_added": date.today().isoformat(),
        "raw_text": raw_text,
    }, indent=2) + "\n", encoding="utf-8")

    print(f"Saved {path.relative_to(ROOT)}")
    print("Run `python scripts/build_user_corpus.py` to fold it into the taxonomy and digest.")


if __name__ == "__main__":
    main()
