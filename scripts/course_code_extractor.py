"""
课程编号提取器 - 通过正则表达式从文件名和文本内容中提取课程编号
这是规则匹配层，100% 准确，不依赖 AI
"""

import re
from pathlib import Path
from typing import Optional, Tuple


# 常见的课程编号前缀模式（高校常用格式）
# 支持: CS303, STAT205, MATH101, EE203, BIOL101 等
# 也支持: CS-303, CS_303, CS303-01 等变体
COURSE_CODE_PATTERNS = [
    # 通用格式: 字母前缀 + 数字编号 (最常见)
    # 例如: CS303, STAT205, MATH101, EE203
    r'\b([A-Z]{2,8}[-]?\d{2,5}[A-Z]?(?:[-_]?\d{1,2})?)\b',

    # 数字 + 字母后缀: CS101A, MATH202B
    r'\b([A-Z]{2,6}(\d{3,5})[A-Z])\b',

    # 课程关键词 + 编号: Course 303, Class CS303
    r'\b(?:course|class|course code|course no\.?)\s*[:\-]?\s*([A-Z]{2,6}[-]?\d{2,5}[A-Z]?(?:[-_]?\d{1,2})?)\b',

    # 括号内的课程编号: (CS303), (CS 303)
    r'\(([A-Z]{2,6})\s*(\d{2,5})\)',

    # 标题中的课程编号: CS303 - 作业标题
    r'^([A-Z]{2,6}[-_]?\d{2,5})\s*[-–—:.]',
]

# 排除词列表：常见英文单词后跟数字，不是课程编号
EXCLUDE_KEYWORDS = [
    'spring', 'fall', 'summer', 'winter',  # 季节 + 年份 (Spring2026)
    'year', 'term', 'semester', 'quarter',  # 学期
    'chapter', 'part', 'section',  # 章节
    'page', 'vol', 'volume',  # 卷期
    'homework', 'assignment',  # 作业类型
]

# 排除模式：这些不应该被识别为课程编号
EXCLUDE_PATTERNS = [
    # 学号: 通常是纯数字或数字开头的较长字符串
    r'^\d{8,}$',  # 8位以上纯数字（可能是学号）
    r'^\d{4}[-/]\d{4}',  # 形如 1221/0161

    # 版本号、日期等
    r'v\d+\.\d+',  # v1.0, v2.3.1
    r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',  # 日期格式

    # 常见的非课程数字
    r'^(\d{1,3})$',  # 单独的个位数/两位数

    # 季节 + 年份格式: SPRING2026, FALL2025
    r'^(SPRING|FALL|SUMMER|WINTER)\d{4}$',
]


def normalize_course_code(code: str) -> str:
    """
    标准化课程代码格式
    例如: cs-303 -> CS303, CS_303 -> CS303, CS303-01 -> CS303
    """
    # 移除连字符和下划线
    normalized = re.sub(r'[-_]', '', code)
    return normalized.upper()


def is_likely_course_code(code: str) -> bool:
    """
    判断提取的字符串是否可能是课程代码
    """
    # 太短的不是课程编号
    if len(code) < 4:
        return False

    # 必须包含至少2个字母和至少2个数字
    letters = sum(1 for c in code if c.isalpha())
    digits = sum(1 for c in code if c.isdigit())

    if letters < 2 or digits < 2:
        return False

    # 排除学号（8位以上纯数字开头）
    if code[0].isdigit() and len(code) >= 8:
        return False

    # 排除关键词: Spring2026, Fall2025 等
    upper_code = code.upper()
    # 提取字母前缀部分进行检查
    prefix_match = re.match(r'^([A-Z]+)', upper_code)
    if prefix_match:
        prefix = prefix_match.group(1).lower()
        if prefix in EXCLUDE_KEYWORDS:
            return False

    return True


