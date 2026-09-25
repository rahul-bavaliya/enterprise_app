from typing import Any

from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr

from app.api.deps import get_current_active_superuser
from app.core.utils import generate_test_email, send_email
from app.schemas import ResponseEnvelope

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
    response_model=ResponseEnvelope[None],
)
def test_email(email_to: EmailStr) -> Any:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return ResponseEnvelope(success=True, message="Test email sent")


@router.get("/health-check/", response_model=ResponseEnvelope[None])
def health_check() -> Any:
    return ResponseEnvelope(success=True, message="Healthy")
