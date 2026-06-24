"""Groq second-opinion analyzer.

The lexicon scorer in analyzer.py is fast, deterministic, and offline. This
module adds an independent LLM read served by Groq (https://groq.com): we send
the statement text and ask the model to classify it on the same hawkish/dovish
scale, returning a label, a -1..+1 score, and a one-sentence rationale.

Groq exposes an OpenAI-compatible Chat Completions endpoint, so this is a plain
HTTPS POST with no extra SDK. It is intentionally fail-soft: if no API key is
configured, or the request errors out, callers get a dict with
``available=False`` and an ``error`` string so the web page degrades gracefully
instead of breaking.

Configuration (environment variables):
    GROQ_API_KEY  - required; your Groq API key (from https://console.groq.com)
    GROQ_MODEL    - optional; defaults to "llama-3.3-70b-versatile"
"""
import json
import os
from pathlib import Path

import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def _load_local_env():
    """Lightweight .env loader (no python-dotenv dependency).

    Walks up from this file (project dir, then a few parents) looking for a
    .env, and sets any KEY=VALUE pairs that aren't already in the environment.
    This lets the key live in a .env beside or just above the project (e.g.
    "Dovish Indicator/.env") without exporting it by hand. Real environment
    variables always win, so it's safe on Vercel where GROQ_API_KEY is set in
    the dashboard.
    """
    here = Path(__file__).resolve().parent
    for directory in [here, *here.parents][:4]:
        env_path = directory / ".env"
        if not env_path.is_file():
            continue
        try:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
        except OSError:
            pass
        break


_load_local_env()

# The five labels mirror app.RATE_IMPACT_BANDS so the model's verdict shares the
# same vocabulary as the lexicon verdict shown right next to it.
LABELS = ["Strongly Hawkish", "Hawkish", "Neutral", "Dovish", "Strongly Dovish"]

# Statements are short (Banxico ~6k chars), but cap defensively to keep token
# use and latency bounded for longer central-bank texts (e.g. BoE minutes).
_MAX_CHARS = 12000

_SYSTEM_PROMPT = (
    "You are a senior central-bank watcher on a rates desk. You read a single "
    "monetary policy statement and judge its overall policy tone on a "
    "hawkish-to-dovish scale, where hawkish = leaning toward tighter policy "
    "(higher/held rates) and dovish = leaning toward easier policy (cuts). "
    "Judge the tone of THIS statement on its own terms.\n\n"
    "Respond with ONLY a JSON object (no markdown, no prose) with exactly these "
    "keys:\n"
    '  "label": one of "Strongly Hawkish", "Hawkish", "Neutral", "Dovish", '
    '"Strongly Dovish"\n'
    '  "score": a number from -1 (most dovish) to +1 (most hawkish)\n'
    '  "summary": a single sentence in plain English explaining the call'
)


def api_key():
    return os.environ.get("GROQ_API_KEY")


def is_configured():
    return bool(api_key())


def _unavailable(error):
    return {"available": False, "error": error, "label": None, "score": None, "summary": None}


def analyze_statement(text, bank_name, meeting_label, meeting_noun, model=None, timeout=60):
    """Ask Groq to classify a statement's tone. Never raises: failures come back
    as ``{"available": False, "error": ...}`` so the caller can render a note."""
    key = api_key()
    if not key:
        return _unavailable("GROQ_API_KEY not set")

    model = model or os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    snippet = text[:_MAX_CHARS]
    user_prompt = (
        f"Central bank: {bank_name}\n"
        f"Document: {meeting_noun} dated {meeting_label}\n\n"
        f"Statement text:\n{snippet}"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        # json_object mode is supported across Groq's chat models (the schema
        # itself is described in the system prompt above).
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "stream": False,
    }

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        if resp.status_code >= 400:
            # Groq returns a JSON {"error": {"message": ...}} body; surface that
            # message rather than a raw HTTP status the user can't act on.
            try:
                err = resp.json().get("error")
                msg = err.get("message") if isinstance(err, dict) else (err or resp.text)
            except ValueError:
                msg = resp.text
            return _unavailable(f"Groq error ({resp.status_code}): {msg}")
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
    except requests.exceptions.RequestException as e:
        return _unavailable(f"request failed: {e}")
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return _unavailable(f"unexpected response: {e}")

    label = data.get("label")
    if label not in LABELS:
        label = None
    try:
        score = round(float(data.get("score")), 3)
    except (TypeError, ValueError):
        score = None

    return {
        "available": True,
        "error": None,
        "label": label,
        "score": score,
        "summary": data.get("summary"),
        "model": model,
    }
