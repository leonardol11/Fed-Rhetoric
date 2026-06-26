"""Download and bundle Bank of England Monetary Policy Summaries as .txt files.

Run this whenever BOE_MEETINGS in app.py gains new meetings:

    python fetch_boe.py

Locally this writes the extracted summary text into data/statements_boe/,
which is then committed so the deployed (read-only) app can serve it.
"""
from app import BOE_MEETINGS
from scraper import fetch_and_cache


def main():
    for date, url in BOE_MEETINGS:
        if not url:
            continue
        try:
            text = fetch_and_cache(url, source="boe")
            print(f"cached {date}  ({len(text):>5} chars)")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {date}: {e}")


if __name__ == "__main__":
    main()
