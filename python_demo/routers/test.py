from fastapi import APIRouter, Body
from utils.ai_util import chat_with_ai
from utils.Result import Result

router = APIRouter(prefix="/test", tags=["test"])

# 示例接口：调用AI生成回复
@router.post("/ask_ai")
async def ask_ai(
	content: str = Body(..., embed=True)
):
	try:
		reply = chat_with_ai(content)
		return Result.success(reply)
	except Exception as e:
		return Result.error(str(e))
