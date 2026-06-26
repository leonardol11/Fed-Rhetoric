"""Download and bundle ECB 'Monetary policy decisions' statements as .txt files.

Run this whenever ECB_MEETINGS in app.py gains new meetings:

    python fetch_ecb.py

Locally this writes the extracted statement text into data/statements_ecb/,
which is then committed so the deployed (read-only) app can serve it.
"""
from app import ECB_MEETINGS
from scraper import fetch_and_cache


def main():
    for date, url in ECB_MEETINGS:
        if not url:
            continue
        try:
            text = fetch_and_cache(url, source="ecb")
            print(f"cached {date}  ({len(text):>5} chars)")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {date}: {e}")


if __name__ == "__main__":
    main()
