# app/api/v1/endpoints/branch.py
from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import NotFoundException
from app.core.response import ResponseEnvelope
from app.models.branch import Branch
from app.schemas.branch import BranchCreate, BranchResponse, BranchUpdate
from app.services.branch import BranchService

router = APIRouter(prefix="/branches", tags=["branches"])


@router.post(
    "/",
    response_model=ResponseEnvelope[BranchResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_branch(
    *,
    branch_in: BranchCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[BranchResponse]:
    """
    Create a new branch.
    """
    service = BranchService(db)
    branch: Branch | None = await service.create(obj_in=branch_in)
    return ResponseEnvelope[BranchResponse].ok(
        data=BranchResponse.model_validate(branch),
        message="Branch created successfully",
    )


@router.get("/", response_model=ResponseEnvelope[list[BranchResponse]])
async def read_branches(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> ResponseEnvelope[list[BranchResponse]]:
    """
    Retrieve branches.
    """
    service = BranchService(db)
    branches: Sequence[Branch] = await service.get_multi(skip=skip, limit=limit)
    branch_responses = [BranchResponse.model_validate(obj=b) for b in branches]
    return ResponseEnvelope[list[BranchResponse]].ok(
        data=branch_responses, message="Branches retrieved successfully"
    )


@router.get("/{branch_id}", response_model=ResponseEnvelope[BranchResponse])
async def read_branch(
    *,
    branch_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[BranchResponse]:
    """
    Get a specific branch by id.
    """
    service = BranchService(db)
    branch: Branch | None = await service.get(id=branch_id)
    if not branch:
        raise NotFoundException(message="Branch not found")
    return ResponseEnvelope[BranchResponse].ok(
        data=BranchResponse.model_validate(branch),
        message="Branch retrieved successfully",
    )


@router.patch("/{branch_id}", response_model=ResponseEnvelope[BranchResponse])
async def update_branch(
    *,
    branch_id: UUID,
    branch_in: BranchUpdate,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[BranchResponse]:
    """
    Update a branch.
    """
    service = BranchService(db)
    branch: Branch | None = await service.get(id=branch_id)
    if not branch:
        raise NotFoundException(message="Branch not found")
    updated_branch: Branch = await service.update(db_obj=branch, obj_in=branch_in)
    return ResponseEnvelope[BranchResponse].ok(
        data=BranchResponse.model_validate(updated_branch),
        message="Branch updated successfully",
    )


@router.delete("/{branch_id}", response_model=ResponseEnvelope[BranchResponse])
async def delete_branch(
    *,
    branch_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[BranchResponse]:
    """
    Delete a branch.
    """
    service = BranchService(db)
    branch: Branch | None = await service.get(id=branch_id)
    if not branch:
        raise NotFoundException(message="Branch not found")
    deleted_branch: Branch | None = await service.remove(id=branch_id)
    return ResponseEnvelope[BranchResponse].ok(
        data=BranchResponse.model_validate(deleted_branch),
        message="Branch deleted successfully",
    )
