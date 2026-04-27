from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(String(1000), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    author = relationship("User", back_populates="posts")
    tags = relationship("PostTag", back_populates="post")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    media_items = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan")
    bookmarked_by = relationship("Bookmark", back_populates="post", cascade="all, delete-orphan")

class TopicTag(Base):
    __tablename__ = "topic_tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    posts = relationship("PostTag", back_populates="tag")

class PostTag(Base):
    __tablename__ = "post_tags"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    tag_id = Column(Integer, ForeignKey("topic_tags.id"))
    post = relationship("Post", back_populates="tags")
    tag = relationship("TopicTag", back_populates="posts")


class PostMedia(Base):
    __tablename__ = "post_media"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    media_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    media_type = Column(String(20), nullable=False)

    post = relationship("Post", back_populates="media_items")