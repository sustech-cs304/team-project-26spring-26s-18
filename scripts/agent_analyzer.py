import json
import re
import os  # 导入 os 模块用于获取环境变量
from datetime import datetime
from dashscope import Generation  # 导入阿里云百炼 SDK
from http import HTTPStatus  # 导入 HTTPStatus 用于检查响应状态

# 初始化阿里云百炼客户端
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY（阿里云百炼 API Key）")


def analyze_document_intent(filename: str, text_content: str, courses: list = None) -> dict:
    """
    调用大语言模型，分析文本，提取课程名称和作业类型。

    注意：这个函数现在主要作为"兜底"使用
    正则规则已经处理了大部分情况（课程编号如 CS303、MATH205）
    AI 只处理正则无法识别的复杂情况

    Args:
        filename: 文件名
        text_content: 文档文本内容
        courses: 已知的课程列表（用于参考）

    Returns:
        {"course": "课程代码", "assignment_type": "作业类型"}
    """
    if not text_content:
        return {"course": "Unknown", "assignment_type": "Unknown"}

    # 动态构建课程列表以增强 Prompt
    course_prompt_part = ""
    if courses:
        course_lines = []
        for course in courses:
            keywords = ", ".join(course.get("keywords", []))
            course_lines.append(f"- {course['code']}: {course['name']} (关键词: {keywords})")

        course_list_str = "\n".join(course_lines)
        course_prompt_part = f"""
如果能从以下课程列表中找到匹配项，请返回对应的课程代码：
{course_list_str}

如果没有匹配项，请根据文件名和内容自己推断一个合理的课程代码。"""
    else:
        course_prompt_part = """
如果没有已知课程列表，请根据文件名和内容推断一个合理的课程代码。

课程代码推断规则：
- 通常是 2-6 个大写字母 + 2-5 位数字，如 CS303、MATH205
- 如果文件名或内容中包含课程名称（如"数据结构"、"算法设计"），请推断对应的课程代码
- 如果无法确定，尝试从内容的主题推断（如"机器学习"→ CS324）
"""

    prompt = f"""你是一个课程分类助手。请根据文件名和文档内容，判断它属于哪门课程。

【文件名】(优先级最高，请仔细看):
{filename}

【文档内容片段】(前500字，课程编号通常在这里):
{text_content[:500]}

{course_prompt_part}

请以 JSON 格式返回，必须包含以下两个字段：
{{"course": "课程代码，如 CS303 或 Unknown", "assignment_type": "作业类型，如 Lab1、HW2、Project、Notes 等"}}

注意：
1. 如果文件名包含课程编号（如 CS303_Lab1.docx），直接使用它
2. assignment_type 可以是：Lab、HW、Project、Quiz、Midterm、Final、Notes、Homework、Assignment 等
3. 如果完全无法判断，返回 "Unknown"
"""

    messages = [{'role': 'user', 'content': prompt}]

    try:
        response = Generation.call(
            model="qwen-turbo",
            messages=messages,
            result_format='message',
            api_key=DASHSCOPE_API_KEY,
            temperature=0.1  # 稍微降低温度，减少随机性
        )

        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            # 尝试解析 JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # 如果不是纯 JSON，尝试提取
                import re
                match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                return {"course": "Unknown", "assignment_type": "Unknown"}
        else:
            print(f"AI 解析失败，状态码: {response.status_code}, 错误信息: {response.message}")
            return {"course": "Unknown", "assignment_type": "Unknown"}
    except Exception as e:
        print(f"AI 解析失败: {e}")
        return {"course": "Unknown", "assignment_type": "Unknown"}


