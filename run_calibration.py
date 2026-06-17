from scraper import fetch_and_cache
from analyzer import score_statement
from test_cases import TEST_CASES


def run():
    results = []
    print(f"{'ID':<28} {'EXPECTED':<10} {'GOT':<10} {'SCORE':>7}  {'H':>5} {'D':>5}  MATCH")
    print("-" * 80)

    for tc in TEST_CASES:
        text = fetch_and_cache(tc["url"])
        r = score_statement(text)
        correct = r["label"] == tc["label"]
        results.append({**tc, "got": r["label"], "score": r["score"], "hawk": r["hawk"], "dove": r["dove"], "correct": correct})
        mark = "OK" if correct else "XX"
        print(f"{tc['id']:<28} {tc['label']:<10} {r['label']:<10} {r['score']:>+7.3f}  {r['hawk']:>5.1f} {r['dove']:>5.1f}  {mark}")

    print("-" * 80)
    accuracy = sum(1 for r in results if r["correct"]) / len(results)
    print(f"\nAccuracy: {sum(r['correct'] for r in results)}/{len(results)} = {accuracy:.0%}")

    # Separation metrics
    hawk_scores = [r["score"] for r in results if r["label"] == "Hawkish"]
    neutral_scores = [r["score"] for r in results if r["label"] == "Neutral"]
    dove_scores = [r["score"] for r in results if r["label"] == "Dovish"]

    hawk_mean = sum(hawk_scores) / len(hawk_scores) if hawk_scores else 0
    neutral_mean = sum(neutral_scores) / len(neutral_scores) if neutral_scores else 0
    dove_mean = sum(dove_scores) / len(dove_scores) if dove_scores else 0

    hawk_neutral_sep = hawk_mean - neutral_mean
    neutral_dove_sep = neutral_mean - dove_mean

    print(f"\nSeparation metrics (higher = better):")
    print(f"  Hawkish mean score  : {hawk_mean:+.3f}")
    print(f"  Neutral  mean score : {neutral_mean:+.3f}")
    print(f"  Dovish   mean score : {dove_mean:+.3f}")
    print(f"  Hawkish vs Neutral  : {hawk_neutral_sep:+.3f}  {'OK' if hawk_neutral_sep > 0 else 'FAIL'}")
    print(f"  Neutral  vs Dovish  : {neutral_dove_sep:+.3f}  {'OK' if neutral_dove_sep > 0 else 'FAIL'}")


if __name__ == "__main__":
    run()
