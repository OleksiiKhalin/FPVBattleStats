from datetime import date

from scraper.app.cli.main import _build_parser


def test_sync_historical_accepts_explicit_date_range() -> None:
    args = _build_parser().parse_args(
        [
            "sync-historical",
            "--start-date",
            "2026-07-01",
            "--end-date",
            "2026-07-31",
            "--no-skip-existing",
        ]
    )

    assert args.start_date == date(2026, 7, 1)
    assert args.end_date == date(2026, 7, 31)
    assert args.skip_existing is False