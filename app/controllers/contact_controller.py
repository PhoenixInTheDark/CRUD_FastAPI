from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.models.contact_schemas import (
    ContactCreate,
    ContactRead,
    ContactUpdate,
)
from app.repositories.contact_repository import ContactRepository
from app.services.contact_service import ContactService


router = APIRouter(prefix="/contacts", tags=["Contacts"])


async def get_contact_service(
    db: AsyncSession = Depends(get_db),
) -> ContactService:
    repository = ContactRepository(db)
    return ContactService(repository)


@router.post(
    "",
    response_model=ContactRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    data: ContactCreate,
    service: ContactService = Depends(get_contact_service),
) -> ContactRead:
    return await service.create_contact(data)


@router.get("", response_model=list[ContactRead])
async def get_contacts(
    service: ContactService = Depends(get_contact_service),
) -> list[ContactRead]:
    return await service.get_contacts()


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: int,
    service: ContactService = Depends(get_contact_service),
) -> ContactRead:
    return await service.get_contact(contact_id)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    service: ContactService = Depends(get_contact_service),
) -> ContactRead:
    return await service.update_contact(contact_id, data)


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contact(
    contact_id: int,
    service: ContactService = Depends(get_contact_service),
) -> Response:
    await service.delete_contact(contact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)