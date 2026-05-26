"""
Users endpoints (placeholder for now)
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_users():
    """List users - placeholder endpoint"""
    return {"message": "Users endpoint - to be implemented", "status": "placeholder"}


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Get user by ID - placeholder endpoint"""
    return {"message": f"Get user {user_id} - to be implemented", "status": "placeholder"}


@router.post("/")
async def create_user():
    """Create user - placeholder endpoint"""
    return {"message": "Create user - to be implemented", "status": "placeholder"}


@router.put("/{user_id}")
async def update_user(user_id: str):
    """Update user - placeholder endpoint"""
    return {"message": f"Update user {user_id} - to be implemented", "status": "placeholder"}


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete user - placeholder endpoint"""
    return {"message": f"Delete user {user_id} - to be implemented", "status": "placeholder"}
