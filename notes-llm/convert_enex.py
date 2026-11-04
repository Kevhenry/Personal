#!/usr/bin/env python3
"""Convert Evernote .enex exports to Markdown (stdlib only, streaming).

Handles multi-GB files: notes are parsed one at a time and attachments are
written straight to disk. Duplicate notes (same title/created/text) across
exports are skipped, so Evernote Export and Old Evernote can be run together.

Usage:
  python convert_enex.py OUT_DIR INPUT [INPUT ...] [--exclude Bank Healthcare]
                         [--attachments none|docs|all]
INPUT is a .enex file or a folder (searched recursively).
"""
import argparse, base64, hashlib, json, re, sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

DOC_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
           ".txt", ".md", ".csv", ".rtf", ".html", ".htm"}


class Enml2Md(HTMLParser):
    """Small ENML -> Markdown converter."""
    def __init__(self, media):
        super().__init__(convert_charrefs=True)
        self.out, self.media, self.href, self.pre = [], media, None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("br",):
            self.out.append("\n")
        elif tag in ("p", "div", "tr", "ul", "ol", "table"):
            self.out.append("\n")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in ("b", "strong"):
            self.out.append("**")
        elif tag in ("i", "em"):
            self.out.append("*")
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag == "a":
            self.href = a.get("href")
            self.out.append("[")
        elif tag == "en-todo":
            self.out.append("[x] " if a.get("checked") == "true" else "[ ] ")
        elif tag == "en-media":
            r = self.media.get(a.get("hash", ""))
            self.out.append(f"\n[attachment: {r}]\n" if r else "\n[attachment]\n")
        elif tag in ("pre", "code"):
            self.pre = True

    def handle_endtag(self, tag):
        if tag in ("p", "div", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol"):
            self.out.append("\n")
        elif tag in ("b", "strong"):
            self.out.append("**")
        elif tag in ("i", "em"):
            self.out.append("*")
        elif tag == "a":
            self.out.append(f"]({self.href})" if self.href else "]")
            self.href = None
        elif tag in ("pre", "code"):
            self.pre = False

    def handle_data(self, data):
        self.out.append(data if self.pre else re.sub(r"[ \t\r\n]+", " ", data))

    def text(self):
        t = "".join(self.out)
        t = re.sub(r"[ \t]+\n", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        return t.strip()


def slug(s, n=60):
    s = re.sub(r"[^\w\- ]+", "", s, flags=re.U).strip().replace(" ", "-")
    return (s or "untitled")[:n]


def safe(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)[:120] or "file"


def find_enex(inputs):
    for p in map(Path, inputs):
        if p.is_dir():
            yield from sorted(p.rglob("*.enex"))
        elif p.suffix.lower() == ".enex":
            yield p


def iter_notes(path, stats):
    """Yield <note> elements. If the XML is malformed, recover note-by-note."""
    try:
        for _, el in ET.iterparse(path, events=("end",)):
            if el.tag == "note":
                yield el
        return
    except ET.ParseError as e:
        stats["recovered_files"] += 1
        print(f"  WARNING: malformed XML in {path.name} ({e}); recovering note by note", flush=True)
    buf = ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        eof = False
        while not eof:
            chunk = f.read(4_000_000)
            eof = not chunk
            buf += chunk
            while True:
                a = buf.find("<note>")
                if a < 0:
                    buf = buf[-8:] if not eof else ""
                    break
                b = buf.find("</note>", a)
                if b < 0:
                    buf = buf[a:]
                    break
                c = buf.find("<note>", a + 6)
                if 0 <= c < b:          # this note never closed: skip just it
                    stats["bad_notes"] += 1
                    buf = buf[c:]
                    continue
                piece, buf = buf[a:b + 7], buf[b + 7:]
                try:
                    yield ET.fromstring(piece)
                except ET.ParseError:
                    stats["bad_notes"] += 1


def convert_file(path, out, seen, mode, stats, seen_fh):
    notebook = path.stem
    nb_dir = out / slug(notebook, 80)
    nb_dir.mkdir(parents=True, exist_ok=True)
    for el in iter_notes(path, stats):
        title = (el.findtext("title") or "Untitled").strip()
        created = el.findtext("created") or ""
        updated = el.findtext("updated") or ""
        tags = [t.text for t in el.findall("tag") if t.text]
        attrs = el.find("note-attributes")
        source_url = (attrs.findtext("source-url") if attrs is not None else "") or ""

        resources = []  # (hash, filename, mime, bytes)
        media = {}
        for r in el.findall("resource"):
            mime = r.findtext("mime") or ""
            ra = r.find("resource-attributes")
            fname = (ra.findtext("file-name") if ra is not None else None) or ""
            data = (r.findtext("data") or "").strip()
            try:
                raw = base64.b64decode(data) if data else b""
            except Exception:
                raw = b""
            if not raw:
                continue
            h = hashlib.md5(raw).hexdigest()
            if not fname:
                ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
                       "application/pdf": ".pdf", "audio/mpeg": ".mp3"}.get(mime, ".bin")
                fname = h[:8] + ext
            media[h] = fname
            resources.append((h, fname, mime, raw))

        parser = Enml2Md(media)
        try:
            parser.feed(el.findtext("content") or "")
        except Exception:
            pass
        body = parser.text()

        key = hashlib.sha1(f"{title}|{created}|{body}".encode()).hexdigest()
        el.clear()
        if key in seen:
            stats["duplicates"] += 1
            continue
        seen.add(key)
        seen_fh.write(key + "\n"); seen_fh.flush()

        att_lines = []
        if resources and mode != "none":
            att_dir = out / "_attachments" / slug(notebook, 80) / key[:10]
            for h, fname, mime, raw in resources:
                ext = Path(fname).suffix.lower()
                if mode == "docs" and ext not in DOC_EXT:
                    continue
                att_dir.mkdir(parents=True, exist_ok=True)
                (att_dir / safe(fname)).write_bytes(raw)
                att_lines.append(f"- {safe(fname)}")
                stats["attachments"] += 1

        front = ["---", f'title: {json.dumps(title, ensure_ascii=False)}',
                 f"notebook: {json.dumps(notebook, ensure_ascii=False)}"]
        if created: front.append(f"created: {created}")
        if updated: front.append(f"updated: {updated}")
        if tags: front.append("tags: " + json.dumps(tags, ensure_ascii=False))
        if source_url: front.append(f"source: {json.dumps(source_url)}")
        front.append("---")
        md = "\n".join(front) + f"\n\n# {title}\n\n{body}\n"
        if att_lines:
            md += "\n## Attachments\n" + "\n".join(att_lines) + "\n"
        (nb_dir / f"{slug(title)}-{key[:8]}.md").write_text(md, encoding="utf-8")
        stats["notes"] += 1
        if stats["notes"] % 500 == 0:
            print(f"  ...{stats['notes']} notes", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out"); ap.add_argument("inputs", nargs="+")
    ap.add_argument("--exclude", nargs="*", default=[], help="notebook names (file stems) to skip")
    ap.add_argument("--attachments", choices=["none", "docs", "all"], default="docs")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    excl = {e.lower() for e in a.exclude}
    stats = {"notes": 0, "duplicates": 0, "attachments": 0, "recovered_files": 0,
             "bad_notes": 0, "failed_files": 0}
    seen_path = out / "_seen.txt"   # lets re-runs skip notes already converted
    seen = set(seen_path.read_text().split()) if seen_path.exists() else set()
    with open(seen_path, "a", encoding="utf-8") as seen_fh:
        for f in find_enex(a.inputs):
            if f.stem.lower() in excl:
                print(f"skip   {f.name}"); continue
            print(f"convert {f}  ({f.stat().st_size/1e6:.0f} MB)", flush=True)
            try:
                convert_file(f, out, seen, a.attachments, stats, seen_fh)
            except Exception as e:
                stats["failed_files"] += 1
                print(f"  ERROR: {f.name}: {e!r} (continuing)", flush=True)
    print(json.dumps(stats))


if __name__ == "__main__":
    sys.exit(main())
