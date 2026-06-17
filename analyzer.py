import re
from lexicon import HAWKISH, DOVISH

NEGATORS = {"not", "no", "without", "never", "less", "fewer"}


def tokenize(text):
    return re.findall(r"\b[\w-]+\b", text.lower())


def score_statement(text):
    tokens = tokenize(text)
    hawk, dove = 0.0, 0.0
    matched = []

    for i, tok in enumerate(tokens):
        window = tokens[max(0, i - 3):i]
        negated = any(w in NEGATORS for w in window)

        if tok in HAWKISH:
            weight = HAWKISH[tok]
            if negated:
                dove += weight
            else:
                hawk += weight
            matched.append((tok, "hawk", negated))
        elif tok in DOVISH:
            weight = DOVISH[tok]
            if negated:
                hawk += weight
            else:
                dove += weight
            matched.append((tok, "dove", negated))

    total = hawk + dove
    if total == 0:
        return {"label": "Neutral", "score": 0, "hawk": 0, "dove": 0, "matched": []}

    # Smoothing constant k pulls weak-signal statements toward zero.
    # A lone matched word can't saturate ±1; dense directional text still clears ±0.15.
    k = 8.0
    net = (hawk - dove) / (total + k)

    if net >= 0:
        label = "Hawkish"
    else:
        label = "Dovish"

    return {
        "label": label,
        "score": round(net, 3),
        "hawk": round(hawk, 1),
        "dove": round(dove, 1),
        "matched": matched,
    }


# Shift threshold is separate from absolute threshold: shift magnitudes
# cluster tighter (most meetings tweak wording slightly), so ±0.08 catches
# meaningful tone movement without firing on boilerplate rewording.
SHIFT_THRESHOLD = 0.08


def score_shift(current_text, prior_text):
    current = score_statement(current_text)
    prior = score_statement(prior_text)
    delta = round(current["score"] - prior["score"], 3)

    if delta > SHIFT_THRESHOLD:
        shift_label = "Hawkish shift"
    elif delta < -SHIFT_THRESHOLD:
        shift_label = "Dovish shift"
    else:
        shift_label = "No material change"

    # Divergence: level and shift disagree — the most actionable signal.
    # e.g. still-Hawkish but delta negative = pivot setup
    divergent = (
        (current["label"] == "Hawkish" and shift_label == "Dovish shift") or
        (current["label"] == "Dovish" and shift_label == "Hawkish shift")
    )

    return {
        "current_score": current["score"],
        "prior_score": prior["score"],
        "current_label": current["label"],
        "prior_label": prior["label"],
        "delta": delta,
        "shift_label": shift_label,
        "divergent": divergent,
    }


def score_sentences(text):
    """Score each sentence individually, then aggregate."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]
    sentence_scores = []
    for sent in sentences:
        result = score_statement(sent)
        if result["hawk"] > 0 or result["dove"] > 0:
            sentence_scores.append({"sentence": sent, **result})

    if not sentence_scores:
        return {"label": "Neutral", "score": 0, "sentences": []}

    avg_score = sum(s["score"] for s in sentence_scores) / len(sentence_scores)
    if avg_score >= 0:
        label = "Hawkish"
    else:
        label = "Dovish"

    return {"label": label, "score": round(avg_score, 3), "sentences": sentence_scores}
