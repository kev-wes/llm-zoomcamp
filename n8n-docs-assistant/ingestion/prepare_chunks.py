"""Chunk the downloaded n8n docs into a JSON knowledge base.

Strategy (see README): one markdown file = one document (doc_id), split by
H2 sections, and sections longer than MAX_CHARS are packed into smaller
chunks paragraph by paragraph. Every chunk gets:

    doc_id    - file path, e.g. "flow-logic/looping"
    chunk_id  - doc_id + running number, e.g. "flow-logic/looping#1"
    title     - document H1 / frontmatter title
    section   - H2 heading the chunk belongs to
    url       - the live page on docs.n8n.io
    text      - chunk text, prefixed with "title / section" for context

Usage:
    python ingestion/prepare_chunks.py
"""

import json
import re
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "docs"
OUT_FILE = Path(__file__).parent.parent / "data" / "chunks.json"

MAX_CHARS = 1500   # split sections longer than this
MIN_CHARS = 200    # drop docs/chunks with less content than this


def clean_markdown(text: str) -> str:
    """Strip mkdocs-material syntax that adds noise to the chunks."""
    # frontmatter
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL)
    # snippet includes: --8<-- "file.md"
    text = re.sub(r'^\s*--8<--.*$', "", text, flags=re.MULTILINE)
    # jinja tags {% ... %} and html comments
    text = re.sub(r"\{%.*?%\}", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # images and standalone html tags
    text = re.sub(r"^!\[.*?\]\(.*?\)\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"</?(figure|figcaption|iframe|video|source)[^>]*>", "", text)
    # inline html anchors (keep the inner text)
    text = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    # admonitions: '!!! note "Title"' -> 'Note: Title'
    text = re.sub(r'^!!!\s+(\w+)(?:\s+"(.*?)")?\s*$',
                  lambda m: f"{m.group(1).capitalize()}: {m.group(2) or ''}".strip(),
                  text, flags=re.MULTILINE)
    # content tabs: '=== "JavaScript"' -> 'JavaScript:'
    text = re.sub(r'^===\s+"(.*?)"\s*$', r"\1:", text, flags=re.MULTILINE)
    # collapse >2 blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_title(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return m.group(1).strip() if m else fallback


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split by H2 headings -> [(section_title, section_text), ...]."""
    parts = re.split(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    sections = []
    intro = re.sub(r"^#\s+.+$", "", parts[0], flags=re.MULTILINE).strip()
    if intro:
        sections.append(("Overview", intro))
    for i in range(1, len(parts), 2):
        sections.append((parts[i].strip(), parts[i + 1].strip()))
    return sections


def pack_paragraphs(text: str, max_chars: int) -> list[str]:
    """Greedily pack paragraphs into chunks of at most max_chars."""
    paragraphs = re.split(r"\n\n+", text)
    chunks, current = [], ""
    for p in paragraphs:
        if current and len(current) + len(p) + 2 > max_chars:
            chunks.append(current.strip())
            current = p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current.strip():
        chunks.append(current.strip())
    return chunks


def main():
    files = sorted(RAW_DIR.rglob("*.md"))
    if not files:
        raise SystemExit("No raw docs found - run download_docs.py first.")

    all_chunks = []
    skipped = 0

    for path in files:
        rel = path.relative_to(RAW_DIR).with_suffix("")
        doc_id = str(rel).removesuffix("/README")  # README.md = section index page
        url = f"https://docs.n8n.io/{doc_id}/"

        text = clean_markdown(path.read_text(encoding="utf-8"))
        if len(text) < MIN_CHARS:
            skipped += 1
            continue

        title = get_title(text, fallback=rel.name.replace("-", " "))
        counter = 0
        for section, body in split_sections(text):
            for piece in pack_paragraphs(body, MAX_CHARS):
                if len(piece) < MIN_CHARS:
                    continue
                all_chunks.append({
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}#{counter}",
                    "title": title,
                    "section": section,
                    "url": url,
                    "text": f"{title} / {section}\n\n{piece}",
                })
                counter += 1

    OUT_FILE.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))
    n_docs = len({c["doc_id"] for c in all_chunks})
    sizes = [len(c["text"]) for c in all_chunks]
    print(f"{len(all_chunks)} chunks from {n_docs} documents "
          f"({skipped} thin files skipped)")
    print(f"chunk size: min={min(sizes)} avg={sum(sizes)//len(sizes)} "
          f"max={max(sizes)} chars")
    print(f"written to {OUT_FILE}")


if __name__ == "__main__":
    main()
