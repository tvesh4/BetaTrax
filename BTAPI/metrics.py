def classify_developer_effectiveness(fixed_count: int, reopened_count: int) -> str:
    if fixed_count < 20:
        return "Insufficient data"
    ratio = reopened_count / fixed_count
    if ratio < 1 / 32:
        return "Good"
    if ratio < 1 / 8:
        return "Fair"
    return "Poor"
