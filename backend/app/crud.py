"""Compatibility shim.

The data-access layer now lives in ``app.services``. This module re-exports
the service functions so older imports like ``from app import crud`` keep
working during the transition.
"""

from app.services import (
    authenticate,
    create_branch,
    create_item,
    create_user,
    create_work_order,
    delete_branch,
    delete_work_order,
    get_branch_by_id,
    get_branches,
    get_user_by_email,
    get_work_order_by_id,
    get_work_orders,
    update_branch,
    update_item,
    update_user,
    update_work_order,
)

__all__ = [
    "authenticate",
    "create_branch",
    "create_item",
    "create_user",
    "create_work_order",
    "delete_branch",
    "delete_work_order",
    "get_branch_by_id",
    "get_branches",
    "get_user_by_email",
    "get_work_order_by_id",
    "get_work_orders",
    "update_branch",
    "update_item",
    "update_user",
    "update_work_order",
]
