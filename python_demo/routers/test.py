import time
print("[启动分析] routers/test.py 开始导入", time.time())
from fastapi import APIRouter, Body
from utils.ai_util import ai_chat
from utils.Result import Result


from utils.test_util import rag_strict_answer, ai_chat_test

router = APIRouter(prefix="/test", tags=["test"])

# RAG受控问答API
@router.post("/rag-answer")
async def rag_answer_api(
	query: str = Body(..., embed=True)
):
	answer = rag_strict_answer(query)
	return Result.success(answer)

