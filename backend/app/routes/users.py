from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, cast, String
from datetime import datetime, timedelta, UTC
from uuid import uuid4
import logging
from jose import jwt, JWTError

from app.database import SessionLocal
from app.models.user import User
from app.models.post import Post, TopicTag, PostTag
from app.models.refresh_token import RefreshToken
from app.models.follow import Follow
from app.models.moderation import UserBlock
from app.services.notifications import create_notification
from app.services.rate_limit import apply_rate_limit
from app.auth import create_access_token, create_refresh_token, hash_token, get_current_user
from app.settings import SECRET_KEY, ALGORITHM, REFRESH_TOKEN_EXPIRE_DAYS, ADMIN_BOOTSTRAP_USER_IDS

router = APIRouter(prefix="/users", tags=["users"]) #Bu dosyadaki tüm endpointler /users ile başlayacak
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_badges(user_id: int, db: Session, limit: int = 3) -> list[str]:
    """Get top N tags by post count for a user."""
    badges = (
        db.query(TopicTag.name, func.count(PostTag.id).label("tag_count"))
        .join(PostTag, PostTag.tag_id == TopicTag.id)
        .join(Post, Post.id == PostTag.post_id)
        .filter(Post.author_id == user_id)
        .group_by(TopicTag.id, TopicTag.name)
        .order_by(func.count(PostTag.id).desc())
        .limit(limit)
        .all()
    )
    return [tag_name for tag_name, _count in badges] #Kullanıcının en çok kullandığı tag’leri buluyor 

class RegisterRequest(BaseModel): #Bunlar API’ye gelen ve giden verinin formatını belirler. mesela deniz emaili ve şifresi gelince onları str diye ayırıyo 
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class ProfileUpdateRequest(BaseModel):
    bio: str | None = None
    avatar_url: str | None = None
    cover_url: str | None = None
    is_private: bool | None = None
    allow_dms_from: str | None = None  # "everyone", "followers", "none"


@router.post("/register", status_code=201) #Bu endpoint yeni kullanıcı kaydı için. Gelen veriyi RegisterRequest formatında bekliyor. Veritabanında kullanıcı oluşturuyor ve oluşturulan kullanıcının id, username ve email’ini döndürüyor.
def register_user(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    apply_rate_limit(request, bucket="users_register", limit=15, window_seconds=60)
    exists = db.query(User).filter(
        (User.username == payload.username) | (User.email == payload.email)
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = User(username=payload.username, email=payload.email)
    user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "email": user.email}


@router.get("/me") #Bu endpoint şu anki kullanıcı bilgilerini döndürüyor. get_current_user fonksiyonu ile kim olduğunu anlıyor ve ona göre bilgileri döndürüyor.
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    badges = get_user_badges(current_user.id, db)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "cover_url": current_user.cover_url,
        "is_private": bool(current_user.is_private),
        "allow_dms_from": current_user.allow_dms_from,
        "is_verified": bool(current_user.is_verified),
        "is_admin": bool(current_user.is_admin) or current_user.id in ADMIN_BOOTSTRAP_USER_IDS,
        "badges": badges,
    }


@router.patch("/me", summary="Update my profile") #Bu endpoint şu anki kullanıcının profilini günceller. Gelen veriye göre bio, avatar_url, cover_url, is_private ve allow_dms_from alanlarını günceller.
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.bio is not None:
        current_user.bio = payload.bio[:300]
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    if payload.cover_url is not None:
        current_user.cover_url = payload.cover_url
    if payload.is_private is not None:
        current_user.is_private = 1 if payload.is_private else 0
    if payload.allow_dms_from is not None:
        if payload.allow_dms_from not in ["everyone", "followers", "none"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid allow_dms_from value")
        current_user.allow_dms_from = payload.allow_dms_from
    db.commit()
    db.refresh(current_user)
    badges = get_user_badges(current_user.id, db)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "cover_url": current_user.cover_url,
        "is_private": bool(current_user.is_private),
        "allow_dms_from": current_user.allow_dms_from,
        "badges": badges,
    }


