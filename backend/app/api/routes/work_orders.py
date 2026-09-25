import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.schemas import (
    ResponseEnvelope,
    WorkOrderCreate,
    WorkOrderPublic,
    WorkOrderUpdate,
)
from app.services.branch import get_branch_by_id
from app.services.work_order import (
    create_work_order,
    get_work_order_by_id,
    get_work_orders,
    update_work_order,
)
from app.services.work_order import (
    void_work_order as void_work_order_service,
)

EXAMPLE_WORK_ORDER = {
    "id": "0f8f1c64-9c1e-4b1e-9f1e-3f6f4b7b6f1a",
    "title": "Replace HVAC filter",
    "description": "Quarterly filter replacement for units 1-3.",
    "status": "open",
    "priority": "medium",
    "due_date": "2026-10-01",
    "assigned_to": "Jane Doe",
    "branch_id": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d",
    "created_at": "2026-09-22T10:00:00Z",
    "updated_at": None,
}


def _validate_status(status: str) -> str:
    from app.models import WorkOrderStatus

    valid = {s.value for s in WorkOrderStatus}
    if status not in valid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Valid values: {sorted(valid)}",
        )
    return status


def _ensure_branch_exists(session: Any, branch_id: uuid.UUID | None) -> None:
    if branch_id is not None and not get_branch_by_id(
        session=session, branch_id=branch_id
    ):
        raise HTTPException(status_code=404, detail="Branch not found")


router = APIRouter(prefix="/work-orders", tags=["work_orders"])


@router.get(
    "/",
    response_model=ResponseEnvelope[list[WorkOrderPublic]],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [EXAMPLE_WORK_ORDER],
                        "message": "Retrieved 1 work order(s)",
                    }
                }
            },
        }
    },
)
def read_work_orders(
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    status: Annotated[
        str | None, Query(description="Filter by lifecycle status")
    ] = None,
    branch_id: Annotated[
        uuid.UUID | None, Query(description="Filter by branch")
    ] = None,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if status is not None:
        status = _validate_status(status)
    _ensure_branch_exists(session=session, branch_id=branch_id)
    work_orders, count = get_work_orders(
        session=session, skip=skip, limit=limit, status=status, branch_id=branch_id
    )
    work_orders_public = [
        WorkOrderPublic.model_validate(work_order) for work_order in work_orders
    ]
    return ResponseEnvelope(
        success=True,
        data=work_orders_public,
        message=f"Retrieved {count} work order(s)",
    )


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[WorkOrderPublic],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": EXAMPLE_WORK_ORDER,
                        "message": None,
                    }
                }
            },
        }
    },
)
def read_work_order(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    work_order = get_work_order_by_id(session=session, work_order_id=id)
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    return ResponseEnvelope(
        success=True, data=WorkOrderPublic.model_validate(work_order)
    )


@router.post(
    "/",
    response_model=ResponseEnvelope[WorkOrderPublic],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": EXAMPLE_WORK_ORDER,
                        "message": "Work order created successfully",
                    }
                }
            },
        }
    },
)
def create_work_order_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    work_order_in: WorkOrderCreate = Body(
        examples={
            "default": {
                "summary": "Create work order",
                "value": {
                    "title": "Replace HVAC filter",
                    "description": "Quarterly filter replacement for units 1-3.",
                    "priority": "medium",
                    "due_date": "2026-10-01",
                    "assigned_to": "Jane Doe",
                },
            }
        },
    ),
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    _ensure_branch_exists(session=session, branch_id=work_order_in.branch_id)
    work_order = create_work_order(session=session, work_order_in=work_order_in)
    return ResponseEnvelope(
        success=True,
        data=WorkOrderPublic.model_validate(work_order),
        message="Work order created successfully",
    )


@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[WorkOrderPublic],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            **EXAMPLE_WORK_ORDER,
                            "title": "Replace HVAC filters",
                            "status": "in_progress",
                            "priority": "high",
                        },
                        "message": "Work order updated successfully",
                    }
                }
            },
        }
    },
)
def update_work_order_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    work_order_in: WorkOrderUpdate = Body(
        examples={
            "default": {
                "summary": "Update work order",
                "value": {
                    "title": "Replace HVAC filters",
                    "status": "in_progress",
                    "priority": "high",
                },
            }
        },
    ),
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    work_order = get_work_order_by_id(session=session, work_order_id=id)
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    _ensure_branch_exists(session=session, branch_id=work_order_in.branch_id)
    updated = update_work_order(
        session=session, db_work_order=work_order, work_order_in=work_order_in
    )
    return ResponseEnvelope(
        success=True,
        data=WorkOrderPublic.model_validate(updated),
        message="Work order updated successfully",
    )


@router.delete(
    "/{id}",
    response_model=ResponseEnvelope[WorkOrderPublic],
    summary="Void a work order",
    responses={
        200: {
            "description": "Work order voided. The record is retained for auditing.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {**EXAMPLE_WORK_ORDER, "status": "voided"},
                        "message": "Work order voided successfully",
                    }
                }
            },
        }
    },
)
def void_work_order(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    work_order = get_work_order_by_id(session=session, work_order_id=id)
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    voided = void_work_order_service(session=session, db_work_order=work_order)
    return ResponseEnvelope(
        success=True,
        data=WorkOrderPublic.model_validate(voided),
        message="Work order voided successfully",
    )
