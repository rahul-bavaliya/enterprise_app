"""Contract tests: every non-auth endpoint speaks ResponseEnvelope, and
failures never leak a raw FastAPI ``detail`` or a traceback."""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.work_order import create_random_work_order

# Auth routes are exempt: login, users, and the password recovery/reset pair
# that hangs off the login router.
AUTH_PREFIXES = ("/login", "/users", "/password-recovery", "/reset-password")

# One representative path per non-auth router.
REPRESENTATIVE_PATHS = (
    "/items/",
    "/branches/",
    "/work-orders/",
    "/parts/",
    "/utils/health-check/",
)


def test_health_check_is_enveloped(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/utils/health-check/")
    assert response.status_code == 200
    content = response.json()
    assert content["success"] is True
    assert content["data"] is None
    assert content["message"] == "Healthy"


def test_404_is_enveloped(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/items/{uuid.uuid4()}")
    # Unauthenticated, but the error shape must still be an envelope.
    assert response.status_code in (401, 403, 404)
    content = response.json()
    assert set(content) == {"success", "data", "message"}
    assert content["success"] is False
    assert content["data"] is None
    assert isinstance(content["message"], str)
    assert "detail" not in content


def test_validation_error_is_enveloped(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/work-orders/",
        headers=superuser_token_headers,
        json={"description": "no title supplied"},
    )
    assert response.status_code == 422
    content = response.json()
    assert content["success"] is False
    assert content["data"] is None
    assert "title" in content["message"]
    assert "detail" not in content


def test_permission_error_is_enveloped(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/", headers=normal_user_token_headers
    )
    assert response.status_code == 403
    content = response.json()
    assert content == {
        "success": False,
        "data": None,
        "message": "Not enough permissions",
    }


def test_not_found_message_is_enveloped(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/work-orders/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    content = response.json()
    assert content == {
        "success": False,
        "data": None,
        "message": "Work order not found",
    }


def test_item_endpoints_are_enveloped(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = client.post(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        json={"title": "Enveloped", "description": "Yes"},
    )
    assert created.status_code == 200
    content = created.json()
    assert content["success"] is True
    assert content["data"]["title"] == "Enveloped"
    assert content["message"] == "Item created successfully"

    listed = client.get(
        f"{settings.API_V1_STR}/items/", headers=superuser_token_headers
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["count"] >= 1

    item_id = content["data"]["id"]
    deleted = client.delete(
        f"{settings.API_V1_STR}/items/{item_id}", headers=superuser_token_headers
    )
    assert deleted.json() == {
        "success": True,
        "data": None,
        "message": "Item deleted successfully",
    }


def test_every_non_auth_router_declares_an_envelope(
    client: TestClient,
) -> None:
    """No non-auth operation may declare a non-envelope success schema."""
    openapi = client.get(f"{settings.API_V1_STR}/openapi.json").json()
    offenders: list[str] = []
    for path, operations in openapi["paths"].items():
        # OpenAPI paths are absolute, so compare against the route-relative path.
        relative = path[len(settings.API_V1_STR) :]
        if any(relative.startswith(prefix) for prefix in AUTH_PREFIXES):
            continue
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            schema_name = (
                operation.get("responses", {})
                .get("200", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
                .get("$ref", "")
            )
            if schema_name and "ResponseEnvelope" not in schema_name:
                offenders.append(f"{method.upper()} {path} -> {schema_name}")
    assert offenders == []


def test_duplicate_part_conflict_is_enveloped(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.part import create_random_part

    part = create_random_part(db)
    response = client.post(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        json={"part_number": part.part_number},
    )
    assert response.status_code == 409
    content = response.json()
    assert content["success"] is False
    assert "already exists" in content["message"]


def test_voided_work_order_rejects_new_parts(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.part import create_random_part

    work_order = create_random_work_order(db)
    part = create_random_part(db)
    client.delete(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}",
        headers=superuser_token_headers,
    )

    response = client.post(
        f"{settings.API_V1_STR}/work-orders/{work_order.id}/parts",
        headers=superuser_token_headers,
        json={"part_id": str(part.id)},
    )
    assert response.status_code == 409
    assert response.json()["success"] is False
    assert "voided" in response.json()["message"]
