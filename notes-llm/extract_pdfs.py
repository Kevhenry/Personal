#!/usr/bin/env python3
"""Extract text from PDFs into Markdown files the indexer can read.

Usage: python extract_pdfs.py OUT_DIR INPUT [INPUT ...]
INPUT is a PDF or a folder (searched recursively), e.g. "Old Evernote" and
D:\\notes-md\\_attachments. Output goes to OUT_DIR/_pdfs/. Needs: pip install pypdf
PDFs with no text layer (scans) are listed in OUT_DIR/_pdfs/_needs_ocr.txt.
Re-runs skip PDFs already done.
"""
import hashlib, json, sys
from pathlib import Path
from pypdf import PdfReader


def pdfs(inputs):
    for p in map(Path, inputs):
        if p.is_dir():
            yield from sorted(p.rglob("*.pdf"))
        elif p.suffix.lower() == ".pdf":
            yield p


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = Path(sys.argv[1]) / "_pdfs"; out.mkdir(parents=True, exist_ok=True)
    stats = {"done": 0, "skipped": 0, "needs_ocr": 0, "failed": 0}
    ocr = open(out / "_needs_ocr.txt", "a", encoding="utf-8")
    for f in pdfs(sys.argv[2:]):
        key = hashlib.sha1(f"{f.name}|{f.stat().st_size}".encode()).hexdigest()[:10]
        dest = out / f"{f.stem[:80]}-{key}.md".replace(" ", "-")
        if dest.exists():
            stats["skipped"] += 1; continue
        try:
            r = PdfReader(str(f))
            pages = [(p.extract_text() or "").strip() for p in r.pages]
        except Exception as e:
            stats["failed"] += 1; print(f"FAILED {f}: {e!r}", flush=True); continue
        text = "\n\n".join(f"<!-- page {i+1} -->\n{t}" for i, t in enumerate(pages) if t)
        if len(text.strip()) < 40:
            ocr.write(str(f) + "\n"); ocr.flush(); stats["needs_ocr"] += 1; continue
        head = ["---", f"title: {json.dumps(f.stem, ensure_ascii=False)}",
                "notebook: PDFs", f"source: {json.dumps(str(f), ensure_ascii=False)}",
                f"pages: {len(pages)}", "---", "", f"# {f.stem}", ""]
        dest.write_text("\n".join(head) + text + "\n", encoding="utf-8")
        stats["done"] += 1
        if stats["done"] % 100 == 0:
            print(f"  ...{stats['done']} pdfs", flush=True)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
