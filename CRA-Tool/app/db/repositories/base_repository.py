"""
Generic asynchronous repository pattern.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base_model import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        return await db.get(self.model, id)

    async def get_all(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: dict[str, Any]) -> ModelType:
        try:
            obj_data = self.model(**obj_in)
            db.add(obj_data)
            await db.commit()
            await db.refresh(obj_data)
            return obj_data
        except SQLAlchemyError:
            await db.rollback()
            raise

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: dict[str, Any]
    ) -> ModelType:
        try:
            for field, value in obj_in.items():
                setattr(db_obj, field, value)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError:
            await db.rollback()
            raise

    async def delete(self, db: AsyncSession, *, id: Any) -> ModelType | None:
        try:
            obj = await db.get(self.model, id)
            if obj:
                await db.delete(obj)
                await db.commit()
            return obj
        except SQLAlchemyError:
            await db.rollback()
            raise


class TenantScopedRepository(BaseRepository[ModelType]):
    """Repository for tenant-owned business rows.

    All read/write helpers require a tenant_id and scope by it. Use
    BaseRepository only for global/reference tables.
    """

    def __init__(self, model: type[ModelType]):
        if not hasattr(model, "tenant_id"):
            raise ValueError(f"{model.__name__} is not tenant scoped")
        super().__init__(model)

    async def get_for_tenant(
        self, db: AsyncSession, *, id: Any, tenant_id: str
    ) -> ModelType | None:
        result = await db.execute(
            select(self.model).where(self.model.id == id, self.model.tenant_id == tenant_id)
        )
        return result.scalars().first()

    async def get_all_for_tenant(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        result = await db.execute(
            select(self.model)
            .where(self.model.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_for_tenant(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        obj_in: dict[str, Any],
    ) -> ModelType:
        return await self.create(db, obj_in={**obj_in, "tenant_id": tenant_id})

    async def update_for_tenant(
        self,
        db: AsyncSession,
        *,
        id: Any,
        tenant_id: str,
        obj_in: dict[str, Any],
    ) -> ModelType | None:
        db_obj = await self.get_for_tenant(db, id=id, tenant_id=tenant_id)
        if db_obj is None:
            return None
        obj_in = {key: value for key, value in obj_in.items() if key != "tenant_id"}
        return await self.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete_for_tenant(
        self, db: AsyncSession, *, id: Any, tenant_id: str
    ) -> ModelType | None:
        try:
            obj = await self.get_for_tenant(db, id=id, tenant_id=tenant_id)
            if obj:
                await db.delete(obj)
                await db.commit()
            return obj
        except SQLAlchemyError:
            await db.rollback()
            raise
