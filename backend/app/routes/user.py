from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def get_users():
    # Placeholder for user listing logic
    return [{"id": 1, "username": "testuser"}]
