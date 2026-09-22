import uuid
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.schemas import BranchCreate, BranchPublic, BranchUpdate, ResponseEnvelope
from app.services.branch import (
    create_branch,
    delete_branch,
    get_branch_by_id,
    get_branches,
    update_branch,
)

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get(
    "/",
    response_model=ResponseEnvelope[list[BranchPublic]],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [
                            {
                                "id": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d",
                                "name": "Main Branch",
                                "location": "New York, NY",
                                "is_active": True,
                            }
                        ],
                        "message": "Retrieved 1 branch(es)",
                    }
                }
            },
        }
    },
)
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


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[BranchPublic],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d",
                            "name": "Main Branch",
                            "location": "New York, NY",
                            "is_active": True,
                        },
                        "message": None,
                    }
                }
            },
        }
    },
)
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


@router.post(
    "/",
    response_model=ResponseEnvelope[BranchPublic],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d",
                            "name": "Main Branch",
                            "location": "New York, NY",
                            "is_active": True,
                        },
                        "message": "Branch created successfully",
                    }
                }
            },
        }
    },
)
def create_branch_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    branch_in: BranchCreate = Body(
        ...,
        examples={
            "default": {
                "summary": "Create branch",
                "value": {
                    "name": "Main Branch",
                    "location": "New York, NY",
                    "is_active": True,
                },
            }
        },
    ),
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    branch = create_branch(session=session, branch_in=branch_in)
    return ResponseEnvelope(success=True, data=BranchPublic.model_validate(branch))


@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[BranchPublic],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d",
                            "name": "Downtown Branch",
                            "location": "Los Angeles, CA",
                            "is_active": False,
                        },
                        "message": "Branch updated successfully",
                    }
                }
            },
        }
    },
)
def update_branch_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    branch_in: BranchUpdate = Body(
        ...,
        examples={
            "default": {
                "summary": "Update branch",
                "value": {
                    "name": "Downtown Branch",
                    "location": "Los Angeles, CA",
                    "is_active": False,
                },
            }
        },
    ),
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
