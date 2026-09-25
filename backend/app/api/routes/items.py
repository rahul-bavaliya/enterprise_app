import uuid
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Item
from app.schemas import (
    ItemCreate,
    ItemPublic,
    ItemsPublic,
    ItemUpdate,
    ResponseEnvelope,
)
from app.services.item import create_item as create_item_service
from app.services.item import update_item as update_item_service

router = APIRouter(prefix="/items", tags=["items"])


@router.get(
    "/",
    response_model=ResponseEnvelope[ItemsPublic],
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
    return ResponseEnvelope(
        success=True,
        data=ItemsPublic(data=items_public, count=count),
        message=f"Retrieved {count} item(s)",
    )


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[ItemPublic],
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
    return ResponseEnvelope(success=True, data=ItemPublic.model_validate(item))


@router.post(
    "/",
    response_model=ResponseEnvelope[ItemPublic],
)
def create_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    item_in: ItemCreate = Body(
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
    item = create_item_service(
        session=session, item_in=item_in, owner_id=current_user.id
    )
    return ResponseEnvelope(
        success=True,
        data=ItemPublic.model_validate(item),
        message="Item created successfully",
    )


@router.put(
    "/{id}",
    response_model=ResponseEnvelope[ItemPublic],
)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate = Body(
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
    updated = update_item_service(session=session, db_item=item, item_in=item_in)
    return ResponseEnvelope(
        success=True,
        data=ItemPublic.model_validate(updated),
        message="Item updated successfully",
    )


@router.delete(
    "/{id}",
    response_model=ResponseEnvelope[None],
)
def delete_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
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
    return ResponseEnvelope(success=True, message="Item deleted successfully")
