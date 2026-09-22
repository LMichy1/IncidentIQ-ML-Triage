from incidentiq_ml.data.preprocess import clean_text, combine_title_description


def test_clean_text_collapses_whitespace():
    assert clean_text("hello   \n\t world  ") == "hello world"


def test_clean_text_handles_none():
    assert clean_text(None) == ""


def test_combine_repeats_title_and_appends_description():
    combined = combine_title_description("Login fails", "User cannot sign in.")
    assert combined.count("Login fails") == 2
    assert "User cannot sign in." in combined
