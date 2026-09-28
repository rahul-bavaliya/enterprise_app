import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlmodel import Session, col, func, select

from app.models import Customer, Fleet
from app.schemas import (
    CustomerCreate as CustomerCreateSchema,
)
from app.schemas import (
    CustomerUpdate as CustomerUpdateSchema,
)
from app.schemas import (
    FleetCreate as FleetCreateSchema,
)
from app.schemas import (
    FleetUpdate as FleetUpdateSchema,
)


def create_customer(*, session: Session, customer_in: CustomerCreateSchema) -> Customer:
    db_customer = Customer.model_validate(customer_in)
    session.add(db_customer)
    session.commit()
    session.refresh(db_customer)
    return db_customer


def get_customer_by_id(*, session: Session, customer_id: uuid.UUID) -> Customer | None:
    return session.get(Customer, customer_id)


def get_customers(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    is_active: bool | None = None,
) -> tuple[Sequence[Customer], int]:
    count_statement = select(func.count()).select_from(Customer)
    statement = select(Customer)
    if search is not None:
        pattern = f"%{search}%"
        count_statement = count_statement.where(
            col(Customer.name).ilike(pattern) | col(Customer.contact_person).ilike(pattern)
        )
        statement = statement.where(
            col(Customer.name).ilike(pattern) | col(Customer.contact_person).ilike(pattern)
        )
    if is_active is not None:
        count_statement = count_statement.where(Customer.is_active == is_active)
        statement = statement.where(Customer.is_active == is_active)
    count = session.exec(count_statement).one()
    statement = statement.order_by(col(Customer.name).asc()).offset(skip).limit(limit)
    return session.exec(statement).all(), count


def update_customer(
    *, session: Session, db_customer: Customer, customer_in: CustomerUpdateSchema
) -> Customer:
    update_data = customer_in.model_dump(exclude_unset=True)
    db_customer.updated_at = datetime.now(UTC)
    db_customer.sqlmodel_update(update_data)
    session.add(db_customer)
    session.commit()
    session.refresh(db_customer)
    return db_customer


def deactivate_customer(*, session: Session, db_customer: Customer) -> Customer:
    db_customer.is_active = False
    db_customer.updated_at = datetime.now(UTC)
    session.add(db_customer)
    session.commit()
    session.refresh(db_customer)
    return db_customer


def create_fleet(*, session: Session, fleet_in: FleetCreateSchema) -> Fleet:
    db_fleet = Fleet.model_validate(fleet_in)
    session.add(db_fleet)
    session.commit()
    session.refresh(db_fleet)
    return db_fleet


def get_fleet_by_id(*, session: Session, fleet_id: uuid.UUID) -> Fleet | None:
    return session.get(Fleet, fleet_id)


def get_fleets(
    *,
    session: Session,
    customer_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
) -> tuple[Sequence[Fleet], int]:
    count_statement = select(func.count()).select_from(Fleet)
    statement = select(Fleet)
    if customer_id is not None:
        count_statement = count_statement.where(Fleet.customer_id == customer_id)
        statement = statement.where(Fleet.customer_id == customer_id)
    if is_active is not None:
        count_statement = count_statement.where(Fleet.is_active == is_active)
        statement = statement.where(Fleet.is_active == is_active)
    count = session.exec(count_statement).one()
    statement = statement.order_by(col(Fleet.asset_tag).asc()).offset(skip).limit(limit)
    return session.exec(statement).all(), count


def update_fleet(
    *, session: Session, db_fleet: Fleet, fleet_in: FleetUpdateSchema
) -> Fleet:
    update_data = fleet_in.model_dump(exclude_unset=True)
    db_fleet.updated_at = datetime.now(UTC)
    db_fleet.sqlmodel_update(update_data)
    session.add(db_fleet)
    session.commit()
    session.refresh(db_fleet)
    return db_fleet


def deactivate_fleet(*, session: Session, db_fleet: Fleet) -> Fleet:
    db_fleet.is_active = False
    db_fleet.updated_at = datetime.now(UTC)
    session.add(db_fleet)
    session.commit()
    session.refresh(db_fleet)
    return db_fleet
