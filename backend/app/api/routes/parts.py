import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.schemas import PartCreate, PartPublic, PartUpdate, ResponseEnvelope
from app.services.part import (
    create_part,
    deactivate_part,
    get_part_by_id,
    get_parts,
    update_part,
)

EXAMPLE_PART = {
    "id": "3b1a9c22-7f4e-4c1b-9a55-2d8f6e0c1a77",
    "part_number": "BRG-6205-2RS",
    "description": "Deep groove ball bearing 6205-2RS",
    "manufacturer": "SKF",
    "unit_of_measure": "EA",
    "list_price": "24.95",
    "is_active": True,
    "created_at": "2026-09-25T10:00:00Z",
    "updated_at": None,
}

router = APIRouter(prefix="/parts", tags=["parts"])


@router.get(
    "/",
    response_model=ResponseEnvelope[list[PartPublic]],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [EXAMPLE_PART],
                        "message": "Retrieved 1 part(s)",
                    }
                }
            },
        }
    },
)
def read_parts(
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    part_number: Annotated[
        str | None, Query(description="Filter by exact part number")
    ] = None,
    is_active: Annotated[
        bool | None, Query(description="Filter by active status")
    ] = None,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    parts, count = get_parts(
        session=session,
        skip=skip,
        limit=limit,
        part_number=part_number,
        is_active=is_active,
    )
    parts_public = [PartPublic.model_validate(part) for part in parts]
    return ResponseEnvelope(
        success=True,
        data=parts_public,
        message=f"Retrieved {count} part(s)",
    )


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[PartPublic],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": EXAMPLE_PART,
                        "message": None,
                    }
                }
            },
        }
    },
)
def read_part(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    part = get_part_by_id(session=session, part_id=id)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return ResponseEnvelope(success=True, data=PartPublic.model_validate(part))


@router.post(
    "/",
    response_model=ResponseEnvelope[PartPublic],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": EXAMPLE_PART,
                        "message": "Part created successfully",
                    }
                }
            },
        },
        409: {"description": "A part with this part number already exists"},
    },
)
def create_part_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    part_in: PartCreate = Body(
        examples={
            "default": {
                "summary": "Create part",
                "value": {
                    "part_number": "BRG-6205-2RS",
                    "description": "Deep groove ball bearing 6205-2RS",
                    "manufacturer": "SKF",
                    "list_price": "24.95",
                },
            }
        },
    ),
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        part = create_part(session=session, part_in=part_in)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ResponseEnvelope(
        success=True,
        data=PartPublic.model_validate(part),
        message="Part created successfully",
    )


@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[PartPublic],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {**EXAMPLE_PART, "list_price": "27.50"},
                        "message": "Part updated successfully",
                    }
                }
            },
        }
    },
)
def update_part_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    part_in: PartUpdate = Body(
        examples={
            "default": {
                "summary": "Update part",
                "value": {"list_price": "27.50"},
            }
        },
    ),
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    part = get_part_by_id(session=session, part_id=id)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    try:
        updated = update_part(session=session, db_part=part, part_in=part_in)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ResponseEnvelope(
        success=True,
        data=PartPublic.model_validate(updated),
        message="Part updated successfully",
    )


@router.delete(
    "/{id}",
    response_model=ResponseEnvelope[PartPublic],
    summary="Deactivate a part",
    responses={
        200: {
            "description": "Part deactivated. The record is retained so work order history still resolves.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {**EXAMPLE_PART, "is_active": False},
                        "message": "Part deactivated successfully",
                    }
                }
            },
        }
    },
)
def deactivate_part_route(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    """Retire a part from the catalog.

    Parts are never removed, because work order line items reference them for
    auditing. The part is marked inactive so it cannot be added to new work.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    part = get_part_by_id(session=session, part_id=id)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    deactivated = deactivate_part(session=session, db_part=part)
    return ResponseEnvelope(
        success=True,
        data=PartPublic.model_validate(deactivated),
        message="Part deactivated successfully",
    )
