"""
课程配置管理

用户课程数据存储，与 API key 分离。
配置文件路径: file_helper/user_config.json
"""

import json
import re
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# ===== 配置路径 =====

def _get_config_path() -> Path:
    """获取用户配置文件路径"""
    return Path(__file__).parent / "user_config.json"


# ===== 课程数据读写 =====

def load_courses() -> List[Dict]:
    """
    加载课程列表。

    查找顺序：
    1. file_helper/user_config.json 的 courses 字段
    2. 如果文件不存在或 courses 为空，返回内置默认课程

    Returns:
        [{"code": "CS201", "name": "离散数学"}, ...]
    """
    config_path = _get_config_path()

    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            courses = data.get("courses", [])
            if courses:
                return courses
        except (json.JSONDecodeError, IOError):
            pass

    # 内置默认课程（示例，用户可覆盖）
    return _get_default_courses()


def save_courses(courses: List[Dict]) -> bool:
    """
    保存课程列表到 user_config.json。

    Args:
        courses: [{"code": "CS201", "name": "离散数学"}, ...]

    Returns:
        True if saved successfully
    """
    config_path = _get_config_path()
    try:
        data = {"courses": courses}
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except IOError:
        return False


def add_course(code: str, name: str) -> bool:
    """添加一门课程"""
    courses = load_courses()
    # 避免重复
    if any(c["code"] == code for c in courses):
        return False
    courses.append({"code": code, "name": name})
    return save_courses(courses)


def remove_course(code: str) -> bool:
    """删除一门课程"""
    courses = load_courses()
    original_len = len(courses)
    courses = [c for c in courses if c["code"] != code]
    if len(courses) < original_len:
        return save_courses(courses)
    return False


# ===== 内置默认课程 =====

def _get_default_courses() -> List[Dict]:
    """
    内置默认课程（计算机专业常见课程）。
    仅在 user_config.json 不存在时使用。
    """
    return [
        {"code": "CS101", "name": "计算机导论"},
        {"code": "CS102", "name": "C语言程序设计"},
        {"code": "CS103", "name": "数据结构"},
        {"code": "CS201", "name": "离散数学"},
        {"code": "CS202", "name": "算法设计"},
        {"code": "CS301", "name": "计算机网络"},
        {"code": "CS302", "name": "数据库系统"},
        {"code": "CS303", "name": "操作系统"},
        {"code": "CS304", "name": "软件工程"},
        {"code": "CS305", "name": "编译原理"},
        {"code": "CS306", "name": "计算机体系结构"},
        {"code": "CS401", "name": "人工智能"},
        {"code": "CS402", "name": "机器学习"},
        {"code": "MATH101", "name": "高等数学"},
        {"code": "MATH102", "name": "线性代数"},
        {"code": "MATH103", "name": "概率论"},
        {"code": "MATH201", "name": "离散数学"},
        {"code": "MATH205", "name": "数值分析"},
        {"code": "EE101", "name": "电路基础"},
        {"code": "PHYS101", "name": "大学物理"},
        {"code": "OS", "name": "操作系统"},
        {"code": "OOP", "name": "面向对象编程"},
        {"code": "DB", "name": "数据库"},
        {"code": "AI", "name": "人工智能"},
    ]


# ===== 课程识别核心 =====

# 置信度等级
class Confidence:
    HIGH = "high"       # 课程代码直接命中（CS303、MATH205 等）
    MEDIUM = "medium"   # 课程名称命中（操作系统、软件工程 等）
    LOW = "low"         # AI 推断
    NONE = "none"       # 无匹配


def build_lookup_table(courses: List[Dict]):
    """
    从课程列表构建两套查找表：

    code_patterns: 高置信度，课程代码直接匹配
    name_patterns: 中置信度，课程名称匹配
    """
    code_patterns, name_patterns = [], []

    for course in courses:
        code, name = course.get("code", ""), course.get("name", "")
        if not code and not name:
            continue

        # 课程代码 → 高置信度
        if code:
            try:
                code_patterns.append((re.compile(re.escape(code), re.IGNORECASE), code, code, name))
            except re.error:
                pass

        # 中文名 / 简称 / 英文名 → 中置信度
        name_kws = []
        if name:
            name_kws.append(name)
            abbrevs = {
                "高数": "高等数学", "线代": "线性代数",
                "概率": "概率论", "离散": "离散数学",
                "机组": "计算机体系结构", "计网": "计算机网络",
                "软工": "软件工程", "算法": "算法设计",
                "数据库": "数据库系统",
            }
            if name in abbrevs:
                name_kws.extend([k for k, v in abbrevs.items() if v == name])
        en = course.get("keywords", [])
        if isinstance(en, list):
            name_kws.extend(en)
        elif isinstance(en, str) and en:
            name_kws.append(en)

        for kw in set(name_kws):
            # 过滤掉太短的通用词，避免误匹配
            STOP_WORDS = {"to", "of", "and", "the", "for", "in", "on", "a", "an", "is", "i", "ii", "iii", "iv", "v", "vi", "ⅵ"}
            parts = kw.split()
            # 提取有意义的词（>=4字符且非停用词）
            meaningful = [p for p in parts if len(p) >= 4 and p.lower() not in STOP_WORDS]

            if meaningful:
                # 多词关键词：每个有意义的词独立匹配
                for part in meaningful:
                    try:
                        name_patterns.append((re.compile(re.escape(part), re.IGNORECASE), part, code, name))
                    except re.error:
                        pass
            else:
                # 单词关键词（<=3字符的非停用词，如 "AI"）：直接匹配
                if kw:
                    try:
                        name_patterns.append((re.compile(re.escape(kw), re.IGNORECASE), kw, code, name))
                    except re.error:
                        pass

    # 长词优先匹配，避免短词被更通用的词抢先
    name_patterns.sort(key=lambda x: len(x[1]), reverse=True)
    return code_patterns, name_patterns


