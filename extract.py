"""Turn captured HTML snapshots into reviewable text and check evidence spans."""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

from sources import ROOT, load_manifest

SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "template"}
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "div", "tr", "td", "th",
              "br", "section", "article", "dt", "dd", "caption", "summary"}


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)


def html_to_text(path: Path | str) -> str:
    p = _TextParser()
    p.feed(Path(path).read_text(encoding="utf-8", errors="replace"))
    raw = "".join(p.parts).replace("\xa0", " ").replace("’", "'")
    lines = (" ".join(line.split()) for line in raw.split("\n"))
    return "\n".join(line for line in lines if line)


def normalise(s: str) -> str:
    return " ".join(s.replace("\xa0", " ").replace("’", "'").split())


def find_span(text: str, needle: str) -> bool:
    return bool(needle.strip()) and normalise(needle) in normalise(text)


def _snapshot_file(source_id: str) -> Path:
    rec = next((r for r in load_manifest() if r.source_id == source_id), None)
    if rec is None or not rec.snapshot_path:
        raise KeyError(f"No snapshot recorded for {source_id}")
    p = Path(rec.snapshot_path)
    return p if p.is_absolute() else ROOT / p


def snapshot_text(source_id: str) -> str:
    return html_to_text(_snapshot_file(source_id))


def _cli(argv: list[str]) -> int:
    if not argv:
        print("usage: python extract.py <SOURCE_ID> [<SOURCE_ID> ...]")
        return 2
    for sid in argv:
        src = _snapshot_file(sid)
        out = src.with_suffix(".txt")
        text = html_to_text(src)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"{sid}: {len(text.splitlines())} lines -> {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
