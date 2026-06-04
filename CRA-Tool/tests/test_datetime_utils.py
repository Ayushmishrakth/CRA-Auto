from datetime import timezone

from app.utils.datetime_utils import parse_graph_datetime


def test_parse_graph_datetime_supports_seven_fractional_digits_with_offset():
    parsed = parse_graph_datetime("2028-05-29T17:18:52.2994169+00:00")

    assert parsed.year == 2028
    assert parsed.month == 5
    assert parsed.day == 29
    assert parsed.hour == 17
    assert parsed.minute == 18
    assert parsed.second == 52
    assert parsed.microsecond == 299416
    assert parsed.tzinfo == timezone.utc


def test_parse_graph_datetime_supports_z_suffix_without_fraction():
    parsed = parse_graph_datetime("2028-05-29T17:18:52Z")

    assert parsed.isoformat() == "2028-05-29T17:18:52+00:00"


def test_parse_graph_datetime_supports_offset_without_fraction():
    parsed = parse_graph_datetime("2028-05-29T17:18:52+00:00")

    assert parsed.isoformat() == "2028-05-29T17:18:52+00:00"


def test_parse_graph_datetime_supports_three_fractional_digits():
    parsed = parse_graph_datetime("2028-05-29T17:18:52.299Z")

    assert parsed.isoformat() == "2028-05-29T17:18:52.299000+00:00"


def test_parse_graph_datetime_supports_six_fractional_digits():
    parsed = parse_graph_datetime("2028-05-29T17:18:52.299416+00:00")

    assert parsed.isoformat() == "2028-05-29T17:18:52.299416+00:00"
