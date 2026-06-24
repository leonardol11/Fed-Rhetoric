import json
import os
import re

import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

_SYSTEM = (
    "You are an expert analyst of Banco de México (Banxico) monetary policy statements. "
    "Your job is to assess the hawkish or dovish tone of official Junta de Gobierno statements "
    "(written in Spanish) and produce a precise numerical score.\n\n"
    "Rating scale:\n"
    "  ≥ +0.25  → Strongly Hawkish  (higher-for-longer; hike risk)\n"
    "  +0.02 to +0.25 → Hawkish     (hold bias; cuts pushed out)\n"
    "  -0.02 to +0.02 → Neutral      (data-dependent; no clear signal)\n"
    "  -0.25 to -0.02 → Dovish       (cut odds rising; easing bias)\n"
    "  < -0.25  → Strongly Dovish   (cut bias; faster easing path)\n\n"
    "Factors to weigh: forward guidance language, balance of risks (upside vs. downside "
    "inflation), pace of any rate moves signaled, inflation convergence rhetoric, "
    "and references to restrictive/accommodative stance."
)

_USER = (
    "Analyze the following Banxico statement and respond with ONLY valid JSON "
    "— no extra text, no markdown:\n"
    '{"score": <float from -1.0 to 1.0>, "reasoning": "<2–3 sentences in English>"}\n\n'
    "Statement:\n{text}"
)


def ai_score_statement(text):
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _USER.format(text=text[:7000])},
        ],
        "temperature": 0.1,
        "max_tokens": 300,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"].strip()

    # Strip optional markdown fences the model sometimes adds
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse JSON from model response: {raw!r}")

    data = json.loads(match.group())
    score = round(max(-1.0, min(1.0, float(data["score"]))), 3)
    reasoning = data.get("reasoning", "")
    return {"score": score, "reasoning": reasoning}
