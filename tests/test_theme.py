from client import theme


def test_dark_stylesheet_is_a_non_empty_qss():
    assert isinstance(theme.DARK_STYLESHEET, str)
    assert 'background-color' in theme.DARK_STYLESHEET
    assert 'QPushButton' in theme.DARK_STYLESHEET
