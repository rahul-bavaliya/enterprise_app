import uuid
from datetime import UTC, datetime

from sqlmodel import Session, col, func, select

from app.models import Branch
from app.schemas import BranchCreate, BranchUpdate


def create_branch(*, session: Session, branch_in: BranchCreate) -> Branch:
    db_branch = Branch.model_validate(branch_in)
    session.add(db_branch)
    session.commit()
    session.refresh(db_branch)
    return db_branch


def get_branch_by_id(*, session: Session, branch_id: uuid.UUID) -> Branch | None:
    return session.get(Branch, branch_id)


def get_branches(
    *, session: Session, skip: int = 0, limit: int = 100
) -> tuple[list[Branch], int]:
    count_statement = select(func.count()).select_from(Branch)
    count = session.exec(count_statement).one()
    statement = (
        select(Branch).order_by(col(Branch.created_at).desc()).offset(skip).limit(limit)
    )
    branches = session.exec(statement).all()
    return branches, count


def update_branch(
    *, session: Session, db_branch: Branch, branch_in: BranchUpdate
) -> Branch:
    update_data = branch_in.model_dump(exclude_unset=True)
    db_branch.updated_at = datetime.now(UTC)
    db_branch.sqlmodel_update(update_data)
    session.add(db_branch)
    session.commit()
    session.refresh(db_branch)
    return db_branch


def delete_branch(*, session: Session, db_branch: Branch) -> None:
    session.delete(db_branch)
    session.commit()
