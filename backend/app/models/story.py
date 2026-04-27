from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String(500), nullable=False)  # Short text content
    media_url = Column(String(500), nullable=True)
    media_type = Column(String(20), nullable=True)  # "image" or "video"
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)  # 24 hours from creation

    author = relationship("User", back_populates="stories")
