"""
database.py : la connexion à la base de données.

- engine : le "câble" vers PostgreSQL.
- SessionLocal : une fabrique de sessions. Une session = une conversation avec la base
  le temps d'une requête (on lit, on écrit, puis on valide avec commit).
- Base : la classe mère de tous nos modèles (tables).
- get_db : une "dépendance" FastAPI qui ouvre une session par requête et la ferme après.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import reglages

engine = create_engine(reglages.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Toutes les tables héritent de cette classe."""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()  # en cas d'erreur, on annule tout ce qui n'a pas été validé
        raise
    finally:
        db.close()
