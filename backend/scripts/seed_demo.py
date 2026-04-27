import sys
from pathlib import Path

# backend kökünü sys.path'e ekle (script doğrudan çalıştırıldığında)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import configure_mappers
from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.post import Post
from app.models.follow import Follow  # noqa: F401
from app.models.like import Like  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.comment import Comment  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message  # noqa: F401

configure_mappers()

def main():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for i in range(1, 6):
            username = f"demo{i}"
            email = f"demo{i}@test.com"
            user = db.query(User).filter(User.username == username).first()
            if not user:
                user = User(username=username, email=email)
                user.set_password("Test1234!")
                db.add(user)
                db.commit()
                db.refresh(user)

            p = Post(title=f"Demo Post {i}", content="Seed content")
            if hasattr(Post, "user_id"):
                p.user_id = user.id
            elif hasattr(Post, "author_id"):
                p.author_id = user.id
            elif hasattr(Post, "owner_id"):
                p.owner_id = user.id
            db.add(p)

        db.commit()
        print("seed done")
    finally:
        db.close()

if __name__ == "__main__":
    main()