from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Session(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SessionContent(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