@router.get("/search", summary="Unified search: users, tags, posts") #Bu endpoint gelen q parametresine göre kullanıcı, tag ve post araması yapar. Kullanıcı adında veya biyografisinde q geçen kullanıcıları, adında q geçen tagleri ve başlığında, içeriğinde veya yazarının kullanıcı adında q geçen postları döndürür.
def unified_search(
    q: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = q.strip() #Eğer q boşsa veya çok uzunsa arama yapmadan boş sonuç döndürüyor. Bu, gereksiz veritabanı sorgularını önlemek için yapılır.
    if not q or len(q) > 100:
        return {"users": [], "tags": [], "posts": []}

    pattern = f"%{q}%"

    users = (
        db.query(User)
        .filter(or_(User.username.ilike(pattern), User.bio.ilike(pattern)))
        .limit(8)
        .all()
    )

    tags = (
        db.query(TopicTag)
        .filter(TopicTag.name.ilike(pattern))
        .limit(8)
        .all()
    )

    posts = (
        db.query(Post)
        .join(User, Post.author_id == User.id)
        .filter(
            or_(
                Post.title.ilike(pattern),
                Post.content.ilike(pattern),
                User.username.ilike(pattern),
            )
        )
        .order_by(Post.created_at.desc())
        .limit(10)
        .all()
    )

    user_results = [] #Kullanıcı sonuçlarını hazırlarken her kullanıcı için get_user_badges fonksiyonunu çağırarak o kullanıcının en çok kullandığı tag’leri de alıyor ve sonuçlara ekliyor. Böylece arama sonuçlarında kullanıcıların hangi konularda aktif olduğunu da görebiliyoruz.
    for u in users:
        badges = get_user_badges(u.id, db, limit=2)
        user_results.append({
            "id": u.id,
            "username": u.username,
            "bio": u.bio,
            "avatar_url": u.avatar_url,
            "is_verified": bool(u.is_verified),
            "badges": badges,
        })

    return {
        "users": user_results,
        "tags": [{"name": t.name} for t in tags],
        "posts": [
            {
                "post_id": p.id,
                "title": p.title,
                "content": p.content[:120],
                "author_username": p.author.username,
                "author_id": p.author_id,
            }
            for p in posts
        ],
    }


@router.get("/{user_id}") #Bu endpoint belirli bir kullanıcının profilini döndürüyor. user_id parametresine göre kullanıcıyı buluyor ve onun bilgilerini, takipçi sayısını, takip ettiği kişi sayısını, gönderi sayısını, o kullanıcıyı takip edip etmediğimizi ve o kullanıcının en çok kullandığı tag’leri döndürüyor.
def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    followers_count = db.query(func.count(Follow.id)).filter(Follow.following_id == user_id).scalar() or 0
    following_count = db.query(func.count(Follow.id)).filter(Follow.follower_id == user_id).scalar() or 0
    posts_count = db.query(func.count(Post.id)).filter(Post.author_id == user_id).scalar() or 0

    is_following = db.query(Follow).filter_by(follower_id=current_user.id, following_id=user_id).first() is not None
    badges = get_user_badges(user_id, db)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "cover_url": user.cover_url,
        "followers_count": int(followers_count),
        "following_count": int(following_count),
        "posts_count": int(posts_count),
        "is_following": bool(is_following),
        "is_me": user.id == current_user.id,
        "is_private": bool(user.is_private),
        "is_verified": bool(user.is_verified),
        "badges": badges,
    }


