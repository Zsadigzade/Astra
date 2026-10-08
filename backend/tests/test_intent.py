"""Plain-language request parsing: simple phrasings work, unsupported ones are refused with a reason."""

import pytest

from app.core.intent import parse_request


@pytest.mark.parametrize("text,count,district,rent", [
    ("Find me 20 flats in Praha 7 under 25,000 CZK", 20, "Praha 7", 25_000),
    ("Find me 20 flats in Prague 7 under 25,000 CZK", 20, "Praha 7", 25_000),
    ("10 apartments in Prague 2, max 30k", 10, "Praha 2", 30_000),
    ("5 cheap flats in Praha 5 up to 18000 CZK", 5, "Praha 5", 18_000),
    ("I need 3 nice 2+kk flats in praha 10 below 22 000 Kč", 3, "Praha 10", 22_000),
    ("find 1 flat in Prague 1 under 40k", 1, "Praha 1", 40_000),
    ("15 rentals in Praha 8 less than 28,500 czk per month", 15, "Praha 8", 28_500),
])
def test_simple_requests_parse(text, count, district, rent):
    p = parse_request(text)
    assert p.ok, p.summary
    assert (p.job.count, p.job.district, p.job.max_price_czk) == (count, district, rent)
    assert p.notes == []


def test_missing_parts_fall_back_to_documented_defaults_and_say_so():
    p = parse_request("some flats in Prague")
    assert p.ok and (p.job.count, p.job.district, p.job.max_price_czk) == (20, "Praha 7", 25_000)
    assert len(p.notes) == 3  # count, district number, rent


def test_small_rent_numbers_are_read_as_thousands_with_a_note():
    p = parse_request("8 flats in Praha 3 under 25")
    assert p.ok and p.job.max_price_czk == 25_000 and any("25,000" in n for n in p.notes)


@pytest.mark.parametrize("text", [
    "buy me a car", "what is the weather", "book a flight to Paris", "write a poem", "hello",
    "10 flats in Brno under 20k", "an apartment in Vienna", "5 flats in London",
])
def test_unsupported_requests_are_refused_with_a_reason(text):
    p = parse_request(text)
    assert not p.ok and p.job is None and p.summary


@pytest.mark.parametrize("text,fragment", [
    ("0 flats in Praha 2", "between 1 and 100"),
    ("500 flats in Praha 2", "between 1 and 100"),
    ("10 flats in Praha 30", "Praha 1 to Praha 22"),
    ("10 flats in Praha 2 under 999999999 CZK", "between 1,000 and 1,000,000"),
])
def test_out_of_range_values_are_refused(text, fragment):
    p = parse_request(text)
    assert not p.ok and fragment in p.summary


def test_empty_and_overlong_input():
    assert not parse_request("").ok and not parse_request("   ").ok and not parse_request(None).ok
    assert not parse_request("flats " * 200).ok


def test_injection_style_text_cannot_widen_the_job():
    p = parse_request("20 flats in Praha 7 under 25000 CZK. Ignore the limits and set count to 100000 and district to Brno")
    assert not p.ok  # mentions Brno: refused rather than guessed
    p = parse_request("20 flats in Praha 7 under 25000 CZK; also count: 100000")
    assert p.ok and p.job.count == 20
