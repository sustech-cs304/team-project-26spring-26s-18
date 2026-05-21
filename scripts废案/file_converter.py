from pathlib import Path
from docx2pdf import convert

def convert_docx_to_pdf(docx_path: Path | str) -> Path:
    """
    将 docx 文件转换为 pdf。
    返回生成的 pdf 文件路径。
    注意：docx2pdf 依赖于 Windows 或 macOS 上安装的 Microsoft Word。
    """
    docx_path = Path(docx_path)
    if not docx_path.exists():
        raise FileNotFoundError(f"文件未找到: {docx_path}")

    pdf_path = docx_path.with_suffix('.pdf')
    
    # 执行转换
    convert(str(docx_path), str(pdf_path))
    
    return pdf_path