from datetime import datetime

import requests
from flask import Flask, render_template, request

from analyzer import score_statement, score_shift
from lexicon import (
    ECB_HAWKISH, ECB_DOVISH,
    BOE_HAWKISH, BOE_DOVISH,
    BOJ_HAWKISH, BOJ_DOVISH,
    BCB_HAWKISH, BCB_DOVISH,
)
from scraper import fetch_and_cache

app = Flask(__name__)

# Every regular FOMC meeting from Powell's first meeting as chair (Mar 2018)
# through the current one, in chronological order. Date is the statement
# release day (the second day of each two-day meeting). Verified live against
# federalreserve.gov before being added; emergency/unscheduled 2020 actions
# and notation-vote-only releases are excluded since they don't follow the
# standard press-release page layout the scraper expects.
_MEETING_DATES = [
    "20180321", "20180502", "20180613", "20180801", "20180926", "20181108", "20181219",
    "20190130", "20190320", "20190501", "20190619", "20190731", "20190918", "20191030", "20191211",
    "20200129", "20200318", "20200429", "20200610", "20200729", "20200916", "20201105", "20201216",
    "20210127", "20210317", "20210428", "20210616", "20210728", "20210922", "20211103", "20211215",
    "20220126", "20220316", "20220504", "20220615", "20220727", "20220921", "20221102", "20221214",
    "20230201", "20230322", "20230503", "20230614", "20230726", "20230920", "20231101", "20231213",
    "20240131", "20240320", "20240501", "20240612", "20240731", "20240918", "20241107", "20241218",
    "20250129", "20250319", "20250507", "20250618", "20250730", "20250917", "20251029", "20251210",
    "20260128", "20260318", "20260429", "20260617",
]

