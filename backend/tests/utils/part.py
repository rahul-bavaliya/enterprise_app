from decimal import Decimal

from sqlmodel import Session

from app.models import Part, PartCreate, PartUnitOfMeasure
from app.services import create_part
from tests.utils.utils import random_lower_string


def create_random_part(
    db: Session,
    *,
    list_price: Decimal | None = None,
    unit_of_measure: PartUnitOfMeasure = PartUnitOfMeasure.EACH,
) -> Part:
    part_number = f"PN-{random_lower_string()[:12]}"
    part_in = PartCreate(
        part_number=part_number,
        description=random_lower_string(),
        manufacturer=random_lower_string(),
        unit_of_measure=unit_of_measure,
        list_price=list_price if list_price is not None else Decimal("10.00"),
    )
    return create_part(session=db, part_in=part_in)