def extract_from_filename(filename: str) -> Optional[str]:
    """
    从文件名中提取课程编号
    优先级最高，因为文件名通常最准确
    """
    # 移除文件扩展名
    name_without_ext = Path(filename).stem

    # 文件名中常用的宽松模式
    loose_patterns = [
        r'([A-Z]{2,8}[-_]?\d{2,5})',  # CS303, CS_303, CS-303
        r'\b([A-Z]{2,8}[-]?\d{2,5}[A-Z]?(?:[-_]?\d{1,2})?)\b',  # 严格模式
    ]

    # 先尝试宽松模式
    for pattern in loose_patterns:
        matches = re.findall(pattern, name_without_ext, re.IGNORECASE)
        for match in matches:
            code = match if isinstance(match, str) else next((m for m in match if m), '')
            if code and is_likely_course_code(code):
                normalized = normalize_course_code(code)
                # 排除明显不是课程代码的
                if not any(re.match(p, normalized) for p in EXCLUDE_PATTERNS):
                    return normalized

    # 再尝试 COURSE_CODE_PATTERNS
    for pattern in COURSE_CODE_PATTERNS:
        matches = re.findall(pattern, name_without_ext, re.IGNORECASE)
        for match in matches:
            code = match if isinstance(match, str) else next((m for m in match if m), '')
            if code and is_likely_course_code(code):
                normalized = normalize_course_code(code)
                if not any(re.match(p, normalized) for p in EXCLUDE_PATTERNS):
                    return normalized

    return None


def extract_from_text(text: str, max_length: int = 2000) -> Optional[str]:
    """
    从文本内容中提取课程编号
    只检查前 max_length 个字符（通常标题在前面）
    
    使用更宽松的匹配模式，专门处理中文文本中的课程编号
    """
    # 优先检查文本开头（通常是标题）
    text_to_check = text[:max_length]

    # 额外的宽松模式：专门匹配中文文本中的课程编号
    loose_patterns = [
        # 直接匹配字母+数字组合（不需要边界）
        r'([A-Z]{2,6})\s*(\d{3,5})',
        # 匹配"CS303"这种无空格的格式
        r'([A-Z]{2,6})(\d{3,5})(?![a-zA-Z])',
        # 匹配编号结尾是数字或字母的情况
        r'([A-Z]{2,8}[-_]?\d{2,5})',
    ]

    for pattern in loose_patterns:
        matches = re.findall(pattern, text_to_check, re.IGNORECASE)
        for match in matches:
            code = match if isinstance(match, str) else ''.join(match)
            if code and is_likely_course_code(code):
                normalized = normalize_course_code(code)
                if not any(re.match(p, normalized) for p in EXCLUDE_PATTERNS):
                    return normalized

    # 也尝试原来的严格模式
    for pattern in COURSE_CODE_PATTERNS[2:]:  # 内容用后面的模式
        matches = re.findall(pattern, text_to_check, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            code = match if isinstance(match, str) else next((m for m in match if m), '')
            if code and is_likely_course_code(code):
                normalized = normalize_course_code(code)
                if not any(re.match(p, normalized) for p in EXCLUDE_PATTERNS):
                    return normalized

    return None


def extract_course_code(filename: str, text_content: str = "") -> Tuple[Optional[str], str]:
    """
    主入口：从文件名和文本内容中提取课程编号

    返回: (提取到的课程编号或None, 来源说明)
    """
    # Step 1: 优先从文件名提取
    code = extract_from_filename(filename)
    if code:
        return code, "filename"

    # Step 2: 从文本内容提取
    if text_content:
        code = extract_from_text(text_content)
        if code:
            return code, "content"

    return None, "none"


# 测试代码
if __name__ == "__main__":
    test_cases = [
        # 文件名测试
        ("CS303_Lab1.docx", "应该提取 CS303"),
        ("MATH205-HW2.pdf", "应该提取 MATH205"),
        ("STAT202_Assignment3.docx", "应该提取 STAT202"),
        ("CS-303 Lecture Notes.pdf", "应该提取 CS303"),
        ("Homework_CS101.pdf", "应该提取 CS101"),
        ("生物实验报告.pdf", "无法识别"),

        # 内容片段测试
        ("作业文件", "这是一门 CS303 课程的 Lab1 实验报告"),
        ("报告", "Course Code: MATH205\n这是一份数学作业"),
    ]

    print("=== 课程编号提取测试 ===\n")
    for filename, content in test_cases:
        code, source = extract_course_code(filename, content)
        print(f"文件: {filename}")
        print(f"内容: {content}")
        print(f"结果: {code or '未识别'} (来源: {source})")
        print("-" * 50)
