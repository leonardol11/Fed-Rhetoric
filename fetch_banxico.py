"""Download and bundle Banco de México (Banxico) statements as .txt.

Run this whenever BANXICO_MEETINGS in app.py gains new meetings:

    python fetch_banxico.py

Banxico publishes the official English translation of each Monetary Policy
Statement as a PDF; the extracted text is written into data/statements_banxico/,
which is then committed so the deployed (read-only) app can serve it.
"""
from app import BANXICO_MEETINGS
from scraper import fetch_and_cache


def main():
    for date, url in BANXICO_MEETINGS:
        if not url:
            continue
        try:
            text = fetch_and_cache(url, source="banxico")
            print(f"cached {date}  ({len(text):>5} chars)")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {date}: {e}")


if __name__ == "__main__":
    main()
