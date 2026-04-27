from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from app.settings import DATABASE_URL, TEST_DATABASE_URL, IS_TEST_ENV

resolved_database_url = TEST_DATABASE_URL if IS_TEST_ENV else DATABASE_URL

engine_kwargs = {}
if resolved_database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(resolved_database_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()