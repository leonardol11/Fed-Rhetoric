import os
import re
import tempfile

import requests
from bs4 import BeautifulSoup
from pathlib import Path

# Statements bundled in the repo (checked into git) are read-only and always
# checked first. On Vercel the project directory itself is read-only, so any
# newly-fetched statement gets written to /tmp instead; locally it falls back
# to the same data dir so behavior is unchanged outside Vercel.
DATA_DIR = Path(__file__).parent / "data"


def _extract_fed(resp):
    soup = BeautifulSoup(resp.text, "html.parser")
    article = soup.find("div", {"class": "col-xs-12 col-sm-8 col-md-8"})
    return article.get_text(separator=" ", strip=True) if article else resp.text


def _extract_ecb(resp):
    # ECB press releases keep the full statement inside <main>; there is no
    # stable inner class to target, so we take the whole main column.
    soup = BeautifulSoup(resp.text, "html.parser")
    main = soup.find("main")
    return main.get_text(separator=" ", strip=True) if main else resp.text


def _extract_boe(resp):
    # BoE pages bundle the Monetary Policy Summary followed by the full MPC
    # minutes; we keep just the summary (the analog of the FOMC statement).
    soup = BeautifulSoup(resp.text, "html.parser")
    el = soup.find("div", {"id": "output"}) or soup.find("main")
    text = el.get_text(separator=" ", strip=True) if el else resp.text
    return text.split("Minutes of the Monetary Policy Committee")[0].strip()


def _extract_boj(resp):
    # BoJ publishes its English "Statement on Monetary Policy" as a PDF, so we
    # read the bytes with pypdf. Imported lazily because it's only needed when
    # fetching a fresh statement; the deployed app serves bundled .txt files.
    import io
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(resp.content))
    text = " ".join((page.extract_text() or "") for page in reader.pages)
    return " ".join(text.split())


def _extract_bcb(resp):
    # BCB serves Copom statements through a JSON API; the statement body is HTML
    # in "textoComunicado". Text is Portuguese (scored with a PT lexicon).
    items = resp.json().get("conteudo") or []
    html = items[0].get("textoComunicado", "") if items else ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def _extract_banxico(resp):
    # Banxico publishes Junta de Gobierno statements as PDFs (Spanish). Same
    # pypdf approach as BoJ; imported lazily since bundled .txt cache is used
    # in production.
    import io
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(resp.content))
    text = " ".join((page.extract_text() or "") for page in reader.pages)
    return " ".join(text.split())


# Each source has its own cache subdirectory (so slugs never collide) and its
# own extractor (the sites all use different markup / formats).
SOURCES = {
    "fed": {"subdir": "statements", "extractor": _extract_fed},
    "ecb": {"subdir": "statements_ecb", "extractor": _extract_ecb},
    "boe": {"subdir": "statements_boe", "extractor": _extract_boe},
    "boj": {"subdir": "statements_boj", "extractor": _extract_boj},
    "bcb": {"subdir": "statements_bcb", "extractor": _extract_bcb},
    "banxico": {"subdir": "statements_banxico", "extractor": _extract_banxico},
}


def _bundled_dir(subdir):
    return DATA_DIR / subdir


def _writable_dir(subdir):
    if os.environ.get("VERCEL"):
        return Path(tempfile.gettempdir()) / "fomc-cache" / subdir
    return DATA_DIR / subdir


def fetch_statement(url, extractor=_extract_fed):
    """Fetch a statement and extract its body text using the given extractor."""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return extractor(resp)


def fetch_and_cache(url, source="fed", cache_dir=None):
    """Fetch a statement, preferring the bundled cache, then a writable cache."""
    cfg = SOURCES[source]
    subdir = cfg["subdir"]
    last = url.rstrip("/").split("/")[-1]
    for ext in (".htm", ".html", ".pdf"):
        last = last.replace(ext, "")
    # Sanitize anything left (e.g. BCB's "?nro_reuniao=279" query string) so the
    # slug is always a safe, unique filename.
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", last)
    filename = f"{slug}.txt"

    bundled_path = _bundled_dir(subdir) / filename
    if bundled_path.exists():
        return bundled_path.read_text()

    write_dir = Path(cache_dir) if cache_dir else _writable_dir(subdir)
    write_path = write_dir / filename
    if write_path.exists():
        return write_path.read_text()

    text = fetch_statement(url, extractor=cfg["extractor"])
    write_dir.mkdir(parents=True, exist_ok=True)
    write_path.write_text(text)
    return text
