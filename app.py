from datetime import datetime

import requests
from flask import Flask, render_template, request

from analyzer import score_statement, score_shift
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

# Score bands and what they typically mean for the rate path.
# Bounds reuse analyzer.SHIFT_THRESHOLD (0.08) for the neutral zone so the
# "no clear signal" band lines up with the same cutoff used to call a shift
# material in score_shift().
RATE_IMPACT_BANDS = [
    (0.25, float("inf"), "Strongly Hawkish", "Higher-for-longer bias; hike risk if data allows"),
    (0.08, 0.25, "Hawkish", "Hold bias; rate cuts likely pushed further out"),
    (-0.08, 0.08, "Neutral", "Data-dependent; no clear signal on next move"),
    (-0.25, -0.08, "Dovish", "Cut odds rising; easing bias building"),
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


def label_for(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")


def prior_meeting(date_str):
    """Return (date, url) of the meeting immediately before date_str, if any."""
    idx = next((i for i, (d, _) in enumerate(MEETINGS) if d == date_str), None)
    if idx is None or idx == 0:
        return None
    return MEETINGS[idx - 1]


@app.route("/")
def index():
    # Only run a report when the user actually submitted the form (Run
    # Report). A bare visit to "/" stays clean with nothing analyzed yet.
    ran = "meeting" in request.args

    selected_date = request.args.get("meeting", DEFAULT_DATE)
    if selected_date not in MEETINGS_BY_DATE:
        selected_date = DEFAULT_DATE
    url = MEETINGS_BY_DATE[selected_date]

    error = None
    result = None
    shift = None

    if ran:
        prior = prior_meeting(selected_date)
        try:
            text = fetch_and_cache(url)
            result = score_statement(text)

            if prior:
                prior_date, prior_url = prior
                try:
                    prior_text = fetch_and_cache(prior_url)
                    shift = score_shift(text, prior_text)
                    shift["prior_label_date"] = label_for(prior_date)
                except requests.exceptions.RequestException:
                    shift = None
        except requests.exceptions.RequestException:
            error = "This statement isn't published yet. Check back after the meeting concludes."

    dropdown = [
        {"date": d, "label": label_for(d), "url": u, "selected": d == selected_date}
        for d, u in MEETINGS
    ]

    bands = rate_impact_bands(result["score"] if result else None)

    return render_template(
        "index.html",
        dropdown=dropdown,
        selected_date=selected_date,
        selected_label=label_for(selected_date),
        url=url,
        result=result,
        shift=shift,
        error=error,
        bands=bands,
        ran=ran,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
