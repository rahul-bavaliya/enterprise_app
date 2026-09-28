import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.work_order import create_random_work_order


def test_create_work_order(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"title": "Test work order", "priority": "high"}
    response = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["success"] is True
    assert content["data"]["title"] == data["title"]
    assert content["data"]["priority"] == data["priority"]
    assert content["data"]["status"] == "open"
    assert "id" in content["data"]


def test_create_work_order_with_branch(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.branch import create_random_branch

    branch = create_random_branch(db)
    data = {"title": "Branch work order", "branch_id": str(branch.id)}
    response = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["data"]["branch_id"] == str(branch.id)


def test_create_work_order_invalid_branch(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"title": "Orphan work order", "branch_id": str(uuid.uuid4())}
    response = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Branch not found"


def test_read_work_order(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["success"] is True
    assert content["data"]["title"] == work_order.title
    assert content["data"]["id"] == str(work_order.id)


def test_read_work_order_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Work order not found"


def test_read_work_orders(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    create_random_work_order(db)
    create_random_work_order(db)
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["success"] is True
    assert len(content["data"]) >= 2
    assert "message" in content


def test_read_work_orders_filter_status(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        params={"status": "open"},
    )
    assert response.status_code == 200
    content = response.json()
    assert any(wo["id"] == str(work_order.id) for wo in content["data"])


def test_read_work_orders_invalid_status(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        params={"status": "bogus"},
    )
    assert response.status_code == 422


def test_read_work_orders_hidden_from_users_without_a_branch(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    # A user with no branch assignment sees nothing rather than everything;
    # the missing branch is never treated as a wildcard.
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["success"] is True
    assert content["data"] == []


def test_update_work_order(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    data = {"title": "Updated work order", "status": "in_progress"}
    response = client.patch(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["success"] is True
    assert content["data"]["title"] == data["title"]
    assert content["data"]["status"] == data["status"]
    assert content["data"]["updated_at"] is not None


def test_update_work_order_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"{settings.API_V1_STR}/work-orders/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json={"title": "Updated work order"},
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Work order not found"


def test_void_work_order(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.delete(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["success"] is True
    assert content["message"] == "Work order voided successfully"
    assert content["data"]["status"] == "voided"

    # The record must still exist in the database after being voided.
    follow_up = client.get(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}",
        headers=superuser_token_headers,
    )
    assert follow_up.status_code == 200
    assert follow_up.json()["data"]["status"] == "voided"


def test_void_work_order_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.delete(
        f"{settings.API_V1_STR}/work-orders/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Work order not found"


def test_void_work_order_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    # Voiding is a management action, so a branch-less user is refused before
    # the work order is even loaded.
    work_order = create_random_work_order(db)
    response = client.delete(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
    assert response.json()["message"] == "You do not have access to this work order"


def test_matching_customer_machine_and_branch_creates_next_segment(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.branch import create_random_branch

    branch = create_random_branch(db)
    suffix = uuid.uuid4().hex[:8]
    customer = client.post(
        f"{settings.API_V1_STR}/customers/",
        headers=superuser_token_headers,
        json={"name": f"Segment customer {suffix}"},
    ).json()["data"]
    fleet = client.post(
        f"{settings.API_V1_STR}/customers/{customer['id']}/fleet",
        headers=superuser_token_headers,
        json={"asset_tag": f"SEG-{suffix}"},
    ).json()["data"]
    payload = {
        "title": "Recurring machine repair",
        "branch_id": str(branch.id),
        "customer_id": customer["id"],
        "fleet_id": fleet["id"],
    }

    first = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json=payload,
    )
    second = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json={
            **payload,
            "title": "Follow-up repair",
            "segment_reason": "Customer requested a follow-up visit.",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()["data"]
    second_data = second.json()["data"]
    assert first_data["segment"] == 1
    assert second_data["segment"] == 2
    assert second_data["work_order_number"] == first_data["work_order_number"]
    assert second_data["parent_work_order_id"] == first_data["id"]


def test_active_work_order_requires_segment_reason(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.branch import create_random_branch

    branch = create_random_branch(db)
    suffix = uuid.uuid4().hex[:8]
    customer = client.post(
        f"{settings.API_V1_STR}/customers/",
        headers=superuser_token_headers,
        json={"name": f"Reason customer {suffix}"},
    ).json()["data"]
    fleet = client.post(
        f"{settings.API_V1_STR}/customers/{customer['id']}/fleet",
        headers=superuser_token_headers,
        json={"asset_tag": f"REA-{suffix}"},
    ).json()["data"]
    payload = {
        "title": "First visit",
        "branch_id": str(branch.id),
        "customer_id": customer["id"],
        "fleet_id": fleet["id"],
    }
    first = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json=payload,
    )
    second = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json={**payload, "title": "Second visit"},
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["message"] == (
        "A reason is required when adding a segment to an active work order"
    )


def test_different_branch_starts_a_new_work_order_group(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.branch import create_random_branch

    first_branch = create_random_branch(db)
    second_branch = create_random_branch(db)
    suffix = uuid.uuid4().hex[:8]
    customer = client.post(
        f"{settings.API_V1_STR}/customers/",
        headers=superuser_token_headers,
        json={"name": f"Branch customer {suffix}"},
    ).json()["data"]
    fleet = client.post(
        f"{settings.API_V1_STR}/customers/{customer['id']}/fleet",
        headers=superuser_token_headers,
        json={"asset_tag": f"BRA-{suffix}"},
    ).json()["data"]
    base = {"customer_id": customer["id"], "fleet_id": fleet["id"]}

    first = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json={**base, "title": "Branch A", "branch_id": str(first_branch.id)},
    ).json()["data"]
    second = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json={**base, "title": "Branch B", "branch_id": str(second_branch.id)},
    ).json()["data"]

    assert first["segment"] == 1
    assert second["segment"] == 1
    assert first["work_order_number"] != second["work_order_number"]
    assert second["parent_work_order_id"] is None


def test_manual_segment_endpoint_is_not_exposed(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.post(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/segments",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404


def test_work_order_accepts_quoted_labor_hours(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json={"title": "Travel", "quoted_labor_hours": "4.00"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["quoted_labor_hours"] == "4.00"
