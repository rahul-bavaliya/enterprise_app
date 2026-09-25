import uuid

from sqlmodel import Session

from app.models import WorkOrder, WorkOrderCreate, WorkOrderStatus
from tests.utils.utils import random_lower_string


def create_random_work_order(
    db: Session, *, status: WorkOrderStatus = WorkOrderStatus.OPEN
) -> WorkOrder:
    title = random_lower_string()
    description = random_lower_string()
    work_order_in = WorkOrderCreate(
        title=title,
        description=description,
        status=status,
    )
    from app.services import create_work_order

    return create_work_order(session=db, work_order_in=work_order_in)


def create_random_work_order_for_branch(db: Session, branch_id: uuid.UUID) -> WorkOrder:
    work_order_in = WorkOrderCreate(
        title=random_lower_string(),
        branch_id=branch_id,
    )
    from app.services import create_work_order

    return create_work_order(session=db, work_order_in=work_order_in)
