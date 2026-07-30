"""Tone-timeline helpers: score a meeting series and cache AI reads.

Lexicon scores are computed on the fly from the statement cache (fast).
AI (Groq) scores are persisted under data/ai_scores/ so "Run All" can resume
without re-calling the model for meetings already scored.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import requests

from analyzer import score_statement
from scraper import fetch_and_cache
import groq_client

DATA_DIR = Path(__file__).parent / "data"


def _ai_cache_paths(source: str):
    """Bundled (read) path and writable (write) path for AI score cache."""
    filename = f"{source}.json"
    bundled = DATA_DIR / "ai_scores" / filename
    if os.environ.get("VERCEL"):
        writable = Path(tempfile.gettempdir()) / "fomc-cache" / "ai_scores" / filename
    else:
        writable = DATA_DIR / "ai_scores" / filename
    return bundled, writable


def load_ai_cache(source: str) -> dict:
    bundled, writable = _ai_cache_paths(source)
    for path in (writable, bundled):
        if path.is_file():
            try:
                return json.loads(path.read_text())
            except (OSError, ValueError, json.JSONDecodeError):
                continue
    return {}


def save_ai_cache(source: str, cache: dict) -> None:
    _, writable = _ai_cache_paths(source)
    writable.parent.mkdir(parents=True, exist_ok=True)
    writable.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


def released_meetings(meetings):
    """Yield (date, url) for meetings that have a published statement URL."""
    for date, url in meetings:
        if url:
            yield date, url


def score_lexicon_point(url, source, hawkish, dovish):
    """Score one statement with the lexicon. Returns None if text is empty."""
    try:
        text = fetch_and_cache(url, source=source, fresh=False)
    except requests.exceptions.RequestException:
        return None
    if not text or not text.strip():
        return None
    result = score_statement(text, hawkish, dovish)
    return {
        "score": result["score"],
        "label": result["label"],
        "mode": "lexicon",
        "hawk": result["hawk"],
        "dove": result["dove"],
    }


def score_ai_point(url, source, bank_name, meeting_label, meeting_noun, force=False):
    """Score one statement with Groq, using disk cache unless force=True.

    Returns a dict with score/label/summary, or an error-shaped dict when the
    model is unavailable. Empty/unfetched statements return None.
    """
    cache = load_ai_cache(source)
    if not force and url in cache and cache[url].get("score") is not None:
        entry = dict(cache[url])
        entry["mode"] = "ai"
        entry["cached"] = True
        return entry

    try:
        text = fetch_and_cache(url, source=source, fresh=False)
    except requests.exceptions.RequestException as e:
        return {"available": False, "error": str(e), "score": None, "label": None, "mode": "ai", "cached": False}

    if not text or not text.strip():
        return None

    grok = groq_client.analyze_statement(
        text,
        bank_name=bank_name,
        meeting_label=meeting_label,
        meeting_noun=meeting_noun,
    )
    if not grok.get("available") or grok.get("score") is None:
        return {
            "available": False,
            "error": grok.get("error") or "no score returned",
            "score": None,
            "label": grok.get("label"),
            "summary": grok.get("summary"),
            "mode": "ai",
            "cached": False,
        }

    entry = {
        "available": True,
        "error": None,
        "score": grok["score"],
        "label": grok.get("label"),
        "summary": grok.get("summary"),
        "model": grok.get("model"),
        "mode": "ai",
        "cached": False,
    }
    cache[url] = {
        "score": entry["score"],
        "label": entry["label"],
        "summary": entry["summary"],
        "model": entry.get("model"),
        "available": True,
        "error": None,
    }
    try:
        save_ai_cache(source, cache)
    except OSError:
        pass
    return entry


def build_lexicon_series(meetings, source, hawkish, dovish, date_from=None, date_to=None):
    """Score all released meetings in range with the lexicon (synchronous)."""
    points = []
    for date, url in released_meetings(meetings):
        if date_from and date < date_from:
            continue
        if date_to and date > date_to:
            continue
        scored = score_lexicon_point(url, source, hawkish, dovish)
        if scored is None:
            continue
        points.append({"date": date, "url": url, **scored})
    return points
