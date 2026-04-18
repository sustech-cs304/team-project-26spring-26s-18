import json
import re
from pathlib import Path
from document_parser import extract_text_from_docx, extract_text_from_pdf
from file_manager import rename_and_move_file

# 加载课程配置
with open(Path(__file__).parent / "config.json", "r", encoding="utf-8") as f:
    student_info = json.load(f)


def _build_course_lookup_table():
    """
    构建课程查找表：课程名称/关键词 → 课程代码
    用于快速匹配文件名或内容中的课程信息
    """
    lookup = {}
    for course in student_info.get("courses", []):
        code = course.get("code", "")
        name = course.get("name", "")
        keywords = course.get("keywords", [])

        # 添加课程代码本身
        if code:
            lookup[code.upper()] = code

        # 添加课程名称（中文/英文）
        if name:
            lookup[name.upper()] = code
            lookup[name.lower()] = code

        # 添加关键词
        for kw in keywords:
            if kw:
                lookup[kw.upper()] = code
                lookup[kw.lower()] = code

    return lookup


def _match_from_config(filename: str, text_content: str) -> tuple:
    """
    从 config.json 的课程列表中匹配课程代码

    返回: (matched_code, match_type) 或 (None, None)
    """
    lookup = _build_course_lookup_table()
    combined_text = f"{filename} {text_content}".upper()

    # 按关键词长度从长到短排序，避免短关键词优先匹配
    sorted_keywords = sorted(lookup.keys(), key=len, reverse=True)

    for keyword in sorted_keywords:
        # 确保是完整的词匹配（前后有分隔符）
        pattern = r'(?:^|[^a-zA-Z0-9])' + re.escape(keyword) + r'(?:$|[^a-zA-Z0-9])'
        if re.search(pattern, combined_text, re.IGNORECASE):
            return lookup[keyword], "config"

    return None, None


def process_single_homework(file_path: str):
    """
    User Story 1: 自动重命名并转 PDF 交作业
    """
    path = Path(file_path)

    # 1. 提取文档内容
    text_content = extract_text_from_docx(path)

    # 2. 匹配 config.json 中的课程
    course_code, _ = _match_from_config(path.name, text_content)

    if not course_code:
        print(f"❌ 无法识别课程，请检查文件名是否包含课程编号（如 CS201）或课程名称")
        return

    # 3. 获取课程文件夹名称
    folder_name = _get_course_folder_name(course_code)
    print(f"✅ 识别到课程: {folder_name}")

    # 4. 拼接目标文件名: 姓名_学号_课程代码.docx
    new_name = f"{student_info['name']}_{student_info['student_id']}_{course_code}.docx"

    # 5. 移动到课程文件夹并重命名
    target_dir = Path(__file__).parent / "output" / folder_name
    renamed_file_path = rename_and_move_file(path, new_name, target_directory=target_dir)

    # 6. 转换为 PDF
    from file_converter import convert_docx_to_pdf
    final_pdf_path = convert_docx_to_pdf(renamed_file_path)

    print(f"✅ 作业处理完成！可直接提交: {final_pdf_path}")


def categorize_file_by_extension(file_path: Path) -> str:
    """
    根据文件扩展名分类文件
    """
    suffix = file_path.suffix.lower()

    document_exts = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.txt', '.md'}
    archive_exts = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
    executable_exts = {'.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.apk', '.app'}

    if suffix in document_exts:
        return "document"
    elif suffix in archive_exts:
        return "archive"
    elif suffix in image_exts:
        return "image"
    elif suffix in executable_exts:
        return "executable"
    else:
        return "other"


def organize_downloads_folder(downloads_dir: str):
    """
    User Story 2: 扫描下载目录，根据内容分类到不同科目文件夹

    分类策略：
    1. 非文档文件 → Archive/Image 等文件夹
    2. 匹配 config.json 课程
    3. 无法匹配 → 其他文件夹
    """
    downloads = Path(downloads_dir)

    stats = {
        "total": 0,
        "categorized_by_config": 0,
        "categorized_by_type": 0,
        "skipped": 0,
    }

    print("=" * 60)
    print(f"已加载 {len(student_info.get('courses', []))} 门课程配置")
    print("开始扫描下载目录...")
    print("=" * 60)

    for file_path in downloads.iterdir():
        if not file_path.is_file():
            continue

        stats["total"] += 1
        file_type = categorize_file_by_extension(file_path)

        # Step 1: 非文档文件 → 按类型分类
        if file_type != "document":
            target_dir = downloads / file_type.capitalize()
            rename_and_move_file(file_path, file_path.name, target_directory=target_dir)
            stats["categorized_by_type"] += 1
            print(f"[{file_type.upper()}] {file_path.name} → {file_type.capitalize()}/")
            continue

        # Step 2: 文档文件 → 提取文本
        text_content = ""
        if file_path.suffix.lower() == '.docx':
            text_content = extract_text_from_docx(file_path)
        elif file_path.suffix.lower() == '.pdf':
            text_content = extract_text_from_pdf(file_path)

        # Step 3: 匹配 config.json 中的课程
        course_code, match_type = _match_from_config(file_path.name, text_content)

        if course_code:
            folder_name = _get_course_folder_name(course_code)
            target_dir = downloads / folder_name
            rename_and_move_file(file_path, file_path.name, target_directory=target_dir)
            stats["categorized_by_config"] += 1
            print(f"[课程] {file_path.name} → {folder_name}/")
        else:
            # 无法匹配 → 放入"其他"文件夹
            target_dir = downloads / "其他"
            rename_and_move_file(file_path, file_path.name, target_directory=target_dir)
            stats["skipped"] += 1
            print(f"[其他] {file_path.name} → 其他/")

    # 打印统计
    print("\n" + "=" * 60)
    print("分类完成！统计信息：")
    print("=" * 60)
    print(f"总文件数: {stats['total']}")
    print(f"  - 课程文件: {stats['categorized_by_config']}")
    print(f"  - 按类型分类: {stats['categorized_by_type']} (Archive/Image等)")
    print(f"  - 其他文件: {stats['skipped']}")


def _get_course_folder_name(course_code: str) -> str:
    """
    获取课程文件夹名称：课程代码_中文名称
    如果找不到对应名称，则返回原始课程代码
    """
    course_code_upper = course_code.upper()
    for course in student_info.get("courses", []):
        if course.get("code", "").upper() == course_code_upper:
            name = course.get("name", "")
            # 如果有中文名称（包含非ASCII字符），使用"代码_名称"格式
            if name and name != course_code_upper:
                # 清理名称中的非法文件名字符
                safe_name = _sanitize_folder_name(name)
                return f"{course_code_upper}_{safe_name}"
            return course_code_upper
    return course_code_upper


def _sanitize_folder_name(name: str) -> str:
    """
    清理文件夹名称中的非法字符
    """
    # Windows 文件名非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    safe_name = re.sub(illegal_chars, '_', name)
    # 去除首尾空格和点
    safe_name = safe_name.strip(' .')
    return safe_name


def _add_new_course(course_code: str):
    """添加新课程到记忆"""
    course_code = _normalize_course_id(course_code)
    if "courses" not in student_info:
        student_info["courses"] = []

    print(f"  📚 发现新课程: {course_code}")
    student_info["courses"].append({
        "code": course_code,
        "name": course_code,
        "keywords": []
    })
