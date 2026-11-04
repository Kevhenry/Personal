#!/usr/bin/env python3
"""Pack many small .md notes into larger files for fast upload/indexing.

Usage: python bundle_notes.py NOTES_DIR [--max-mb 1.5]
Reads NOTES_DIR/<notebook>/*.md and NOTES_DIR/_pdfs/*.md, writes
NOTES_DIR/_bundles/<notebook>-001.md ... Each note keeps its title, notebook and
dates in a header so answers can cite where they came from. Bundles are rebuilt
from scratch each run.
"""
import argparse, re, shutil
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("notes")
    ap.add_argument("--max-mb", type=float, default=1.5)
    a = ap.parse_args()
    root = Path(a.notes); dest = root / "_bundles"
    shutil.rmtree(dest, ignore_errors=True); dest.mkdir()
    limit = int(a.max_mb * 1e6)
    total_notes = total_bundles = 0
    for nb in sorted(d for d in root.iterdir() if d.is_dir() and d.name not in ("_attachments", "_bundles")):
        name = re.sub(r"[^\w\-]+", "_", nb.name.lstrip("_")) or "notes"
        idx, size, fh = 0, 0, None
        for f in sorted(nb.glob("*.md")):
            text = f.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                continue
            chunk = f"\n\n=====NOTE=====\n{text}\n"
            if fh is None or size + len(chunk) > limit:
                if fh: fh.close()
                idx += 1; total_bundles += 1
                fh = open(dest / f"{name}-{idx:03d}.md", "w", encoding="utf-8"); size = 0
            fh.write(chunk); size += len(chunk.encode("utf-8")); total_notes += 1
        if fh: fh.close()
    print(f"{total_notes} notes -> {total_bundles} bundle files in {dest}")


if __name__ == "__main__":
    main()