def match_course_by_regex(text: str, patterns: List[Tuple[re.Pattern, str, str]]) -> Optional[Tuple[str, str]]:
    """
    按优先级匹配：
    1. 多词课程（>=2个词命中）优先——命中词数最多的胜出
    2. 单字词兜底——没有任何多词命中时，取匹配词数最多的课程
    """
    from collections import defaultdict

    # 统计每个课程被多少个模式命中
    score = defaultdict(lambda: {"count": 0, "words": set(), "code": "", "name": ""})
    for item in patterns:
        pattern, keyword, code, name = item
        if pattern.search(text):
            score[code]["count"] += 1
            score[code]["words"].add(keyword)
            score[code]["code"] = code
            score[code]["name"] = name

    if not score:
        return None

    # 多词课程（>=2个词命中）优先
    multi = {k: v for k, v in score.items() if v["count"] >= 2}
    if multi:
        best = max(multi.values(),
                   key=lambda x: (x["count"], len(max(x["words"], key=len))))
        return (best["code"], best["name"])

    # 单字词兜底
    best = max(score.values(), key=lambda x: x["count"])
    return (best["code"], best["name"])


def get_folder_name(code: str, name: str) -> str:
    """生成课程文件夹名称"""
    if code and name:
        return f"{code}_{name}"
    elif code:
        return f"{code}_未知课程"
    else:
        return "其他_无法识别"


# ===== AI 识别（依赖百炼 API） =====

