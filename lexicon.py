HAWKISH = {
    # Strong policy-intent signals
    "tighten": 1.5, "overheating": 1.5, "restrictive": 1.4,
    "raise": 1.2, "hike": 1.2, "upside risk": 1.3,
    "vigilant": 1.0, "persistent": 1.1, "accelerate": 1.0,
    "firmer": 1.0, "determined": 1.2, "ongoing": 0.9,
    "attentive": 0.6, "exceed": 0.8, "above": 0.5,
    # Downweighted — directional but not decisive alone
    "strong": 0.3, "robust": 0.3,
}

DOVISH = {
    # Strong policy-intent signals
    "accommodative": 1.5, "ease": 1.3, "downside risk": 1.3,
    "cut": 1.2, "stimulus": 1.2, "patient": 1.0,
    "transitory": 1.3, "pause": 1.1, "cooling": 1.0,
    "softening": 1.1, "subdued": 1.1, "lower": 1.0, "weak": 1.0,
    "diminished": 0.8, "progress": 0.7, "gradual": 0.7,
    "carefully": 0.5,
    # Downweighted
    "moderate": 0.3,
}

# ECB statements share most of the Fed vocabulary but lean on their own
# phrasing. These extend (not replace) the base lexicon so the ECB page scores
# the same core terms plus a handful of ECB-specific ones, while the Fed page
# is left completely unchanged.
ECB_HAWKISH = {
    **HAWKISH,
    "elevated": 0.7, "sufficiently": 0.6, "decisive": 0.9,
    "reinforce": 0.6, "vigorous": 1.0, "timely": 0.5,
}

ECB_DOVISH = {
    **DOVISH,
    "disinflation": 1.2, "disinflationary": 1.2, "easing": 1.2,
    "moderating": 1.0, "receding": 0.9, "declining": 0.8,
    "reinvest": 0.6, "reinvestment": 0.6, "slowdown": 0.9,
}

# Bank of England MPC vocabulary. The MPC leans heavily on "restrictiveness",
# inflation "persistence", and labour-market "slack", so those carry the
# institution-specific signal on top of the shared base terms.
BOE_HAWKISH = {
    **HAWKISH,
    "restrictiveness": 1.0, "persistence": 1.0, "embedded": 0.8,
    "elevated": 0.7, "stickiness": 0.9, "second-round": 0.8,
}

BOE_DOVISH = {
    **DOVISH,
    "disinflation": 1.2, "easing": 1.2, "loosening": 1.1,
    "slack": 0.9, "moderating": 1.0, "receding": 0.9,
    "declining": 0.8, "waning": 0.8,
}

# Bank of Japan vocabulary. The BoJ ran ultra-loose policy for years, so its
# hawkish signal is about *exiting* that stance ("normalization", "exit",
# raising rates), while its dovish signal is the language of continued
# "monetary easing" it leaned on throughout.
BOJ_HAWKISH = {
    **HAWKISH,
    "normalization": 1.3, "normalize": 1.3, "exit": 0.8,
    "adjust": 0.5, "unwind": 0.9, "elevated": 0.6,
}

BOJ_DOVISH = {
    **DOVISH,
    "easing": 1.2, "patiently": 1.0, "powerful": 0.8,
    "sustainable": 0.4, "deflation": 0.9, "underlying": 0.3,
    "purchases": 0.5,
}

# Banco Central do Brasil (Copom). The statements are published in Portuguese,
# and since the analyzer is pure keyword matching we score them directly with a
# Portuguese lexicon (no translation needed). Terms are the Copom's standard
# hawkish/dovish vocabulary around the Selic rate and inflation.
BCB_HAWKISH = {
    "elevar": 1.2, "elevação": 1.2, "alta": 0.9, "aumentar": 1.1,
    "aumento": 1.0, "aperto": 1.3, "restritiva": 1.4, "restritivo": 1.4,
    "restrição": 1.2, "persistência": 1.1, "persistente": 1.1,
    "pressões": 0.8, "pressão": 0.8, "acima": 0.6, "vigilância": 1.0,
    "cautela": 0.7, "desancoragem": 1.2, "deterioração": 0.9,
    "elevada": 0.7, "elevados": 0.7,
}

BCB_DOVISH = {
    "reduzir": 1.2, "redução": 1.2, "corte": 1.2, "queda": 1.0,
    "afrouxamento": 1.4, "flexibilização": 1.3, "estímulo": 1.2,
    "expansionista": 1.3, "desaceleração": 1.0, "arrefecimento": 1.1,
    "moderação": 0.8, "moderado": 0.5, "recuo": 0.9, "abaixo": 0.6,
    "alívio": 1.0, "convergência": 0.7, "desinflação": 1.2,
    "enfraquecimento": 1.0,
}
