"""Pre-populate the Groq AI-score cache for the tone timeline.

The web app's AI mode scores each meeting with a *live* Groq call. On Groq's
free tier the token budget (~12k tokens/min) is exhausted after ~7 Copom
statements, so a full 36-meeting run returns HTTP 429 for the tail and the
timeline shows "N not yet available". This script scores every released
meeting *offline*, paced under the rate limit and retrying on 429, and writes
the results to ``data/ai_scores/<source>.json``. Once cached, the app serves
those scores instantly (``cached=True``) with no live API calls.

Usage:
    python prepopulate_ai_cache.py                # bcb (Copom), resumable
    python prepopulate_ai_cache.py bcb ecb        # specific sources
    python prepopulate_ai_cache.py all            # every configured source
    python prepopulate_ai_cache.py bcb --force    # re-score even if cached
    python prepopulate_ai_cache.py bcb --delay 8  # tune inter-call pacing (s)

Requires GROQ_API_KEY (read from the environment or the local .env file).
"""
import argparse
import sys
import time

import groq_client
import timeline
from app import SOURCE_CONFIG, label_for


# Groq free tier caps ~12k tokens/min; a Copom statement is ~1.7k tokens, so
# ~7 calls/min is the ceiling. One call every 11s keeps a safe margin. Only
# applied after a *live* call — cache hits are free and never sleep.
DEFAULT_DELAY = 11.0
# On a 429 the per-minute token bucket refills within ~60s; wait a full window
# (plus slack) before retrying the same meeting.
RATELIMIT_BACKOFF = 65.0
MAX_RETRIES = 6


def _is_rate_limited(error: str) -> bool:
    e = (error or "").lower()
    return "429" in e or "rate limit" in e


def _is_transient(error: str) -> bool:
    e = (error or "").lower()
    return _is_rate_limited(error) or "request failed" in e or "timed out" in e


def score_source(source: str, force: bool, delay: float) -> dict:
    cfg = SOURCE_CONFIG.get(source)
    if cfg is None:
        print(f"[{source}] unknown source; skipping", file=sys.stderr)
        return {"ok": 0, "cached": 0, "no_text": 0, "failed": 0}

    released = [(d, u) for d, u in cfg["meetings"] if u]
    stats = {"ok": 0, "cached": 0, "no_text": 0, "failed": 0}
    total = len(released)
    print(f"\n=== {source}: {total} released meetings "
          f"({cfg['bank_name']}) ===")

    for i, (date, url) in enumerate(released, 1):
        label = label_for(date)
        prefix = f"[{source} {i:2d}/{total}] {date} {label}"

        result = None
        for attempt in range(1, MAX_RETRIES + 1):
            result = timeline.score_ai_point(
                url,
                cfg["scraper"],
                bank_name=cfg["bank_name"],
                meeting_label=label,
                meeting_noun=cfg["meeting_noun"],
                force=force,
            )
            if result is None:
                break  # no statement text; nothing to retry
            if result.get("score") is not None:
                break  # success (live or cache hit)
            err = result.get("error") or "no score returned"
            if _is_transient(err) and attempt < MAX_RETRIES:
                wait = RATELIMIT_BACKOFF if _is_rate_limited(err) else 5.0 * attempt
                print(f"{prefix}  ->  retry {attempt}/{MAX_RETRIES} in "
                      f"{wait:.0f}s ({err[:60]})")
                time.sleep(wait)
                continue
            break  # non-transient error, or out of retries

        if result is None:
            stats["no_text"] += 1
            print(f"{prefix}  ->  no statement text (skipped)")
            continue
        if result.get("score") is None:
            stats["failed"] += 1
            print(f"{prefix}  ->  FAILED: {result.get('error')}")
            continue

        if result.get("cached"):
            stats["cached"] += 1
            print(f"{prefix}  ->  cached  score={result['score']:+.3f} "
                  f"{result.get('label')}")
        else:
            stats["ok"] += 1
            print(f"{prefix}  ->  scored  score={result['score']:+.3f} "
                  f"{result.get('label')}")
            # Pace only after a fresh live call to stay under the token limit.
            if i < total:
                time.sleep(delay)

    _, writable = timeline._ai_cache_paths(source)
    print(f"--- {source}: scored={stats['ok']} cached={stats['cached']} "
          f"no_text={stats['no_text']} failed={stats['failed']} "
          f"-> {writable}")
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", default=["bcb"],
                        help="source keys (e.g. bcb ecb) or 'all' (default: bcb)")
    parser.add_argument("--force", action="store_true",
                        help="re-score meetings even if already cached")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help=f"seconds between live calls (default {DEFAULT_DELAY})")
    args = parser.parse_args()

    if not groq_client.is_configured():
        print("GROQ_API_KEY is not set (env or .env). Aborting.", file=sys.stderr)
        return 1

    sources = args.sources or ["bcb"]
    if "all" in sources:
        sources = list(SOURCE_CONFIG.keys())

    grand = {"ok": 0, "cached": 0, "no_text": 0, "failed": 0}
    for source in sources:
        s = score_source(source, force=args.force, delay=args.delay)
        for k in grand:
            grand[k] += s[k]

    print(f"\nTOTAL: scored={grand['ok']} cached={grand['cached']} "
          f"no_text={grand['no_text']} failed={grand['failed']}")
    return 1 if grand["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
