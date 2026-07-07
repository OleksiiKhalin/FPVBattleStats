from collections.abc import Generator

from sqlalchemy.orm import Session

from ..db.bootstrap import SessionFactory


def get_session() -> Generator[Session, None, None]:
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
