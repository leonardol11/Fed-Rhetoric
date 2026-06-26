"""Download and bundle Banco Central do Brasil (Copom) statements as .txt.

Run this whenever BCB_MEETINGS in app.py gains new meetings:

    python fetch_bcb.py

Statements come from the BCB's JSON API and are in Portuguese (scored with a
Portuguese lexicon). The extracted text is written into data/statements_bcb/,
which is then committed so the deployed (read-only) app can serve it.
"""
from app import BCB_MEETINGS
from scraper import fetch_and_cache


def main():
    for date, url in BCB_MEETINGS:
        if not url:
            continue
        try:
            text = fetch_and_cache(url, source="bcb")
            print(f"cached {date}  ({len(text):>5} chars)")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {date}: {e}")


if __name__ == "__main__":
    main()
