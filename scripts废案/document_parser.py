import docx
import fitz  # PyMuPDF
from pathlib import Path

def extract_text_from_docx(file_path: Path | str, max_chars: int = 1000) -> str:
    """
    提取 docx 文件中的前部分文本用于意图识别。
    为了节约 token 且高效，默认提取前 1000 个字符（通常包含标题、课程名等信息）。
    """
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())
        return "\n".join(full_text)[:max_chars]
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return ""

def extract_text_from_pdf(file_path: Path | str, max_chars: int = 1000) -> str:
    """
    提取 pdf 文件中的前部分文本用于意图识别。
    """
    try:
        doc = fitz.open(file_path)
        full_text = []
        # 为了节约 token 和提高效率，只读取前5页
        for page_num in range(min(len(doc), 5)):
            page = doc.load_page(page_num)
            full_text.append(page.get_text("text"))
        return "\n".join(full_text)[:max_chars]
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return ""