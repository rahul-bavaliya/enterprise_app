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


def test_read_work_orders_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Not enough permissions"


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
    work_order = create_random_work_order(db)
    response = client.delete(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Not enough permissions"
