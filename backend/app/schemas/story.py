from pydantic import BaseModel
from datetime import datetime

class StoryCreate(BaseModel):
    content: str
    media_url: str | None = None
    media_type: str | None = None  # "image" or "video"


class StoryResponse(BaseModel):
    id: int
    author_id: int
    author_username: str | None = None
    content: str
    media_url: str | None = None
    media_type: str | None = None
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True
