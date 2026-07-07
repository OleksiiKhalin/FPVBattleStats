from datetime import date

from scraper.app.parsers.battle_page import parse_battle_page


def test_parse_page_defaults() -> None:
    payload = parse_battle_page(
        html="<html><body><h1>Sample Track</h1></body></html>",
        target_date=date(2026, 7, 2),
        race_class="open",
    )

    assert payload.track == "Sample Track"
    assert payload.season == "2026-07"
