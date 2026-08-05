import hashlib

_COVER_TONES = 6


def category_cover(category: str) -> dict[str, str]:
    """Deterministic tonal cover for a product card in place of a real image.

    The dataset has no product images, so cards get a category-tinted
    background (cycling through the design system's tonal palette) with the
    category's initial as a monogram. Uses a stable hash (not Python's
    randomized `hash()`) so the same category always maps to the same tone
    across restarts.
    """
    category = category.strip()
    digest = hashlib.md5(category.lower().encode("utf-8")).hexdigest()
    tone = int(digest, 16) % _COVER_TONES
    letter = category[0].upper() if category else "?"
    return {"tone_class": f"cover-{tone}", "letter": letter}
