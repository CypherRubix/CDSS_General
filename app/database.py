from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def redact_url_password(database_url: str) -> str:
    try:
        parsed = make_url(database_url)
    except Exception:
        return database_url
    if parsed.password:
        parsed.password = "***redacted***"
    return str(parsed)


def build_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    if not url:
        raise RuntimeError("CDSS_DATABASE_URL is not configured. Set it in the .env file or environment.")
    try:
        make_url(url)
    except Exception as exc:  # pragma: no cover - validation branch
        raise RuntimeError(
            "Invalid database URL in CDSS_DATABASE_URL. Expected a SQLAlchemy URL such as "
            "mysql+pymysql://user:password@host:3306/database. "
            f"Received: {redact_url_password(url)}"
        ) from exc
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=get_settings().sql_echo, future=True, connect_args=connect_args)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database connection failed. Check that MySQL is running and CDSS_DATABASE_URL is correct: "
            f"{redact_url_password(get_settings().database_url)}"
        ) from exc
    Base.metadata.create_all(bind=engine)
