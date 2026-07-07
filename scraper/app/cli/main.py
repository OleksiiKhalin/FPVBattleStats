from __future__ import annotations

import argparse
from datetime import date

from ..logging import configure_logging
from ..services.scraper import BattleScraperService


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Date must be in YYYY-MM-DD format.") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FPVBattle scraper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    historical = subparsers.add_parser("sync-historical", help="Backfill historical results.")
    historical.add_argument("--end-date", type=_parse_date, default=None, help="Inclusive end date in YYYY-MM-DD format.")
    historical.add_argument(
        "--skip-existing",
        dest="skip_existing",
        action="store_true",
        default=True,
        help="Skip days already present in the database.",
    )
    historical.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="Force re-sync even if a day already exists.",
    )

    current = subparsers.add_parser("sync-current", help="Sync the active current UTC race day.")

    sync_day = subparsers.add_parser("sync-day", help="Sync one explicit date and class.")
    sync_day.add_argument("target_date", type=_parse_date, help="Target date in YYYY-MM-DD format.")
    sync_day.add_argument("--class", dest="race_class", choices=["open", "whoop"], default="open")

    return parser


def main() -> None:
    configure_logging()
    parser = _build_parser()
    args = parser.parse_args()

    service = BattleScraperService()
    try:
        if args.command == "sync-historical":
            service.sync_historical(end_date=args.end_date, skip_existing=args.skip_existing)
        elif args.command == "sync-current":
            service.sync_current_window()
        elif args.command == "sync-day":
            service.sync_day(target_date=args.target_date, race_class=args.race_class)
        else:
            parser.error(f"Unknown command: {args.command}")
    finally:
        service.close()


if __name__ == "__main__":
    main()
