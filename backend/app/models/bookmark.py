from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)

    user = relationship("User", back_populates="bookmarks")
    post = relationship("Post", back_populates="bookmarked_by")

    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="unique_bookmark"),
    )
