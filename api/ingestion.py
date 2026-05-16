"""
api/ingestion.py
Parse, chunk, and index Markdown documents into the vector store.
"""
from __future__ import annotations
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple

import frontmatter

from config import get_settings
from logger import logger
from api.vector_store import get_vector_store

settings = get_settings()

CHUNK_SIZE = 512       # characters
CHUNK_OVERLAP = 64


# ── Text utilities ──────────────────────────────────────────────────────────

def _clean_markdown(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_by_heading(text: str) -> List[Tuple[str, str]]:
    """
    Split document into (heading, body) sections by Markdown headings.
    Returns list of (section_title, section_text).
    """
    pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
    parts = pattern.split(text)

    sections: List[Tuple[str, str]] = []
    if not pattern.search(text):
        # No headings – treat whole doc as one section
        return [("Document", text)]

    i = 0
    heading = "Introduction"
    while i < len(parts):
        chunk = parts[i].strip()
        if pattern.match(chunk):
            heading = chunk.lstrip("#").strip()
            i += 1
        else:
            if chunk:
                sections.append((heading, chunk))
            i += 1
    return sections


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Sliding window character-level chunking."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c.strip() for c in chunks if c.strip()]


def _doc_id(source: str, chunk_idx: int) -> str:
    key = f"{source}::{chunk_idx}"
    return hashlib.md5(key.encode()).hexdigest()


# ── Public API ──────────────────────────────────────────────────────────────

def ingest_markdown(content: str, filename: str) -> Dict[str, Any]:
    """
    Parse a Markdown string, chunk it, embed, and store in ChromaDB.
    Returns ingestion summary.
    """
    store = get_vector_store()

    # Remove old chunks for this source
    removed = store.delete_by_source(filename)
    if removed:
        logger.info(f"Replaced {removed} existing chunks for '{filename}'")

    # Parse frontmatter
    post = frontmatter.loads(content)
    meta_base: Dict[str, Any] = dict(post.metadata)
    body = _clean_markdown(post.content)

    # Split into sections then chunks
    sections = _split_by_heading(body)
    all_chunks: List[str] = []
    all_metas: List[Dict[str, Any]] = []
    all_ids: List[str] = []

    idx = 0
    for section_title, section_body in sections:
        for chunk in _chunk_text(section_body):
            meta = {
                **meta_base,
                "source": filename,
                "section": section_title,
                "chunk_index": idx,
            }
            # ChromaDB metadata values must be str/int/float/bool
            meta = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                    for k, v in meta.items()}
            all_chunks.append(chunk)
            all_metas.append(meta)
            all_ids.append(_doc_id(filename, idx))
            idx += 1

    if not all_chunks:
        return {"status": "empty", "filename": filename, "chunks": 0}

    store.upsert(all_chunks, all_metas, all_ids)
    logger.info(f"Ingested '{filename}' → {len(all_chunks)} chunks")

    return {
        "status": "indexed",
        "filename": filename,
        "chunks": len(all_chunks),
        "sections": len(sections),
        "total_chars": len(body),
    }


def ingest_file(path: Path) -> Dict[str, Any]:
    """Ingest a Markdown file from disk."""
    content = path.read_text(encoding="utf-8")
    return ingest_markdown(content, path.name)


def bulk_ingest_directory(directory: Path) -> List[Dict[str, Any]]:
    """Ingest all .md files in a directory."""
    results = []
    for md_file in sorted(directory.glob("**/*.md")):
        try:
            result = ingest_file(md_file)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to ingest {md_file}: {e}")
            results.append({"status": "error", "filename": md_file.name, "error": str(e)})
    return results
