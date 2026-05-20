import time
print("[启动分析] routers/rag.py 开始导入", time.time())
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
from utils.rag_util import store_document
from utils.Result import Result
import base64
import os
import mimetypes
from pathlib import Path
from urllib.parse import quote

router = APIRouter(prefix="/rag", tags=["rag"])

# RAG文档存储目录 - 使用相对于当前文件的绝对路径
import sys
# 获取项目根目录（python_demo的父目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CAMPUS_DOCS_DIR = PROJECT_ROOT / "campus_docs"

print(f"[rag.py] Python version: {sys.version}")
print(f"[rag.py] __file__: {__file__}")
print(f"[rag.py] PROJECT_ROOT: {PROJECT_ROOT}")
print(f"[rag.py] CAMPUS_DOCS_DIR: {CAMPUS_DOCS_DIR}")
print(f"[rag.py] CAMPUS_DOCS_DIR exists: {CAMPUS_DOCS_DIR.exists()}")
print(f"[rag.py] CAMPUS_DOCS_DIR is absolute: {CAMPUS_DOCS_DIR.is_absolute()}")

if CAMPUS_DOCS_DIR.exists():
    try:
        files = [f.name for f in CAMPUS_DOCS_DIR.iterdir() if f.is_file()]
        pdf_count = sum(1 for f in files if f.lower().endswith('.pdf'))
        print(f"[rag.py] Total files: {len(files)}, PDF files: {pdf_count}")
        print(f"[rag.py] Sample files: {files[:10]}")
    except Exception as e:
        print(f"[rag.py] Error listing files: {e}")
else:
    # 尝试列出项目根目录内容
    print(f"[rag.py] PROJECT_ROOT exists: {PROJECT_ROOT.exists()}")
    if PROJECT_ROOT.exists():
        try:
            root_items = [f.name for f in PROJECT_ROOT.iterdir()]
            print(f"[rag.py] PROJECT_ROOT contents: {root_items}")
        except Exception as e:
            print(f"[rag.py] Error listing PROJECT_ROOT: {e}")


# 支持批量上传base64文件内容，类型，文件名
@router.post("/upload")
async def upload_document(
    files: Optional[List[str]] = Body(None, embed=True),         # base64内容数组
    file_types: Optional[List[str]] = Body(None, embed=True),    # 文件类型数组
    file_names: Optional[List[str]] = Body(None, embed=True)     # 文件名数组
):
    if not files or not file_names:
        return Result.error("未收到文件")

    # 确保 campus_docs 目录存在
    CAMPUS_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    decoded_files = []
    saved_files = []

    for idx, file_b64 in enumerate(files):
        content = base64.b64decode(file_b64)
        decoded_files.append(content)

        # 保存原始文件到 campus_docs 目录
        filename = file_names[idx] if idx < len(file_names) else f"uploaded_file_{idx}"
        # 安全检查文件名
        safe_filename = os.path.basename(filename)
        file_path = CAMPUS_DOCS_DIR / safe_filename

        # 如果文件已存在，添加数字后缀
        counter = 1
        original_path = file_path
        while file_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            file_path = CAMPUS_DOCS_DIR / f"{stem}_{counter}{suffix}"
            counter += 1

        try:
            with open(file_path, 'wb') as f:
                f.write(content)
            saved_files.append(file_path.name)
            # 更新文件名（如果发生了重命名）
            if idx < len(file_names):
                file_names[idx] = file_path.name
        except Exception as e:
            print(f"保存文件失败 {filename}: {e}")

    # 统一传递三个数组到向量数据库
    store_document(decoded_files, file_types, file_names)
    return Result.success(f"共{len(files)}个文件上传并存储成功，已保存原始文件: {', '.join(saved_files)}")


def encode_filename_for_header(filename: str) -> str:
    """对中文文件名进行 RFC 5987 编码，用于 Content-Disposition 头"""
    # ASCII 字符直接保留，非 ASCII 字符使用 UTF-8 编码
    try:
        # 尝试 latin-1 编码，如果成功说明是 ASCII
        filename.encode('latin-1')
        return f'filename="{filename}"'
    except UnicodeEncodeError:
        # 包含非 ASCII 字符，使用 RFC 5987 编码
        encoded = quote(filename, safe='')
        return f"filename*=UTF-8''{encoded}"


@router.get("/download/{filename}")
async def download_document(filename: str):
    """下载原始RAG文档"""
    # 安全检查：防止目录遍历攻击
    safe_filename = os.path.basename(filename)
    file_path = CAMPUS_DOCS_DIR / safe_filename

    print(f"[download] Looking for file: {file_path}")
    print(f"[download] File exists: {file_path.exists()}")

    if not file_path.exists():
        # 列出目录中的文件帮助调试
        if CAMPUS_DOCS_DIR.exists():
            available_files = [f.name for f in CAMPUS_DOCS_DIR.iterdir() if f.is_file()]
            print(f"[download] Available files: {available_files[:10]}...")
        raise HTTPException(status_code=404, detail=f"文件不存在: {safe_filename}")

    # 检测MIME类型
    media_type, _ = mimetypes.guess_type(str(file_path))
    if not media_type:
        media_type = "application/octet-stream"

    print(f"[download] Serving file: {file_path}, type: {media_type}")

    # 使用 RFC 5987 编码处理中文文件名
    content_disposition = f"attachment; {encode_filename_for_header(safe_filename)}"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={"Content-Disposition": content_disposition}
    )


@router.get("/file-exists/{filename}")
async def check_file_exists(filename: str):
    """检查文件是否存在（供前端判断是否需要显示下载按钮）"""
    safe_filename = os.path.basename(filename)
    file_path = CAMPUS_DOCS_DIR / safe_filename
    return Result.success({
        "filename": safe_filename,
        "exists": file_path.exists(),
        "size": file_path.stat().st_size if file_path.exists() else 0
    })


@router.get("/preview/{filename}")
async def preview_document(filename: str):
    """预览/查看原始RAG文档内容（文本文件直接返回内容，PDF等返回文件）"""
    # 安全检查：防止目录遍历攻击
    safe_filename = os.path.basename(filename)
    file_path = CAMPUS_DOCS_DIR / safe_filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    # 检测MIME类型
    media_type, _ = mimetypes.guess_type(str(file_path))
    if not media_type:
        media_type = "application/octet-stream"

    # 文本文件直接返回内容
    if media_type and (media_type.startswith("text/") or media_type == "application/json"):
        try:
            content = file_path.read_text(encoding="utf-8")
            return {"filename": safe_filename, "content": content, "type": "text"}
        except Exception as e:
            # 如果读取失败，作为二进制文件返回
            pass

    # 其他文件返回文件响应（浏览器会尝试预览）
    # 使用 RFC 5987 编码处理中文文件名
    content_disposition = f"inline; {encode_filename_for_header(safe_filename)}"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={"Content-Disposition": content_disposition}
    )


@router.get("/list")
async def list_documents():
    """列出所有可用的RAG文档"""
    if not CAMPUS_DOCS_DIR.exists():
        return Result.success([])

    files = []
    for file_path in CAMPUS_DOCS_DIR.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            media_type, _ = mimetypes.guess_type(str(file_path))
            files.append({
                "filename": file_path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "type": media_type or "application/octet-stream",
                "download_url": f"/rag/download/{file_path.name}",
                "preview_url": f"/rag/preview/{file_path.name}",
            })

    return Result.success(files)