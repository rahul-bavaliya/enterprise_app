# app/api/v1/services/branch.py
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine.result import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch
from app.schemas.branch import BranchCreate, BranchUpdate


class BranchService:
    def __init__(self, db: AsyncSession):
        self.db: AsyncSession = db

    async def get(self, id: UUID) -> Branch | None:
        return await self.db.get(entity=Branch, ident=id)

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> Sequence[Branch]:
        result: Result[tuple[Branch]] = await self.db.execute(
            statement=select(Branch).offset(offset=skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, *, obj_in: BranchCreate) -> Branch | None:
        data = obj_in.model_dump()

        db_obj = Branch(**data)
        self.db.add(db_obj)

        try:
            await self.db.commit()
            await self.db.refresh(db_obj)
            return db_obj
        except IntegrityError:
            # Rollback the failed transaction so the session remains usable for next rows
            await self.db.rollback()
            # Depending on your use case, you can either return None,
            # re-raise a custom HTTPException, or handle upsert logic here.
            return None

    async def update(self, *, db_obj: Branch, obj_in: BranchUpdate | dict) -> Branch:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def remove(self, *, id: UUID) -> Branch | None:
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.commit()
        return obj
