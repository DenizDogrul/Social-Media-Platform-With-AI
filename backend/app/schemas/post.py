from pydantic import BaseModel

class PostCreate(BaseModel):
    title: str
    content: str
    media_url: str | None = None
    thumbnail_url: str | None = None
    media_type: str | None = None


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    media_type: str | None = None