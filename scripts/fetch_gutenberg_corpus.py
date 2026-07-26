"""Download a small real-prose sample from a Project Gutenberg mirror.

Project Gutenberg's own stated policy (gutenberg.org/policy/robot_access.html)
discourages direct automated access to www.gutenberg.org and asks bulk users
to use a mirror instead -- this fetches from mirror.cs.odu.edu (an official
mirror listed at gutenberg.org/MIRRORS.ALL), not the main site, and paces
requests politely. All texts are pre-1929 or otherwise US public domain;
Project Gutenberg's permission policy states no reuse permission is needed.

This gives real prose and a real structural graph via
app.heuristic_extractor -- it does not give real reader engagement.
app/real_corpus.py attaches the same documented synthetic continue_rate
formula training_corpus.py uses, applied to these real extracted features
instead of fabricated ones. Say so wherever a prediction reaches a screen.

Usage:
    uv run python scripts/fetch_gutenberg_corpus.py --out data/gutenberg_raw
"""

from __future__ import annotations

import argparse
import re
import time
import urllib.request
from pathlib import Path

MIRROR_BASE = "https://mirror.cs.odu.edu/gutenberg"
REQUEST_PACE_SECONDS = 2.0

# ~20 well-known, chapter-structured, US-public-domain novels. Curated for
# having clear "CHAPTER"-style headings so split_into_chapters has something
# real to split on -- not an attempt at genre/era diversity.
BOOK_IDS: tuple[int, ...] = (
    1342,  # Pride and Prejudice
    84,    # Frankenstein
    1661,  # The Adventures of Sherlock Holmes
    11,    # Alice's Adventures in Wonderland
    98,    # A Tale of Two Cities
    345,   # Dracula
    2701,  # Moby Dick
    174,   # The Picture of Dorian Gray
    76,    # Adventures of Huckleberry Finn
    1400,  # Great Expectations
    5200,  # Metamorphosis
    55,    # The Wonderful Wizard of Oz
    2554,  # Crime and Punishment
    219,   # Heart of Darkness
    120,   # Treasure Island
    768,   # Wuthering Heights
    1260,  # Jane Eyre
    43,    # Dr Jekyll and Mr Hyde
    36,    # The War of the Worlds
    514,   # Little Women
)

_START_MARKER = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE)
_END_MARKER = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE)
_CHAPTER_HEADING = re.compile(
    r"^\s*(?:CHAPTER|Chapter)\s+[IVXLCDM\d]+\.?\s*$", re.MULTILINE
)


def gutenberg_path(book_id: int) -> str:
    """Mirror path for a book id, per Project Gutenberg's own directory rule:
    one directory level per digit of the id except the last, "0" for a
    single-digit id."""
    digits = str(book_id)[:-1] or "0"
    dirs = "/".join(digits)
    return f"{dirs}/{book_id}/{book_id}-0.txt"


def strip_gutenberg_boilerplate(text: str) -> str:
    """Drop everything outside the START/END markers Gutenberg wraps every
    text in -- licence terms and metadata are not the novel."""
    start = _START_MARKER.search(text)
    end = _END_MARKER.search(text)
    body = text[start.end() : end.start()] if start and end else text
    return body.strip()


def split_into_chapters(text: str) -> list[str]:
    """Split on 'CHAPTER <roman-or-digit>' headings. Falls back to the whole
    text as one chapter when no heading matches -- still real prose, just
    with one boundary instead of many."""
    pieces = _CHAPTER_HEADING.split(text)
    chapters = [piece.strip() for piece in pieces if piece.strip()]
    return chapters if chapters else [text]


def fetch_book_text(book_id: int, *, mirror_base: str = MIRROR_BASE) -> str:
    url = f"{mirror_base}/{gutenberg_path(book_id)}"
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="replace")


def download_corpus(out_dir: Path, *, book_ids: tuple[int, ...] = BOOK_IDS, pace_seconds: float = REQUEST_PACE_SECONDS) -> list[int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fetched: list[int] = []
    for book_id in book_ids:
        target = out_dir / f"{book_id}.txt"
        if target.exists():
            fetched.append(book_id)
            continue
        raw = fetch_book_text(book_id)
        target.write_text(strip_gutenberg_boilerplate(raw), encoding="utf-8")
        fetched.append(book_id)
        time.sleep(pace_seconds)
    return fetched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/gutenberg_raw")
    args = parser.parse_args()
    fetched = download_corpus(Path(args.out))
    print(f"fetched {len(fetched)} books into {args.out}")


if __name__ == "__main__":
    main()
