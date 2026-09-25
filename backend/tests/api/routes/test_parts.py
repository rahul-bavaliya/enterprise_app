import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.part import create_random_part
from tests.utils.utils import random_lower_string
from tests.utils.work_order import create_random_work_order


def test_create_part(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    # Part numbers are unique, so use a fresh one on every run.
    data = {
        "part_number": f"BRG-6205-{random_lower_string()[:8]}",
        "description": "Deep groove ball bearing",
        "manufacturer": "SKF",
        "list_price": "24.95",
    }
    response = client.post(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["success"] is True
    assert content["data"]["part_number"] == data["part_number"]
    assert content["data"]["list_price"] == "24.95"
    assert content["data"]["unit_of_measure"] == "EA"
    assert content["data"]["is_active"] is True
    assert "id" in content["data"]


def test_create_duplicate_part_conflicts(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    response = client.post(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        json={"part_number": part.part_number},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["message"]


def test_read_part(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    response = client.get(
        f"{settings.API_V1_STR}/parts/{part.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["part_number"] == part.part_number


def test_read_part_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/parts/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Part not found"


def test_read_parts_filters(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    response = client.get(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        params={"part_number": part.part_number},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert [p["id"] for p in data] == [str(part.id)]


def test_read_parts_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/parts/",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403


def test_update_part(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    response = client.patch(
        f"{settings.API_V1_STR}/parts/{part.id}",
        headers=superuser_token_headers,
        json={"list_price": "27.50", "description": "Updated"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["data"]["list_price"] == "27.50"
    assert content["data"]["description"] == "Updated"


def test_deactivate_part_retains_record(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Part deactivated successfully"
    assert content["data"]["is_active"] is False

    follow_up = client.get(
        f"{settings.API_V1_STR}/parts/{part.id}",
        headers=superuser_token_headers,
    )
    assert follow_up.status_code == 200
    assert follow_up.json()["data"]["is_active"] is False


def test_add_part_to_work_order(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    part = create_random_part(db, list_price=Decimal("12.50"))

    response = client.post(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts",
        headers=superuser_token_headers,
        json={"part_id": str(part.id), "quantity": 2},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["data"]["part_id"] == str(part.id)
    assert content["data"]["part_number"] == part.part_number
    assert content["data"]["quantity"] == 2
    assert content["data"]["unit_price"] == "12.50"
    assert content["data"]["line_total"] == "25.00"


def test_add_unknown_part_to_work_order(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.post(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts",
        headers=superuser_token_headers,
        json={"part_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Part not found"


def test_add_inactive_part_conflicts(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    part = create_random_part(db)
    client.delete(
        f"{settings.API_V1_STR}/parts/{part.id}",
        headers=superuser_token_headers,
    )

    response = client.post(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts",
        headers=superuser_token_headers,
        json={"part_id": str(part.id)},
    )
    assert response.status_code == 409
    assert "inactive" in response.json()["message"]


def test_read_work_order_parts(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    parts = [create_random_part(db) for _ in range(2)]
    for part in parts:
        response = client.post(
            f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts",
            headers=superuser_token_headers,
            json={"part_id": str(part.id), "quantity": 1},
        )
        assert response.status_code == 200

    response = client.get(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["data"]) == 2
    assert {p["part_id"] for p in content["data"]} == {str(p.id) for p in parts}


def test_update_and_remove_work_order_part(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    part = create_random_part(db)
    created = client.post(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts",
        headers=superuser_token_headers,
        json={"part_id": str(part.id), "quantity": 1},
    )
    line_item_id = created.json()["data"]["id"]

    updated = client.patch(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts/{line_item_id}",
        headers=superuser_token_headers,
        json={"quantity": 4, "unit_price": "5.00"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["quantity"] == 4
    assert updated.json()["data"]["line_total"] == "20.00"

    removed = client.delete(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts/{line_item_id}",
        headers=superuser_token_headers,
    )
    assert removed.status_code == 200
    assert removed.json()["message"] == "Part removed from work order successfully"

    listed = client.get(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts",
        headers=superuser_token_headers,
    )
    assert listed.json()["data"] == []


def test_work_order_parts_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    work_order = create_random_work_order(db)
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
