from datetime import datetime

import requests
from flask import Flask, render_template, request

from analyzer import score_statement, score_shift
from lexicon import (
    ECB_HAWKISH, ECB_DOVISH,
    BOE_HAWKISH, BOE_DOVISH,
    BOJ_HAWKISH, BOJ_DOVISH,
    BCB_HAWKISH, BCB_DOVISH,
    BANXICO_HAWKISH, BANXICO_DOVISH,
)
from scraper import fetch_and_cache
import groq_client

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

_FED_SCHEDULED = [
    # 2026 remainder — [FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
    ("2026-07-29", ""),
    ("2026-09-16", ""),
    ("2026-10-28", ""),
    ("2026-12-09", ""),
]

MEETINGS = [
    (f"{d[:4]}-{d[4:6]}-{d[6:]}", f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{d}a.htm")
    for d in _MEETING_DATES
] + _FED_SCHEDULED

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
    # 2026 remainder — [ECB Governing Council calendar](https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html)
    # URLs unknown until published; empty string shows "not released yet".
]
_ECB_SCHEDULED = [
    ("2026-07-23", ""),
    ("2026-09-10", ""),
    ("2026-10-29", ""),
    ("2026-12-17", ""),
]


def _ecb_date(url):
    slug = url.split("ecb.mp")[1][:6]  # YYMMDD
    return f"20{slug[:2]}-{slug[2:4]}-{slug[4:6]}"


ECB_MEETINGS = sorted((_ecb_date(u), u) for u in _ECB_URLS) + _ECB_SCHEDULED
ECB_MEETINGS_BY_DATE = {date: url for date, url in ECB_MEETINGS}

# Bank of England MPC meetings ("Monetary Policy Summary and minutes"). The URL
# encodes only the month, so the exact decision date (parsed from each page's
# "Published on" line) is stored explicitly alongside it. Only meetings with a
# published summary are listed; future scheduled meetings use an empty URL until live.
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
    # 2026 remainder — [BoE MPC dates](https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates)
    ("2026-07-30", ""),
    ("2026-09-17", ""),
    ("2026-11-05", ""),
    ("2026-12-17", ""),
]
BOE_MEETINGS_BY_DATE = {date: url for date, url in BOE_MEETINGS}

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
    # 2026 remainder — [BoJ MPM schedule](https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm)
]
_BOJ_SCHEDULED = [
    ("2026-07-31", ""),
    ("2026-09-18", ""),
    ("2026-10-30", ""),
    ("2026-12-18", ""),
]


def _boj_date(url):
    slug = url.rstrip("/").split("/")[-1]  # kYYMMDDa.pdf
    ymd = slug[1:7]
    return f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:6]}"


BOJ_MEETINGS = sorted((_boj_date(u), u) for u in _BOJ_URLS) + _BOJ_SCHEDULED
BOJ_MEETINGS_BY_DATE = {date: url for date, url in BOJ_MEETINGS}

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
    # 2026 remainder — [BCB Copom calendar](https://www.bcb.gov.br/controleinflacao/copom)
    ("2026-08-05", ""),
    ("2026-09-16", ""),
    ("2026-11-04", ""),
    ("2026-12-09", ""),
]
BCB_MEETINGS_BY_DATE = {date: url for date, url in BCB_MEETINGS}

