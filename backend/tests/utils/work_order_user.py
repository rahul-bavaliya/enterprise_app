"""Helpers for creating users with a specific role and branch.

The permission tests need real accounts at real branches, not mocked users, so
these build them through the same service layer the API uses. The plaintext
password is returned alongside the user, because creation only stores a hash
and the caller still needs the original to sign in.
"""

from sqlmodel import Session

from app.models import Branch, User, UserCreate, UserRole
from app.services import create_user
from tests.utils.utils import random_lower_string


def create_role_user(
    db: Session,
    *,
    role: UserRole,
    branch: Branch | None = None,
    is_active: bool = True,
) -> tuple[User, str]:
    """Create a user holding ``role``, scoped to ``branch``.

    Returns the user and its plaintext password, since creation only stores a
    hash and the caller needs the original to sign in.
    """
    password = random_lower_string() + "Aa1!"
    user_in = UserCreate(
        email=f"{role.value}-{random_lower_string()[:10]}@example.com",
        password=password,
        full_name=f"Test {role.value}",
        role=role,
        branch_id=branch.id if branch else None,
        is_active=is_active,
    )
    user = create_user(session=db, user_create=user_in)
    return user, password
