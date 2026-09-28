"""Tests for the work-order lifecycle, timeline, and totals.

These cover the rules that make a work order maintainable rather than merely
storable: legal status transitions, a frozen closed state, an append-only
audit trail, and money that actually adds up.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import WorkOrderStatus
from app.schemas import WorkOrderCreate, WorkOrderUpdate
from app.services import create_work_order, update_work_order
from tests.utils.branch import create_random_branch
from tests.utils.part import create_random_part
from tests.utils.work_order import create_random_work_order

WO = settings.API_V1_STR


def _url(work_order_id: uuid.UUID, suffix: str = "") -> str:
    return f"{WO}/work-orders/{work_order_id}{suffix}"


# --- status lifecycle -------------------------------------------------


def test_open_to_in_progress_stamps_started_at(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    assert work_order.started_at is None

    response = client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "in_progress"
    assert data["started_at"] is not None


def test_open_to_completed_is_allowed_directly(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"status": "completed"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


def test_illegal_status_change_is_rejected(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db, status=WorkOrderStatus.CANCELLED)
    response = client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"status": "in_progress"},
    )
    assert response.status_code == 409
    message = response.json()["message"]
    assert "Cannot change status from 'cancelled' to 'in_progress'" in message
    # The rejection explains what is legal from the current state.
    assert "open" in message


def test_completed_work_order_rejects_content_edits(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db, status=WorkOrderStatus.COMPLETED)
    response = client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"title": "Changed after completion"},
    )
    assert response.status_code == 409
    assert "reopen it before" in response.json()["message"]


def test_voided_work_order_is_frozen(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    assert (
        client.delete(
            _url(work_order.id), headers=superuser_token_headers
        ).status_code
        == 200
    )

    patch = client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"title": "Nope"},
    )
    assert patch.status_code == 409
    assert patch.json()["message"] == "A voided work order cannot be modified"

    reopen = client.post(
        _url(work_order.id, "/reopen"), headers=superuser_token_headers, json={}
    )
    assert reopen.status_code == 409

    note = client.post(
        _url(work_order.id, "/notes"),
        headers=superuser_token_headers,
        json={"body": "anything"},
    )
    assert note.status_code == 409


def test_voiding_twice_is_rejected(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    client.delete(_url(work_order.id), headers=superuser_token_headers)
    second = client.delete(_url(work_order.id), headers=superuser_token_headers)
    assert second.status_code == 409
    assert second.json()["message"] == "Work order is already voided"


# --- complete / reopen actions ----------------------------------------


def test_complete_records_actual_hours_and_returns_summary(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    branch = create_random_branch(db)
    work_order = create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title="Replace compressor", branch_id=branch.id, labor_rate="95.00"
        ),
    )
    response = client.post(
        _url(work_order.id, "/complete"),
        headers=superuser_token_headers,
        json={"actual_labor_hours": "3.50", "body": "Verified under load."},
    )
    assert response.status_code == 200
    content = response.json()
    data = content["data"]
    assert data["work_order"]["status"] == "completed"
    assert data["work_order"]["actual_labor_hours"] == "3.50"
    assert data["work_order"]["completed_at"] is not None
    # 3.50 hours at 95.00
    assert data["totals"]["labor_total"] == "332.50"
    assert data["totals"]["total_cost"] == "332.50"


def test_complete_stores_the_closing_note_on_the_timeline(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    client.post(
        _url(work_order.id, "/complete"),
        headers=superuser_token_headers,
        json={"body": "Replaced the compressor."},
    )
    timeline = client.get(
        _url(work_order.id, "/timeline"), headers=superuser_token_headers
    )
    assert timeline.status_code == 200
    events = timeline.json()["data"]
    completed = [e for e in events if e["event_type"] == "completed"]
    assert len(completed) == 1
    assert completed[0]["body"] == "Replaced the compressor."
    assert completed[0]["to_status"] == "completed"


def test_reopen_clears_completed_at_but_keeps_started_at(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"status": "in_progress"},
    )
    client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"status": "completed"},
    )
    original_start = client.get(
        _url(work_order.id), headers=superuser_token_headers
    ).json()["data"]["started_at"]
    assert original_start is not None

    response = client.post(
        _url(work_order.id, "/reopen"),
        headers=superuser_token_headers,
        json={"body": "Failed again under warranty."},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "open"
    assert data["completed_at"] is None
    assert data["started_at"] == original_start


def test_reopening_an_open_work_order_is_rejected(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.post(
        _url(work_order.id, "/reopen"), headers=superuser_token_headers, json={}
    )
    assert response.status_code == 409
    assert "does not need reopening" in response.json()["message"]


def test_completing_a_completed_work_order_is_rejected(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db, status=WorkOrderStatus.COMPLETED)
    response = client.post(
        _url(work_order.id, "/complete"), headers=superuser_token_headers, json={}
    )
    assert response.status_code == 409
    assert "already completed" in response.json()["message"]


# --- assignment --------------------------------------------------------


def test_work_order_can_be_assigned_to_a_real_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from app.models import UserRole
    from tests.utils.work_order_user import create_role_user

    technician, _ = create_role_user(db, role=UserRole.TECHNICIAN)
    work_order = create_random_work_order(db)
    response = client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"assigned_user_id": str(technician.id)},
    )
    assert response.status_code == 200
    assert response.json()["data"]["assigned_user_id"] == str(technician.id)


def test_assigning_to_an_unknown_user_is_rejected(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"assigned_user_id": str(uuid.uuid4())},
    )
    assert response.status_code == 409
    assert response.json()["message"] == "Assignee not found"


def test_assigning_to_an_inactive_user_is_rejected(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from app.models import UserRole
    from tests.utils.work_order_user import create_role_user

    technician, _ = create_role_user(
        db, role=UserRole.TECHNICIAN, is_active=False
    )
    work_order = create_random_work_order(db)
    response = client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"assigned_user_id": str(technician.id)},
    )
    assert response.status_code == 409
    assert "inactive" in response.json()["message"]


# --- notes / timeline --------------------------------------------------


def test_note_is_appended_with_author(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.post(
        _url(work_order.id, "/notes"),
        headers=superuser_token_headers,
        json={"body": "Found a cracked housing on arrival."},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["event_type"] == "note"
    assert data["body"] == "Found a cracked housing on arrival."
    assert data["author_name"] is not None


def test_blank_note_is_rejected(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.post(
        _url(work_order.id, "/notes"),
        headers=superuser_token_headers,
        json={"body": "   "},
    )
    assert response.status_code == 422


def test_timeline_records_the_whole_story_in_order(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    client.patch(
        _url(work_order.id),
        headers=superuser_token_headers,
        json={"status": "in_progress"},
    )
    client.post(
        _url(work_order.id, "/notes"),
        headers=superuser_token_headers,
        json={"body": "Ordering the part."},
    )
    client.post(
        _url(work_order.id, "/complete"),
        headers=superuser_token_headers,
        json={"body": "Part fitted and tested."},
    )

    events = client.get(
        _url(work_order.id, "/timeline"), headers=superuser_token_headers
    ).json()["data"]
    types = [e["event_type"] for e in events]
    assert types == ["created", "status_changed", "note", "completed"]
    # The status change records where it came from and where it went.
    status_change = events[1]
    assert status_change["from_status"] == "open"
    assert status_change["to_status"] == "in_progress"


def test_creation_is_recorded_on_the_timeline(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    events = client.get(
        _url(work_order.id, "/timeline"), headers=superuser_token_headers
    ).json()["data"]
    assert len(events) == 1
    assert events[0]["event_type"] == "created"
    assert events[0]["body"] == "Work order created"


# --- totals ------------------------------------------------------------


def test_totals_sum_parts_and_labor(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    branch = create_random_branch(db)
    work_order = create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title="Billed job",
            branch_id=branch.id,
            actual_labor_hours="2.00",
            labor_rate="50.00",
        ),
    )
    part_a = create_random_part(db, list_price=Decimal("10.00"))
    part_b = create_random_part(db, list_price=Decimal("7.50"))

    client.post(
        _url(work_order.id, "/parts"),
        headers=superuser_token_headers,
        json={"part_id": str(part_a.id), "quantity": 3},
    )
    client.post(
        _url(work_order.id, "/parts"),
        headers=superuser_token_headers,
        json={"part_id": str(part_b.id), "quantity": 2},
    )

    response = client.get(
        _url(work_order.id, "/totals"), headers=superuser_token_headers
    )
    assert response.status_code == 200
    totals = response.json()["data"]
    # 3 x 10.00 + 2 x 7.50
    assert totals["parts_total"] == "45.00"
    assert totals["labor_total"] == "100.00"
    assert totals["total_cost"] == "145.00"


def test_labor_falls_back_to_quoted_hours_when_no_actuals(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    branch = create_random_branch(db)
    work_order = create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title="Quoted only",
            branch_id=branch.id,
            quoted_labor_hours="4.00",
            labor_rate="60.00",
        ),
    )
    totals = client.get(
        _url(work_order.id, "/totals"), headers=superuser_token_headers
    ).json()["data"]
    assert totals["labor_hours"] == "4.00"
    assert totals["labor_total"] == "240.00"


def test_actual_hours_override_quoted_hours(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    branch = create_random_branch(db)
    work_order = create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title="Overran the estimate",
            branch_id=branch.id,
            quoted_labor_hours="2.00",
            actual_labor_hours="5.00",
            labor_rate="60.00",
        ),
    )
    totals = client.get(
        _url(work_order.id, "/totals"), headers=superuser_token_headers
    ).json()["data"]
    assert totals["labor_hours"] == "5.00"
    assert totals["labor_total"] == "300.00"


def test_summary_returns_parts_timeline_and_totals(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    part = create_random_part(db, list_price=Decimal("12.00"))
    client.post(
        _url(work_order.id, "/parts"),
        headers=superuser_token_headers,
        json={"part_id": str(part.id), "quantity": 2},
    )
    client.post(
        _url(work_order.id, "/notes"),
        headers=superuser_token_headers,
        json={"body": "On site."},
    )

    response = client.get(
        _url(work_order.id, "/summary"), headers=superuser_token_headers
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["work_order"]["id"] == str(work_order.id)
    assert len(data["parts"]) == 1
    assert len(data["events"]) == 2
    assert data["totals"]["parts_total"] == "24.00"


# --- list filters ------------------------------------------------------


def test_filter_by_assignee(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from app.models import UserRole
    from tests.utils.work_order_user import create_role_user

    technician, _ = create_role_user(db, role=UserRole.TECHNICIAN)
    mine = create_random_work_order(db)
    update_work_order(
        session=db,
        db_work_order=mine,
        work_order_in=WorkOrderUpdate(assigned_user_id=technician.id),
    )
    create_random_work_order(db)

    response = client.get(
        f"{WO}/work-orders/",
        headers=superuser_token_headers,
        params={"assigned_user_id": str(technician.id)},
    )
    assert response.status_code == 200
    ids = [w["id"] for w in response.json()["data"]]
    assert ids == [str(mine.id)]


def test_filter_by_overdue_excludes_closed_work(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    branch = create_random_branch(db)
    yesterday = date.today() - timedelta(days=3)
    next_week = date.today() + timedelta(days=3)

    overdue = create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title="Overdue job", branch_id=branch.id, due_date=yesterday
        ),
    )
    done = create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title="Overdue but done",
            branch_id=branch.id,
            due_date=yesterday,
            status=WorkOrderStatus.COMPLETED,
        ),
    )
    create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title="Not due yet", branch_id=branch.id, due_date=next_week
        ),
    )

    response = client.get(
        f"{WO}/work-orders/",
        headers=superuser_token_headers,
        params={"overdue": "true"},
    )
    assert response.status_code == 200
    ids = [w["id"] for w in response.json()["data"]]
    assert str(overdue.id) in ids
    assert str(done.id) not in ids


def test_search_matches_title_case_insensitively(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    branch = create_random_branch(db)
    # A token unique to this test, so results cannot be polluted by titles
    # other tests create in the same session.
    unique = f"searchtoken{uuid.uuid4().hex[:8]}"
    create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title=f"Replace {unique} unit", branch_id=branch.id
        ),
    )
    create_work_order(
        session=db,
        work_order_in=WorkOrderCreate(
            title=f"Unrelated job {uuid.uuid4().hex[:8]}", branch_id=branch.id
        ),
    )

    response = client.get(
        f"{WO}/work-orders/",
        headers=superuser_token_headers,
        params={"search": unique.upper()},
    )
    assert response.status_code == 200
    titles = [w["title"] for w in response.json()["data"]]
    assert titles == [f"Replace {unique} unit"]


def test_creating_a_work_order_opens_a_timeline_entry(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    branch = create_random_branch(db)
    response = client.post(
        f"{WO}/work-orders/",
        headers=superuser_token_headers,
        json={"title": "Timeline on create", "branch_id": str(branch.id)},
    )
    assert response.status_code == 200
    created_id = response.json()["data"]["id"]
    events = client.get(
        _url(uuid.UUID(created_id), "/timeline"), headers=superuser_token_headers
    ).json()["data"]
    assert events[0]["event_type"] == "created"
    assert events[0]["body"] == "Work order created"
