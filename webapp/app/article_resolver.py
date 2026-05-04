"""
article_resolver.py

Place this file in your webapp/app/ folder alongside app_logic.py.

It loads article_lookup.json and provides a function to resolve
a text chunk back to its source article metadata.
"""

import json
import os
from functools import lru_cache

# Path to the lookup JSON — sits next to this file in webapp/app/
_LOOKUP_PATH = os.path.join(os.path.dirname(__file__), "article_lookup.json")


@lru_cache(maxsize=1)
def _load_lookup() -> dict:
    """Load and cache the article lookup table."""
    if not os.path.exists(_LOOKUP_PATH):
        return {}
    with open(_LOOKUP_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_article_for_chunk(document_title: str, chunk_text: str) -> dict:
    """
    Given a document filename (e.g. '1.txt') and the chunk's raw text,
    return the best-matching article metadata dict:
        { title, author, date, source, char_start }
    or an empty dict if no match is found.

    Strategy: find which article's char_start is closest to (but not after)
    the position of the chunk text inside the full document text.
    We approximate chunk position by searching for a distinctive substring
    of the chunk inside the document.
    """
    lookup = _load_lookup()
    articles = lookup.get(document_title, [])

    if not articles:
        return {}

    # Try to find the chunk's position in the source document
    # We use the first 120 chars of the chunk as a search key
    search_key = chunk_text.strip()[:120].strip()

    # Load the source document text to find position
    input_dir = _find_input_dir()
    if not input_dir:
        # Fallback: return first article
        return articles[0]

    doc_path = os.path.join(input_dir, document_title)
    if not os.path.exists(doc_path):
        return articles[0]

    try:
        with open(doc_path, encoding="utf-8") as f:
            doc_text = f.read()
    except Exception:
        return articles[0]

    chunk_pos = doc_text.find(search_key)
    if chunk_pos == -1:
        # Try with a shorter key
        chunk_pos = doc_text.find(search_key[:60].strip())

    if chunk_pos == -1:
        return articles[0]

    # Find the article whose char_start is closest to but <= chunk_pos
    best = articles[0]
    for article in articles:
        if article["char_start"] <= chunk_pos:
            best = article
        else:
            break  # articles are in order, stop once we overshoot

    return best


def _find_input_dir() -> str | None:
    """Try to locate the input/ folder relative to common project layouts."""
    candidates = [
        # When DATA_ROOT is set, documents are under DATA_ROOT/<dataset>/input
        # We don't know the dataset name here, so check env
        os.path.join(os.getenv("DATA_ROOT", ""), "my-dataset", "input"),
        # Relative fallbacks
        "input",
        "../input",
        "../../input",
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            return path
    return None


def format_article_citation(meta: dict) -> str:
    """Return a compact HTML string for display in the citations table."""
    if not meta:
        return ""
    parts = []
    if meta.get("title"):
        parts.append(f"<b>{meta['title']}</b>")
    sub = " · ".join(filter(None, [
        meta.get("author", ""),
        meta.get("date", ""),
        meta.get("source", ""),
    ]))
    if sub:
        parts.append(f"<small>{sub}</small>")
    return "<br/>".join(parts)
