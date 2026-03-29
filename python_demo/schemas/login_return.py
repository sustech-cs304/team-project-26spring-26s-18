from pydantic import BaseModel
from typing import Optional

class LoginReturn(BaseModel):
    id: int
    userName: str
    phone: str
    email: str
    avatarURL: str
    token: Optional[str] = None  #有需要时可以添加token字段，不需要时返回None
