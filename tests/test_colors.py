from shared.constants import Colors


def test_relative_luminance_bounds():
    assert round(Colors.WHITE.relative_luminance(), 4) == 1.0
    assert round(Colors.BLACK.relative_luminance(), 4) == 0.0


def test_contrast_ratio_black_on_white_is_maximal():
    assert round(Colors.WHITE.contrast_ratio(Colors.BLACK), 1) == 21.0
    assert round(Colors.WHITE.contrast_ratio(Colors.WHITE), 1) == 1.0


def test_has_contrast_filters_by_ratio():
    readable = Colors.has_contrast(4.65, background=Colors.WHITE)
    assert Colors.BLACK in readable
    assert Colors.WHITE not in readable
    assert all(Colors.WHITE.contrast_ratio(color) >= 4.65 for color in readable)
