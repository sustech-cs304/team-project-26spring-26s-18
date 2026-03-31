from fastapi import APIRouter, Body
from utils.ai_util import ai_chat
from utils.Result import Result

router = APIRouter(prefix="/test", tags=["test"])