def extract_date_from_text(text: str) -> str:
    """
    从文本中提取日期信息，返回格式化的日期字符串
    """
    # 常见日期格式匹配
    date_patterns = [
        r'(\d{4})[年\-\/](\d{1,2})[月\-\/](\d{1,2})',  # 2025-04-18 或 2025年4月18日
        r'(\d{4})(\d{2})(\d{2})',  # 20250418
        r'(\d{1,2})[月\-\/](\d{1,2})[日\-\/]?,?\s*(\d{4})?',  # 04月18日 或 04月18日,2025
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            parts = match.groups()
            if len(parts) >= 3 and parts[2]:  # 有年月日
                year, month, day = parts[0], parts[1], parts[2]
                return f"{year}{month.zfill(2)}{day.zfill(2)}"
            elif len(parts) >= 2:  # 只有月日
                month, day = parts[0], parts[1]
                year = parts[2] if len(parts) > 2 and parts[2] else datetime.now().year
                return f"{year}{month.zfill(2)}{day.zfill(2)}"

    # 如果没找到具体日期，返回当前年月
    now = datetime.now()
    return f"{now.year}{now.month:02d}"


def analyze_life_document(filename: str, text_content: str) -> dict:
    """
    调用大语言模型，分析生活类文档（酒店订单、机票行程单、发票、合同等），
    识别文件类型并生成文件夹名称。

    Args:
        filename: 文件名
        text_content: 文档文本内容

    Returns:
        {
            "is_life_doc": True/False,  # 是否是生活类文档
            "category": "hotel/flight/invoice/contract/insurance/other",
            "folder_name": "2025_携程酒店订单",
            "suggested_rename": "20250418_深圳威尼斯人_入住确认.pdf",
            "year": "2025"  # 提取的年份
        }
    """
    if not text_content:
        return {
            "is_life_doc": False,
            "category": "unknown",
            "folder_name": "",
            "suggested_rename": "",
            "year": ""
        }

    # 先尝试快速检测关键词，快速排除非生活类文档
    quick_keywords = [
        # 生活类关键词
        "酒店", "机票", "行程单", "发票", "合同", "保险", "预订", "入住",
        "航班", "登机", "旅客", "护照", "签证", "护照号",
        "携程", "去哪儿", "飞猪", "Booking", "Airbnb", "Marriott", "Hilton",
        "南方航空", "国航", "东航", "深航", "Air China", "China Southern",
        "中国人民保险", "平安保险", "太平洋保险",
        "租房", "房东", "物业费", "水电费", "燃气费",
        "手机费", "宽带费", "学费", "考试", "准考证",
        "核酸", "疫苗", "健康码", "体检", "挂号",
        "外卖", "团购", "订单", "收据", "账单"
    ]

    text_lower = text_content.lower()
    filename_lower = filename.lower()

    # 快速检测
    detected_keywords = []
    for kw in quick_keywords:
        if kw.lower() in text_lower or kw.lower() in filename_lower:
            detected_keywords.append(kw)

    # 如果检测到的生活类关键词少于2个，大概率不是生活类文档
    if len(detected_keywords) < 2:
        return {
            "is_life_doc": False,
            "category": "unknown",
            "folder_name": "",
            "suggested_rename": "",
            "year": ""
        }

    # 提取日期信息
    year = extract_date_from_text(text_content)

    prompt = f"""你是一个文档分类助手。请分析以下文档，判断它属于哪种生活类文件，并给出文件夹命名建议。

【文件名】:
{filename}

【文档内容片段】(前800字，包含关键信息):
{text_content[:800]}

【快速检测到的关键词】:
{', '.join(detected_keywords)}

请根据内容识别文件的：
1. 类型（category）：hotel（酒店）/ flight（机票/行程单）/ invoice（发票）/ contract（合同）/ insurance（保险）/ medical（医疗）/ telecom（通讯费）/ tuition（学费）/ other（其他）
2. 提取关键信息：供应商名称（如"携程"、"南方航空"）、地点（如"深圳"、"北京"）、时间
3. 生成文件夹名称：格式为"年份_类型_关键信息"，如"2025_携程酒店订单"、"2025_南方航空行程单"、"2025_移动话费账单"
4. 生成建议的文件重命名：保留日期，添加关键标识，如"20250418_南方航空_CZ1234_深圳-北京.pdf"

请以 JSON 格式返回：
{{
    "is_life_doc": true,
    "category": "hotel/flight/invoice/contract/insurance/medical/telecom/tuition/other",
    "folder_name": "2025_携程酒店订单",
    "suggested_rename": "20250418_深圳威尼斯人_入住确认.pdf",
    "year": "2025",
    "reason": "识别理由，简短说明"
}}

如果判断不是生活类文档（是课程作业等），返回：
{{"is_life_doc": false}}
"""

    messages = [{'role': 'user', 'content': prompt}]

    try:
        response = Generation.call(
            model="qwen-turbo",
            messages=messages,
            result_format='message',
            api_key=DASHSCOPE_API_KEY,
            temperature=0.1
        )

        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            try:
                result = json.loads(content)
                # 确保返回结果包含所有必要字段
                result.setdefault("is_life_doc", False)
                result.setdefault("category", "unknown")
                result.setdefault("folder_name", "")
                result.setdefault("suggested_rename", "")
                result.setdefault("year", year)
                result.setdefault("reason", "")
                return result
            except json.JSONDecodeError:
                match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                if match:
                    result = json.loads(match.group(0))
                    result.setdefault("is_life_doc", False)
                    result.setdefault("category", "unknown")
                    result.setdefault("folder_name", "")
                    result.setdefault("suggested_rename", "")
                    result.setdefault("year", year)
                    return result
        else:
            print(f"AI 解析失败，状态码: {response.status_code}, 错误信息: {response.message}")

    except Exception as e:
        print(f"AI 解析失败: {e}")

    return {
        "is_life_doc": False,
        "category": "unknown",
        "folder_name": "",
        "suggested_rename": "",
        "year": year
    }
