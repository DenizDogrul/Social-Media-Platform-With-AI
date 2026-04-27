from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.settings import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_FOLDER,
    MEDIA_BASE_URL,
    MEDIA_UPLOAD_ROOT,
    STORAGE_BACKEND,
)


ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/webm",
    "video/quicktime",
}

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".mov"}


@dataclass
class StoredMedia:
    media_url: str
    media_type: str
    thumbnail_url: str | None = None


def _expected_mime_by_magic(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return "image/gif"
    if len(content) > 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if len(content) > 12 and content[4:8] == b"ftyp":
        brand = content[8:12]
        if brand in {b"isom", b"mp41", b"mp42", b"avc1"}:
            return "video/mp4"
        if brand in {b"qt  "}:
            return "video/quicktime"
    if content.startswith(b"\x1aE\xdf\xa3"):
        return "video/webm"
    return None


def validate_upload(declared_mime: str, ext: str, content: bytes) -> None:
    if declared_mime not in ALLOWED_MIME:
        raise ValueError("Unsupported media type")
    if ext not in ALLOWED_EXT:
        raise ValueError("Unsupported file extension")

    detected = _expected_mime_by_magic(content)
    if detected is None:
        raise ValueError("Unable to validate media signature")

    image_pair_ok = declared_mime.startswith("image/") and detected.startswith("image/")
    video_pair_ok = declared_mime.startswith("video/") and detected.startswith("video/")
    if not (image_pair_ok or video_pair_ok):
        raise ValueError("Media signature does not match declared type")


class LocalMediaStorage:
    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parents[2] / MEDIA_UPLOAD_ROOT
        self.posts_dir = self.root / "posts"
        self.thumb_dir = self.root / "thumbnails"
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.thumb_dir.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, ext: str, content_type: str) -> StoredMedia:
        file_name = f"{uuid4().hex}{ext}"
        media_path = self.posts_dir / file_name
        media_path.write_bytes(content)

        media_url = f"{MEDIA_BASE_URL}/posts/{file_name}".replace("//", "/")
        media_type = "image" if content_type.startswith("image/") else "video"

        thumbnail_url: str | None = None
        if media_type == "image":
            thumb_name = f"{Path(file_name).stem}_thumb.jpg"
            thumb_path = self.thumb_dir / thumb_name
            try:
                with Image.open(BytesIO(content)) as image:
                    image = image.convert("RGB")
                    image.thumbnail((560, 560))
                    image.save(thumb_path, format="JPEG", quality=82, optimize=True, progressive=True)
                    thumbnail_url = f"{MEDIA_BASE_URL}/thumbnails/{thumb_name}".replace("//", "/")
            except UnidentifiedImageError:
                thumbnail_url = media_url

        return StoredMedia(media_url=media_url, media_type=media_type, thumbnail_url=thumbnail_url)


class CloudinaryMediaStorage:
    def __init__(self) -> None:
        if not (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET):
            raise RuntimeError("Cloudinary settings are incomplete")

        import cloudinary

        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True,
        )

    def save(self, content: bytes, ext: str, content_type: str) -> StoredMedia:
        import cloudinary.uploader
        import cloudinary.utils

        media_type = "image" if content_type.startswith("image/") else "video"
        public_id = uuid4().hex

        upload_result = cloudinary.uploader.upload(
            BytesIO(content),
            resource_type=("image" if media_type == "image" else "video"),
            folder=CLOUDINARY_FOLDER,
            public_id=public_id,
            overwrite=False,
        )

        uploaded_public_id = upload_result.get("public_id")
        if not uploaded_public_id:
            raise RuntimeError("Cloudinary upload failed")

        if media_type == "image":
            media_url = cloudinary.utils.cloudinary_url(
                uploaded_public_id,
                secure=True,
                transformation=[
                    {"fetch_format": "auto", "quality": "auto:good"},
                ],
            )[0]
        else:
            media_url = cloudinary.utils.cloudinary_url(
                uploaded_public_id,
                resource_type="video",
                secure=True,
                transformation=[
                    {"quality": "auto"},
                ],
            )[0]

        thumbnail_url: str | None = None
        if media_type == "image":
            thumbnail_url = cloudinary.utils.cloudinary_url(
                uploaded_public_id,
                secure=True,
                transformation=[
                    {"width": 1200, "crop": "limit", "fetch_format": "auto", "quality": "auto:good"}
                ],
            )[0]
        else:
            thumbnail_url = cloudinary.utils.cloudinary_url(
                uploaded_public_id,
                resource_type="video",
                secure=True,
                transformation=[{"start_offset": "1", "width": 1200, "crop": "limit"}],
                format="jpg",
            )[0]

        return StoredMedia(media_url=media_url, media_type=media_type, thumbnail_url=thumbnail_url)


def get_media_storage() -> LocalMediaStorage | CloudinaryMediaStorage:
    if STORAGE_BACKEND == "cloudinary":
        return CloudinaryMediaStorage()
    return LocalMediaStorage()
