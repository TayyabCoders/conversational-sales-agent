from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    All models must inherit from this class to be included in migrations.
    """
    pass
