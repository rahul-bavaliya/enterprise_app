from sqlmodel import Session

from app.models import (
    BranchCreate,
    BranchUpdate,
    ItemCreate,
    ItemUpdate,
    UserCreate,
    UserUpdate,
)
from app.services import (
    create_branch,
    create_item,
    create_user,
    update_branch,
    update_item,
    update_user,
)
from tests.utils.utils import random_email, random_lower_string


def test_user_timestamps_on_create_and_update(db: Session) -> None:
    user = create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
            full_name="Test User",
        ),
    )

    assert user.created_at is not None
    assert user.updated_at is None

    updated_user = update_user(
        session=db,
        db_user=user,
        user_in=UserUpdate(full_name="Updated User"),
    )

    assert updated_user.updated_at is not None
    assert updated_user.updated_at >= updated_user.created_at


def test_item_timestamps_on_create_and_update(db: Session) -> None:
    user = create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
            full_name="Item Owner",
        ),
    )

    item = create_item(
        session=db,
        item_in=ItemCreate(title="Test Item", description="Initial description"),
        owner_id=user.id,
    )

    assert item.created_at is not None
    assert item.updated_at is None

    updated_item = update_item(
        session=db,
        db_item=item,
        item_in=ItemUpdate(title="Updated title"),
    )

    assert updated_item.updated_at is not None
    assert updated_item.updated_at >= updated_item.created_at


def test_branch_timestamps_on_create_and_update(db: Session) -> None:
    branch = create_branch(
        session=db,
        branch_in=BranchCreate(name="Main Branch", location="HQ"),
    )

    assert branch.created_at is not None
    assert branch.updated_at is None

    updated_branch = update_branch(
        session=db,
        db_branch=branch,
        branch_in=BranchUpdate(location="New HQ"),
    )

    assert updated_branch.updated_at is not None
    assert updated_branch.updated_at >= updated_branch.created_at
