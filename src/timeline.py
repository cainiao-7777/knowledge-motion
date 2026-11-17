"""Place scene boundaries on nearby beat markers without changing total length."""
def normalize_durations(durations, target_seconds=60, minimum=45, maximum=75):
    total=sum(durations)
    if total <= 0: raise ValueError('分镜总时长必须大于0')
    if minimum <= total <= maximum: return list(durations)
    # Keep each scene's relative pace while bringing the total back to target.
    scale=target_seconds/total
    adjusted=[max(2.0,min(30.0,float(value)*scale)) for value in durations]
    remainder=target_seconds-sum(adjusted)
    for index,value in enumerate(adjusted):
        if abs(remainder)<0.01: break
        room=(30.0-value) if remainder>0 else (value-2.0)
        change=min(abs(remainder),room)
        adjusted[index]+=change if remainder>0 else -change
        remainder+=-change if remainder>0 else change
    return adjusted

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
