from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import (
    Branch,
    Customer,
    Fleet,
    Item,
    Part,
    User,
    WorkOrder,
    WorkOrderEvent,
    WorkOrderPart,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session]:
    with Session(engine) as session:
        init_db(session)
        yield session
        # Work-order children first: they cascade anyway, but deleting them
        # explicitly keeps the intent obvious and the teardown order explicit.
        for table in (
            WorkOrderEvent,
            WorkOrderPart,
            WorkOrder,
            Part,
            Fleet,
            Customer,
            Item,
        ):
            session.execute(delete(table))
        session.execute(delete(Branch))
        # The dev superuser is shared with the running app, so it must survive.
        session.execute(delete(User).where(User.email != settings.FIRST_SUPERUSER))
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
