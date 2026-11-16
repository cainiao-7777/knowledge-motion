"""Place scene boundaries on nearby beat markers without changing total length."""
def align_scenes(durations, beats):
    total = sum(durations)
    available = sorted(set(float(b) for b in beats if 0 < b < total))
    boundaries, target = [0], 0
    for index, duration in enumerate(durations[:-1]):
        target += duration
        lower = boundaries[-1] + 2
        upper = total - 2 * (len(durations) - index - 1)
        candidates = [b for b in available if lower <= b <= upper]
        closest = min(candidates, key=lambda b: (abs(b-target), -b), default=target)
        boundaries.append(closest if candidates and abs(closest-target) <= 2 else max(lower, min(upper, target)))
    return boundaries + [total]
