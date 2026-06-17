try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_tok = None
_model = None

# finbert-tone labels: neutral=0, positive=1, negative=2
# We treat positive sentiment as dovish (accommodative) and negative as hawkish (tightening)
LABEL_MAP = {0: "Neutral", 1: "Dovish", 2: "Hawkish"}


def _load():
    global _tok, _model
    if _tok is None:
        _tok = AutoTokenizer.from_pretrained("yiyanghkust/finbert-tone")
        _model = AutoModelForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone")
        _model.eval()


def classify_sentences(text):
    if not _AVAILABLE:
        raise RuntimeError("transformers and torch are required: pip install transformers torch")
    _load()
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
    results = []
    for sent in sentences:
        inputs = _tok(sent, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            logits = _model(**inputs).logits
        probs = torch.softmax(logits, dim=1)[0].tolist()
        label_idx = probs.index(max(probs))
        results.append({
            "sentence": sent,
            "label": LABEL_MAP[label_idx],
            "probs": {"neutral": round(probs[0], 3), "dovish": round(probs[1], 3), "hawkish": round(probs[2], 3)},
        })
    return results


def aggregate_ml_score(sentence_results):
    if not sentence_results:
        return {"label": "Neutral", "score": 0.0}
    hawk = sum(r["probs"]["hawkish"] for r in sentence_results)
    dove = sum(r["probs"]["dovish"] for r in sentence_results)
    total = hawk + dove
    if total == 0:
        return {"label": "Neutral", "score": 0.0}
    net = (hawk - dove) / total
    if net > 0.15:
        label = "Hawkish"
    elif net < -0.15:
        label = "Dovish"
    else:
        label = "Neutral"
    return {"label": label, "score": round(net, 3)}
