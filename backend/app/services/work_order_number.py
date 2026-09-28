"""Work order number generation.

Numbers follow ``BranchCode-mmyy-0001``: a branch code, the month in ``mmyy``
form, and a sequence restarting at 1 for each branch each month.

Example: a work order raised at the ``MAIN`` branch in September 2026 is
``MAIN-0926-0001``.
"""

import re
import threading
from datetime import datetime

from sqlalchemy import String, cast, func
from sqlmodel import Session, col, select

from app.models import WorkOrder

# Serialises concurrent creators within one process. The unique index on
# work_order_number remains the final guard across processes.
_LOCK = threading.Lock()


def branch_code_for(branch_name: str) -> str:
    """Derive a compact branch code, e.g. 'Main Branch' -> 'MAIN'."""
    letters = re.sub(r"[^A-Za-z0-9]", "", branch_name).upper()
    return letters[:4] or "GEN"


def next_work_order_number(
    *, session: Session, branch_code: str, moment: datetime
) -> str:
    """Return the next sequential number for a branch within the month."""
    period = moment.strftime("%m%y")
    prefix = f"{branch_code}-{period}"

    # Read the highest sequence already stored for this prefix.
    statement = select(
        func.max(
            func.substring(cast(WorkOrder.work_order_number, String), len(prefix) + 2)
        )
    ).where(col(WorkOrder.work_order_number).like(f"{prefix}-%"))
    highest = session.exec(statement).one()

    with _LOCK:
        sequence = (int(highest) if highest else 0) + 1
    return f"{prefix}-{sequence:04d}"


def work_order_number_for_branch(
    *, session: Session, branch_name: str, moment: datetime
) -> str:
    """Build the next work order number for a named branch."""
    return next_work_order_number(
        session=session, branch_code=branch_code_for(branch_name), moment=moment
    )
