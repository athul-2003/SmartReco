from app.services.ui import category_cover


def test_category_cover_is_deterministic():
    first = category_cover("Data Science")
    second = category_cover("Data Science")
    assert first == second


def test_category_cover_uses_first_letter_as_monogram():
    cover = category_cover("Leadership")
    assert cover["letter"] == "L"


def test_category_cover_varies_tone_class_across_categories():
    tones = {
        category_cover(c)["tone_class"]
        for c in ["Dev", "Design", "Business", "Data", "Health", "Music"]
    }
    assert len(tones) > 1


def test_category_cover_handles_empty_category():
    cover = category_cover("")
    assert cover["letter"] == "?"
