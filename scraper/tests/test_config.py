from scraper.app.core.config import ScraperSettings


def test_scraper_settings_default_api_base_url(monkeypatch) -> None:
    monkeypatch.delenv("FPVBATTLE_API_BASE_URL", raising=False)

    settings = ScraperSettings(_env_file=None)

    assert settings.api_base_url == "https://velocidrone-bot.gorbach.dev"
