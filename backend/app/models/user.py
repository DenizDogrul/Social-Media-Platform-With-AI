from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    bio = Column(String(300), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    cover_url = Column(String(500), nullable=True)
    is_private = Column(Integer, default=0, nullable=False)  # 0=public, 1=private
    allow_dms_from = Column(String(20), default="everyone", nullable=False)  # "everyone", "followers", "none"
    is_verified = Column(Integer, default=0, nullable=False)
    is_admin = Column(Integer, default=0, nullable=False)

    posts = relationship("Post", back_populates="author")
    stories = relationship("Story", back_populates="author", cascade="all, delete-orphan")
    followers = relationship("Follow", foreign_keys="[Follow.following_id]", back_populates="following")
    following = relationship("Follow", foreign_keys="[Follow.follower_id]", back_populates="follower")
    liked_posts = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)