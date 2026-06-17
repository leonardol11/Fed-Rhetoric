import os
import sys

# Vercel runs this file in isolation, so the project root (where app.py,
# analyzer.py, scraper.py, lexicon.py, and templates/ all live) needs to be
# added to sys.path before the real app can be imported.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
