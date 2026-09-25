import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlmodel import Session, col, func, select

from app.models import WorkOrder, WorkOrderStatus
from app.schemas import WorkOrderCreate, WorkOrderUpdate


def create_work_order(*, session: Session, work_order_in: WorkOrderCreate) -> WorkOrder:
    db_work_order = WorkOrder.model_validate(work_order_in)
    session.add(db_work_order)
    session.commit()
    session.refresh(db_work_order)
    return db_work_order


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
) -> tuple[Sequence[WorkOrder], int]:
    count_statement = select(func.count()).select_from(WorkOrder)
    statement = select(WorkOrder)
    if status is not None:
        count_statement = count_statement.where(WorkOrder.status == status)
        statement = statement.where(WorkOrder.status == status)
    if branch_id is not None:
        count_statement = count_statement.where(WorkOrder.branch_id == branch_id)
        statement = statement.where(WorkOrder.branch_id == branch_id)
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
) -> WorkOrder:
    update_data = work_order_in.model_dump(exclude_unset=True)
    db_work_order.updated_at = datetime.now(UTC)
    db_work_order.sqlmodel_update(update_data)
    session.add(db_work_order)
    session.commit()
    session.refresh(db_work_order)
    return db_work_order


def void_work_order(*, session: Session, db_work_order: WorkOrder) -> WorkOrder:
    """Void a work order.

    The record is kept for auditing purposes; only its status changes to
    ``VOIDED`` and its ``updated_at`` timestamp is refreshed.
    """
    db_work_order.status = WorkOrderStatus.VOIDED
    db_work_order.updated_at = datetime.now(UTC)
    session.add(db_work_order)
    session.commit()
    session.refresh(db_work_order)
    return db_work_order
