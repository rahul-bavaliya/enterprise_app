from app.models import Item, ResponseEnvelope, User
from app.models.auth import Message, Token
from app.models.item import ItemCreate
from app.models.user import UserCreate


def test_models_package_exports_expected_classes() -> None:
    assert User is not None
    assert Item is not None
    assert UserCreate is not None
    assert ItemCreate is not None
    assert Message is not None
    assert Token is not None
    assert ResponseEnvelope is not None
