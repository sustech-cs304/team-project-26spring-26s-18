import time
print("[启动分析] routers/rag.py 开始导入", time.time())
from fastapi import APIRouter, Body
from typing import List, Optional
from utils.rag_util import store_document
from utils.Result import Result
import base64
router = APIRouter(prefix="/rag", tags=["rag"])

# 支持批量上传base64文件内容，类型，文件名
@router.post("/upload")
async def upload_document(
    files: Optional[List[str]] = Body(None, embed=True),         # base64内容数组
    file_types: Optional[List[str]] = Body(None, embed=True),    # 文件类型数组
    file_names: Optional[List[str]] = Body(None, embed=True)     # 文件名数组
):
    if not files or not file_names:
        return Result.error("未收到文件")
    decoded_files = []
    for idx, file_b64 in enumerate(files):
        content = base64.b64decode(file_b64)
        decoded_files.append(content)
    # 统一传递三个数组
    store_document(decoded_files, file_types, file_names)
    return Result.success(f"共{len(files)}个文件上传并存储成功")