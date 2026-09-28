import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.schemas import (
    CustomerCreate,
    CustomerPublic,
    CustomerUpdate,
    FleetBase,
    FleetCreate,
    FleetPublic,
    ResponseEnvelope,
)
from app.services.customer import (
    create_customer,
    create_fleet,
    deactivate_customer,
    get_customer_by_id,
    get_customers,
    get_fleet_by_id,
    get_fleets,
    update_customer,
)

EXAMPLE_CUSTOMER = {
    "id": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14",
    "name": "Acme Facilities Ltd",
    "contact_person": "Jane Doe",
    "email": "jane.doe@acme.test",
    "phone": "+1 555 0100",
    "is_active": True,
    "created_at": "2026-09-25T10:00:00Z",
    "updated_at": None,
}

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

router = APIRouter(prefix="/customers", tags=["customers"])


def _load_customer_or_404(session: SessionDep, customer_id: uuid.UUID) -> Any:
    customer = get_customer_by_id(session=session, customer_id=customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get(
    "/",
    response_model=ResponseEnvelope[list[CustomerPublic]],
)
def read_customers(
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    search: Annotated[
        str | None, Query(description="Match name or contact person")
    ] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    customers, count = get_customers(
        session=session, skip=skip, limit=limit, search=search, is_active=is_active
    )
    return ResponseEnvelope(
        success=True,
        data=[CustomerPublic.model_validate(c) for c in customers],
        message=f"Retrieved {count} customer(s)",
    )


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[CustomerPublic],
)
def read_customer(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    customer = _load_customer_or_404(session=session, customer_id=id)
    return ResponseEnvelope(
        success=True, data=CustomerPublic.model_validate(customer)
    )


@router.post(
    "/",
    response_model=ResponseEnvelope[CustomerPublic],
    status_code=201,
)
def create_customer_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    customer_in: CustomerCreate = Body(
        examples={
            "default": {
                "summary": "Register customer",
                "value": {
                    "name": "Acme Facilities Ltd",
                    "contact_person": "Jane Doe",
                    "email": "jane.doe@acme.test",
                    "phone": "+1 555 0100",
                    "service_address": "22 Industrial Way, Springfield",
                },
            }
        },
    ),
) -> Any:
    """Register a customer, capturing all known details in one call."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    customer = create_customer(session=session, customer_in=customer_in)
    return ResponseEnvelope(
        success=True,
        data=CustomerPublic.model_validate(customer),
        message="Customer registered successfully",
    )


@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[CustomerPublic],
)
def update_customer_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    customer_in: CustomerUpdate = Body(
        examples={
            "default": {
                "summary": "Update customer",
                "value": {"phone": "+1 555 0111"},
            }
        },
    ),
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    customer = _load_customer_or_404(session=session, customer_id=id)
    updated = update_customer(
        session=session, db_customer=customer, customer_in=customer_in
    )
    return ResponseEnvelope(
        success=True,
        data=CustomerPublic.model_validate(updated),
        message="Customer updated successfully",
    )


@router.delete(
    "/{id}",
    response_model=ResponseEnvelope[CustomerPublic],
    summary="Deactivate a customer",
)
def deactivate_customer_route(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """Retire a customer.

    The record is kept so existing work orders and their machines still
    resolve; the customer simply cannot be selected for new work.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    customer = _load_customer_or_404(session=session, customer_id=id)
    deactivated = deactivate_customer(session=session, db_customer=customer)
    return ResponseEnvelope(
        success=True,
        data=CustomerPublic.model_validate(deactivated),
        message="Customer deactivated successfully",
    )


@router.get(
    "/{id}/fleet",
    response_model=ResponseEnvelope[list[FleetPublic]],
    summary="List a customer's machines",
)
def read_customer_fleet(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> Any:
    """The customer's fleet, used to auto-populate the machine picker."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    _load_customer_or_404(session=session, customer_id=id)
    fleet, count = get_fleets(session=session, customer_id=id, skip=skip, limit=limit)
    return ResponseEnvelope(
        success=True,
        data=[FleetPublic.model_validate(f) for f in fleet],
        message=f"Retrieved {count} machine(s)",
    )


@router.post(
    "/{id}/fleet",
    response_model=ResponseEnvelope[FleetPublic],
    status_code=201,
    summary="Add a machine to a customer's fleet",
)
def create_customer_fleet_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    fleet_in: FleetBase = Body(
        examples={
            "default": {
                "summary": "Add machine",
                "value": {
                    "asset_tag": "ACME-PMP-002",
                    "description": "Centrifugal pump, 30kW",
                    "make": "Wilo",
                    "model": "Afero 3",
                },
            }
        },
    ),
) -> Any:
    """Add a new machine while a work order is being raised.

    The customer id comes from the path, so the payload does not repeat it and
    a machine can never be filed under the wrong owner.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    customer = _load_customer_or_404(session=session, customer_id=id)
    if not customer.is_active:
        raise HTTPException(
            status_code=409, detail=f"Customer '{customer.name}' is inactive"
        )
    fleet = create_fleet(
        session=session,
        fleet_in=FleetCreate.model_validate(
            {**fleet_in.model_dump(), "customer_id": id}
        ),
    )
    return ResponseEnvelope(
        success=True,
        data=FleetPublic.model_validate(fleet),
        message="Machine added to customer fleet successfully",
    )


@router.get(
    "/{id}/fleet/{fleet_id}",
    response_model=ResponseEnvelope[FleetPublic],
)
def read_customer_fleet_item(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    fleet_id: uuid.UUID,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    _load_customer_or_404(session=session, customer_id=id)
    fleet = get_fleet_by_id(session=session, fleet_id=fleet_id)
    if fleet is None or fleet.customer_id != id:
        raise HTTPException(status_code=404, detail="Machine not found")
    return ResponseEnvelope(success=True, data=FleetPublic.model_validate(fleet))
