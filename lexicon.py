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
