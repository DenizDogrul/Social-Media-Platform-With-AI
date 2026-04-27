import os
import pytest

# Force isolated test DB before importing app.database
os.environ["APP_ENV"] = "test"
os.environ.setdefault("TEST_DATABASE_URL", "sqlite:///./test_suite.db")

from app.database import engine, Base

# modellerin import edilmesi lazım ki metadata dolsun
from app.models.user import User  # noqa: F401
from app.models.post import Post, TopicTag, PostTag  # noqa: F401
from app.models.like import Like  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()