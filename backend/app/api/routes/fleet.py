import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.schemas import FleetPublic, FleetUpdate, ResponseEnvelope
from app.services.customer import (
    deactivate_fleet,
    get_fleet_by_id,
    get_fleets,
    update_fleet,
)

EXAMPLE_FLEET = {
    "id": "9a3d6c18-77b2-4e05-8c41-2d9f0b7a6e53",
    "customer_id": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14",
    "asset_tag": "ACME-PMP-001",
    "description": "Centrifugal pump, 22kW",
    "make": "Grundfos",
    "model": "NB 65-200",
    "is_active": True,
    "created_at": "2026-09-25T10:05:00Z",
    "updated_at": None,
}

router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.get(
    "/",
    response_model=ResponseEnvelope[list[FleetPublic]],
)
def read_fleet(
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    customer_id: Annotated[
        uuid.UUID | None, Query(description="Filter by owning customer")
    ] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    fleet, count = get_fleets(
        session=session,
        customer_id=customer_id,
        skip=skip,
        limit=limit,
        is_active=is_active,
    )
    return ResponseEnvelope(
        success=True,
        data=[FleetPublic.model_validate(f) for f in fleet],
        message=f"Retrieved {count} machine(s)",
    )


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[FleetPublic],
)
def read_fleet_item(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    fleet = get_fleet_by_id(session=session, fleet_id=id)
    if fleet is None:
        raise HTTPException(status_code=404, detail="Machine not found")
    return ResponseEnvelope(success=True, data=FleetPublic.model_validate(fleet))


@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[FleetPublic],
)
def update_fleet_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    fleet_in: FleetUpdate = Body(
        examples={
            "default": {
                "summary": "Update machine",
                "value": {"meter_reading": "14890.50", "location": "Pump house C"},
            }
        },
    ),
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    fleet = get_fleet_by_id(session=session, fleet_id=id)
    if fleet is None:
        raise HTTPException(status_code=404, detail="Machine not found")
    updated = update_fleet(session=session, db_fleet=fleet, fleet_in=fleet_in)
    return ResponseEnvelope(
        success=True,
        data=FleetPublic.model_validate(updated),
        message="Machine updated successfully",
    )


@router.delete(
    "/{id}",
    response_model=ResponseEnvelope[FleetPublic],
    summary="Deactivate a machine",
)
def deactivate_fleet_route(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """Retire a machine without removing it from completed work orders."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    fleet = get_fleet_by_id(session=session, fleet_id=id)
    if fleet is None:
        raise HTTPException(status_code=404, detail="Machine not found")
    deactivated = deactivate_fleet(session=session, db_fleet=fleet)
    return ResponseEnvelope(
        success=True,
        data=FleetPublic.model_validate(deactivated),
        message="Machine deactivated successfully",
    )
