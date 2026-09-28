"""Tests for branch-scoped, role-based access to work orders.

The API used to be superuser-only. These tests pin the replacement: admins and
dispatchers act on their own branch, technicians only touch jobs assigned to
them, and a user with no branch assignment is locked out rather than trusted.
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User, UserRole, WorkOrder
from app.schemas import WorkOrderCreate, WorkOrderUpdate
from app.services import create_work_order, update_work_order
from tests.utils.branch import create_random_branch
from tests.utils.user import user_authentication_headers
from tests.utils.work_order_user import create_role_user

WO = settings.API_V1_STR


def _url(work_order_id: uuid.UUID, suffix: str = "") -> str:
    return f"{WO}/work-orders/{work_order_id}{suffix}"


def _sign_in(client: TestClient, user: User, password: str) -> dict[str, str]:
    return user_authentication_headers(
        client=client, email=user.email, password=password
    )


def _work_order_at(db: Session, branch_id: uuid.UUID) -> uuid.UUID:
    return create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title=f"Job at {branch_id}", branch_id=branch_id
        ),
    ).id


def _assign(
    db: Session, work_order_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Assign a work order directly through the service.

    Assignment is a management action, so technician tests set it up here
    rather than through the API they are not permitted to use.
    """
    work_order = db.exec(select(WorkOrder).where(WorkOrder.id == work_order_id)).one()
    update_work_order(
        session=db,
        db_work_order=work_order,
        work_order_in=WorkOrderUpdate(assigned_user_id=user_id),
    )


# --- visibility --------------------------------------------------------


