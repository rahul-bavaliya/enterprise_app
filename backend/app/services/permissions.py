"""Branch-scoped authorization for work-order operations.

The API used to be all-or-nothing: every domain route demanded
``is_superuser``. That leaves no way for a dispatcher or a technician to do
their job. These helpers replace that gate with three operational roles, each
restricted to the branch the user belongs to.

Roles:

* ``ADMIN`` - full control of work orders raised at their own branch,
  including reassignment, voiding, and reopening.
* ``DISPATCHER`` - raises, schedules, assigns, and edits work orders at their
  own branch.
* ``TECHNICIAN`` - reads work at their own branch, and may only record work on
  jobs assigned to them.

A user with no branch assignment sees nothing rather than everything; the
absence of a branch is never treated as a wildcard.
"""

import uuid
from collections.abc import Sequence

from app.core.exceptions import ForbiddenException
from app.models import User, UserRole, WorkOrder, WorkOrderStatus

#: Roles that may raise and schedule new work.
SCHEDULING_ROLES = frozenset({UserRole.ADMIN, UserRole.DISPATCHER})

#: Roles that may change how a job is scheduled or billed.
MANAGEMENT_ROLES = frozenset({UserRole.ADMIN, UserRole.DISPATCHER})

#: Roles that may close, reopen, or void a job outright.
CLOSING_ROLES = frozenset({UserRole.ADMIN, UserRole.DISPATCHER})


def is_superuser(user: User) -> bool:
    return user.is_superuser


def can_create_work_orders(user: User) -> bool:
    """Admins and dispatchers raise work; technicians do not."""
    if is_superuser(user):
        return True
    return user.role in SCHEDULING_ROLES and user.branch_id is not None


def can_view_work_order(user: User, db_work_order: WorkOrder) -> bool:
    """A user may read work orders raised at their own branch."""
    if is_superuser(user):
        return True
    if user.branch_id is None:
        return False
    return db_work_order.branch_id == user.branch_id


def can_update_work_order(user: User, db_work_order: WorkOrder) -> bool:
    """Admins and dispatchers edit; technicians only their own assigned jobs."""
    if is_superuser(user):
        return True
    if user.branch_id is None or db_work_order.branch_id != user.branch_id:
        return False
    if user.role in MANAGEMENT_ROLES:
        return True
    return user.role == UserRole.TECHNICIAN and (
        db_work_order.assigned_user_id == user.id
    )


def can_assign_work_order(user: User, db_work_order: WorkOrder) -> bool:
    """Only admins and dispatchers decide who does the work."""
    if is_superuser(user):
        return True
    if user.branch_id is None or db_work_order.branch_id != user.branch_id:
        return False
    return user.role in MANAGEMENT_ROLES


def can_close_work_order(user: User, db_work_order: WorkOrder) -> bool:
    """Closing, reopening, and voiding are management actions."""
    if is_superuser(user):
        return True
    if user.branch_id is None or db_work_order.branch_id != user.branch_id:
        return False
    if user.role not in CLOSING_ROLES:
        return False
    return db_work_order.status != WorkOrderStatus.VOIDED


def can_add_note(user: User, db_work_order: WorkOrder) -> bool:
    """Anyone who can see the work order may add a note to it."""
    return can_view_work_order(user, db_work_order)


def visible_branch_ids(user: User) -> Sequence[uuid.UUID] | None:
    """Branches a user may read, or ``None`` when unrestricted.

    A non-superuser with no branch assignment gets an empty allow-list rather
    than a wildcard, so misconfigured accounts fail closed.
    """
    if is_superuser(user):
        return None
    return [user.branch_id] if user.branch_id is not None else []


def ensure_can_view(user: User, db_work_order: WorkOrder) -> None:
    if not can_view_work_order(user, db_work_order):
        raise ForbiddenException("You do not have access to this work order")


def ensure_can_update(user: User, db_work_order: WorkOrder) -> None:
    if not can_update_work_order(user, db_work_order):
        raise ForbiddenException("You cannot modify this work order")


def ensure_can_assign(user: User, db_work_order: WorkOrder) -> None:
    if not can_assign_work_order(user, db_work_order):
        raise ForbiddenException("You cannot assign this work order")


def ensure_can_close(user: User, db_work_order: WorkOrder) -> None:
    if not can_close_work_order(user, db_work_order):
        raise ForbiddenException("You cannot close or void this work order")


def ensure_can_create(user: User) -> None:
    if not can_create_work_orders(user):
        raise ForbiddenException("You cannot raise work orders")
