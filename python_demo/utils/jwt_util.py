import jwt
from datetime import datetime, timedelta
from typing import Optional

class JWTUtil:
    SECRET = "a_very_long_and_random_secret_key_1234567890!@#$%^&*()"
    ALGORITHM = "HS256"
    EXPIRE_HOURS = 24

    @staticmethod
    def generate_token(user_id: int) -> str:
        payload = {
            "userId": user_id,
            "exp": datetime.utcnow() + timedelta(hours=JWTUtil.EXPIRE_HOURS)
        }
        token = jwt.encode(payload, JWTUtil.SECRET, algorithm=JWTUtil.ALGORITHM)
        # PyJWT >=2.0 返回str，<2.0返回bytes
        if isinstance(token, bytes):
            token = token.decode()
        return token

    @staticmethod
    def parse_token(token: str) -> Optional[int]:
        try:
            payload = jwt.decode(token, JWTUtil.SECRET, algorithms=[JWTUtil.ALGORITHM])
            user_id = payload.get("userId")
            return int(user_id) if user_id is not None else None
        except Exception:
            return None
