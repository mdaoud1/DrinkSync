GRAMS_PER_OZ = 29.5735
MIN_DRINK_GRAMS = 5.0


def next_drink(previous_weight, current_weight, min_grams=MIN_DRINK_GRAMS):
    """Return (grams_to_send_or_None, new_previous_weight).

    The first reading only sets a baseline. A drop of at least min_grams is a
    sip. A rise of at least min_grams is a refill. Anything smaller is noise.
    """
    if current_weight is None:
        return None, previous_weight
    current = float(current_weight)
    if previous_weight is None:
        return None, current
    previous = float(previous_weight)
    delta = previous - current
    if delta >= min_grams:
        return delta, current
    if -delta >= min_grams:
        return None, current
    return None, previous


def leftover_after_adding(existing_leftover_grams, added_grams):
    """Pair leftover grams into whole ounces the same way the phone does."""
    total = float(existing_leftover_grams) + float(added_grams)
    ounces = int(round(total / GRAMS_PER_OZ))
    if ounces <= 0:
        return 0, total
    return ounces, total - ounces * GRAMS_PER_OZ