def test_user_without_a_branch_sees_no_work_orders(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    _work_order_at(db, branch.id)
    user, password = create_role_user(db, role=UserRole.DISPATCHER)
    response = client.get(f"{WO}/work-orders/", headers=_sign_in(client, user, password))
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_dispatcher_sees_only_their_own_branch(
    client: TestClient, db: Session
) -> None:
    mine, theirs = create_random_branch(db), create_random_branch(db)
    mine_id = _work_order_at(db, mine.id)
    _work_order_at(db, theirs.id)

    user, password = create_role_user(db, role=UserRole.DISPATCHER, branch=mine)
    response = client.get(
        f"{WO}/work-orders/", headers=_sign_in(client, user, password)
    )
    assert response.status_code == 200
    ids = [w["id"] for w in response.json()["data"]]
    assert ids == [str(mine_id)]


def test_reading_another_branches_work_order_is_refused(
    client: TestClient, db: Session
) -> None:
    mine, theirs = create_random_branch(db), create_random_branch(db)
    other_id = _work_order_at(db, theirs.id)
    user, password = create_role_user(db, role=UserRole.ADMIN, branch=mine)
    response = client.get(_url(other_id), headers=_sign_in(client, user, password))
    assert response.status_code == 403
    assert response.json()["message"] == "You do not have access to this work order"


def test_superuser_still_sees_everything(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    first, second = create_random_branch(db), create_random_branch(db)
    first_id = _work_order_at(db, first.id)
    second_id = _work_order_at(db, second.id)
    response = client.get(
        f"{WO}/work-orders/", headers=superuser_token_headers, params={"limit": 100}
    )
    ids = {w["id"] for w in response.json()["data"]}
    assert {str(first_id), str(second_id)}.issubset(ids)


# --- creating ----------------------------------------------------------


def test_dispatcher_can_raise_work_at_their_own_branch(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    user, password = create_role_user(db, role=UserRole.DISPATCHER, branch=branch)
    response = client.post(
        f"{WO}/work-orders/",
        headers=_sign_in(client, user, password),
        json={"title": "Raised by dispatcher", "branch_id": str(branch.id)},
    )
    assert response.status_code == 200
    assert response.json()["data"]["branch_id"] == str(branch.id)


def test_dispatcher_cannot_raise_work_at_another_branch(
    client: TestClient, db: Session
) -> None:
    mine, theirs = create_random_branch(db), create_random_branch(db)
    user, password = create_role_user(db, role=UserRole.DISPATCHER, branch=mine)
    response = client.post(
        f"{WO}/work-orders/",
        headers=_sign_in(client, user, password),
        json={"title": "Cross branch", "branch_id": str(theirs.id)},
    )
    assert response.status_code == 403
    assert response.json()["message"] == (
        "You can only raise work orders at your own branch"
    )


def test_technician_cannot_raise_work_orders(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    user, password = create_role_user(db, role=UserRole.TECHNICIAN, branch=branch)
    response = client.post(
        f"{WO}/work-orders/",
        headers=_sign_in(client, user, password),
        json={"title": "Technician raised", "branch_id": str(branch.id)},
    )
    assert response.status_code == 403
    assert response.json()["message"] == "You cannot raise work orders"


# --- editing -----------------------------------------------------------


def test_dispatcher_can_edit_work_at_their_branch(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    work_order_id = _work_order_at(db, branch.id)
    user, password = create_role_user(db, role=UserRole.DISPATCHER, branch=branch)
    response = client.patch(
        _url(work_order_id),
        headers=_sign_in(client, user, password),
        json={"priority": "urgent"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["priority"] == "urgent"


def test_technician_can_edit_work_assigned_to_them(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    technician, password = create_role_user(
        db, role=UserRole.TECHNICIAN, branch=branch
    )
    work_order_id = _work_order_at(db, branch.id)
    _assign(db, work_order_id, technician.id)

    response = client.patch(
        _url(work_order_id),
        headers=_sign_in(client, technician, password),
        json={"priority": "high"},
    )
    assert response.status_code == 200


def test_technician_cannot_edit_unassigned_work(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    technician, password = create_role_user(
        db, role=UserRole.TECHNICIAN, branch=branch
    )
    work_order_id = _work_order_at(db, branch.id)

    response = client.patch(
        _url(work_order_id),
        headers=_sign_in(client, technician, password),
        json={"priority": "high"},
    )
    assert response.status_code == 403
    assert response.json()["message"] == "You cannot modify this work order"


def test_technician_cannot_assign_work(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    technician, password = create_role_user(
        db, role=UserRole.TECHNICIAN, branch=branch
    )
    other, _ = create_role_user(db, role=UserRole.TECHNICIAN, branch=branch)
    work_order_id = _work_order_at(db, branch.id)
    _assign(db, work_order_id, technician.id)

    response = client.patch(
        _url(work_order_id),
        headers=_sign_in(client, technician, password),
        json={"assigned_user_id": str(other.id)},
    )
    assert response.status_code == 403
    assert response.json()["message"] == "You cannot assign this work order"


def test_technician_cannot_close_work(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    technician, password = create_role_user(
        db, role=UserRole.TECHNICIAN, branch=branch
    )
    work_order_id = _work_order_at(db, branch.id)
    _assign(db, work_order_id, technician.id)

    response = client.post(
        _url(work_order_id, "/complete"),
        headers=_sign_in(client, technician, password),
        json={},
    )
    assert response.status_code == 403
    assert response.json()["message"] == "You cannot close or void this work order"


def test_dispatcher_can_close_work_at_their_branch(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    work_order_id = _work_order_at(db, branch.id)
    user, password = create_role_user(db, role=UserRole.DISPATCHER, branch=branch)
    response = client.post(
        _url(work_order_id, "/complete"),
        headers=_sign_in(client, user, password),
        json={"actual_labor_hours": "1.00"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["work_order"]["status"] == "completed"


# --- notes -------------------------------------------------------------


def test_technician_can_note_work_assigned_to_them(
    client: TestClient, db: Session
) -> None:
    branch = create_random_branch(db)
    technician, password = create_role_user(
        db, role=UserRole.TECHNICIAN, branch=branch
    )
    work_order_id = _work_order_at(db, branch.id)
    _assign(db, work_order_id, technician.id)

    response = client.post(
        _url(work_order_id, "/notes"),
        headers=_sign_in(client, technician, password),
        json={"body": "Checked the belt, all good."},
    )
    assert response.status_code == 200
    assert response.json()["data"]["body"] == "Checked the belt, all good."


def test_technician_cannot_note_work_at_another_branch(
    client: TestClient, db: Session
) -> None:
    mine, theirs = create_random_branch(db), create_random_branch(db)
    technician, password = create_role_user(
        db, role=UserRole.TECHNICIAN, branch=mine
    )
    other_id = _work_order_at(db, theirs.id)

    response = client.post(
        _url(other_id, "/notes"),
        headers=_sign_in(client, technician, password),
        json={"body": "Not mine."},
    )
    assert response.status_code == 403
