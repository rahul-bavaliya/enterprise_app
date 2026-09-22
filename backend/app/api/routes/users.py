import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlmodel import col, delete, func, select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.core.utils import generate_new_account_email, send_email
from app.models import Item, User
from app.schemas import (
    Message,
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.services import create_user as create_user_service
from app.services import get_user_by_email
from app.services import update_user as update_user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                                "email": "john.doe@example.com",
                                "full_name": "John Doe",
                                "is_active": True,
                                "is_superuser": False,
                            }
                        ],
                        "count": 1,
                    }
                }
            },
        }
    },
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = (
        select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    )
    users = session.exec(statement).all()

    users_public = [UserPublic.model_validate(user) for user in users]
    return UsersPublic(data=users_public, count=count)


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                        "email": "john.doe@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "is_superuser": False,
                    }
                }
            },
        }
    },
)
def create_user(
    *,
    session: SessionDep,
    user_in: UserCreate = Body(
        ...,
        examples={
            "default": {
                "summary": "Create user",
                "value": {
                    "email": "john.doe@example.com",
                    "password": "StrongPass!123",
                    "full_name": "John Doe",
                    "is_active": True,
                    "is_superuser": False,
                },
            }
        },
    ),
) -> Any:
    """
    Create new user.
    """
    user = get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = create_user_service(session=session, user_create=user_in)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch(
    "/me",
    response_model=UserPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                        "email": "jane.smith@example.com",
                        "full_name": "Jane Smith",
                        "is_active": True,
                        "is_superuser": False,
                    }
                }
            },
        }
    },
)
def update_user_me(
    *,
    session: SessionDep,
    user_in: UserUpdateMe = Body(
        ...,
        examples={
            "default": {
                "summary": "Update current user",
                "value": {
                    "full_name": "Jane Smith",
                    "email": "jane.smith@example.com",
                },
            }
        },
    ),
    current_user: CurrentUser,
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.updated_at = datetime.now(UTC)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch(
    "/me/password",
    response_model=Message,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Password updated successfully",
                    }
                }
            },
        }
    },
)
def update_password_me(
    *,
    session: SessionDep,
    body: UpdatePassword = Body(
        ...,
        examples={
            "default": {
                "summary": "Change password",
                "value": {
                    "current_password": "OldPass!123",
                    "new_password": "NewStrongPass!456",
                },
            }
        },
    ),
    current_user: CurrentUser,
) -> Any:
    """
    Update own password.
    """
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    current_user.updated_at = datetime.now(UTC)
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get(
    "/me",
    response_model=UserPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                        "email": "john.doe@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "is_superuser": False,
                    }
                }
            },
        }
    },
)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.delete(
    "/me",
    response_model=Message,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User deleted successfully",
                    }
                }
            },
        }
    },
)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post(
    "/signup",
    response_model=UserPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                        "email": "new.user@example.com",
                        "full_name": "New User",
                        "is_active": True,
                        "is_superuser": False,
                    }
                }
            },
        }
    },
)
def register_user(
    session: SessionDep,
    user_in: UserRegister = Body(
        ...,
        examples={
            "default": {
                "summary": "Register user",
                "value": {
                    "email": "new.user@example.com",
                    "password": "SecureP@ss456",
                    "full_name": "New User",
                },
            }
        },
    ),
) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user = create_user_service(session=session, user_create=user_create)
    return user


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                        "email": "john.doe@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "is_superuser": False,
                    }
                }
            },
        }
    },
)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                        "email": "updated.email@example.com",
                        "full_name": "Jane Doe",
                        "is_active": True,
                        "is_superuser": False,
                    }
                }
            },
        }
    },
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate = Body(
        ...,
        examples={
            "default": {
                "summary": "Update user",
                "value": {
                    "email": "updated.email@example.com",
                    "is_active": True,
                    "is_superuser": False,
                    "full_name": "Jane Doe",
                    "password": "AnotherStrongPass!456",
                },
            }
        },
    ),
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = update_user_service(session=session, db_user=db_user, user_in=user_in)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    statement = delete(Item).where(col(Item.owner_id) == user_id)
    session.exec(statement)
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")