@router.get("/discover/follow-suggestions") #Bu endpoint, kullanıcının takip edebileceği önerilen kullanıcıları döndürüyor. Kullanıcının takip ettiği kişileri ve ilgi alanlarını dikkate alarak öneriler oluşturuyor.
def follow_suggestions(
    limit: int = 8,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    followed_ids = [
        value
        for (value,) in db.query(Follow.following_id).filter(Follow.follower_id == current_user.id).all()
    ]
    current_user_tags = {
        name
        for (name,) in (
            db.query(TopicTag.name)
            .join(PostTag, PostTag.tag_id == TopicTag.id)
            .join(Post, Post.id == PostTag.post_id)
            .filter(Post.author_id == current_user.id)
            .distinct()
            .all()
        )
    }

    candidate_users = (
        db.query(User)
        .filter(User.id != current_user.id)
        .filter(~User.id.in_(followed_ids or [-1]))
        .limit(40)
        .all()
    )

    suggestions = []
    recent_cutoff = datetime.now(UTC) - timedelta(days=14)
    for candidate in candidate_users:
        followers_count = db.query(func.count(Follow.id)).filter(Follow.following_id == candidate.id).scalar() or 0
        recent_posts = db.query(func.count(Post.id)).filter(Post.author_id == candidate.id, Post.created_at >= recent_cutoff).scalar() or 0
        candidate_tags = {
            name
            for (name,) in (
                db.query(TopicTag.name)
                .join(PostTag, PostTag.tag_id == TopicTag.id)
                .join(Post, Post.id == PostTag.post_id)
                .filter(Post.author_id == candidate.id)
                .distinct()
                .limit(10)
                .all()
            )
        }
        shared_tags = len(current_user_tags & candidate_tags)
        score = (followers_count * 1.0) + (recent_posts * 2.0) + (shared_tags * 4.0) + (3.0 if candidate.is_verified else 0.0) #algoritmnın kalbi burası en çok önemli olan ortak ilgi alanı 

        reason = "Popular creator"
        if shared_tags > 0:
            reason = f"{shared_tags} shared interests"
        elif recent_posts > 0:
            reason = "Recently active"

        suggestions.append({
            "id": candidate.id,
            "username": candidate.username,
            "email": candidate.email,
            "is_verified": bool(candidate.is_verified),
            "reason": reason,
            "score": round(score, 2), #sonra skora göre öneriliyor
        })

    suggestions.sort(key=lambda item: (item["score"], item["id"]), reverse=True)
    return suggestions[:limit]


@router.post("/{user_id}/follow", summary="Follow a user") #Bu endpoint, belirli bir kullanıcıyı takip etmeyi sağlar. user_id parametresine göre kullanıcıyı bulur ve mevcut kullanıcıyı takip etmeye çalışır.
async def follow_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    apply_rate_limit(request, bucket="users_follow", limit=40, window_seconds=60, user_id=current_user.id)
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    has_block = (  #biri birini enfelldiyse follow olmaz 
        db.query(UserBlock)
        .filter(
            ((UserBlock.blocker_id == current_user.id) & (UserBlock.blocked_id == user_id))
            | ((UserBlock.blocker_id == user_id) & (UserBlock.blocked_id == current_user.id))
        )
        .first()
    )
    if has_block:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Follow unavailable due to block settings")

    existing_follow = db.query(Follow).filter_by(follower_id=current_user.id, following_id=user_id).first()
    if existing_follow:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already following this user")

    follow = Follow(follower_id=current_user.id, following_id=user_id)
    db.add(follow)
    db.commit()

    try:
        await create_notification(
            db,
            user_id=user_id,
            event_type="new_follower",
            title="You have a new follower",
            body=f"@{current_user.username} started following you.",
        )
    except Exception:
        logger.exception("Follow notification delivery failed", extra={"follower_id": current_user.id, "following_id": user_id})

    return {"message": "Followed successfully"}

@router.post("/{user_id}/unfollow", summary="Unfollow a user") #Bu endpoint, belirli bir kullanıcıyı takipten çıkarmayı sağlar. user_id parametresine göre kullanıcıyı bulur ve mevcut kullanıcının o kullanıcıyı takip etmesini kaldırır.
def unfollow_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    apply_rate_limit(request, bucket="users_unfollow", limit=40, window_seconds=60, user_id=current_user.id)
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    follow = db.query(Follow).filter_by(follower_id=current_user.id, following_id=user_id).first()
    if not follow:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not following this user")

    db.delete(follow)
    db.commit()
    return {"message": "Unfollowed successfully"}

@router.get("/{user_id}/followers", summary="Get followers of a user")
def get_followers(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    followers = (
        db.query(User)
        .join(Follow, Follow.follower_id == User.id)
        .filter(Follow.following_id == user_id)
        .all()
    )
    return [{"id": f.id, "username": f.username} for f in followers]

@router.get("/{user_id}/following", summary="Get users followed by a user")
def get_following(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    following = (
        db.query(User)
        .join(Follow, Follow.following_id == User.id)
        .filter(Follow.follower_id == user_id)
        .all()
    )
    return [{"id": f.id, "username": f.username} for f in following]


@router.post("/refresh") #Bu endpoint, access token’ı yenilemek için kullanılır. Gelen refresh token’ı doğrular, geçerliyse yeni bir access token ve refresh token oluşturur ve döndürür. Eski refresh token’ı da geçersiz hale getirir.
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        username = data.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    old = db.query(RefreshToken).filter(
        RefreshToken.token_hash == hash_token(payload.refresh_token),
        RefreshToken.revoked.is_(False),
    ).first()

    if not old:
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    old_exp = old.expires_at
    if old_exp.tzinfo is not None:
        old_exp = old_exp.astimezone(UTC).replace(tzinfo=None)

    if old_exp < _utcnow_naive():
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    old.revoked = True
    new_access = create_access_token({"sub": user.username, "type": "access"})
    new_refresh = create_refresh_token({"sub": user.username, "type": "refresh", "jti": str(uuid4())})

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh),
            expires_at=_utcnow_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            revoked=False,
        )
    )
    db.commit()

    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}

@router.post("/logout") #Bu endpoint, kullanıcının refresh token'ını geçersiz kılarak çıkış yapmasını sağlar.
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    row = db.query(RefreshToken).filter(
        RefreshToken.token_hash == hash_token(payload.refresh_token),
        RefreshToken.revoked.is_(False),
    ).first()
    if row:
        row.revoked = True
        db.commit()
    return {"message": "Logged out"}

@router.post("/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    apply_rate_limit(request, bucket="users_login", limit=10, window_seconds=60)
    identifier = payload.username.strip()
    user = db.query(User).filter(
        or_(
            func.lower(User.username) == identifier.lower(),
            func.lower(User.email) == identifier.lower(),
        )
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.verify_password(payload.password):  # check_password -> verify_password
        raise HTTPException(status_code=400, detail="Invalid password")

    access_token = create_access_token({"sub": user.username, "type": "access"})
    refresh_token = create_refresh_token({"sub": user.username, "type": "refresh", "jti": str(uuid4())})

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=_utcnow_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            revoked=False,
        )
    )
    db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)