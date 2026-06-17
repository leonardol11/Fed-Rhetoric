import argparse
from scraper import fetch_and_cache
from analyzer import score_statement, score_sentences, score_shift

FOMC_URLS = [
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20250618a.htm",
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20250507a.htm",
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20250319a.htm",
]

# Named sequences for validation. Chronological order (oldest first).
SEQUENCES = {
    "hikes-2022": [
        ("2022-03", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20220316a.htm"),
        ("2022-05", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20220504a.htm"),
        ("2022-06", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20220615a.htm"),
        ("2022-07", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20220727a.htm"),
        ("2022-09", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20220921a.htm"),
        ("2022-11", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20221102a.htm"),
        ("2022-12", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20221214a.htm"),
        ("2023-02", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20230201a.htm"),
        ("2023-06", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20230614a.htm"),
    ],
    "pivot-2024": [
        ("2024-01", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240131a.htm"),
        ("2024-03", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240320a.htm"),
        ("2024-05", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240501a.htm"),
        ("2024-07", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240731a.htm"),
        ("2024-09", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm"),
        ("2024-11", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20241107a.htm"),
    ],
}


def analyze_url(url, per_sentence=False):
    print(f"\nFetching: {url}")
    text = fetch_and_cache(url)
    if per_sentence:
        result = score_sentences(text)
        print(f"Verdict (sentence-aggregated): {result['label']} (avg score {result['score']:+.3f})")
        print(f"  Scored sentences: {len(result['sentences'])}")
        for s in result["sentences"][:5]:
            print(f"  [{s['label']:7s} {s['score']:+.2f}] {s['sentence'][:80]}...")
    else:
        result = score_statement(text)
        print(f"Verdict: {result['label']} (net score {result['score']:+.3f})")
        print(f"  Hawkish weight: {result['hawk']} | Dovish weight: {result['dove']}")
        print(f"  Matched terms: {[(m[0], m[1]) for m in result['matched'][:10]]}")
    return result


def diff_timeline(entries):
    """
    entries: list of (date_label, url) tuples, chronological.
    Prints a delta table: date | score | label | delta | shift | divergence flag.
    """
    print(f"\n{'DATE':<10} {'SCORE':>7}  {'LEVEL':<10} {'DELTA':>7}  {'SHIFT':<22} NOTE")
    print("-" * 75)

    texts = [(label, fetch_and_cache(url)) for label, url in entries]
    prior_text = None
    prior_score = None

    for date_label, text in texts:
        r = score_statement(text)
        score = r["score"]

        if prior_text is None:
            delta_str = "   —   "
            shift_str = "—"
            flag = ""
        else:
            shift = score_shift(text, prior_text)
            delta = shift["delta"]
            delta_str = f"{delta:+.3f}"
            shift_str = shift["shift_label"]
            flag = "*** DIVERGENT" if shift["divergent"] else ""

        bar_len = int(abs(score) * 30)
        bar = (">" * bar_len) if score >= 0 else ("<" * bar_len)
        direction = "H" if score >= 0 else "D"
        print(f"{date_label:<10} {score:>+7.3f}  {r['label']:<10} {delta_str}  {shift_str:<22} {flag}")

        prior_text = text
        prior_score = score

    print("-" * 75)


def compare_statements(urls):
    """Absolute timeline only (no diff), used for ad-hoc URL lists."""
    print("\n=== FOMC Sentiment Timeline ===")
    for url in urls:
        r = score_statement(fetch_and_cache(url))
        slug = url.rstrip("/").split("/")[-1].replace(".htm", "").replace("monetary", "")
        bar = "#" * int(abs(r["score"]) * 20)
        direction = "H>" if r["score"] > 0 else "<D"
        print(f"  {slug}  {direction} {bar:20s}  {r['score']:+.3f}  {r['label']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fed Sentiment Analyzer")
    parser.add_argument("--url", help="Single FOMC statement URL to analyze")
    parser.add_argument("--compare", action="store_true", help="Absolute timeline for built-in URL list")
    parser.add_argument("--diff", metavar="SEQUENCE", help=f"Delta timeline for a named sequence: {list(SEQUENCES)}")
    parser.add_argument("--per-sentence", action="store_true", help="Score per sentence then aggregate")
    parser.add_argument("--ml", action="store_true", help="Use FinBERT ML classifier")
    args = parser.parse_args()

    if args.ml:
        from ml_classifier import classify_sentences, aggregate_ml_score
        url = args.url or FOMC_URLS[0]
        text = fetch_and_cache(url)
        results = classify_sentences(text)
        agg = aggregate_ml_score(results)
        print(f"ML Verdict: {agg['label']} (score {agg['score']:+.3f})")
    elif args.diff:
        if args.diff not in SEQUENCES:
            print(f"Unknown sequence '{args.diff}'. Available: {list(SEQUENCES)}")
        else:
            diff_timeline(SEQUENCES[args.diff])
    elif args.compare:
        compare_statements(FOMC_URLS)
    else:
        url = args.url or FOMC_URLS[0]
        analyze_url(url, per_sentence=args.per_sentence)
