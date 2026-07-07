from fpvbattle_core.db.session import create_db_engine, create_session_factory, init_db

from ..core.config import settings

engine = create_db_engine(settings.database_url)
SessionFactory = create_session_factory(engine)


def bootstrap_database() -> None:
    init_db(engine)