# Banco de México (Banxico). Banxico publishes the official English translation
# of each "Monetary Policy Statement" as a PDF whose URL carries an opaque GUID
# (like the ECB), so the full URL is stored alongside the decision date. The
# text is English, scored with a shared-English + Banxico-specific lexicon.
BANXICO_MEETINGS = [
    ("2022-02-10", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{8C41C206-FFD7-D2F1-53C1-F99B49828E42}.pdf"),
    ("2022-03-24", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{51CBBC0C-AD76-1B7F-A8F4-1E4D31261BE7}.pdf"),
    ("2022-05-12", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{D2DD420D-FEEB-C682-3621-46B2AC0CA13E}.pdf"),
    ("2022-06-23", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{418A3848-5F56-AADC-72B6-2D5D6ACD953B}.pdf"),
    ("2022-08-11", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{96D51354-49EC-881E-A105-DB13882FBE95}.pdf"),
    ("2022-09-29", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{5D6CCFE7-FBBC-A653-1AAF-FFFE47A1C4E0}.pdf"),
    ("2022-11-10", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{FD5B6E4F-810F-2615-EAD3-6A38FBD3719E}.pdf"),
    ("2022-12-15", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{ACF4298D-BFF0-56B9-5204-535809945352}.pdf"),
    ("2023-02-09", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{980D7F0D-1BD9-0271-AC09-B5E5CFD2F0EE}.pdf"),
    ("2023-03-30", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{6582F82C-C62B-A222-FA76-48CA213C40B8}.pdf"),
    ("2023-05-18", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{C1859402-0578-833E-22FA-BAD52FD4E302}.pdf"),
    ("2023-06-22", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{BE9A474F-C31A-105C-704C-F0D83F946952}.pdf"),
    ("2023-08-10", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{7D376C26-0D56-D9D9-88BC-36872FDE3877}.pdf"),
    ("2023-09-28", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{103B82DD-7EF3-67E5-D464-C427CA71A8C9}.pdf"),
    ("2023-11-09", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{0C72F586-D049-4DA0-ADE7-51191732D2E8}.pdf"),
    ("2023-12-14", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{361D29D6-2C10-6BD0-90E5-CC20E37740AD}.pdf"),
    ("2024-02-08", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{C7575A2B-9433-177D-F705-9EFB60DFECB0}.pdf"),
    ("2024-03-21", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{37E09D62-344B-CB2E-178A-3DFD89B45FAB}.pdf"),
    ("2024-05-09", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{82CC4453-9FB7-62E3-F382-B9A706E687EB}.pdf"),
    ("2024-06-27", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{4819AE22-2A5A-47A0-AB73-3844E55FC103}.pdf"),
    ("2024-08-08", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{C54982F1-0AE2-4D4E-7B01-782B71B833A0}.pdf"),
    ("2024-09-26", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{12F00F7D-9500-4783-8D4C-BD70CEFC3CB0}.pdf"),
    ("2024-11-14", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{CB65DD59-972C-33CB-405C-13329FF4C1B3}.pdf"),
    ("2024-12-19", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{D6C36379-9883-1D2C-4044-C1C95D826472}.pdf"),
    ("2025-02-06", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{2A312FE9-46E2-ECA2-18CA-E41525914605}.pdf"),
    ("2025-03-27", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{AAA950F8-AC4D-BB42-4373-67F1F76688BF}.pdf"),
    ("2025-05-15", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{05A3168F-9270-E2AC-5447-997D3260FCD6}.pdf"),
    ("2025-06-26", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{1E6C2F60-BAB9-9AE4-8D86-E933A9F7053F}.pdf"),
    ("2025-08-07", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{6DD1297B-DDAB-EB9D-16B7-274E45A4547A}.pdf"),
    ("2025-09-25", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{AB9F839E-1F94-B888-699F-9CEE8291C3D0}.pdf"),
    ("2025-11-06", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{80D0AFF9-2BD6-F24D-889E-7DB5C462A13C}.pdf"),
    ("2025-12-18", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{7DCCD7FD-3BCF-CB35-FD10-B2E19859980F}.pdf"),
    ("2026-02-05", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{A09BC2E1-83D7-6E38-2C95-1E9D6B4D3D5F}.pdf"),
    ("2026-03-26", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{0C0B38DB-88E4-DBA0-F925-550450052746}.pdf"),
    ("2026-05-07", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{CA5BAB07-D1DB-8A20-747A-642EB163A599}.pdf"),
    ("2026-06-25", "https://www.banxico.org.mx/publications-and-press/announcements-of-monetary-policy-decisions/{1232328B-67C5-6882-B908-B200C19F3E3D}.pdf"),
    # 2026 remainder — [Banxico calendar](https://www.banxico.org.mx/monetary-policy/d/{0C35369C-BF8F-E5A8-7710-FD5A6716474F}.pdf)
    ("2026-08-06", ""),
    ("2026-09-24", ""),
    ("2026-11-05", ""),
    ("2026-12-17", ""),
]
BANXICO_MEETINGS_BY_DATE = {date: url for date, url in BANXICO_MEETINGS}

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


def css_class_for_label(name):
    """Map a verdict label (e.g. "Strongly Dovish") to its display color class.
    Shared by the lexicon verdict and Grok's verdict so both color the same way."""
    if not name:
        return "neutral"
    if "Hawkish" in name:
        return "hawkish"
    if "Dovish" in name:
        return "dovish"
    return "neutral"


def verdict_for_score(score):
    """Map a score to the same band the rate-impact legend highlights, so the
    verdict shown in the report always matches the highlighted legend row."""
    band = next(b for b in rate_impact_bands(score) if b["current"])
    name = band["name"]
    return name, css_class_for_label(name)


def label_for(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")


def prior_meeting(meetings, date_str):
    """Return (date, url) of the meeting immediately before date_str, if any."""
    idx = next((i for i, (d, _) in enumerate(meetings) if d == date_str), None)
    if idx is None or idx == 0:
        return None
    return meetings[idx - 1]


def default_meeting_date(meetings, today=None):
    """Default dropdown to whichever meeting date is closest to today."""
    if today is None:
        today = datetime.now().date()
    return min(
        meetings,
        key=lambda item: abs((datetime.strptime(item[0], "%Y-%m-%d").date() - today).days),
    )[0]


# Per-source configuration. Everything else (scoring, bands, verdicts, the
# template) is shared, so a new central bank is just another entry here plus a
# meeting list and lexicon.
SOURCE_CONFIG = {
    "fed": {
        "scraper": "fed",
        "meetings": MEETINGS,
        "meetings_by_date": MEETINGS_BY_DATE,
        "hawkish": None,
        "dovish": None,
        "bank_name": "U.S. Federal Reserve (FOMC)",
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
        "hawkish": ECB_HAWKISH,
        "dovish": ECB_DOVISH,
        "bank_name": "European Central Bank",
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
        "hawkish": BOE_HAWKISH,
        "dovish": BOE_DOVISH,
        "bank_name": "Bank of England (MPC)",
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
        "hawkish": BOJ_HAWKISH,
        "dovish": BOJ_DOVISH,
        "bank_name": "Bank of Japan",
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
        "hawkish": BCB_HAWKISH,
        "dovish": BCB_DOVISH,
        "bank_name": "Banco Central do Brasil (Copom)",
        "page_title": "Copom Statement Parser",
        "masthead_title": "BANCO CENTRAL DO BRASIL PARSER",
        "select_label": "Copom Meeting",
        "meeting_noun": "Copom Statement (Portuguese source)",
        "action": "/bcb",
    },
    "banxico": {
        "scraper": "banxico",
        "meetings": BANXICO_MEETINGS,
        "meetings_by_date": BANXICO_MEETINGS_BY_DATE,
        "hawkish": BANXICO_HAWKISH,
        "dovish": BANXICO_DOVISH,
        "bank_name": "Banco de México (Banxico)",
        "page_title": "Banxico Statement Parser",
        "masthead_title": "BANCO DE MÉXICO PARSER",
        "select_label": "Banxico Meeting",
        "meeting_noun": "Banxico Monetary Policy Statement",
        "action": "/banxico",
    },
}


def build_report(source):
    cfg = SOURCE_CONFIG[source]
    meetings = cfg["meetings"]
    meetings_by_date = cfg["meetings_by_date"]

    # Only run a report when the user actually submitted the form (Run Report).
    # A bare visit to the page stays clean with nothing analyzed yet.
    ran = "meeting" in request.args

    # AI mode is an opt-in toggle for all banks except Banxico, where it defaults on.
    if source == "banxico":
        if "ai_default" in request.args:
            ai_on = request.args.get("ai") == "on"
        else:
            ai_on = True
    else:
        ai_on = request.args.get("ai") == "on"

    selected_date = request.args.get("meeting", default_meeting_date(meetings))
    if selected_date not in meetings_by_date:
        selected_date = default_meeting_date(meetings)
    url = meetings_by_date[selected_date]
    # An empty URL marks a scheduled-but-unreleased meeting (e.g. one that hasn't
    # happened yet), which we surface explicitly rather than trying to fetch.
    released = bool(url)

    error = None
    unreleased = False
    result = None
    shift = None
    grok = None

    if ran and not released:
        unreleased = True
    elif ran:
        prior = prior_meeting(meetings, selected_date)
        try:
            text = fetch_and_cache(url, source=cfg["scraper"], fresh=True)
            result = score_statement(text, cfg["hawkish"], cfg["dovish"])

            if prior:
                prior_date, prior_url = prior
                # Skip the prior comparison if the prior meeting is unreleased.
                if prior_url:
                    try:
                        prior_text = fetch_and_cache(prior_url, source=cfg["scraper"], fresh=True)
                        shift = score_shift(text, prior_text, cfg["hawkish"], cfg["dovish"])
                        shift["prior_label_date"] = label_for(prior_date)
                        shift["prior_label"], _ = verdict_for_score(shift["prior_score"])
                    except requests.exceptions.RequestException:
                        shift = None

            # Independent LLM read from Groq, only when AI mode is toggled on.
            # Fail-soft: a missing key or a bad response comes back as
            # available=False and just shows a note, so the lexicon report is
            # never blocked on the network call.
            if ai_on:
                grok = groq_client.analyze_statement(
                    text,
                    bank_name=cfg["bank_name"],
                    meeting_label=label_for(selected_date),
                    meeting_noun=cfg["meeting_noun"],
                )
                grok["css_class"] = css_class_for_label(grok.get("label"))
        except requests.exceptions.RequestException:
            error = "This statement isn't published yet. Check back after the meeting concludes."

    dropdown = [
        {"date": d, "label": label_for(d), "url": u, "selected": d == selected_date}
        for d, u in meetings
    ]

    # The legend highlights whichever read is on screen: in AI mode it follows
    # Groq's label (matched by name), otherwise the lexicon's numeric score. This
    # keeps the two reads fully separate so neither leaks into the other's view.
    if ai_on and grok and grok.get("label"):
        bands = rate_impact_bands(None)
        for b in bands:
            b["current"] = b["name"] == grok["label"]
    else:
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
        grok=grok,
        grok_enabled=groq_client.is_configured(),
        ai_on=ai_on,
        unreleased=unreleased,
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


@app.route("/banxico")
def banxico():
    return build_report("banxico")


if __name__ == "__main__":
    app.run(debug=True, port=5050)
