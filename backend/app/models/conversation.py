from datetime import datetime, UTC
from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("user1_id", "user2_id", name="uq_conversation_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user1_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user2_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))