from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.story import Story
from app.models.user import User
from app.schemas.story import StoryCreate, StoryResponse
from app.auth import get_current_user

router = APIRouter(prefix="/stories", tags=["stories"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("", response_model=dict, status_code=201)
def create_story(
    story_in: StoryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new story (24-hour visibility)"""
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=24)

    story = Story(
        author_id=current_user.id,
        content=story_in.content,
        media_url=story_in.media_url,
        media_type=story_in.media_type,
        created_at=now,
        expires_at=expires_at,
    )

    db.add(story)
    db.commit()
    db.refresh(story)

    # Schedule cleanup of expired stories
    background_tasks.add_task(cleanup_expired_stories, db)

    return {
        "id": story.id,
        "author_id": story.author_id,
        "content": story.content,
        "media_url": story.media_url,
        "media_type": story.media_type,
        "created_at": story.created_at,
        "expires_at": story.expires_at,
    }


@router.get("", response_model=list[StoryResponse])
def get_stories_from_following(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get stories from users the current user follows (non-expired only)"""
    now = datetime.utcnow()

    # Get IDs of users that current_user follows
    following_ids = [f.following_id for f in current_user.following]
    following_ids.append(current_user.id)  # Include own stories

    # Get non-expired stories from followed users, ordered by created_at DESC
    stories = (
        db.query(Story)
        .filter(
            Story.author_id.in_(following_ids),
            Story.expires_at > now,
        )
        .order_by(Story.created_at.desc())
        .all()
    )

    result = []
    for story in stories:
        result.append(
            StoryResponse(
                id=story.id,
                author_id=story.author_id,
                author_username=story.author.username,
                content=story.content,
                media_url=story.media_url,
                media_type=story.media_type,
                created_at=story.created_at,
                expires_at=story.expires_at,
            )
        )

    return result


@router.get("/my", response_model=list[StoryResponse])
def get_my_stories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all my stories (including expired, for archive purposes)"""
    stories = (
        db.query(Story)
        .filter(Story.author_id == current_user.id)
        .order_by(Story.created_at.desc())
        .all()
    )

    result = []
    for story in stories:
        result.append(
            StoryResponse(
                id=story.id,
                author_id=story.author_id,
                author_username=story.author.username,
                content=story.content,
                media_url=story.media_url,
                media_type=story.media_type,
                created_at=story.created_at,
                expires_at=story.expires_at,
            )
        )

    return result


@router.get("/user/{user_id}", response_model=list[StoryResponse])
def get_user_active_stories(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active (non-expired) stories for a specific user."""
    now = datetime.utcnow()

    stories = (
        db.query(Story)
        .filter(
            Story.author_id == user_id,
            Story.expires_at > now,
        )
        .order_by(Story.created_at.desc())
        .all()
    )

    result = []
    for story in stories:
        result.append(
            StoryResponse(
                id=story.id,
                author_id=story.author_id,
                author_username=story.author.username,
                content=story.content,
                media_url=story.media_url,
                media_type=story.media_type,
                created_at=story.created_at,
                expires_at=story.expires_at,
            )
        )

    return result


@router.delete("/{story_id}", status_code=204)
def delete_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a story (only author can delete)"""
    story = db.query(Story).filter(Story.id == story_id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own stories")

    db.delete(story)
    db.commit()

    return None


def cleanup_expired_stories(db: Session):
    """Remove expired stories from database"""
    now = datetime.utcnow()
    db.query(Story).filter(Story.expires_at <= now).delete()
    db.commit()