def _call_bailian_ai(filename: str, content_hint: str = "") -> Optional[dict]:
    """
    调用百炼 AI 识别文件所属课程（参考 agent_analyzer.py 的高质量实现）。

    Args:
        filename: 文件名
        content_hint: 文件内容片段

    Returns:
        {"course_code": "CS303", "course_name": "操作系统"} 或 None
    """
    try:
        from .config import BAILIAN_API_KEY
    except ImportError:
        return None

    if not BAILIAN_API_KEY:
        return None

    courses = load_courses()
    course_lines = []
    for c in courses:
        kw = ", ".join(c.get("keywords", [])) if c.get("keywords") else ""
        if kw:
            course_lines.append(f"{c['code']} - {c['name']} ({kw})")
        else:
            course_lines.append(f"{c['code']} - {c['name']}")
    course_list = "\n".join(course_lines)

    prompt = f"""文件名: {filename}
内容: {content_hint[:300] if content_hint else "无"}

课程列表:
{course_list}

请根据文件名判断属于哪门课程，直接返回JSON：
{{"course_code": "课程代码", "course_name": "课程名称"}}
无法判断返回: {{"course_code": "Unknown", "course_name": "Unknown"}}
"""

    import urllib.request

    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    try:
        req = urllib.request.Request(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {BAILIAN_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()

            # 尝试解析 JSON
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # 提取 JSON 片段
                match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                else:
                    return None

            course_code = parsed.get("course_code", "Unknown")
            course_name = parsed.get("course_name", "Unknown")

            # 如果 AI 返回的代码不在已知列表，尝试映射
            if course_code != "Unknown":
                for c in courses:
                    if c["code"].lower() == course_code.lower():
                        return {"course_code": c["code"], "course_name": c["name"]}
                    if c["name"] == course_name:
                        return {"course_code": c["code"], "course_name": c["name"]}
                # AI 推断了一个新代码，保留
                return {"course_code": course_code, "course_name": course_name}

            return None

    except Exception:
        return None


def batch_classify_courses(files: list, batch_size: int = 30) -> dict:
    """
    批量分类文件所属课程，一次 API 调用处理多个文件。

    Args:
        files: 文件路径列表
        batch_size: 每批文件数量（默认30，避免超出 token 限制）

    Returns:
        {filepath: {"course_code": "CS307", "course_name": "数据库原理"}} 或 "OTHER"
    """
    try:
        from .config import BAILIAN_API_KEY
    except ImportError:
        return {}

    if not BAILIAN_API_KEY:
        return {}

    courses = load_courses()
    course_lines = []
    for c in courses:
        kw = ", ".join(c.get("keywords", [])) if c.get("keywords") else ""
        line = f"{c['code']} - {c['name']}"
        if kw:
            line += f" ({kw})"
        course_lines.append(line)
    course_list = "\n".join(course_lines)

    import urllib.request
    results = {}

    # 分批处理
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]

        # 构造文件列表，附带内容片段
        file_lines = []
        for idx, f in enumerate(batch, 1):
            path = Path(f)
            hint = _read_file_content(path, max_chars=200)
            hint_str = hint.replace("\n", " ")[:200] if hint else "无"
            file_lines.append(f"{idx}. {path.name} | {hint_str}")

        files_text = "\n".join(file_lines)

        prompt = f"""以下是 {len(batch)} 个文件，请将每个文件分类到对应课程。

文件列表（编号. 文件名 | 内容片段）：
{files_text}

课程列表：
{course_list}

请返回 JSON 数组，每个元素对应一个文件（按编号顺序）：
[
  {{"idx": 1, "course_code": "课程代码", "course_name": "课程名称"}},
  ...
]
无法判断的填：{{"idx": N, "course_code": "Unknown", "course_name": "Unknown"}}
只返回 JSON 数组，不要其他文字。"""

        payload = {
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        try:
            req = urllib.request.Request(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {BAILIAN_API_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                content = raw["choices"][0]["message"]["content"].strip()

            # 提取 JSON 数组
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if not match:
                continue
            parsed = json.loads(match.group(0))

            # 建立 code → 官方名称 的查找表
            code_to_name = {c["code"].lower(): c["name"] for c in courses}

            for item in parsed:
                idx = item.get("idx", 0) - 1
                if 0 <= idx < len(batch):
                    code = item.get("course_code", "Unknown")
                    name = item.get("course_name", "Unknown")
                    if code and code != "Unknown":
                        # 用 known courses 里的官方名称，避免 AI 返回不一致的变体
                        canonical = code_to_name.get(code.lower())
                        results[batch[idx]] = {
                            "course_code": code,
                            "course_name": canonical if canonical else name,
                        }
                    else:
                        results[batch[idx]] = "OTHER"

        except Exception as e:
            print(f"  [批量分类] 第 {i//batch_size + 1} 批失败: {e}")
            # 该批次标记为 OTHER
            for f in batch:
                if f not in results:
                    results[f] = "OTHER"

    return results


def _read_file_content(filepath: Path, max_chars: int = 500) -> str:
    """
    读取文件内容用于辅助课程识别。

    支持多种格式：txt, md, py, java, c, cpp, h, pdf, docx 等。
    """
    ext = filepath.suffix.lower()

    # 纯文本格式：直接读取
    if ext in (".txt", ".md", ".py", ".java", ".c", ".cpp", ".h",
                ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml",
                ".xml", ".sh", ".bat", ".ps1"):
        try:
            return filepath.read_text(encoding="utf-8", errors="ignore")[:max_chars]
        except Exception:
            pass

    # PDF：尝试用 pypdf
    elif ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(filepath)
            text_parts = []
            for i, page in enumerate(reader.pages[:3]):  # 只读前3页
                text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts)[:max_chars]
        except Exception:
            pass

    # Word (.docx)：尝试用 python-docx
    elif ext in (".docx",):
        try:
            import docx
            doc = docx.Document(filepath)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)[:max_chars]
        except Exception:
            pass

    # Excel (.xlsx)
    elif ext in (".xlsx",):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
            text_parts = []
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(max_row=20, values_only=True):
                    for cell in row:
                        if cell:
                            text_parts.append(str(cell))
            return " ".join(text_parts)[:max_chars]
        except Exception:
            pass

    return ""


def identify_course_for_file(filepath: str, use_ai: bool = True) -> Tuple[str, str, str]:
    """
    识别单个文件的所属课程。只调用 AI，不做其他任何处理。
    """
    path = Path(filepath)
    filename = path.name
    content_hint = _read_file_content(path)

    result = _call_bailian_ai(filename, content_hint)
    if result:
        code = result.get("course_code", "OTHER")
        name = result.get("course_name", "其他")
        if code != "Unknown":
            return (code, name, Confidence.LOW)

    return ("OTHER", "其他_无法识别", Confidence.NONE)
