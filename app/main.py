from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.controllers.contact_controller import router as contact_router
from app.exceptions.contact_exceptions import (
    ContactNotFoundError,
    NicknameAlreadyExistsError,
)


app = FastAPI(title="Contact Manager API")
app.include_router(contact_router)


@app.exception_handler(ContactNotFoundError)
async def contact_not_found_handler(
    request: Request,
    error: ContactNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Contact not found"},
    )


@app.exception_handler(NicknameAlreadyExistsError)
async def nickname_conflict_handler(
    request: Request,
    error: NicknameAlreadyExistsError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Contact nickname already exists"},
    )