def percentile(values: list[int], p: float) -> float | None:
    if not values:
        return None

    sorted_values = sorted(values)

    if len(sorted_values) == 1:
        return float(sorted_values[0])

    index = round((len(sorted_values) - 1) * p)
    return float(sorted_values[index])
