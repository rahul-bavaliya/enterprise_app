import uuid

from fastapi.testclient import TestClient

from app.core.config import settings
from tests.utils.utils import random_lower_string


def _customer_payload() -> dict[str, object]:
    suffix = uuid.uuid4().hex[:8]
    return {
        "name": f"Customer {suffix}",
        "contact_person": "Jane Doe",
        "email": f"jane.{suffix}@example.test",
        "phone": "+1 555 0100",
        "tax_id": f"TAX-{suffix}",
        "billing_address": "1 Market Street",
        "service_address": "22 Industrial Way",
        "notes": "Prefers morning visits",
    }


def test_customer_fleet_and_work_order_flow(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    customer_response = client.post(
        f"{settings.API_V1_STR}/customers/",
        headers=superuser_token_headers,
        json=_customer_payload(),
    )
    assert customer_response.status_code == 201
    customer = customer_response.json()["data"]

    empty_fleet = client.get(
        f"{settings.API_V1_STR}/customers/{customer['id']}/fleet",
        headers=superuser_token_headers,
    )
    assert empty_fleet.status_code == 200
    assert empty_fleet.json()["data"] == []

    fleet_response = client.post(
        f"{settings.API_V1_STR}/customers/{customer['id']}/fleet",
        headers=superuser_token_headers,
        json={
            "asset_tag": f"ASSET-{uuid.uuid4().hex[:10]}",
            "description": "Centrifugal pump",
            "make": "Grundfos",
            "model": "NB 65-200",
            "serial_number": f"SERIAL-{uuid.uuid4().hex[:8]}",
            "year_manufactured": 2022,
            "meter_reading": "1250.50",
            "location": "Pump house A",
        },
    )
    assert fleet_response.status_code == 201
    fleet = fleet_response.json()["data"]
    assert fleet["customer_id"] == customer["id"]

    fleet_list = client.get(
        f"{settings.API_V1_STR}/customers/{customer['id']}/fleet",
        headers=superuser_token_headers,
    )
    assert fleet_list.status_code == 200
    assert [item["id"] for item in fleet_list.json()["data"]] == [fleet["id"]]

    work_order_response = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json={
            "title": "Repair customer pump",
            "customer_id": customer["id"],
            "fleet_id": fleet["id"],
        },
    )
    assert work_order_response.status_code == 200
    work_order = work_order_response.json()["data"]
    assert work_order["customer_id"] == customer["id"]
    assert work_order["fleet_id"] == fleet["id"]
    assert work_order["work_order_number"] is not None
    assert work_order["segment"] == 1


def test_work_order_rejects_fleet_owned_by_another_customer(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    customer_ids: list[str] = []
    fleet_ids: list[str] = []
    for _ in range(2):
        customer = client.post(
            f"{settings.API_V1_STR}/customers/",
            headers=superuser_token_headers,
            json=_customer_payload(),
        ).json()["data"]
        fleet = client.post(
            f"{settings.API_V1_STR}/customers/{customer['id']}/fleet",
            headers=superuser_token_headers,
            json={"asset_tag": f"ASSET-{uuid.uuid4().hex[:10]}"},
        ).json()["data"]
        customer_ids.append(customer["id"])
        fleet_ids.append(fleet["id"])

    response = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json={
            "title": "Invalid ownership",
            "customer_id": customer_ids[0],
            "fleet_id": fleet_ids[1],
        },
    )
    assert response.status_code == 409
    assert response.json()["message"] == (
        "Fleet does not belong to the selected customer"
    )


def test_customer_endpoints_require_superuser(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/customers/",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
    assert response.json()["success"] is False


def test_customer_and_fleet_records_are_retained_on_deactivation(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    customer = client.post(
        f"{settings.API_V1_STR}/customers/",
        headers=superuser_token_headers,
        json=_customer_payload(),
    ).json()["data"]
    fleet = client.post(
        f"{settings.API_V1_STR}/customers/{customer['id']}/fleet",
        headers=superuser_token_headers,
        json={"asset_tag": f"ASSET-{uuid.uuid4().hex[:10]}"},
    ).json()["data"]

    customer_response = client.delete(
        f"{settings.API_V1_STR}/customers/{customer['id']}",
        headers=superuser_token_headers,
    )
    fleet_response = client.delete(
        f"{settings.API_V1_STR}/fleet/{fleet['id']}",
        headers=superuser_token_headers,
    )
    assert customer_response.status_code == 200
    assert customer_response.json()["data"]["is_active"] is False
    assert fleet_response.status_code == 200
    assert fleet_response.json()["data"]["is_active"] is False
    assert client.get(
        f"{settings.API_V1_STR}/customers/{customer['id']}",
        headers=superuser_token_headers,
    ).status_code == 200
    assert client.get(
        f"{settings.API_V1_STR}/fleet/{fleet['id']}",
        headers=superuser_token_headers,
    ).status_code == 200


def test_customer_search_filters_registered_customers(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    payload = _customer_payload()
    payload["name"] = f"Searchable {random_lower_string()}"
    created = client.post(
        f"{settings.API_V1_STR}/customers/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert created.status_code == 201

    response = client.get(
        f"{settings.API_V1_STR}/customers/",
        headers=superuser_token_headers,
        params={"search": payload["name"]},
    )
    assert response.status_code == 200
    assert any(
        item["id"] == created.json()["data"]["id"] for item in response.json()["data"]
    )
