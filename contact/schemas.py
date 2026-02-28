from pydantic import BaseModel
from typing import Optional

class Contact(BaseModel):
    nickname: str
    phone: int = 88003555
    isActive: Optional[bool] = True


class ContactNickname(BaseModel):
    nickname: str