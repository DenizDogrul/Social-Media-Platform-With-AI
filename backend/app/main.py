from pathlib import Path
from datetime import datetime
import shutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from sqlalchemy import inspect, text
from sqlalchemy.orm import configure_mappers

from app.database import engine, Base
from app.models.user import User
from app.models.post import Post, TopicTag, PostTag, PostMedia
from app.models.story import Story
from app.models.like import Like
from app.models.bookmark import Bookmark
from app.models.follow import Follow  # noqa: F401
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.refresh_token import RefreshToken
from app.models.moderation import Report, UserBlock, UserMute
from app.models.comment import Comment  # noqa: F401
from app.models.comment_like import CommentLike  # noqa: F401 – registers table for create_all
from app.models.message import Message  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.repost import Repost  # noqa: F401 – registers table for create_all
from app.settings import (
    SECRET_KEY,
    ALGORITHM,
    AMBIENT_INGEST_KEY,
    CORS_ORIGINS,
    DEBUG,
    DATABASE_URL,
    DB_BACKUP_ON_START,
    DB_BACKUP_DIR,
    DB_BACKUP_KEEP,
    IS_TEST_ENV,
)

from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.posts import router as posts_router
from app.routes.comments import router as comments_router
from app.routes.stories import router as stories_router
from app.routes.messages import router as messages_router
from app.routes.notifications import router as notifications_router
from app.routes.moderation import router as moderation_router
from app.routes.analytics import router as analytics_router
from app.routes.admin import router as admin_router
from app.services.realtime import notification_hub, ambient_hub, message_hub
from fastapi.middleware.cors import CORSMiddleware

configure_mappers()


def maybe_backup_sqlite_db() -> None:
    if not DB_BACKUP_ON_START or IS_TEST_ENV:
        return
    if not DATABASE_URL.startswith("sqlite:///"):
        return

    db_path = Path(DATABASE_URL.replace("sqlite:///", "", 1))
    if not db_path.exists() or db_path.suffix != ".db":
        return

    backup_dir = Path(DB_BACKUP_DIR)
    if not backup_dir.is_absolute():
        backup_dir = Path(__file__).resolve().parents[1] / backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{db_path.stem}_auto_{timestamp}.db"
    shutil.copy2(db_path, backup_dir / backup_name)

    backups = sorted(backup_dir.glob(f"{db_path.stem}_auto_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old_backup in backups[DB_BACKUP_KEEP:]:
        try:
            old_backup.unlink()
        except OSError:
            pass


app = FastAPI(debug=DEBUG)
Base.metadata.create_all(bind=engine)
maybe_backup_sqlite_db()


def ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    statements: list[str] = []
    if "is_verified" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
    if "is_admin" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

    if "comments" in inspector.get_table_names():
        comment_columns = {column["name"] for column in inspector.get_columns("comments")}
        if "parent_id" not in comment_columns:
            statements.append("ALTER TABLE comments ADD COLUMN parent_id INTEGER")

    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))


ensure_runtime_schema()

upload_dir = Path(__file__).resolve().parents[1] / "uploads"
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=upload_dir), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(stories_router)
app.include_router(messages_router)
app.include_router(notifications_router)
app.include_router(moderation_router)
app.include_router(analytics_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {"message": "Backend running"}


@app.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        token_type = payload.get("type")
        if not username or (token_type is not None and token_type != "access"):
            await websocket.close(code=1008)
            return
    except JWTError:
        await websocket.close(code=1008)
        return

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await websocket.close(code=1008)
            return

        await notification_hub.connect(user.id, websocket)
        await websocket.send_json({"type": "connected", "user_id": user.id})
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if 'user' in locals() and user:
            notification_hub.disconnect(user.id, websocket)
    finally:
        db.close()


@app.websocket("/ws/messages")
async def messages_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        token_type = payload.get("type")
        if not username or (token_type is not None and token_type != "access"):
            await websocket.close(code=1008)
            return
    except JWTError:
        await websocket.close(code=1008)
        return

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await websocket.close(code=1008)
            return

        await message_hub.connect(user.id, websocket)
        await websocket.send_json({"type": "connected", "user_id": user.id})
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if 'user' in locals() and user:
            message_hub.disconnect(user.id, websocket)
    finally:
        db.close()


@app.websocket("/ws/ambient")
async def ambient_ws(websocket: WebSocket):
    await ambient_hub.connect(websocket)
    latest = ambient_hub.latest_lux()
    if latest is not None:
        await websocket.send_json({"type": "lux", "lux": latest, "source": "cache"})

    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ambient_hub.disconnect(websocket)


@app.websocket("/ws/ambient/ingest")
async def ambient_ingest_ws(websocket: WebSocket):
    provided_key = websocket.query_params.get("key", "")
    if AMBIENT_INGEST_KEY and provided_key != AMBIENT_INGEST_KEY:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    await websocket.send_json({"type": "connected", "channel": "ambient-ingest"})

    try:
        while True:
            payload = await websocket.receive_json()
            lux_raw = payload.get("lux")
            if not isinstance(lux_raw, (int, float)):
                continue

            lux = max(0.0, min(10000.0, float(lux_raw)))
            await ambient_hub.broadcast_lux(lux)
    except WebSocketDisconnect:
        return