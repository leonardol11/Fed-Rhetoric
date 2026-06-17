import os
import tempfile

import requests
from bs4 import BeautifulSoup
from pathlib import Path

# Statements bundled in the repo (checked into git) are read-only and always
# checked first. On Vercel the project directory itself is read-only, so any
# newly-fetched statement gets written to /tmp instead; locally it falls back
# to the same data/statements dir so behavior is unchanged outside Vercel.
BUNDLED_CACHE_DIR = Path(__file__).parent / "data" / "statements"
WRITABLE_CACHE_DIR = (
    Path(tempfile.gettempdir()) / "fomc-cache" if os.environ.get("VERCEL") else BUNDLED_CACHE_DIR
)


def fetch_statement(url):
    """Fetch FOMC statement from a federalreserve.gov press release URL."""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    article = soup.find("div", {"class": "col-xs-12 col-sm-8 col-md-8"})
    return article.get_text(separator=" ", strip=True) if article else resp.text


def fetch_and_cache(url, cache_dir=None):
    """Fetch a statement, preferring the bundled cache, then a writable cache."""
    slug = url.rstrip("/").split("/")[-1].replace(".htm", "")
    filename = f"{slug}.txt"

    bundled_path = BUNDLED_CACHE_DIR / filename
    if bundled_path.exists():
        return bundled_path.read_text()

    write_dir = Path(cache_dir) if cache_dir else WRITABLE_CACHE_DIR
    write_path = write_dir / filename
    if write_path.exists():
        return write_path.read_text()

    text = fetch_statement(url)
    write_dir.mkdir(parents=True, exist_ok=True)
    write_path.write_text(text)
    return text
