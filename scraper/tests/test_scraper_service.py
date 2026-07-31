from datetime import date

from scraper.app.services.scraper import BattleScraperService


def test_build_dashboard_api_url_uses_competition_overview_endpoint() -> None:
    url = BattleScraperService._build_dashboard_api_url(
        object(),
        target_date=date(2026, 7, 31),
        race_class="open",
    )

    assert url == (
        "https://velocidrone-bot.gorbach.dev/"
        "api/competitions/overview?cupId=open-class&date=2026-07-31"
    )