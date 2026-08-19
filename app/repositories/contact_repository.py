from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact_model import ContactModel


class ContactRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, contact: ContactModel) -> ContactModel:
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)
        return contact

    async def get_all(self) -> list[ContactModel]:
        statement = select(ContactModel).order_by(ContactModel.id)
        result = await self.db.scalars(statement)
        return list(result.all())

    async def get_by_id(self, contact_id: int) -> ContactModel | None:
        return await self.db.get(ContactModel, contact_id)

    async def get_by_nickname(self, contact_nickname: str) -> ContactModel | None:
        statement = select(ContactModel).where(
            ContactModel.nickname == contact_nickname
        )
        return await self.db.scalar(statement)

    async def delete(self, contact: ContactModel) -> None:
        await self.db.delete(contact)
        await self.db.flush()
