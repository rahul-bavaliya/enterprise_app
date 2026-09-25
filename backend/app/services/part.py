import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select

from app.models import Part, WorkOrder, WorkOrderPart, WorkOrderStatus, quantize_money
from app.schemas import PartCreate, PartUpdate, WorkOrderPartCreate, WorkOrderPartUpdate


def create_part(*, session: Session, part_in: PartCreate) -> Part:
    db_part = Part.model_validate(part_in)
    session.add(db_part)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError(f"Part number '{part_in.part_number}' already exists")
    session.refresh(db_part)
    return db_part


def get_part_by_id(*, session: Session, part_id: uuid.UUID) -> Part | None:
    return session.get(Part, part_id)


def get_part_by_number(*, session: Session, part_number: str) -> Part | None:
    statement = select(Part).where(Part.part_number == part_number)
    return session.exec(statement).first()


def get_parts(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    part_number: str | None = None,
    is_active: bool | None = None,
) -> tuple[Sequence[Part], int]:
    count_statement = select(func.count()).select_from(Part)
    statement = select(Part)
    if part_number is not None:
        count_statement = count_statement.where(Part.part_number == part_number)
        statement = statement.where(Part.part_number == part_number)
    if is_active is not None:
        count_statement = count_statement.where(Part.is_active == is_active)
        statement = statement.where(Part.is_active == is_active)
    count = session.exec(count_statement).one()
    statement = (
        statement.order_by(col(Part.part_number).asc()).offset(skip).limit(limit)
    )
    return session.exec(statement).all(), count


def update_part(*, session: Session, db_part: Part, part_in: PartUpdate) -> Part:
    update_data = part_in.model_dump(exclude_unset=True)
    if "list_price" in update_data and update_data["list_price"] is not None:
        update_data["list_price"] = quantize_money(update_data["list_price"])
    db_part.updated_at = datetime.now(UTC)
    db_part.sqlmodel_update(update_data)
    session.add(db_part)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("Part number already exists")
    session.refresh(db_part)
    return db_part


def deactivate_part(*, session: Session, db_part: Part) -> Part:
    """Retire a part from the catalog.

    Parts referenced by work orders are never removed so historical line items
    keep resolving; the part is simply no longer selectable for new work.
    """
    db_part.is_active = False
    db_part.updated_at = datetime.now(UTC)
    session.add(db_part)
    session.commit()
    session.refresh(db_part)
    return db_part


def add_part_to_work_order(
    *,
    session: Session,
    db_work_order: WorkOrder,
    db_part: Part,
    work_order_part_in: WorkOrderPartCreate,
) -> WorkOrderPart:
    """Attach a part to a work order as a line item.

    ``unit_price`` defaults to the part's current list price, captured on the
    line item so later price changes do not rewrite work order history.
    """
    if db_work_order.status == WorkOrderStatus.VOIDED:
        raise ValueError("Cannot add parts to a voided work order")
    if not db_part.is_active:
        raise ValueError(f"Part '{db_part.part_number}' is inactive")

    existing = get_work_order_part_by_part(
        session=session, work_order_id=db_work_order.id, part_id=db_part.id
    )
    if existing is not None:
        # Treat a repeated add as a quantity increase rather than a duplicate line.
        existing.quantity += work_order_part_in.quantity
        existing.unit_price = quantize_money(
            work_order_part_in.unit_price
            if work_order_part_in.unit_price
            else db_part.list_price
        )
        existing.updated_at = datetime.now(UTC)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    db_work_order_part = WorkOrderPart(
        work_order_id=db_work_order.id,
        part_id=db_part.id,
        quantity=work_order_part_in.quantity,
        unit_price=quantize_money(
            work_order_part_in.unit_price
            if work_order_part_in.unit_price
            else db_part.list_price
        ),
    )
    session.add(db_work_order_part)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("Part is already attached to this work order")
    session.refresh(db_work_order_part)
    return db_work_order_part


def get_work_order_parts_with_parts(
    *, session: Session, work_order_id: uuid.UUID
) -> Sequence[tuple[WorkOrderPart, Part]]:
    """Fetch a work order's line items together with their parts in one query.

    Joining here avoids the N+1 round trips of loading each part separately.
    """
    statement = (
        select(WorkOrderPart, Part)
        .join(Part, WorkOrderPart.part_id == Part.id)
        .where(WorkOrderPart.work_order_id == work_order_id)
        .order_by(col(WorkOrderPart.created_at).asc())
    )
    return session.exec(statement).all()


def get_work_order_part_by_id(
    *, session: Session, work_order_part_id: uuid.UUID
) -> WorkOrderPart | None:
    return session.get(WorkOrderPart, work_order_part_id)


def get_work_order_part_by_part(
    *, session: Session, work_order_id: uuid.UUID, part_id: uuid.UUID
) -> WorkOrderPart | None:
    statement = select(WorkOrderPart).where(
        WorkOrderPart.work_order_id == work_order_id,
        WorkOrderPart.part_id == part_id,
    )
    return session.exec(statement).first()


def get_work_order_parts(
    *, session: Session, work_order_id: uuid.UUID
) -> Sequence[WorkOrderPart]:
    statement = (
        select(WorkOrderPart)
        .where(WorkOrderPart.work_order_id == work_order_id)
        .order_by(col(WorkOrderPart.created_at).asc())
    )
    return session.exec(statement).all()


def update_work_order_part(
    *,
    session: Session,
    db_work_order_part: WorkOrderPart,
    work_order_part_in: WorkOrderPartUpdate,
) -> WorkOrderPart:
    update_data = work_order_part_in.model_dump(exclude_unset=True)
    if "unit_price" in update_data and update_data["unit_price"] is not None:
        update_data["unit_price"] = quantize_money(update_data["unit_price"])
    db_work_order_part.updated_at = datetime.now(UTC)
    db_work_order_part.sqlmodel_update(update_data)
    session.add(db_work_order_part)
    session.commit()
    session.refresh(db_work_order_part)
    return db_work_order_part


def remove_work_order_part(
    *, session: Session, db_work_order_part: WorkOrderPart
) -> None:
    """Remove a line item from a work order.

    The part itself is untouched; only this work order's reference is dropped.
    """
    session.delete(db_work_order_part)
    session.commit()


def build_work_order_part_public(
    *, db_work_order_part: WorkOrderPart, db_part: Part
) -> dict[str, object]:
    """Flatten a line item and its part into the public response payload."""
    quantity = Decimal(db_work_order_part.quantity)
    return {
        "id": db_work_order_part.id,
        "work_order_id": db_work_order_part.work_order_id,
        "part_id": db_work_order_part.part_id,
        "part_number": db_part.part_number,
        "part_description": db_part.description,
        "quantity": db_work_order_part.quantity,
        "unit_price": db_work_order_part.unit_price,
        "line_total": quantize_money(quantity * db_work_order_part.unit_price),
        "created_at": db_work_order_part.created_at,
        "updated_at": db_work_order_part.updated_at,
    }
