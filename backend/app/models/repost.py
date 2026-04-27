from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime


class Repost(Base):
    __tablename__ = "reposts"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    original_post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    comment = Column(String(500), nullable=True)  # Optional quote/comment on repost (Twitter quote RT style)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    post = relationship("Post", foreign_keys=[post_id])
    original_post = relationship("Post", foreign_keys=[original_post_id])
    author = relationship("User")
