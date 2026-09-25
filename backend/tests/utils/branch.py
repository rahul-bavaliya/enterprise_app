from sqlmodel import Session

from app.models import Branch, BranchCreate
from app.services import create_branch
from tests.utils.utils import random_lower_string


def create_random_branch(db: Session) -> Branch:
    name = random_lower_string()
    location = random_lower_string()
    branch_in = BranchCreate(name=name, location=location)
    return create_branch(session=db, branch_in=branch_in)
