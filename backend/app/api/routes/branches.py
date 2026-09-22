import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    BranchCreate,
    BranchPublic,
    BranchUpdate,
    ResponseEnvelope,
)
from app.services.branch import (
    create_branch,
    delete_branch,
    get_branch_by_id,
    get_branches,
    update_branch,
)

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("/", response_model=ResponseEnvelope[list[BranchPublic]])
def read_branches(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    branches, count = get_branches(session=session, skip=skip, limit=limit)
    branches_public = [BranchPublic.model_validate(branch) for branch in branches]
    return ResponseEnvelope(
        success=True,
        data=branches_public,
        message=f"Retrieved {count} branch(es)",
    )


@router.get("/{id}", response_model=ResponseEnvelope[BranchPublic])
def read_branch(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    branch = get_branch_by_id(session=session, branch_id=id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return ResponseEnvelope(success=True, data=BranchPublic.model_validate(branch))


@router.post("/", response_model=ResponseEnvelope[BranchPublic])
def create_branch_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    branch_in: BranchCreate,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    branch = create_branch(session=session, branch_in=branch_in)
    return ResponseEnvelope(success=True, data=BranchPublic.model_validate(branch))


@router.patch("/{id}", response_model=ResponseEnvelope[BranchPublic])
def update_branch_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    branch_in: BranchUpdate,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    branch = get_branch_by_id(session=session, branch_id=id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    updated = update_branch(session=session, db_branch=branch, branch_in=branch_in)
    return ResponseEnvelope(success=True, data=BranchPublic.model_validate(updated))


@router.delete("/{id}", response_model=ResponseEnvelope[None])
def delete_branch_route(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    branch = get_branch_by_id(session=session, branch_id=id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    delete_branch(session=session, db_branch=branch)
    return ResponseEnvelope(success=True, message="Branch deleted successfully")
