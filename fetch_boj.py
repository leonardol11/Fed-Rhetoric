"""Download and bundle Bank of Japan Statements on Monetary Policy as .txt.

Run this whenever BOJ_MEETINGS in app.py gains new meetings:

    python fetch_boj.py

The BoJ publishes its English statement as a PDF, so this requires pypdf
(pip install pypdf). The extracted text is written into data/statements_boj/,
which is then committed so the deployed (read-only) app can serve it.
"""
from app import BOJ_MEETINGS
from scraper import fetch_and_cache


def main():
    for date, url in BOJ_MEETINGS:
        if not url:
            continue
        try:
            text = fetch_and_cache(url, source="boj")
            print(f"cached {date}  ({len(text):>5} chars)")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {date}: {e}")


if __name__ == "__main__":
    main()
