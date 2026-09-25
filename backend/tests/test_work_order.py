from sqlmodel import Session

from app.models import (
    WorkOrderCreate,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderUpdate,
)
from app.services import (
    create_work_order,
    get_work_order_by_id,
    get_work_orders,
    update_work_order,
    void_work_order,
)
from tests.utils.utils import random_lower_string


def test_work_order_timestamps_on_create_and_update(db: Session) -> None:
    work_order = create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(title="Test work order"),
    )

    assert work_order.created_at is not None
    assert work_order.updated_at is None
    assert work_order.status == WorkOrderStatus.OPEN
    assert work_order.priority == WorkOrderPriority.MEDIUM

    updated_work_order = update_work_order(
        session=db,
        db_work_order=work_order,
        work_order_in=WorkOrderUpdate(status=WorkOrderStatus.IN_PROGRESS),
    )

    assert updated_work_order.updated_at is not None
    assert updated_work_order.updated_at >= updated_work_order.created_at
    assert updated_work_order.status == WorkOrderStatus.IN_PROGRESS


def test_get_work_orders_filters_by_status(db: Session) -> None:
    created = create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(title=random_lower_string()),
    )
    work_orders, count = get_work_orders(session=db, status=WorkOrderStatus.OPEN.value)
    assert count >= 1
    assert any(wo.id == created.id for wo in work_orders)
    closed_orders, closed_count = get_work_orders(
        session=db, status=WorkOrderStatus.CANCELLED.value
    )
    assert all(wo.id != created.id for wo in closed_orders)


def test_void_work_order_retains_the_record(db: Session) -> None:
    work_order = create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(title=random_lower_string()),
    )
    voided = void_work_order(session=db, db_work_order=work_order)

    assert voided.status == WorkOrderStatus.VOIDED
    assert voided.updated_at is not None
    # The row must survive a void so the history stays auditable.
    persisted = get_work_order_by_id(session=db, work_order_id=work_order.id)
    assert persisted is not None
    assert persisted.status == WorkOrderStatus.VOIDED
