import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.models import WorkOrder, WorkOrderStatus
from app.schemas import (
    ResponseEnvelope,
    WorkOrderClose,
    WorkOrderCreate,
    WorkOrderNoteCreate,
    WorkOrderPartCreate,
    WorkOrderPartPublic,
    WorkOrderPartUpdate,
    WorkOrderPublic,
    WorkOrderReopen,
    WorkOrderSummary,
    WorkOrderTotals,
    WorkOrderUpdate,
)
from app.schemas import (
    WorkOrderEventPublic as WorkOrderEventSchema,
)
from app.services import permissions
from app.services.branch import get_branch_by_id
from app.services.part import (
    add_part_to_work_order,
    build_work_order_part_public,
    get_part_by_id,
    get_work_order_part_by_id,
    get_work_order_parts_with_parts,
    remove_work_order_part,
    update_work_order_part,
)
from app.services.work_order import (
    add_work_order_note,
    close_work_order,
    compute_work_order_totals,
    create_work_order,
    get_work_order_by_id,
    get_work_order_events,
    get_work_orders,
    reopen_work_order,
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

EXAMPLE_EVENT = {
    "id": "3d7b9a11-0c2e-4f5a-8e13-6b4d2a9c7e50",
    "work_order_id": "0f8f1c64-9c1e-4b1e-9f1e-3f6f4b7b6f1a",
    "event_type": "note",
    "body": "Replaced the failed capacitor and tested under load.",
    "from_status": None,
    "to_status": None,
    "author_id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
    "author_name": "Jane Doe",
    "created_at": "2026-09-25T11:20:00Z",
}


def _validate_status(status: str) -> str:
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


def _ensure_assignee_exists(session: Any, user_id: uuid.UUID | None) -> None:
    if user_id is None:
        return
    from app.models import User

    assignee = session.get(User, user_id)
    if assignee is None:
        raise HTTPException(status_code=404, detail="Assignee not found")
    if not assignee.is_active:
        raise HTTPException(status_code=409, detail="Assignee is inactive")


def _load_visible_work_order(
    *, session: Any, current_user: Any, work_order_id: uuid.UUID
) -> WorkOrder:
    """Fetch a work order and confirm the caller may see it."""
    work_order = get_work_order_by_id(session=session, work_order_id=work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    permissions.ensure_can_view(current_user, work_order)
    return work_order


def _public_events(session: Any, work_order_id: uuid.UUID) -> list[Any]:
    return [
        WorkOrderEventSchema.model_validate(event, from_attributes=True)
        for event in get_work_order_events(session=session, work_order_id=work_order_id)
    ]


def _public_parts(session: Any, work_order_id: uuid.UUID) -> list[Any]:
    return [
        WorkOrderPartPublic.model_validate(
            build_work_order_part_public(db_work_order_part=line_item, db_part=part)
        )
        for line_item, part in get_work_order_parts_with_parts(
            session=session, work_order_id=work_order_id
        )
    ]


router = APIRouter(prefix="/work-orders", tags=["work_orders"])


@router.get(
    "/",
    response_model=ResponseEnvelope[list[WorkOrderPublic]],
    summary="List work orders",
    description=(
        "Lists work orders newest first. Non-superusers only ever see work "
        "orders raised at their own branch. Combine filters to build a queue, "
        "for example assigned_user_id plus status=open for a technician's "
        "current work, or overdue=true for everything that has slipped."
    ),
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
    customer_id: Annotated[
        uuid.UUID | None, Query(description="Filter by customer")
    ] = None,
    fleet_id: Annotated[
        uuid.UUID | None, Query(description="Filter by machine")
    ] = None,
    assigned_user_id: Annotated[
        uuid.UUID | None,
        Query(description="Filter to work assigned to this user account"),
    ] = None,
    overdue: Annotated[
        bool,
        Query(description="Only work orders past their due date that are still live"),
    ] = False,
    search: Annotated[
        str | None,
        Query(max_length=255, description="Case-insensitive substring match on title"),
    ] = None,
) -> Any:
    if status is not None:
        status = _validate_status(status)
    _ensure_branch_exists(session=session, branch_id=branch_id)
    _ensure_assignee_exists(session=session, user_id=assigned_user_id)
    work_orders, count = get_work_orders(
        session=session,
        skip=skip,
        limit=limit,
        status=status,
        branch_id=branch_id,
        customer_id=customer_id,
        fleet_id=fleet_id,
        assigned_user_id=assigned_user_id,
        overdue=overdue,
        search=search,
        visible_branch_ids=permissions.visible_branch_ids(current_user),
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
    summary="Read one work order",
)
def read_work_order(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    return ResponseEnvelope(
        success=True, data=WorkOrderPublic.model_validate(work_order)
    )


@router.get(
    "/{id}/summary",
    response_model=ResponseEnvelope[WorkOrderSummary],
    summary="Read a work order with its parts, timeline, and totals",
    description=(
        "One round trip for a full work-order screen: the work order, its part "
        "lines, its timeline, and the computed parts, labor, and combined "
        "totals. Totals use the unit prices frozen when each part was "
        "attached, and bill actual labor hours when recorded, falling back to "
        "the quoted estimate otherwise."
    ),
    responses={
        404: {"description": "Work order not found"},
    },
)
def read_work_order_summary(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    summary = WorkOrderSummary(
        work_order=WorkOrderPublic.model_validate(work_order),
        parts=_public_parts(session=session, work_order_id=id),
        events=_public_events(session=session, work_order_id=id),
        totals=compute_work_order_totals(session=session, db_work_order=work_order),
    )
    return ResponseEnvelope(
        success=True,
        data=summary,
        message="Retrieved work order summary",
    )


@router.get(
    "/{id}/totals",
    response_model=ResponseEnvelope[WorkOrderTotals],
    summary="Read the parts and labor totals for a work order",
)
def read_work_order_totals(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    totals = compute_work_order_totals(session=session, db_work_order=work_order)
    return ResponseEnvelope(
        success=True, data=totals, message="Retrieved work order totals"
    )


@router.get(
    "/{id}/timeline",
    response_model=ResponseEnvelope[list[WorkOrderEventSchema]],
    summary="Read a work order's activity timeline",
    description=(
        "Every recorded action on this work order, oldest first: hand-written "
        "notes, status changes, assignment changes, completion, reopening, "
        "voiding, and part changes. The author's name is captured on each "
        "entry, so history stays readable after an account is deleted."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [EXAMPLE_EVENT],
                        "message": "Retrieved 1 timeline entry",
                    }
                }
            },
        }
    },
)
def read_work_order_timeline(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    events = _public_events(session=session, work_order_id=id)
    return ResponseEnvelope(
        success=True,
        data=events,
        message=f"Retrieved {len(events)} timeline entry(ies)",
    )


@router.post(
    "/{id}/notes",
    response_model=ResponseEnvelope[WorkOrderEventSchema],
    summary="Add a note to a work order",
    description=(
        "Appends a hand-written note to the work order's timeline. Notes are "
        "append-only and can be added by anyone who can see the work order, "
        "including the assigned technician. Blank notes are rejected."
    ),
    responses={
        403: {"description": "No access to this work order"},
        404: {"description": "Work order not found"},
        409: {"description": "The work order is voided and cannot be annotated"},
    },
)
def add_work_order_note_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    note_in: WorkOrderNoteCreate = Body(
        examples={
            "default": {
                "summary": "Add note",
                "value": {
                    "body": "Replaced the failed capacitor and tested under load."
                },
            }
        },
    ),
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    try:
        event = add_work_order_note(
            session=session,
            db_work_order=work_order,
            note_in=note_in,
            author=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ResponseEnvelope(
        success=True,
        data=WorkOrderEventSchema.model_validate(event, from_attributes=True),
        message="Note added to work order",
    )


@router.post(
    "/",
    response_model=ResponseEnvelope[WorkOrderPublic],
    summary="Create a work order or continuation segment",
    description=(
        "Creates a new work order when the selected branch, customer, and fleet "
        "do not have an active work-order group. If an active group already "
        "exists for the same branch, customer, and fleet, the new record is "
        "automatically added as the next segment and shares the existing "
        "work_order_number. A non-empty segment_reason is required for that "
        "continuation; otherwise the endpoint returns HTTP 409. Completed, "
        "cancelled, and voided groups are closed and start a new group."
    ),
    responses={
        200: {
            "description": "Work order or continuation segment created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": EXAMPLE_WORK_ORDER,
                        "message": "Work order created successfully",
                    }
                }
            },
        },
        403: {"description": "The caller's role may not raise work orders"},
        409: {
            "description": (
                "The customer/fleet is inactive, the fleet does not belong to "
                "the customer, or segment_reason is missing for an active group."
            )
        },
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
    permissions.ensure_can_create(current_user)
    _ensure_branch_exists(session=session, branch_id=work_order_in.branch_id)
    if not current_user.is_superuser:
        # Non-superusers raise work at their own branch; the client cannot pick another.
        if work_order_in.branch_id is None or (
            work_order_in.branch_id != current_user.branch_id
        ):
            raise HTTPException(
                status_code=403,
                detail="You can only raise work orders at your own branch",
            )
    try:
        work_order = create_work_order(
            session=session, work_order_in=work_order_in, author=current_user
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    message = (
        f"Segment {work_order.segment} created for work order "
        f"{work_order.work_order_number}"
        if work_order.segment > 1
        else "Work order created successfully"
    )
    return ResponseEnvelope(
        success=True,
        data=WorkOrderPublic.model_validate(work_order),
        message=message,
    )


@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[WorkOrderPublic],
    summary="Update a work order",
    description=(
        "Applies a partial update. Status changes must follow the lifecycle: "
        "open moves to in_progress, completed, or cancelled; in_progress moves "
        "to open, completed, or cancelled; completed and cancelled may only be "
        "returned to open. Voided is terminal. Any edit other than a status "
        "change to a closed work order is rejected until it is reopened."
    ),
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
        },
        403: {"description": "The caller may not modify this work order"},
        404: {"description": "Work order not found"},
        409: {
            "description": (
                "The requested status change is not legal, the work order is "
                "closed or voided, or the assignee is invalid."
            )
        },
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
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    if "assigned_user_id" in work_order_in.model_dump(exclude_unset=True):
        permissions.ensure_can_assign(current_user, work_order)
    else:
        permissions.ensure_can_update(current_user, work_order)
    if work_order_in.branch_id is not None:
        _ensure_branch_exists(session=session, branch_id=work_order_in.branch_id)
    try:
        updated = update_work_order(
            session=session,
            db_work_order=work_order,
            work_order_in=work_order_in,
            author=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ResponseEnvelope(
        success=True,
        data=WorkOrderPublic.model_validate(updated),
        message="Work order updated successfully",
    )


@router.post(
    "/{id}/complete",
    response_model=ResponseEnvelope[WorkOrderSummary],
    summary="Complete a work order",
    description=(
        "Marks the work order completed, stamps completed_at, optionally "
        "records the actual labor hours spent, and appends a closing note to "
        "the timeline. Returns the full summary so the caller immediately sees "
        "the final totals."
    ),
    responses={
        403: {"description": "The caller may not close this work order"},
        404: {"description": "Work order not found"},
        409: {"description": "The work order is already closed or voided"},
    },
)
def complete_work_order_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    close_in: Annotated[WorkOrderClose, Body()] = WorkOrderClose(),
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    permissions.ensure_can_close(current_user, work_order)
    try:
        closed = close_work_order(
            session=session,
            db_work_order=work_order,
            close_in=close_in,
            author=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    summary = WorkOrderSummary(
        work_order=WorkOrderPublic.model_validate(closed),
        parts=_public_parts(session=session, work_order_id=id),
        events=_public_events(session=session, work_order_id=id),
        totals=compute_work_order_totals(session=session, db_work_order=closed),
    )
    return ResponseEnvelope(
        success=True,
        data=summary,
        message=f"Work order {closed.work_order_number} completed",
    )


@router.post(
    "/{id}/reopen",
    response_model=ResponseEnvelope[WorkOrderPublic],
    summary="Reopen a closed work order",
    description=(
        "Returns a completed or cancelled work order to open and records why "
        "on the timeline. completed_at is cleared; started_at is preserved so "
        "the original start time is not lost. Voided work orders can never be "
        "reopened."
    ),
    responses={
        403: {"description": "The caller may not reopen this work order"},
        404: {"description": "Work order not found"},
        409: {"description": "The work order is voided or was never closed"},
    },
)
def reopen_work_order_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    reopen_in: Annotated[WorkOrderReopen, Body()] = WorkOrderReopen(),
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    permissions.ensure_can_close(current_user, work_order)
    try:
        reopened = reopen_work_order(
            session=session,
            db_work_order=work_order,
            reopen_in=reopen_in,
            author=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ResponseEnvelope(
        success=True,
        data=WorkOrderPublic.model_validate(reopened),
        message="Work order reopened",
    )


@router.delete(
    "/{id}",
    response_model=ResponseEnvelope[WorkOrderPublic],
    summary="Void a work order",
    description=(
        "Voids a work order. The record is retained for auditing; only its "
        "status changes. Voiding is terminal: a voided work order cannot be "
        "edited, completed, reopened, or annotated, and voiding it again is "
        "rejected."
    ),
    responses={
        403: {"description": "The caller may not void this work order"},
        404: {"description": "Work order not found"},
        409: {"description": "The work order is already voided"},
    },
)
def void_work_order(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    permissions.ensure_can_close(current_user, work_order)
    try:
        voided = void_work_order_service(
            session=session, db_work_order=work_order, author=current_user
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ResponseEnvelope(
        success=True,
        data=WorkOrderPublic.model_validate(voided),
        message="Work order voided successfully",
    )


@router.get(
    "/{id}/parts",
    response_model=ResponseEnvelope[list[WorkOrderPartPublic]],
    summary="List the parts on a work order",
)
def read_work_order_parts(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    line_items = _public_parts(session=session, work_order_id=id)
    return ResponseEnvelope(
        success=True,
        data=line_items,
        message=f"Retrieved {len(line_items)} part line(s)",
    )


@router.post(
    "/{id}/parts",
    response_model=ResponseEnvelope[WorkOrderPartPublic],
    summary="Attach a part to a work order",
    responses={
        403: {"description": "The caller may not modify this work order"},
        404: {"description": "Work order or part not found"},
        409: {"description": "Part is inactive or the work order is closed"},
    },
)
def add_work_order_part(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    work_order_part_in: WorkOrderPartCreate = Body(
        examples={
            "default": {
                "summary": "Attach part",
                "value": {
                    "part_id": "3b1a9c22-7f4e-4c1b-9a55-2d8f6e0c1a77",
                    "quantity": 2,
                },
            }
        },
    ),
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    permissions.ensure_can_update(current_user, work_order)
    part = get_part_by_id(session=session, part_id=work_order_part_in.part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    try:
        line_item = add_part_to_work_order(
            session=session,
            db_work_order=work_order,
            db_part=part,
            work_order_part_in=work_order_part_in,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ResponseEnvelope(
        success=True,
        data=WorkOrderPartPublic.model_validate(
            build_work_order_part_public(db_work_order_part=line_item, db_part=part)
        ),
        message="Part added to work order successfully",
    )


@router.patch(
    "/{id}/parts/{line_item_id}",
    response_model=ResponseEnvelope[WorkOrderPartPublic],
    summary="Update quantity or unit price on a work order line",
    responses={
        403: {"description": "The caller may not modify this work order"},
        404: {"description": "Work order part not found"},
    },
)
def update_work_order_part_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    line_item_id: uuid.UUID,
    work_order_part_in: WorkOrderPartUpdate = Body(
        examples={
            "default": {
                "summary": "Update work order part",
                "value": {"quantity": 3, "unit_price": "22.50"},
            }
        },
    ),
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    permissions.ensure_can_update(current_user, work_order)
    line_item = get_work_order_part_by_id(
        session=session, work_order_part_id=line_item_id
    )
    if not line_item or line_item.work_order_id != id:
        raise HTTPException(status_code=404, detail="Work order part not found")
    part = get_part_by_id(session=session, part_id=line_item.part_id)
    if part is None:
        raise HTTPException(status_code=404, detail="Part not found")
    updated = update_work_order_part(
        session=session,
        db_work_order_part=line_item,
        work_order_part_in=work_order_part_in,
    )
    return ResponseEnvelope(
        success=True,
        data=WorkOrderPartPublic.model_validate(
            build_work_order_part_public(db_work_order_part=updated, db_part=part)
        ),
        message="Work order part updated successfully",
    )


@router.delete(
    "/{id}/parts/{line_item_id}",
    response_model=ResponseEnvelope[None],
    summary="Remove a part line from a work order",
    responses={
        403: {"description": "The caller may not modify this work order"},
        404: {"description": "Work order part not found"},
    },
)
def remove_work_order_part_route(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    line_item_id: uuid.UUID,
) -> Any:
    work_order = _load_visible_work_order(
        session=session, current_user=current_user, work_order_id=id
    )
    permissions.ensure_can_update(current_user, work_order)
    line_item = get_work_order_part_by_id(
        session=session, work_order_part_id=line_item_id
    )
    if not line_item or line_item.work_order_id != id:
        raise HTTPException(status_code=404, detail="Work order part not found")
    remove_work_order_part(session=session, db_work_order_part=line_item)
    return ResponseEnvelope(
        success=True, message="Part removed from work order successfully"
    )
