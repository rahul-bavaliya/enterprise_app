from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from app.models import (
    PartCreate,
    PartUnitOfMeasure,
    PartUpdate,
    WorkOrder,
    WorkOrderCreate,
    WorkOrderPartCreate,
    WorkOrderPartUpdate,
    WorkOrderStatus,
)
from app.services import (
    add_part_to_work_order,
    create_part,
    create_work_order,
    deactivate_part,
    get_part_by_number,
    get_work_order_parts,
    remove_work_order_part,
    update_part,
    update_work_order_part,
)
from tests.utils.utils import random_lower_string


def _new_part(**overrides: object) -> PartCreate:
    defaults: dict[str, object] = {
        "part_number": f"PN-{random_lower_string()[:8]}",
        "description": "Test part",
        "manufacturer": "Acme",
        "list_price": Decimal("24.95"),
    }
    defaults.update(overrides)
    return PartCreate(**defaults)  # type: ignore[arg-type]


def _new_work_order() -> WorkOrderCreate:
    return WorkOrderCreate(title=f"WO-{random_lower_string()[:8]}")


def test_create_part_snapshots_pricing(db: Session) -> None:
    part = create_part(
        session=db,
        part_in=_new_part(
            list_price=Decimal("19.99"), unit_of_measure=PartUnitOfMeasure.BOX
        ),
    )

    assert part.part_number
    assert part.list_price == Decimal("19.99")
    assert part.unit_of_measure == PartUnitOfMeasure.BOX
    assert part.is_active is True
    assert part.created_at is not None
    assert part.updated_at is None

    assert get_part_by_number(session=db, part_number=part.part_number) is not None


def test_part_price_rejects_sub_cent_precision() -> None:
    # Money is stored as Numeric(12, 2); anything finer is rejected outright
    # rather than silently rounded.
    with pytest.raises(ValidationError):
        _new_part(list_price=Decimal("19.999"))


def test_duplicate_part_number_is_rejected(db: Session) -> None:
    part_in = _new_part()
    create_part(session=db, part_in=part_in)

    with pytest.raises(ValueError, match="already exists"):
        create_part(session=db, part_in=part_in)


def test_update_and_deactivate_part(db: Session) -> None:
    part = create_part(session=db, part_in=_new_part())

    updated = update_part(
        session=db, db_part=part, part_in=PartUpdate(list_price=Decimal("30.00"))
    )
    assert updated.list_price == Decimal("30.00")
    assert updated.updated_at is not None

    # Deactivating keeps the record so work order history still resolves.
    deactivated = deactivate_part(session=db, db_part=part)
    assert deactivated.is_active is False


def test_add_part_to_work_order_uses_list_price(db: Session) -> None:
    part = create_part(session=db, part_in=_new_part(list_price=Decimal("10.00")))
    work_order = create_work_order(session=db, work_order_in=_new_work_order())

    line_item = add_part_to_work_order(
        session=db,
        db_work_order=work_order,
        db_part=part,
        work_order_part_in=WorkOrderPartCreate(part_id=part.id, quantity=3),
    )

    assert line_item.quantity == 3
    assert line_item.unit_price == Decimal("10.00")
    assert line_item.work_order_id == work_order.id


def test_line_item_price_is_snapshotted_at_time_of_add(db: Session) -> None:
    part = create_part(session=db, part_in=_new_part(list_price=Decimal("10.00")))
    work_order = create_work_order(session=db, work_order_in=_new_work_order())

    add_part_to_work_order(
        session=db,
        db_work_order=work_order,
        db_part=part,
        work_order_part_in=WorkOrderPartCreate(part_id=part.id, quantity=1),
    )

    # A later catalog price change must not rewrite the work order line.
    update_part(
        session=db, db_part=part, part_in=PartUpdate(list_price=Decimal("99.00"))
    )
    line_items = get_work_order_parts(session=db, work_order_id=work_order.id)

    assert len(line_items) == 1
    assert line_items[0].unit_price == Decimal("10.00")


def test_adding_same_part_twice_increases_quantity(db: Session) -> None:
    part = create_part(session=db, part_in=_new_part())
    work_order = create_work_order(session=db, work_order_in=_new_work_order())

    add_part_to_work_order(
        session=db,
        db_work_order=work_order,
        db_part=part,
        work_order_part_in=WorkOrderPartCreate(part_id=part.id, quantity=2),
    )
    add_part_to_work_order(
        session=db,
        db_work_order=work_order,
        db_part=part,
        work_order_part_in=WorkOrderPartCreate(part_id=part.id, quantity=3),
    )

    line_items = get_work_order_parts(session=db, work_order_id=work_order.id)
    assert len(line_items) == 1
    assert line_items[0].quantity == 5


def test_cannot_add_inactive_or_voided(db: Session) -> None:
    part = create_part(session=db, part_in=_new_part())
    deactivate_part(session=db, db_part=part)
    work_order = create_work_order(session=db, work_order_in=_new_work_order())

    with pytest.raises(ValueError, match="inactive"):
        add_part_to_work_order(
            session=db,
            db_work_order=work_order,
            db_part=part,
            work_order_part_in=WorkOrderPartCreate(part_id=part.id),
        )

    active_part = create_part(session=db, part_in=_new_part())
    voided_work_order = create_work_order(session=db, work_order_in=_new_work_order())
    voided_work_order.status = WorkOrderStatus.VOIDED
    db.add(voided_work_order)
    db.commit()
    db.refresh(voided_work_order)

    with pytest.raises(ValueError, match="voided"):
        add_part_to_work_order(
            session=db,
            db_work_order=voided_work_order,
            db_part=active_part,
            work_order_part_in=WorkOrderPartCreate(part_id=active_part.id),
        )


def test_update_and_remove_work_order_part(db: Session) -> None:
    part = create_part(session=db, part_in=_new_part())
    work_order = create_work_order(session=db, work_order_in=_new_work_order())
    line_item = add_part_to_work_order(
        session=db,
        db_work_order=work_order,
        db_part=part,
        work_order_part_in=WorkOrderPartCreate(part_id=part.id, quantity=1),
    )

    updated = update_work_order_part(
        session=db,
        db_work_order_part=line_item,
        work_order_part_in=WorkOrderPartUpdate(quantity=7, unit_price=Decimal("5.25")),
    )
    assert updated.quantity == 7
    assert updated.unit_price == Decimal("5.25")
    assert updated.updated_at is not None

    # Removing the line leaves the part itself intact.
    remove_work_order_part(session=db, db_work_order_part=updated)
    assert get_work_order_parts(session=db, work_order_id=work_order.id) == []


def test_work_order_can_reference_multiple_parts(db: Session) -> None:
    work_order = create_work_order(session=db, work_order_in=_new_work_order())
    parts = [create_part(session=db, part_in=_new_part()) for _ in range(3)]

    for index, part in enumerate(parts, start=1):
        add_part_to_work_order(
            session=db,
            db_work_order=work_order,
            db_part=part,
            work_order_part_in=WorkOrderPartCreate(part_id=part.id, quantity=index),
        )

    line_items = get_work_order_parts(session=db, work_order_id=work_order.id)
    assert len(line_items) == 3
    assert {item.part_id for item in line_items} == {p.id for p in parts}
    assert isinstance(work_order, WorkOrder)
