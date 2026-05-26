# """
# Example routes demonstrating authentication middleware usage
# This file shows how to use the new auth dependency functions
# """
# from typing import Optional
# from fastapi import APIRouter, Depends, HTTPException, status
# from app.middlewares.auth_middleware import (
#     get_current_user,
#     get_current_active_user,
#     get_optional_user,
#     require_role,
#     require_admin
# )
# from app.models.user_model import User, Role

# router = APIRouter(prefix="/api/v1/examples", tags=["examples"])


# # ============================================================================
# # BASIC AUTHENTICATION EXAMPLES
# # ============================================================================

# @router.get("/protected")
# async def protected_route(current_user: User = Depends(get_current_user)):
#     """
#     Basic protected route - requires authentication.
#     Returns user information for authenticated users only.
#     """
#     return {
#         "message": "This is a protected route",
#         "user": {
#             "id": str(current_user.id),
#             "username": current_user.username,
#             "email": current_user.email,
#             "role": current_user.role.value
#         }
#     }


# @router.get("/profile")
# async def get_my_profile(user: User = Depends(get_current_active_user)):
#     """
#     Get current user's profile.
#     Uses get_current_active_user which is a convenience wrapper.
#     """
#     return {
#         "id": str(user.id),
#         "username": user.username,
#         "email": user.email,
#         "role": user.role.value,
#         "is_active": user.is_active,
#         "created_at": user.created_at.isoformat() if user.created_at else None
#     }


# # ============================================================================
# # OPTIONAL AUTHENTICATION EXAMPLE
# # ============================================================================

# @router.get("/content")
# async def get_content(user: Optional[User] = Depends(get_optional_user)):
#     """
#     Route with optional authentication.
#     Shows different content for logged-in vs guest users.
#     """
#     if user:
#         return {
#             "message": f"Welcome back, {user.username}!",
#             "content": "Premium content for authenticated users",
#             "features": ["advanced_analytics", "export_data", "priority_support"],
#             "user_type": "authenticated"
#         }
    
#     return {
#         "message": "Welcome, guest!",
#         "content": "Basic content for all users",
#         "features": ["basic_analytics"],
#         "user_type": "guest",
#         "suggestion": "Login to access premium features"
#     }


# # ============================================================================
# # ROLE-BASED ACCESS CONTROL (RBAC) EXAMPLES
# # ============================================================================

# @router.get("/admin/dashboard")
# async def admin_dashboard(admin: User = Depends(require_admin)):
#     """
#     Admin-only route.
#     Only users with Role.admin can access this endpoint.
#     """
#     return {
#         "message": "Admin Dashboard",
#         "admin": {
#             "username": admin.username,
#             "email": admin.email
#         },
#         "stats": {
#             "total_users": 150,
#             "active_users": 120,
#             "new_users_today": 5
#         }
#     }


# @router.delete("/admin/users/{user_id}")
# async def delete_user(user_id: str, admin: User = Depends(require_admin)):
#     """
#     Delete user - admin only.
#     Demonstrates admin-required destructive operation.
#     """
#     # In real implementation, this would delete the user from database
#     return {
#         "message": f"User {user_id} deleted successfully",
#         "deleted_by": admin.username
#     }


# @router.get("/staff/reports")
# async def staff_reports(
#     user: User = Depends(require_role(Role.admin, Role.user))
# ):
#     """
#     Staff area - accessible by both admins and regular users.
#     Guests are not allowed.
#     """
#     return {
#         "message": "Staff Reports",
#         "accessible_by": ["admin", "user"],
#         "current_user": {
#             "username": user.username,
#             "role": user.role.value
#         },
#         "reports": [
#             {"id": 1, "name": "Monthly Sales", "date": "2026-02"},
#             {"id": 2, "name": "User Activity", "date": "2026-02"}
#         ]
#     }


# @router.post("/admin/settings")
# async def update_settings(
#     settings: dict,
#     admin: User = Depends(require_admin)
# ):
#     """
#     Update application settings - admin only.
#     Shows how to combine auth with request body.
#     """
#     return {
#         "message": "Settings updated successfully",
#         "updated_by": admin.username,
#         "new_settings": settings
#     }


# # ============================================================================
# # MIXED PERMISSION EXAMPLES
# # ============================================================================

# @router.get("/posts/{post_id}")
# async def get_post(
#     post_id: int,
#     user: Optional[User] = Depends(get_optional_user)
# ):
#     """
#     Get post with optional authentication.
#     Shows different data based on user role.
#     """
#     # Base post data (available to everyone)
#     post = {
#         "id": post_id,
#         "title": "Sample Post",
#         "content": "This is a sample post",
#         "published": True
#     }
    
#     # Add extra data for authenticated users
#     if user:
#         post["author_email"] = "author@example.com"
#         post["views"] = 1234
        
#         # Add even more data for admins
#         if user.role == Role.admin:
#             post["draft_versions"] = 3
#             post["scheduled_publish": None
#             post["analytics"] = {"clicks": 567, "shares": 89}
    
#     return post


# @router.put("/posts/{post_id}")
# async def update_post(
#     post_id: int,
#     post_data: dict,
#     user: User = Depends(require_role(Role.admin, Role.user))
# ):
#     """
#     Update post - users and admins can update.
#     In real implementation, you'd check if user owns the post.
#     """
#     # In practice, verify user owns the post or is admin
#     return {
#         "message": "Post updated",
#         "post_id": post_id,
#         "updated_by": user.username,
#         "can_publish": user.role == Role.admin
#     }


# # ============================================================================
# # ERROR HANDLING EXAMPLES
# # ============================================================================

# @router.get("/test-errors/unauthorized")
# async def test_unauthorized():
#     """
#     Test endpoint to demonstrate 401 error.
#     Call this WITHOUT Authorization header to see auth error response.
#     """
#     # This will never execute if auth is required
#     # The middleware will return 401 before reaching here
#     return {"message": "This should not be visible"}


# @router.get("/test-errors/forbidden")
# async def test_forbidden(user: User = Depends(require_admin)):
#     """
#     Test endpoint to demonstrate 403 error.
#     Call this with non-admin user to see forbidden error.
#     """
#     return {"message": "Admin area"}


# # ============================================================================
# # USAGE INSTRUCTIONS
# # ============================================================================

# @router.get("/usage-guide")
# async def usage_guide():
#     """
#     Returns instructions on how to use authentication.
#     This is a public route (add to PUBLIC_ROUTES if needed).
#     """
#     return {
#         "title": "Authentication Usage Guide",
#         "instructions": [
#             "1. Register: POST /api/v1/auth/register with username, email, password",
#             "2. Login: POST /api/v1/auth/login with email and password",
#             "3. Receive tokens: You'll get access_token and refresh_token",
#             "4. Use token: Add 'Authorization: Bearer <access_token>' header to requests",
#             "5. Refresh: POST /api/v1/auth/refresh with refresh_token when access_token expires"
#         ],
#         "examples": {
#             "login": {
#                 "method": "POST",
#                 "url": "/api/v1/auth/login",
#                 "body": {"email": "user@example.com", "password": "password123"}
#             },
#             "authenticated_request": {
#                 "method": "GET",
#                 "url": "/api/v1/examples/protected",
#                 "headers": {"Authorization": "Bearer eyJhbGc..."}
#             }
#         },
#         "roles": {
#             "admin": "Full access to all endpoints",
#             "user": "Standard user access",
#             "guest": "Limited access (if allowed)"
#         }
#     }