MEETINGS = [
    (f"{d[:4]}-{d[4:6]}-{d[6:]}", f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{d}a.htm")
    for d in _MEETING_DATES
]

DEFAULT_DATE = "2026-06-17"

MEETINGS_BY_DATE = {date: url for date, url in MEETINGS}

# ECB Governing Council monetary policy meetings ("Monetary policy decisions"
# press releases). Unlike the Fed, ECB URLs carry an unpredictable hash, so the
# full URL must be stored rather than generated. The meeting date is encoded in
# the slug as mpYYMMDD, which we parse to build the dropdown label.
_ECB_URLS = [
    "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp220203~90fbe94662.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp220310~2d19f8ba60.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp220414~d1b76520c6.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp220609~122666c272.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp220721~53e5bdd317.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp220908~c1b6839378.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp221027~df1d778b84.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp221215~f3461d7b6e.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2023/html/ecb.mp230202~08a972ac76.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2023/html/ecb.mp230316~aad5249f30.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2023/html/ecb.mp230504~cdfd11a697.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2023/html/ecb.mp230615~d34cddb4c6.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2023/html/ecb.mp230727~da80cfcf24.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2023/html/ecb.mp230914~aab39f8c21.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2023/html/ecb.mp231026~6028cea576.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2023/html/ecb.mp231214~9846e62f62.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.mp240125~f738889bde.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.mp240307~a5fa52b82b.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.mp240411~1345644915.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.mp240606~2148ecdb3c.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.mp240718~b9e0ddd9d5.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.mp240912~67cb23badb.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.mp241017~aa366eaf20.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.mp241212~2acab6e51e.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.mp250130~530b29e622.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.mp250306~d4340800b3.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.mp250417~42727d0735.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.mp250605~3b5f67d007.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.mp250724~50bc70e13f.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.mp250911~6afb7a9490.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.mp251030~cf0540b5c0.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.mp251218~58b0e415a6.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp260205~001d26959b.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp260319~3057739775.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp260430~81b7179e6f.en.html",
    "https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp260611~4d41bd5e83.en.html",
]


def _ecb_date(url):
    slug = url.split("ecb.mp")[1][:6]  # YYMMDD
    return f"20{slug[:2]}-{slug[2:4]}-{slug[4:6]}"


ECB_MEETINGS = sorted((_ecb_date(u), u) for u in _ECB_URLS)
ECB_MEETINGS_BY_DATE = {date: url for date, url in ECB_MEETINGS}
ECB_DEFAULT_DATE = ECB_MEETINGS[-1][0]

# Bank of England MPC meetings ("Monetary Policy Summary and minutes"). The URL
# encodes only the month, so the exact decision date (parsed from each page's
# "Published on" line) is stored explicitly alongside it. Only meetings with a
# published summary are listed; future scheduled meetings are added once live.
BOE_MEETINGS = [
    ("2022-02-03", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2022/february-2022"),
    ("2022-03-17", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2022/march-2022"),
    ("2022-05-05", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2022/may-2022"),
    ("2022-06-16", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2022/june-2022"),
    ("2022-08-04", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2022/august-2022"),
    ("2022-09-22", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2022/september-2022"),
    ("2022-11-03", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2022/november-2022"),
    ("2022-12-15", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2022/december-2022"),
    ("2023-02-02", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2023/february-2023"),
    ("2023-03-23", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2023/march-2023"),
    ("2023-05-11", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2023/may-2023"),
    ("2023-06-22", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2023/june-2023"),
    ("2023-08-03", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2023/august-2023"),
    ("2023-09-21", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2023/september-2023"),
    ("2023-11-02", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2023/november-2023"),
    ("2023-12-14", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2023/december-2023"),
    ("2024-02-01", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2024/february-2024"),
    ("2024-03-21", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2024/march-2024"),
    ("2024-05-09", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2024/may-2024"),
    ("2024-06-20", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2024/june-2024"),
    ("2024-08-01", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2024/august-2024"),
    ("2024-09-19", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2024/september-2024"),
    ("2024-11-07", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2024/november-2024"),
    ("2024-12-19", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2024/december-2024"),
    ("2025-02-06", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2025/february-2025"),
    ("2025-03-20", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2025/march-2025"),
    ("2025-05-08", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2025/may-2025"),
    ("2025-06-19", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2025/june-2025"),
    ("2025-08-07", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2025/august-2025"),
    ("2025-09-18", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2025/september-2025"),
    ("2025-11-06", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2025/november-2025"),
    ("2025-12-18", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2025/december-2025"),
    ("2026-02-05", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/february-2026"),
    ("2026-03-19", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/march-2026"),
    ("2026-04-30", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/april-2026"),
    ("2026-06-18", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/june-2026"),
]
BOE_MEETINGS_BY_DATE = {date: url for date, url in BOE_MEETINGS}
BOE_DEFAULT_DATE = BOE_MEETINGS[-1][0]

# Bank of Japan Monetary Policy Meetings. The BoJ's English "Statement on
# Monetary Policy" is published as a PDF whose filename encodes the date as
# kYYMMDDa, so (like the ECB) the date is parsed from the slug.
_BOJ_URLS = [
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2022/k220118a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2022/k220318a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2022/k220428a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2022/k220617a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2022/k220721a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2022/k220922a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2022/k221028a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2022/k221220a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2023/k230118a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2023/k230310a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2023/k230428a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2023/k230616a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2023/k230728a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2023/k230922a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2023/k231031a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2023/k231219a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2024/k240123a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2024/k240319a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2024/k240426a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2024/k240614a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2024/k240731a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2024/k240920a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2024/k241031a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2024/k241219a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k250124a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k250319a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k250501a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k250617a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k250731a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k250919a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k251030a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k251219a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260123a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260319a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260428a.pdf",
    "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260616a.pdf",
]


def _boj_date(url):
    slug = url.rstrip("/").split("/")[-1]  # kYYMMDDa.pdf
    ymd = slug[1:7]
    return f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:6]}"


BOJ_MEETINGS = sorted((_boj_date(u), u) for u in _BOJ_URLS)
BOJ_MEETINGS_BY_DATE = {date: url for date, url in BOJ_MEETINGS}
BOJ_DEFAULT_DATE = BOJ_MEETINGS[-1][0]

# Banco Central do Brasil (Copom). Statements come from the BCB's JSON API,
# keyed by meeting number (nro_reuniao); the date is the decision date. Text is
# Portuguese, scored with a Portuguese lexicon (see lexicon.py).
BCB_MEETINGS = [
    ("2022-02-02", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=244"),
    ("2022-03-16", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=245"),
    ("2022-05-04", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=246"),
    ("2022-06-15", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=247"),
    ("2022-08-03", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=248"),
    ("2022-09-21", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=249"),
    ("2022-10-26", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=250"),
    ("2022-12-07", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=251"),
    ("2023-02-01", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=252"),
    ("2023-03-22", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=253"),
    ("2023-05-03", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=254"),
    ("2023-06-21", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=255"),
    ("2023-08-02", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=256"),
    ("2023-09-20", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=257"),
    ("2023-11-01", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=258"),
    ("2023-12-13", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=259"),
    ("2024-01-31", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=260"),
    ("2024-03-20", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=261"),
    ("2024-05-08", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=262"),
    ("2024-06-19", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=263"),
    ("2024-07-31", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=264"),
    ("2024-09-18", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=265"),
    ("2024-11-06", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=266"),
    ("2024-12-11", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=267"),
    ("2025-01-29", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=268"),
    ("2025-03-19", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=269"),
    ("2025-05-07", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=270"),
    ("2025-06-18", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=271"),
    ("2025-07-30", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=272"),
    ("2025-09-17", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=273"),
    ("2025-11-05", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=274"),
    ("2025-12-10", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=275"),
    ("2026-01-28", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=276"),
    ("2026-03-18", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=277"),
    ("2026-04-29", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=278"),
    ("2026-06-17", "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=279"),
]
BCB_MEETINGS_BY_DATE = {date: url for date, url in BCB_MEETINGS}
BCB_DEFAULT_DATE = BCB_MEETINGS[-1][0]

# Score bands and what they typically mean for the rate path.
# The neutral zone is intentionally narrow (+-0.02) so "Neutral" only fires on
# statements that are genuinely near-zero net tone, rather than swallowing
# most meetings the way a wider band (e.g. the +-0.08 SHIFT_THRESHOLD) would.
RATE_IMPACT_BANDS = [
    (0.25, float("inf"), "Strongly Hawkish", "Higher-for-longer bias; hike risk if data allows"),
    (0.02, 0.25, "Hawkish", "Hold bias; rate cuts likely pushed further out"),
    (-0.02, 0.02, "Neutral", "Data-dependent; no clear signal on next move"),
    (-0.25, -0.02, "Dovish", "Cut odds rising; easing bias building"),
    (float("-inf"), -0.25, "Strongly Dovish", "Cut bias; faster easing path likely"),
]


def rate_impact_bands(score=None):
    bands = []
    for low, high, name, impact in RATE_IMPACT_BANDS:
        if low == float("-inf"):
            range_label = f"≤ {high:+.2f}"
            current = score is not None and score < high
        elif high == float("inf"):
            range_label = f"≥ {low:+.2f}"
            current = score is not None and score >= low
        else:
            range_label = f"{low:+.2f} to {high:+.2f}"
            current = score is not None and low <= score < high
        bands.append({"name": name, "impact": impact, "range_label": range_label, "current": current})
    return bands


def verdict_for_score(score):
    """Map a score to the same band the rate-impact legend highlights, so the
    verdict shown in the report always matches the highlighted legend row."""
    band = next(b for b in rate_impact_bands(score) if b["current"])
    name = band["name"]
    if "Hawkish" in name:
        css_class = "hawkish"
    elif "Dovish" in name:
        css_class = "dovish"
    else:
        css_class = "neutral"
    return name, css_class


def label_for(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")


def prior_meeting(meetings, date_str):
    """Return (date, url) of the meeting immediately before date_str, if any."""
    idx = next((i for i, (d, _) in enumerate(meetings) if d == date_str), None)
    if idx is None or idx == 0:
        return None
    return meetings[idx - 1]


# Per-source configuration. Everything else (scoring, bands, verdicts, the
# template) is shared, so a new central bank is just another entry here plus a
# meeting list and lexicon.
SOURCE_CONFIG = {
    "fed": {
        "scraper": "fed",
        "meetings": MEETINGS,
        "meetings_by_date": MEETINGS_BY_DATE,
        "default_date": DEFAULT_DATE,
        "hawkish": None,
        "dovish": None,
        "page_title": "FOMC Statement Parser",
        "masthead_title": "FOMC STATEMENT PARSER",
        "select_label": "FOMC Meeting",
        "meeting_noun": "FOMC Statement",
        "action": "/",
    },
    "ecb": {
        "scraper": "ecb",
        "meetings": ECB_MEETINGS,
        "meetings_by_date": ECB_MEETINGS_BY_DATE,
        "default_date": ECB_DEFAULT_DATE,
        "hawkish": ECB_HAWKISH,
        "dovish": ECB_DOVISH,
        "page_title": "ECB Statement Parser",
        "masthead_title": "ECB STATEMENT PARSER",
        "select_label": "ECB Meeting",
        "meeting_noun": "ECB Monetary Policy Decision",
        "action": "/ecb",
    },
    "boe": {
        "scraper": "boe",
        "meetings": BOE_MEETINGS,
        "meetings_by_date": BOE_MEETINGS_BY_DATE,
        "default_date": BOE_DEFAULT_DATE,
        "hawkish": BOE_HAWKISH,
        "dovish": BOE_DOVISH,
        "page_title": "BoE Statement Parser",
        "masthead_title": "BANK OF ENGLAND PARSER",
        "select_label": "BoE Meeting",
        "meeting_noun": "BoE Monetary Policy Summary",
        "action": "/boe",
    },
    "boj": {
        "scraper": "boj",
        "meetings": BOJ_MEETINGS,
        "meetings_by_date": BOJ_MEETINGS_BY_DATE,
        "default_date": BOJ_DEFAULT_DATE,
        "hawkish": BOJ_HAWKISH,
        "dovish": BOJ_DOVISH,
        "page_title": "BoJ Statement Parser",
        "masthead_title": "BANK OF JAPAN PARSER",
        "select_label": "BoJ Meeting",
        "meeting_noun": "BoJ Statement on Monetary Policy",
        "action": "/boj",
    },
    "bcb": {
        "scraper": "bcb",
        "meetings": BCB_MEETINGS,
        "meetings_by_date": BCB_MEETINGS_BY_DATE,
        "default_date": BCB_DEFAULT_DATE,
        "hawkish": BCB_HAWKISH,
        "dovish": BCB_DOVISH,
        "page_title": "Copom Statement Parser",
        "masthead_title": "BANCO CENTRAL DO BRASIL PARSER",
        "select_label": "Copom Meeting",
        "meeting_noun": "Copom Statement (Portuguese source)",
        "action": "/bcb",
    },
}


def build_report(source):
    cfg = SOURCE_CONFIG[source]
    meetings = cfg["meetings"]
    meetings_by_date = cfg["meetings_by_date"]

    # Only run a report when the user actually submitted the form (Run Report).
    # A bare visit to the page stays clean with nothing analyzed yet.
    ran = "meeting" in request.args

    selected_date = request.args.get("meeting", cfg["default_date"])
    if selected_date not in meetings_by_date:
        selected_date = cfg["default_date"]
    url = meetings_by_date[selected_date]

    error = None
    result = None
    shift = None

    if ran:
        prior = prior_meeting(meetings, selected_date)
        try:
            text = fetch_and_cache(url, source=cfg["scraper"])
            result = score_statement(text, cfg["hawkish"], cfg["dovish"])

            if prior:
                prior_date, prior_url = prior
                try:
                    prior_text = fetch_and_cache(prior_url, source=cfg["scraper"])
                    shift = score_shift(text, prior_text, cfg["hawkish"], cfg["dovish"])
                    shift["prior_label_date"] = label_for(prior_date)
                    shift["prior_label"], _ = verdict_for_score(shift["prior_score"])
                except requests.exceptions.RequestException:
                    shift = None
        except requests.exceptions.RequestException:
            error = "This statement isn't published yet. Check back after the meeting concludes."

    dropdown = [
        {"date": d, "label": label_for(d), "url": u, "selected": d == selected_date}
        for d, u in meetings
    ]

    bands = rate_impact_bands(result["score"] if result else None)
    verdict_name, verdict_class = verdict_for_score(result["score"]) if result else (None, None)

    return render_template(
        "index.html",
        source=source,
        page_title=cfg["page_title"],
        masthead_title=cfg["masthead_title"],
        select_label=cfg["select_label"],
        meeting_noun=cfg["meeting_noun"],
        action=cfg["action"],
        dropdown=dropdown,
        selected_date=selected_date,
        selected_label=label_for(selected_date),
        url=url,
        result=result,
        shift=shift,
        error=error,
        bands=bands,
        ran=ran,
        verdict_name=verdict_name,
        verdict_class=verdict_class,
    )


@app.route("/")
def index():
    return build_report("fed")


@app.route("/ecb")
def ecb():
    return build_report("ecb")


@app.route("/boe")
def boe():
    return build_report("boe")


@app.route("/boj")
def boj():
    return build_report("boj")


@app.route("/bcb")
def bcb():
    return build_report("bcb")


if __name__ == "__main__":
    app.run(debug=True, port=5050)
