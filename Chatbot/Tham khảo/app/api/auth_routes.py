"""
Authentication routes for login, registration, and user management.
Admin-only routes for managing users.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth_dependencies import get_current_admin_user, get_current_user
from app.application.factory import ProviderFactory
from app.core.auth import create_access_token, get_password_hash, verify_password
from app.core.mongodb_models import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserInDB,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Login with username and password.
    Returns JWT access token.
    """
    mongodb = await ProviderFactory.get_mongodb_client()
    
    # Get user from database
    user_data = await mongodb.get_user_by_username(credentials.username)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Verify password
    if not verify_password(credentials.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Check if user is active
    if not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    # Update last login
    await mongodb.update_user(
        user_data["_id"],
        {"last_login": datetime.now()}
    )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user_data["username"], "role": user_data["role"]}
    )
    
    # Prepare user response
    user_response = UserResponse(
        id=user_data["_id"],
        username=user_data["username"],
        email=user_data["email"],
        full_name=user_data.get("full_name"),
        role=user_data["role"],
        is_active=user_data["is_active"],
        created_at=user_data["created_at"],
        last_login=datetime.now(),
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Register a new user (Admin only).
    First user should be created via script.
    """
    mongodb = await ProviderFactory.get_mongodb_client()
    
    # Check if username already exists
    existing_user = await mongodb.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    
    # Check if email already exists
    existing_email = await mongodb.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user document
    user_doc = {
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
        "role": user_data.role,
        "is_active": user_data.is_active,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    
    # Insert into database
    user_id = await mongodb.create_user(user_doc)
    
    # Return user response
    return UserResponse(
        id=user_id,
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=user_data.is_active,
        created_at=user_doc["created_at"],
        last_login=None,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
    """Get current authenticated user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    is_active: bool = None,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    List all users (Admin only).
    Supports pagination and filtering by active status.
    """
    mongodb = await ProviderFactory.get_mongodb_client()
    
    users_data = await mongodb.list_users(skip=skip, limit=limit, is_active=is_active)
    total = await mongodb.db.users.count_documents(
        {"is_active": is_active} if is_active is not None else {}
    )
    
    users = [
        UserResponse(
            id=user["_id"],
            username=user["username"],
            email=user["email"],
            full_name=user.get("full_name"),
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user.get("last_login"),
        )
        for user in users_data
    ]
    
    return UserListResponse(
        users=users,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Update user information (Admin only).
    Can update email, full_name, role, is_active, password.
    """
    mongodb = await ProviderFactory.get_mongodb_client()
    
    # Check if user exists
    existing_user = await mongodb.get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prepare update data
    update_data = {}
    if user_update.email:
        update_data["email"] = user_update.email
    if user_update.full_name:
        update_data["full_name"] = user_update.full_name
    if user_update.role:
        update_data["role"] = user_update.role
    if user_update.is_active is not None:
        update_data["is_active"] = user_update.is_active
    if user_update.password:
        update_data["hashed_password"] = get_password_hash(user_update.password)
    
    if update_data:
        update_data["updated_at"] = datetime.now()
        await mongodb.update_user(user_id, update_data)
    
    # Get updated user
    updated_user = await mongodb.get_user_by_id(user_id)
    
    return UserResponse(
        id=updated_user["_id"],
        username=updated_user["username"],
        email=updated_user["email"],
        full_name=updated_user.get("full_name"),
        role=updated_user["role"],
        is_active=updated_user["is_active"],
        created_at=updated_user["created_at"],
        last_login=updated_user.get("last_login"),
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Soft delete user (Admin only).
    Sets is_active=False instead of removing from database.
    """
    mongodb = await ProviderFactory.get_mongodb_client()
    
    # Check if user exists
    existing_user = await mongodb.get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prevent deleting yourself
    if existing_user["_id"] == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    # Soft delete
    await mongodb.delete_user(user_id)
    
    return None

