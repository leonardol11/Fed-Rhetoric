# Ground-truth labels based on market reaction and contemporaneous Fed coverage.
# Sources: FOMC press releases, WSJ/Bloomberg post-meeting analysis.

TEST_CASES = [
    {
        "id": "2022-06-hawkish",
        "label": "Hawkish",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20220615a.htm",
        "note": "75bp hike — largest since 1994, explicit inflation-fighting pivot",
    },
    {
        "id": "2022-11-hawkish",
        "label": "Hawkish",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20221102a.htm",
        "note": "75bp hike #4, 'ongoing increases appropriate' language",
    },
    {
        "id": "2023-02-hawkish",
        "label": "Hawkish",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20230201a.htm",
        "note": "25bp hike but 'ongoing increases' still in statement",
    },
    {
        "id": "2023-09-neutral",
        "label": "Neutral",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20230920a.htm",
        "note": "Hold — hawkish lean but data-dependent pause; market read as neutral",
    },
    {
        "id": "2024-01-neutral",
        "label": "Neutral",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240131a.htm",
        "note": "Hold — Powell explicitly pushed back on March cut expectations",
    },
    {
        "id": "2019-06-neutral-patient",
        "label": "Neutral",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20190619a.htm",
        "note": "'Patient' hold — clear neutral with dovish tilt but no action taken",
    },
    {
        "id": "2021-11-dovish",
        "label": "Dovish",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20211103a.htm",
        "note": "Taper announced but 'transitory' inflation framing still present; accommodative stance",
    },
    {
        "id": "2025-05-neutral",
        "label": "Neutral",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20250507a.htm",
        "note": "Hold at 4.25-4.5%, uncertainty framing, no directional commitment",
    },
]
