def classify_ndvi(ndvi: float | None) -> str:
    if ndvi is None:
        return "Not available (satellite scene missing or cloudy)"
    if ndvi < 0.0:
        return "Water / snow / clouds — non-agricultural surface"
    if ndvi < 0.1:
        return "Bare soil / fallow — no crop canopy"
    if ndvi < 0.3:
        return "Sparse / emerging vegetation — early growth"
    if ndvi < 0.6:
        return "Moderate cover — active vegetative growth"
    if ndvi < 0.8:
        return "Good crop condition — healthy canopy"
    return "Dense, highly productive canopy"
