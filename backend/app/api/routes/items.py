import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Item
from app.schemas import ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message

router = APIRouter(prefix="/items", tags=["items"])


@router.get(
    "/",
    response_model=ItemsPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "d95ea23b-34eb-44d8-bf7a-98f8d9fb7b33",
                                "title": "Laptop",
                                "description": "14-inch laptop with 16GB RAM",
                                "owner_id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                            }
                        ],
                        "count": 1,
                    }
                }
            },
        }
    },
)
def read_items(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve items.
    """

    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Item)
        count = session.exec(count_statement).one()
        statement = (
            select(Item).order_by(col(Item.created_at).desc()).offset(skip).limit(limit)
        )
        items = session.exec(statement).all()
    else:
        count_statement = (
            select(func.count())
            .select_from(Item)
            .where(Item.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(Item)
            .where(Item.owner_id == current_user.id)
            .order_by(col(Item.created_at).desc())
            .offset(skip)
            .limit(limit)
        )
        items = session.exec(statement).all()

    items_public = [ItemPublic.model_validate(item) for item in items]
    return ItemsPublic(data=items_public, count=count)


@router.get(
    "/{id}",
    response_model=ItemPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "id": "d95ea23b-34eb-44d8-bf7a-98f8d9fb7b33",
                        "title": "Laptop",
                        "description": "14-inch laptop with 16GB RAM",
                        "owner_id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                    }
                }
            },
        }
    },
)
def read_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get item by ID.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return item


@router.post(
    "/",
    response_model=ItemPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "id": "d95ea23b-34eb-44d8-bf7a-98f8d9fb7b33",
                        "title": "Laptop",
                        "description": "14-inch laptop with 16GB RAM",
                        "owner_id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                    }
                }
            },
        }
    },
)
def create_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    item_in: ItemCreate = Body(
        ...,
        examples={
            "default": {
                "summary": "Create item",
                "value": {
                    "title": "Laptop",
                    "description": "14-inch laptop with 16GB RAM",
                },
            }
        },
    ),
) -> Any:
    """
    Create new item.
    """
    item = Item.model_validate(item_in, update={"owner_id": current_user.id})
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put(
    "/{id}",
    response_model=ItemPublic,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "id": "d95ea23b-34eb-44d8-bf7a-98f8d9fb7b33",
                        "title": "Gaming Laptop",
                        "description": "Updated specs for the new model",
                        "owner_id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                    }
                }
            },
        }
    },
)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate = Body(
        ...,
        examples={
            "default": {
                "summary": "Update item",
                "value": {
                    "title": "Gaming Laptop",
                    "description": "Updated specs for the new model",
                },
            }
        },
    ),
) -> Any:
    """
    Update an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_dict = item_in.model_dump(exclude_unset=True)
    item.updated_at = datetime.now(UTC)
    item.sqlmodel_update(update_dict)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete(
    "/{id}",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Item deleted successfully",
                    }
                }
            },
        }
    },
)
def delete_item(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(item)
    session.commit()
    return Message(message="Item deleted successfully")
