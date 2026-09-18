from app.models import MediaType
from app.parser import missing_info_reply, parse_message


def test_clear_movie():
    req = parse_message("Movie: No Time to Die (2021)")[0]
    assert req.title == "No Time to Die"
    assert req.year == 2021
    assert req.media_type == MediaType.MOVIE
    assert req.is_complete


def test_clear_series_suffix():
    req = parse_message("FBI (2018) - Series")[0]
    assert req.title == "FBI"
    assert req.year == 2018
    assert req.media_type == MediaType.SERIES


def test_missing_type_and_year():
    req = parse_message("The Drop")[0]
    assert req.title == "The Drop"
    assert req.year is None
    assert req.media_type is None
    assert set(req.missing_fields) == {"year", "type"}


def test_multiple_requests_are_split():
    reqs = parse_message("Series: Law & Order (1990)\nSeries: FBI (2018)\nSeries: Chicago PD (2014)")
    assert len(reqs) == 3
    assert all(r.is_complete for r in reqs)


def test_commentary_ignored():
    reqs = parse_message("Follow up on this;\nSeries: The Drop (2026)")
    assert len(reqs) == 1
    assert reqs[0].title == "The Drop"


def test_reply_text():
    req = parse_message("The Drop")[0]
    text = missing_info_reply([req])
    assert "missing year, type" in text
    assert "Movie: Title (Year)" in text
