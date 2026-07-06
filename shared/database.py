from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from shared.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine_kwargs = {'future': True}
if settings.database_url.startswith('postgresql'):
    engine_kwargs['connect_args'] = {'connect_timeout': 2}
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
