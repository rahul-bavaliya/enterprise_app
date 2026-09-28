import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlmodel import Session, col, func, select

from app.models import (
    User,
    WorkOrder,
    WorkOrderEvent,
    WorkOrderEventType,
    WorkOrderStatus,
    WorkOrderTotals,
    quantize_money,
)
from app.schemas import (
    WorkOrderClose,
    WorkOrderCreate,
    WorkOrderNoteCreate,
    WorkOrderReopen,
    WorkOrderUpdate,
)
from app.services.customer import get_customer_by_id, get_fleet_by_id
from app.services.work_order_number import work_order_number_for_branch

#: Statuses from which no further work may be recorded without an explicit reopen.
CLOSED_STATUSES = frozenset(
    {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED, WorkOrderStatus.VOIDED}
)

#: The only status changes the API accepts. Anything else is a 409.
ALLOWED_TRANSITIONS: dict[WorkOrderStatus, frozenset[WorkOrderStatus]] = {
    WorkOrderStatus.OPEN: frozenset(
        {
            WorkOrderStatus.IN_PROGRESS,
            WorkOrderStatus.COMPLETED,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.IN_PROGRESS: frozenset(
        {
            WorkOrderStatus.OPEN,
            WorkOrderStatus.COMPLETED,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.COMPLETED: frozenset({WorkOrderStatus.OPEN}),
    WorkOrderStatus.CANCELLED: frozenset({WorkOrderStatus.OPEN}),
    WorkOrderStatus.VOIDED: frozenset(),
}


def _resolve_customer_and_fleet(
    *,
    session: Session,
    customer_id: uuid.UUID | None,
    fleet_id: uuid.UUID | None,
) -> None:
    """Validate that a selected fleet belongs to the selected active customer.

    Work orders may still be created without a customer, preserving existing
    callers, but a fleet can never be selected without its owning customer.
    """
    if customer_id is None:
        if fleet_id is not None:
            raise ValueError("A fleet cannot be selected without a customer")
        return

    customer = get_customer_by_id(session=session, customer_id=customer_id)
    if customer is None:
        raise ValueError("Customer not found")
    if not customer.is_active:
        raise ValueError(f"Customer '{customer.name}' is inactive")

    if fleet_id is not None:
        fleet = get_fleet_by_id(session=session, fleet_id=fleet_id)
        if fleet is None:
            raise ValueError("Fleet not found")
        if fleet.customer_id != customer_id:
            raise ValueError("Fleet does not belong to the selected customer")
        if not fleet.is_active:
            raise ValueError(f"Fleet '{fleet.asset_tag}' is inactive")


def _resolve_assignee(
    *, session: Session, assigned_user_id: uuid.UUID | None
) -> None:
    """Validate that a work order is only assigned to a real, active account."""
    if assigned_user_id is None:
        return
    assignee = session.get(User, assigned_user_id)
    if assignee is None:
        raise ValueError("Assignee not found")
    if not assignee.is_active:
        raise ValueError(f"Assignee '{assignee.email}' is inactive")


def _assert_transition(current: WorkOrderStatus, target: WorkOrderStatus) -> None:
    """Reject any status change the lifecycle does not allow.

    Voided is terminal, so it never appears as an allowed target. Closed orders
    may only return to open, and that is deliberately the single exit.
    """
    if current == target:
        return
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        allowed_names = ", ".join(sorted(s.value for s in allowed)) or "none"
        raise ValueError(
            f"Cannot change status from '{current.value}' to '{target.value}'. "
            f"Allowed from '{current.value}': {allowed_names}"
        )


def assert_editable(
    db_work_order: WorkOrder, *, changing_fields: frozenset[str] = frozenset()
) -> None:
    """Refuse edits to a closed work order unless they are a reopen.

    Voided work orders are permanently frozen. Completed and cancelled ones may
    only be reopened, so a change touching any field other than ``status`` is
    rejected outright.
    """
    if db_work_order.status == WorkOrderStatus.VOIDED:
        raise ValueError("A voided work order cannot be modified")
    if db_work_order.status in CLOSED_STATUSES:
        if changing_fields - {"status"}:
            raise ValueError(
                f"Work order is {db_work_order.status.value}; "
                "reopen it before making further changes"
            )


def record_event(
    *,
    session: Session,
    db_work_order: WorkOrder,
    event_type: WorkOrderEventType,
    author: User | None = None,
    body: str | None = None,
    from_status: WorkOrderStatus | None = None,
    to_status: WorkOrderStatus | None = None,
) -> WorkOrderEvent:
    """Append one entry to a work order's timeline.

    The author's display name is copied onto the entry so the audit trail stays
    readable after the account is deleted.
    """
    event = WorkOrderEvent(
        work_order_id=db_work_order.id,
        event_type=event_type,
        body=body,
        from_status=from_status,
        to_status=to_status,
        author_id=author.id if author else None,
        author_name=(author.full_name or author.email) if author else None,
    )
    session.add(event)
    return event


def add_work_order_note(
    *,
    session: Session,
    db_work_order: WorkOrder,
    note_in: WorkOrderNoteCreate,
    author: User | None = None,
) -> WorkOrderEvent:
    """Append a hand-written note to a work order's timeline."""
    if db_work_order.status == WorkOrderStatus.VOIDED:
        raise ValueError("Cannot add a note to a voided work order")
    body = note_in.body.strip()
    if not body:
        raise ValueError("A note cannot be empty")
    event = record_event(
        session=session,
        db_work_order=db_work_order,
        event_type=WorkOrderEventType.NOTE,
        author=author,
        body=body,
    )
    session.commit()
    session.refresh(event)
    return event


def get_work_order_events(
    *, session: Session, work_order_id: uuid.UUID
) -> Sequence[WorkOrderEvent]:
    """Return a work order's timeline, oldest first."""
    statement = (
        select(WorkOrderEvent)
        .where(WorkOrderEvent.work_order_id == work_order_id)
        .order_by(col(WorkOrderEvent.created_at).asc(), col(WorkOrderEvent.id).asc())
    )
    return session.exec(statement).all()


def compute_work_order_totals(
    *, session: Session, db_work_order: WorkOrder
) -> WorkOrderTotals:
    """Roll up parts and labor into a priced total.

    Parts come from the line items, whose unit prices were frozen at attach
    time. Labor bills actual hours when recorded and falls back to the quoted
    estimate otherwise, so a work order is never silently worth nothing.
    """
    from app.models import WorkOrderPart

    statement = select(
        func.coalesce(
            func.sum(WorkOrderPart.quantity * WorkOrderPart.unit_price), 0
        )
    ).where(WorkOrderPart.work_order_id == db_work_order.id)
    parts_total = quantize_money(Decimal(session.exec(statement).one() or 0))

    labor_hours = db_work_order.actual_labor_hours
    if labor_hours is None:
        labor_hours = db_work_order.quoted_labor_hours
    labor_hours = labor_hours or Decimal("0.00")
    labor_rate = db_work_order.labor_rate or Decimal("0.00")
    labor_total = quantize_money(Decimal(labor_hours) * Decimal(labor_rate))

    return WorkOrderTotals(
        parts_total=parts_total,
        labor_hours=quantize_money(Decimal(labor_hours)),
        labor_total=labor_total,
        total_cost=quantize_money(parts_total + labor_total),
    )


def create_work_order(
    *,
    session: Session,
    work_order_in: WorkOrderCreate,
    author: User | None = None,
) -> WorkOrder:
    _resolve_customer_and_fleet(
        session=session,
        customer_id=work_order_in.customer_id,
        fleet_id=work_order_in.fleet_id,
    )
    _resolve_assignee(session=session, assigned_user_id=work_order_in.assigned_user_id)
    db_work_order = WorkOrder.model_validate(work_order_in)
    previous = _find_latest_group_member(
        session=session,
        branch_id=work_order_in.branch_id,
        customer_id=work_order_in.customer_id,
        fleet_id=work_order_in.fleet_id,
    )
    if previous is None:
        db_work_order.segment = 1
        _assign_work_order_number(session=session, work_order=db_work_order)
    else:
        if not work_order_in.segment_reason or not work_order_in.segment_reason.strip():
            raise ValueError(
                "A reason is required when adding a segment to an active work order"
            )
        _assign_next_segment(
            session=session,
            previous=previous,
            work_order=db_work_order,
        )
    session.add(db_work_order)
    record_event(
        session=session,
        db_work_order=db_work_order,
        event_type=WorkOrderEventType.CREATED,
        author=author,
        body=(
            f"Segment {db_work_order.segment} created for "
            f"{db_work_order.work_order_number}"
            if db_work_order.segment > 1
            else "Work order created"
        ),
        to_status=db_work_order.status,
    )
    session.commit()
    session.refresh(db_work_order)
    return db_work_order


def _find_latest_group_member(
    *,
    session: Session,
    branch_id: uuid.UUID | None,
    customer_id: uuid.UUID | None,
    fleet_id: uuid.UUID | None,
) -> WorkOrder | None:
    """Find the active work-order group for the same branch/customer/machine.

    A work order only joins an existing group when all three identifiers are
    present and the existing group is still active. Customerless or machine-less
    work orders remain independent. Completed, cancelled, and voided groups are
    closed and never receive a new segment.
    """
    if branch_id is None or customer_id is None or fleet_id is None:
        return None
    statement = (
        select(WorkOrder)
        .where(
            WorkOrder.branch_id == branch_id,
            WorkOrder.customer_id == customer_id,
            WorkOrder.fleet_id == fleet_id,
            col(WorkOrder.status).in_(
                [WorkOrderStatus.OPEN, WorkOrderStatus.IN_PROGRESS]
            ),
        )
        .order_by(col(WorkOrder.created_at).desc())
    )
    return session.exec(statement).first()


def _assign_next_segment(
    *, session: Session, previous: WorkOrder, work_order: WorkOrder
) -> None:
    """Continue an existing work-order group with the next segment."""
    group_max = session.exec(
        select(func.max(WorkOrder.segment)).where(
            WorkOrder.work_order_number == previous.work_order_number
        )
    ).one()
    work_order.work_order_number = previous.work_order_number
    work_order.segment = (group_max or previous.segment) + 1
    work_order.parent_work_order_id = previous.id


def _assign_work_order_number(*, session: Session, work_order: WorkOrder) -> None:
    """Stamp the work order with its generated human readable number."""
    from app.services.branch import get_branch_by_id

    branch_name = "General"
    if work_order.branch_id is not None:
        branch = get_branch_by_id(session=session, branch_id=work_order.branch_id)
        if branch is not None:
            branch_name = branch.name
    work_order.work_order_number = work_order_number_for_branch(
        session=session, branch_name=branch_name, moment=datetime.now(UTC)
    )


def get_work_order_by_id(
    *, session: Session, work_order_id: uuid.UUID
) -> WorkOrder | None:
    return session.get(WorkOrder, work_order_id)


def get_work_orders(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    branch_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    fleet_id: uuid.UUID | None = None,
    assigned_user_id: uuid.UUID | None = None,
    overdue: bool = False,
    search: str | None = None,
    visible_branch_ids: Sequence[uuid.UUID] | None = None,
) -> tuple[Sequence[WorkOrder], int]:
    """List work orders, newest first, with the caller's visibility applied.

    ``visible_branch_ids`` is the set of branches a non-superuser may see. It is
    an explicit allow-list rather than a single branch so an administrator with
    no branch assignment is not silently granted or denied everything.
    """
    count_statement = select(func.count()).select_from(WorkOrder)
    statement = select(WorkOrder)
    if status is not None:
        count_statement = count_statement.where(WorkOrder.status == status)
        statement = statement.where(WorkOrder.status == status)
    if branch_id is not None:
        count_statement = count_statement.where(WorkOrder.branch_id == branch_id)
        statement = statement.where(WorkOrder.branch_id == branch_id)
    if customer_id is not None:
        count_statement = count_statement.where(
            WorkOrder.customer_id == customer_id
        )
        statement = statement.where(WorkOrder.customer_id == customer_id)
    if fleet_id is not None:
        count_statement = count_statement.where(WorkOrder.fleet_id == fleet_id)
        statement = statement.where(WorkOrder.fleet_id == fleet_id)
    if assigned_user_id is not None:
        count_statement = count_statement.where(
            WorkOrder.assigned_user_id == assigned_user_id
        )
        statement = statement.where(WorkOrder.assigned_user_id == assigned_user_id)
    if overdue:
        # Overdue means the due date has passed and the job is still live.
        live = [WorkOrderStatus.OPEN, WorkOrderStatus.IN_PROGRESS]
        count_statement = count_statement.where(
            col(WorkOrder.due_date) < date.today(),
            col(WorkOrder.status).in_(live),
        )
        statement = statement.where(
            col(WorkOrder.due_date) < date.today(),
            col(WorkOrder.status).in_(live),
        )
    if search:
        pattern = f"%{search.strip()}%"
        count_statement = count_statement.where(col(WorkOrder.title).ilike(pattern))
        statement = statement.where(col(WorkOrder.title).ilike(pattern))
    if visible_branch_ids is not None:
        allowed = list(visible_branch_ids)
        if not allowed:
            # No visible branches means no results, without an impossible predicate.
            return [], 0
        count_statement = count_statement.where(
            col(WorkOrder.branch_id).in_(allowed)
        )
        statement = statement.where(col(WorkOrder.branch_id).in_(allowed))
    count = session.exec(count_statement).one()
    statement = (
        statement.order_by(col(WorkOrder.created_at).desc()).offset(skip).limit(limit)
    )
    work_orders = session.exec(statement).all()
    return work_orders, count


def update_work_order(
    *,
    session: Session,
    db_work_order: WorkOrder,
    work_order_in: WorkOrderUpdate,
    author: User | None = None,
) -> WorkOrder:
    """Apply a partial update, enforcing the lifecycle on the way in."""
    update_data = work_order_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_work_order

    # Validate the resulting combination, not just the fields being changed.
    _resolve_customer_and_fleet(
        session=session,
        customer_id=update_data.get("customer_id", db_work_order.customer_id),
        fleet_id=update_data.get("fleet_id", db_work_order.fleet_id),
    )
    if "assigned_user_id" in update_data:
        _resolve_assignee(
            session=session, assigned_user_id=update_data["assigned_user_id"]
        )

    previous_assignee = db_work_order.assigned_user_id
    previous_status = db_work_order.status

    assert_editable(db_work_order, changing_fields=frozenset(update_data))
    if "status" in update_data:
        _assert_transition(previous_status, update_data["status"])

    if "labor_rate" in update_data and update_data["labor_rate"] is not None:
        update_data["labor_rate"] = quantize_money(update_data["labor_rate"])

    now = datetime.now(UTC)
    target_status = update_data.get("status", previous_status)
    _apply_status_timestamps(
        work_order=db_work_order,
        previous=previous_status,
        target=target_status,
        moment=now,
    )
    db_work_order.updated_at = now
    db_work_order.sqlmodel_update(update_data)

    if "status" in update_data and update_data["status"] != previous_status:
        record_event(
            session=session,
            db_work_order=db_work_order,
            event_type=WorkOrderEventType.STATUS_CHANGED,
            author=author,
            from_status=previous_status,
            to_status=target_status,
        )
    if "assigned_user_id" in update_data and (
        update_data["assigned_user_id"] != previous_assignee
    ):
        record_event(
            session=session,
            db_work_order=db_work_order,
            event_type=WorkOrderEventType.ASSIGNED,
            author=author,
            body=_assignee_label(
                session=session, user_id=update_data["assigned_user_id"]
            ),
        )

    session.add(db_work_order)
    session.commit()
    session.refresh(db_work_order)
    return db_work_order


def _assignee_label(*, session: Session, user_id: uuid.UUID | None) -> str:
    if user_id is None:
        return "Unassigned"
    assignee = session.get(User, user_id)
    if assignee is None:
        return f"User {user_id}"
    return assignee.full_name or assignee.email


def _apply_status_timestamps(
    *,
    work_order: WorkOrder,
    previous: WorkOrderStatus,
    target: WorkOrderStatus,
    moment: datetime,
) -> None:
    """Stamp started_at and completed_at as the status moves.

    Both stamps are write-once so reopening and re-closing a work order keeps
    the original start and records the most recent completion.
    """
    if target == WorkOrderStatus.IN_PROGRESS and previous != target:
        if work_order.started_at is None:
            work_order.started_at = moment
    if target == WorkOrderStatus.COMPLETED:
        work_order.completed_at = moment
    elif target == WorkOrderStatus.OPEN:
        # Reopening clears completion but keeps when the work originally started.
        work_order.completed_at = None


def close_work_order(
    *,
    session: Session,
    db_work_order: WorkOrder,
    close_in: WorkOrderClose,
    author: User | None = None,
) -> WorkOrder:
    """Complete a work order, recording actual hours and a closing note."""
    if db_work_order.status in CLOSED_STATUSES:
        raise ValueError(
            f"Work order is already {db_work_order.status.value} and cannot be completed"
        )
    if close_in.actual_labor_hours is not None:
        db_work_order.actual_labor_hours = close_in.actual_labor_hours
    body = (close_in.body or "").strip() or None

    now = datetime.now(UTC)
    previous = db_work_order.status
    _apply_status_timestamps(
        work_order=db_work_order,
        previous=previous,
        target=WorkOrderStatus.COMPLETED,
        moment=now,
    )
    db_work_order.status = WorkOrderStatus.COMPLETED
    db_work_order.updated_at = now
    session.add(db_work_order)
    record_event(
        session=session,
        db_work_order=db_work_order,
        event_type=WorkOrderEventType.COMPLETED,
        author=author,
        body=body,
        from_status=previous,
        to_status=WorkOrderStatus.COMPLETED,
    )
    session.commit()
    session.refresh(db_work_order)
    return db_work_order


def reopen_work_order(
    *,
    session: Session,
    db_work_order: WorkOrder,
    reopen_in: WorkOrderReopen,
    author: User | None = None,
) -> WorkOrder:
    """Return a completed or cancelled work order to open."""
    if db_work_order.status == WorkOrderStatus.VOIDED:
        raise ValueError("A voided work order cannot be reopened")
    if db_work_order.status not in CLOSED_STATUSES:
        raise ValueError(
            f"Work order is {db_work_order.status.value} and does not need reopening"
        )
    now = datetime.now(UTC)
    previous = db_work_order.status
    _apply_status_timestamps(
        work_order=db_work_order,
        previous=previous,
        target=WorkOrderStatus.OPEN,
        moment=now,
    )
    db_work_order.status = WorkOrderStatus.OPEN
    db_work_order.updated_at = now
    session.add(db_work_order)
    record_event(
        session=session,
        db_work_order=db_work_order,
        event_type=WorkOrderEventType.REOPENED,
        author=author,
        body=(reopen_in.body or "").strip() or None,
        from_status=previous,
        to_status=WorkOrderStatus.OPEN,
    )
    session.commit()
    session.refresh(db_work_order)
    return db_work_order


def void_work_order(
    *,
    session: Session,
    db_work_order: WorkOrder,
    author: User | None = None,
    body: str | None = None,
) -> WorkOrder:
    """Void a work order.

    The record is kept for auditing purposes; only its status changes to
    ``VOIDED`` and its ``updated_at`` timestamp is refreshed. Voiding is
    terminal, so it is rejected on an already-voided work order.
    """
    if db_work_order.status == WorkOrderStatus.VOIDED:
        raise ValueError("Work order is already voided")
    now = datetime.now(UTC)
    previous = db_work_order.status
    db_work_order.status = WorkOrderStatus.VOIDED
    db_work_order.updated_at = now
    session.add(db_work_order)
    record_event(
        session=session,
        db_work_order=db_work_order,
        event_type=WorkOrderEventType.VOIDED,
        author=author,
        body=(body or "").strip() or None,
        from_status=previous,
        to_status=WorkOrderStatus.VOIDED,
    )
    session.commit()
    session.refresh(db_work_order)
    return db_work_order
