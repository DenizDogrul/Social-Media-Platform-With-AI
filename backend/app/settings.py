import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", os.getenv("ALGORITHM", "HS256"))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
DEBUG = APP_ENV != "production"
IS_TEST_ENV = APP_ENV == "test" or bool(os.getenv("PYTEST_CURRENT_TEST"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
if DATABASE_URL.startswith("sqlite:///"):
    sqlite_path = DATABASE_URL.replace("sqlite:///", "", 1)
    if sqlite_path.startswith("./") or sqlite_path.startswith(".\\"):
        backend_dir = Path(__file__).resolve().parents[1]
        normalized = (backend_dir / sqlite_path[2:]).resolve()
        DATABASE_URL = f"sqlite:///{normalized.as_posix()}"

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_suite.db")
if TEST_DATABASE_URL.startswith("sqlite:///"):
    sqlite_test_path = TEST_DATABASE_URL.replace("sqlite:///", "", 1)
    if sqlite_test_path.startswith("./") or sqlite_test_path.startswith(".\\"):
        backend_dir = Path(__file__).resolve().parents[1]
        normalized_test = (backend_dir / sqlite_test_path[2:]).resolve()
        TEST_DATABASE_URL = f"sqlite:///{normalized_test.as_posix()}"

DB_BACKUP_ON_START = os.getenv("DB_BACKUP_ON_START", "1").strip() not in {"0", "false", "False"}
DB_BACKUP_DIR = os.getenv("DB_BACKUP_DIR", "./backups")
DB_BACKUP_KEEP = int(os.getenv("DB_BACKUP_KEEP", "14"))

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ORIGINS = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "/media")
MEDIA_UPLOAD_ROOT = os.getenv("MEDIA_UPLOAD_ROOT", "uploads")

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "nebula")
AMBIENT_INGEST_KEY = os.getenv("AMBIENT_INGEST_KEY", "")

FOLLOWED_FEED_RATIO = float(os.getenv("FOLLOWED_FEED_RATIO", "0.7"))
_admin_bootstrap_ids = os.getenv("ADMIN_BOOTSTRAP_USER_IDS", "1")
ADMIN_BOOTSTRAP_USER_IDS = [
    int(value.strip())
    for value in _admin_bootstrap_ids.split(",")
    if value.strip().isdigit()
]
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PRIVATE_KEY_PATH = os.getenv("VAPID_PRIVATE_KEY_PATH", "")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@nebula.local")

if not VAPID_PRIVATE_KEY and VAPID_PRIVATE_KEY_PATH:
    private_key_path = Path(VAPID_PRIVATE_KEY_PATH)
    if not private_key_path.is_absolute():
        private_key_path = Path(__file__).resolve().parents[1] / private_key_path
    if private_key_path.exists():
        VAPID_PRIVATE_KEY = private_key_path.read_text(encoding="utf-8")

PUSH_NOTIFICATIONS_ENABLED = bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY and VAPID_SUBJECT)

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set. Add it to .env")