from pydantic import BaseModel, ConfigDict, Field


class ContactCreate(BaseModel):
    nickname: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=32)
    is_active: bool = True


class ContactUpdate(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    is_active: bool | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    phone: str
    is_active: bool
