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
    # Ending the ultra-loose stance (exit/taper) is the BoJ's hawkish tell.
    "discontinue": 0.9, "discontinuing": 0.9, "terminate": 1.0, "termination": 0.8,
}

BOJ_DOVISH = {
    **DOVISH,
    "easing": 1.2, "patiently": 1.0, "powerful": 0.8,
    "sustainable": 0.4, "deflation": 0.9, "underlying": 0.3,
}

# Banco Central do Brasil (Copom). The statements are published in Portuguese,
# and since the analyzer is pure keyword matching we score them directly with a
# Portuguese lexicon (no translation needed). Terms are the Copom's standard
# hawkish/dovish vocabulary around the Selic rate and inflation.
BCB_HAWKISH = {
    "elevar": 1.2, "elevação": 1.2, "alta": 0.5, "aumentar": 0.5,
    "aumento": 0.5, "aperto": 1.3, "restritiva": 1.4, "restritivo": 1.4,
    "restrição": 1.2, "persistência": 1.1, "persistente": 1.1,
    "pressões": 0.8, "pressão": 0.8, "acima": 0.6, "vigilância": 1.0,
    "cautela": 0.3, "desancoragem": 1.2, "deterioração": 0.9,
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

# Banco de México (Banxico). Banxico publishes an official English translation
# of each "Monetary Policy Statement", so (unlike the BCB) we score it with the
# shared English lexicon plus Banxico-specific phrasing. Their hawkish signal is
# the language of "monetary restriction" and upside inflation risks; the dovish
# signal is "rate cuts", "convergence" of inflation to the 3% target, and
# economic "weakness".
BANXICO_HAWKISH = {
    **HAWKISH,
    "restriction": 1.2, "upward": 0.6, "persistence": 1.0,
    "complex": 0.4, "deterioration": 0.8, "depreciation": 0.7,
    "pressures": 0.6, "elevated": 0.6,
}

BANXICO_DOVISH = {
    **DOVISH,
    "easing": 1.2, "convergence": 0.7, "downward": 0.6,
    "weakness": 0.9, "slack": 0.8, "moderation": 0.6,
    "decreased": 0.8, "conclude": 0.6,
}

# ---------------------------------------------------------------------------
# Phrase lexicons (multi-word terms) for BoJ, Copom (BCB) and Banxico.
#
# The base single-word scoring can't see multi-word signals, and the strongest,
# least ambiguous tone cue in a central-bank statement is the policy *action*
# ("lower the target", "reduzir a taxa", "raise the policy interest rate"). These
# phrases are matched ahead of single words and weighted higher, so the action
# and other genuine multi-word signals dominate persistent boilerplate. Fed, ECB
# and BoE deliberately have no phrase dicts and are scored exactly as before.
# Weights were calibrated against every cached statement for each bank.
# ---------------------------------------------------------------------------

# Bank of Japan. Dovish = the language of QQE/YCC/NIRP easing it ran for years;
# hawkish = raising the policy rate, tapering JGB purchases, and exiting easing.
BOJ_HAWK_PHRASES = {
    "raise the policy interest rate": 2.6, "raise the short-term policy interest rate": 2.6,
    "raise interest rates": 2.2, "adjust the degree of monetary accommodation": 1.6,
    "change in the guideline for money market operations": 1.2,
    "changes in the monetary policy framework": 1.0,
    "reduction of the purchase amount": 1.6, "reduction of its purchase amount": 1.6,
    "upside risks to prices": 1.6, "fulfilled their roles": 1.4,
    "raise wages": 1.0, "wage increases": 0.8,
}

BOJ_DOVE_PHRASES = {
    "yield curve control": 1.6, "negative interest rate": 1.8, "monetary easing": 2.0,
    "powerful monetary easing": 2.4, "quantitative and qualitative monetary easing": 2.2,
    "additional easing": 2.0, "additional easing measures": 2.2, "asset purchases": 1.0,
    "accommodative financial conditions": 0.8, "large-scale": 0.8,
}

# Banco Central do Brasil (Copom) — Portuguese. The Selic action ("reduzir/elevar
# a taxa") is weighted heavily so a cut reads dovish even in the restrictive,
# hawkish-toned 2025-2026 statements.
BCB_HAWK_PHRASES = {
    "elevar a taxa": 4.0, "elevando a taxa": 4.0, "elevou a taxa": 4.0,
    "elevação da taxa": 4.0, "elevação da selic": 4.0,
    "aumento da taxa": 3.8, "aumentar a taxa": 3.8,
    "acima da meta": 1.4, "expectativas desancoradas": 1.6,
    "desancoragem das expectativas": 1.6, "patamar contracionista": 1.8,
    "política monetária restritiva": 1.8,
}

BCB_DOVE_PHRASES = {
    "reduzir a taxa": 4.0, "reduzindo a taxa": 4.0, "reduziu a taxa": 4.0,
    "redução da taxa": 4.0, "redução da selic": 4.0,
    "corte de juros": 3.4, "corte na taxa": 3.4,
    "abaixo da meta": 1.4, "efeitos desinflacionários": 1.6,
    "desaceleração da atividade": 1.4, "flexibilização monetária": 2.0,
    "afrouxamento monetário": 2.0,
}

# Banco de México (Banxico) — official English translation. "lower/raise the
# target [for the overnight interbank interest rate]" is the decisive action cue.
BANXICO_HAWK_PHRASES = {
    "raise the target": 2.6, "increase the target": 2.6,
    "raised the target": 2.6, "increased the target": 2.6,
    "monetary restriction": 1.4, "restrictive stance": 1.8,
    "inflation increased": 1.3, "inflation rose": 1.3,
    "revised upwards": 1.1, "upward pressures": 1.3,
}

BANXICO_DOVE_PHRASES = {
    "lower the target": 2.6, "reduce the target": 2.6, "reduced the target": 2.6,
    "rate cut": 1.8, "rate cuts": 1.8, "downward risks": 1.6,
    "weakness of economic activity": 1.8, "economic slack": 1.6,
    "economic weakness": 1.6, "inflation decreased": 1.3, "downward adjustment": 1.4,
}
