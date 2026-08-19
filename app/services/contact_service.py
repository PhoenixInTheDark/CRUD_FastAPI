from sqlalchemy.exc import SQLAlchemyError

from app.exceptions.contact_exceptions import (
    ContactNotFoundError,
    NicknameAlreadyExistsError,
)
from app.models.contact_model import ContactModel
from app.models.contact_schemas import ContactCreate, ContactUpdate
from app.repositories.contact_repository import ContactRepository

class ContactService:
    def __init__(self, repository: ContactRepository) -> None:
        self.repository = repository

    async def create_contact(self, data: ContactCreate) -> ContactModel:
        existing_contact = await self.repository.get_by_nickname(data.nickname)
        if existing_contact is not None:
            raise NicknameAlreadyExistsError(data.nickname)

        contact = ContactModel(
            nickname=data.nickname,
            phone=data.phone,
            is_active=data.is_active,
        )

        try:
            created_contact = await self.repository.create(contact)
            await self.repository.db.commit()
            return created_contact
        except SQLAlchemyError:
            await self.repository.db.rollback()
            raise

    async def get_contacts(self) -> list[ContactModel]:
        return await self.repository.get_all()

    async def get_contact(self, contact_id: int) -> ContactModel:
        contact = await self.repository.get_by_id(contact_id)

        if contact is None:
            raise ContactNotFoundError(contact_id)

        return contact

    async def update_contact(self, contact_id: int, data: ContactUpdate) -> ContactModel:
        contact = await self.get_contact(contact_id)
        changes = data.model_dump(exclude_unset=True)

        duplicate = None
        if "nickname" in changes:
            duplicate = await self.repository.get_by_nickname(changes["nickname"])

            if duplicate is not None and duplicate.id != contact.id:
                raise NicknameAlreadyExistsError(changes["nickname"])

        for field, value in changes.items():
            setattr(contact, field, value)

        try:
            await self.repository.db.commit()
            await self.repository.db.refresh(contact)
            return contact
        except SQLAlchemyError:
            await self.repository.db.rollback()
            raise

    async def delete_contact(self, contact_id: int) -> None:
        contact = await self.get_contact(contact_id)

        try:
            await self.repository.delete(contact)
            await self.repository.db.commit()
        except SQLAlchemyError:
            await self.repository.db.rollback()
            raise
