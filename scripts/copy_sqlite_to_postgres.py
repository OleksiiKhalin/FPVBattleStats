from __future__ import annotations

import argparse
from collections.abc import Iterable

from sqlalchemy import MetaData, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from fpvbattle_core.db.models import DaySpecModel, PilotModel, ResultModel, SeasonLeaderboardModel
from fpvbattle_core.db.session import create_db_engine

TABLES_IN_COPY_ORDER = [
    PilotModel.__table__,
    DaySpecModel.__table__,
    ResultModel.__table__,
    SeasonLeaderboardModel.__table__,
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copy FPVBattle data from a SQLite database into a PostgreSQL database.",
    )
    parser.add_argument("--source", required=True, help="SQLite SQLAlchemy URL, for example sqlite:///data/fpvbattle.db")
    parser.add_argument(
        "--target",
        required=True,
        help="PostgreSQL SQLAlchemy URL, for example postgresql+psycopg://user:pass@host/db",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Delete all FPVBattle tables in the target database before copying.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="How many rows to stream from SQLite per batch.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm that the target database should be modified.",
    )
    return parser


def validate_urls(source_engine: Engine, target_engine: Engine) -> None:
    if not source_engine.url.drivername.startswith("sqlite"):
        raise ValueError("Source database must be SQLite.")
    if not target_engine.url.drivername.startswith("postgresql"):
        raise ValueError("Target database must be PostgreSQL.")


def table_row_count(engine: Engine, table_name: str) -> int:
    metadata = MetaData()
    metadata.reflect(bind=engine, only=[table_name])
    table = metadata.tables[table_name]
    with engine.connect() as connection:
        return connection.execute(select(func.count()).select_from(table)).scalar_one()


def ensure_target_is_empty(engine: Engine) -> None:
    row_count = sum(table_row_count(engine, table.name) for table in TABLES_IN_COPY_ORDER)
    if row_count:
        raise ValueError(
            "Target database already contains FPVBattle rows. Re-run with --truncate-target to replace them.",
        )


def truncate_target(connection) -> None:
    table_names = ", ".join(table.name for table in reversed(TABLES_IN_COPY_ORDER))
    connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


def reset_postgres_sequences(connection) -> None:
    for table in TABLES_IN_COPY_ORDER:
        if "id" not in table.c:
            continue
        sequence_name = connection.execute(
            text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
            {"table_name": table.name},
        ).scalar_one()
        if sequence_name is None:
            continue
        connection.execute(
            text(
                """
                SELECT setval(
                    :sequence_name,
                    COALESCE((SELECT MAX(id) FROM """ + table.name + """), 1),
                    (SELECT COUNT(*) > 0 FROM """ + table.name + """)
                )
                """,
            ),
            {"sequence_name": sequence_name},
        )


def iter_rows(engine: Engine, table, batch_size: int) -> Iterable[list[dict[str, object]]]:
    with engine.connect() as connection:
        result = connection.execution_options(stream_results=True).execute(select(table))
        while True:
            chunk = result.fetchmany(batch_size)
            if not chunk:
                break
            yield [dict(row._mapping) for row in chunk]


def copy_tables(source_engine: Engine, target_engine: Engine, *, batch_size: int, truncate: bool) -> None:
    with target_engine.begin() as target_connection:
        if truncate:
            truncate_target(target_connection)
        else:
            ensure_target_is_empty(target_engine)

        for table in TABLES_IN_COPY_ORDER:
            inserted = 0
            for chunk in iter_rows(source_engine, table, batch_size):
                if chunk:
                    target_connection.execute(table.insert(), chunk)
                    inserted += len(chunk)
            print(f"Copied {inserted} rows into {table.name}.")
        reset_postgres_sequences(target_connection)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.yes:
        parser.error("Pass --yes to confirm the target database should be modified.")

    source_engine = create_db_engine(args.source)
    target_engine = create_db_engine(args.target)

    try:
        validate_urls(source_engine, target_engine)
        copy_tables(
            source_engine,
            target_engine,
            batch_size=args.batch_size,
            truncate=args.truncate_target,
        )
    except (SQLAlchemyError, ValueError) as exc:
        print(f"Copy failed: {exc}")
        return 1
    finally:
        source_engine.dispose()
        target_engine.dispose()

    print("Copy complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
