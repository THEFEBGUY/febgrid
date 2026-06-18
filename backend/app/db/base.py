from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Alembic can discover all metadata from Base.
from app.models import *  # noqa: E402,F403
