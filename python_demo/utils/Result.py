from pydantic import BaseModel
from typing import Any, Optional

class Result(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

    @staticmethod
    def success(data=None):
        return Result(code=1, message="success", data=data)

    @staticmethod
    def error(message):
        return Result(code=0, message=message, data=None)