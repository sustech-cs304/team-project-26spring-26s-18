"""
纯 AI 意图解析器（无规则匹配）

将所有意图理解完全交给百炼大模型。
作为与规则解析器的对比方案。

特点：
- 无任何硬编码关键词
- 能理解任意自然语言表达
- 依赖网络和API，速度较慢（~1-2秒/次）

使用方式：
    from file_helper.ai_only_parser import AIOnlyParser

    parser = AIOnlyParser()
    plan = parser.parse("把大于100MB的视频移到归档")
"""

import json
import os
from typing import Dict, Optional

import dashscope
from dashscope import Generation

# API 配置
DASHSCOPE_API_KEY = "sk-446b58d9cfc5424aade01a05e396f13c"
MODEL = "qwen-turbo"


def _build_prompt(user_input: str) -> str:
    """构建提示词，把支持的关键词注入给AI"""

    # 可用的文件类型及扩展名（让AI知道我们支持哪些）
    file_types = {
        "图片": ["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "ico"],
        "视频": ["mp4", "avi", "mkv", "mov", "wmv", "flv", "webm"],
        "音频": ["mp3", "wav", "flac", "aac", "ogg", "m4a"],
        "文档": ["doc", "docx", "pdf", "txt", "rtf", "odt", "ppt", "pptx", "xls", "xlsx"],
        "压缩包": ["zip", "rar", "7z", "tar", "gz"],
        "代码": ["py", "java", "js", "ts", "cpp", "c", "h", "html", "css", "json", "xml", "yaml", "yml", "md"],
    }

    # 可用的操作类型
    actions = {
        "search": "搜索/查找文件",
        "move": "移动文件到指定目录",
        "copy": "复制文件到指定目录",
        "delete": "删除文件",
        "rename": "重命名文件",
        "organize": "整理/分类文件",
        "clean": "清理文件（如重复文件、空文件）",
        "analyze": "分析文件（如统计大小、类型分布）",
        "archive": "归档文件",
    }

    # 时间相关词汇
    time_words = ["今天", "昨天", "前天", "本周", "上周", "本月", "上月", "今年", "去年"]

    # 大小相关词汇
    size_words = ["大于", "小于", "不超过", "不少于", "超过", "小于等于"]

    ft_lines = "\n".join(f"  {k}: {', '.join(v)}" for k, v in file_types.items())
    action_lines = "\n".join(f"  {k}: {v}" for k, v in actions.items())

    # 多动作时额外需要的操作类型
    extra_actions = {
        "mkdir": "创建目录/文件夹",
    }

    extra_lines = "\n".join(f"  {k}: {v}" for k, v in extra_actions.items())

    prompt = f"""你是文件管理助手。用户说："{user_input}"

请分析用户意图，返回结构化的JSON：

## 单动作命令
如果用户只说了一件事，返回：
{{
  "action": "操作类型，见下方列表",
  "source": "源路径（相对路径或绝对路径，省略则为当前目录）",
  "target": "目标路径（如移动/复制到某处）",
  "filters": [
    {{
      "type": "extension | name_contains | name_pattern | size | modified",
      "value": "具体值"
    }}
  ],
  "params": {{
    "dry": false,
    "recursive": false,
    "time_range": "时间范围描述"
  }},
  "summary": "一句话描述你理解到的操作"
}}

## 多动作命令
如果用户说了多个步骤（包含"然后"、"接着"、"再"、"先...再..."、"把"等连接词），必须返回：
{{
  "actions": [
    {{"action": "第一个动作", "source": "路径", "target": "路径", "filters": [], "params": {{}}}},
    {{"action": "第二个动作", "source": "路径", "target": "路径", "filters": [], "params": {{}}}}
  ],
  "summary": "一句话描述所有操作"
}}

## 示例（"把"字句也是多动作）
命令："新建一个backup文件夹，然后把downloads里的pdf复制到backup"
返回：{{"actions": [{{"action":"mkdir","source":"","target":"backup","filters":[],"params":{{}}}},{{"action":"copy","source":"downloads","target":"backup","filters":[{{"type":"extension","value":"pdf"}}],"params":{{}}}}],"summary":"新建backup并复制pdf"}}

命令："把abc中的文件移到xyz"
返回：{{"actions": [{{"action":"mkdir","source":"","target":"xyz","filters":[],"params":{{}}}},{{"action":"move","source":"abc","target":"xyz","filters":[],"params":{{}}}}],"summary":"新建xyz并移动abc的文件"}}

命令："新建一个photo文件夹，把照片都放进去"
返回：{{"actions": [{{"action":"mkdir","source":"","target":"photo","filters":[],"params":{{}}}},{{"action":"move","source":".","target":"photo","filters":[{{"type":"extension","value":"jpg,jpeg,png,gif,webp,bmp,svg"}}],"params":{{}}}}],"summary":"新建photo并移动照片文件"}}

命令："把视频都移到archive"
返回：{{"actions": [{{"action":"mkdir","source":"","target":"archive","filters":[],"params":{{}}}},{{"action":"move","source":".","target":"archive","filters":[{{"type":"extension","value":"mp4,avi,mkv,mov,wmv,flv,webm"}}],"params":{{}}}}],"summary":"新建archive并移动视频文件"}}

命令："把所有pdf整理到一个文件夹"
返回：{{"actions": [{{"action":"mkdir","source":"","target":"pdf_整理","filters":[],"params":{{}}}},{{"action":"move","source":".","target":"pdf_整理","filters":[{{"type":"extension","value":"pdf"}}],"params":{{}}}}],"summary":"新建pdf_整理并移动pdf文件"}}

命令："按课程整理downloads"
返回：{{"actions": [{{"action":"organize","source":"downloads","target":"downloads","filters":[],"params":{{"organize_mode":"course"}}}}],"summary":"按课程分类整理文件"}}

命令："把下载的文件按学科分类"
返回：{{"actions": [{{"action":"organize","source":"downloads","target":"downloads","filters":[],"params":{{"organize_mode":"course"}}}}],"summary":"按学科分类整理文件"}}

命令："按月份整理downloads"
返回：{{"actions": [{{"action":"organize","source":"downloads","target":"downloads","filters":[],"params":{{"organize_mode":"month"}}}}],"summary":"按月份分类整理文件"}}

命令："把文件按日期分类"
返回：{{"actions": [{{"action":"organize","source":".","target":".","filters":[],"params":{{"organize_mode":"month"}}}}],"summary":"按月份分类整理文件"}}

命令："按年份分类"
返回：{{"actions": [{{"action":"organize","source":".","target":".","filters":[],"params":{{"organize_mode":"year"}}}}],"summary":"按年份分类整理文件"}}

命令："按月份整理这个文件夹"
返回：{{"actions": [{{"action":"organize","source":".","target":".","filters":[],"params":{{"organize_mode":"month"}}}}],"summary":"按月份分类整理文件"}}

命令："按日期整理"
返回：{{"actions": [{{"action":"organize","source":".","target":".","filters":[],"params":{{"organize_mode":"month"}}}}],"summary":"按月份分类整理文件"}}

命令："创建一个文件夹叫行程单，然后把所有机票行程单放进去"
返回：{{"actions": [{{"action":"mkdir","source":"","target":"行程单","filters":[],"params":{{}}}},{{"action":"move","source":".","target":"行程单","filters":[{{"type":"name_contains","value":"机票行程单"}},{{"type":"name_contains","value":"机票出行单"}},{{"type":"name_contains","value":"机票"}},{{"type":"name_contains","value":"Booking"}},{{"type":"name_contains","value":"Confirmation"}},{{"type":"name_contains","value":"Itinerary"}}],"params":{{}}}}],"summary":"创建行程单文件夹并移动机票行程单文件"}}

命令："新建一个pdf文件夹，把所有pdf整理进去"
返回：{{"actions": [{{"action":"mkdir","source":"","target":"pdf","filters":[],"params":{{}}}},{{"action":"move","source":".","target":"pdf","filters":[{{"type":"extension","value":"pdf"}}],"params":{{}}}}],"summary":"新建pdf文件夹并移动pdf文件"}}

命令："把所有文件按课程归类"
返回：{{"actions": [{{"action":"organize","source":".","target":".","filters":[],"params":{{"organize_mode":"course"}}}}],"summary":"按课程分类整理文件"}}

## 支持的文件类型（扩展名）
{ft_lines}

## 支持的操作（单动作）
{action_lines}

## 支持的操作（多动作额外）
{extra_lines}

## 注意事项
- 扩展名不要加点号，如 "txt" 不是 ".txt"
- 时间描述：如"上周"→ params.time_range="上周"
- 大小描述：如"大于100MB"→ filters.type="size", value="100MB"
- 常见多动作模式：
  - "新建X文件夹，然后把Y里的文件复制到X" → mkdir + copy
  - "把A中的文件移到B" → mkdir + move
  - "找到所有pdf，然后删除" → search + delete
- 判断标准：只要命令中出现了表示顺序的连接词（然后、接着、再、先后、最后、把），一律用 actions 数组格式
- 如果无法确定，返回 action=null 并在 summary 里说明
- **重命名规则**：rename 时 source=原路径，target=新名称（不是完整路径）
  - 示例："把名为PDF的文件夹改名为BBF" → source="PDF", target="BBF"
  - 示例："rename D:/file_helper_demo/PDF BBF" → source="D:/file_helper_demo/PDF", target="BBF"

请直接返回JSON，不要其他文字："""

    return prompt


def _split_ba_construction(user_input: str) -> list:
    """
    检测中文"把"字句并拆分成多个子命令。
    例如："新建abc文件夹，把name里的文件复制到abc"
      → ["新建abc文件夹", "把name里的文件复制到abc"]

    注意：多动作命令交给 AI 统一处理（_build_prompt 已支持识别"然后"等连接词），
    此函数只处理纯"把"字句（无连接词）的情况。
    """
    import re

    ba_patterns = [
        r"^(.+?)，\s*把(.+)$",
    ]
    for pattern in ba_patterns:
        m = re.match(pattern, user_input)
        if m:
            part1, part2 = m.group(1).strip(), m.group(2).strip()
            create_verbs = ["新建", "创建", "新建一个", "创建一个", "建一个", "建立一个"]
            if any(part1.startswith(v) for v in create_verbs):
                return [part1, part2]

    return []


def _call_api(prompt: str) -> Optional[str]:
    api_key = DASHSCOPE_API_KEY or os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return None
    try:
        response = Generation.call(
            model=MODEL,
            prompt=prompt,
            api_key=api_key,
            result_format="message",
        )
        if response.status_code != 200:
            return None
        return response.output["choices"][0]["message"]["content"]
    except Exception:
        return None


def _resolve_source_path(source: str, workspace: str = None) -> str:
    """
    将 AI 返回的 source 路径按 workspace 隔离。
    如果 workspace 设置了，"downloads"/"桌面" 等别名会映射到 workspace 下的子目录。
    """
    if not workspace:
        return source

    import os
    # 别名映射表
    alias_map = {
        "downloads": "downloads",
        "Downloads": "downloads",
        "下载": "downloads",
        "桌面": "桌面",
        "Desktop": "桌面",
        "文档": "文档",
        "Documents": "文档",
    }
    alias = alias_map.get(source)
    if alias:
        return os.path.join(workspace, alias)
    # 如果是当前目录
    if source in (".", "", "当前目录", "当前文件夹", "这里"):
        return workspace
    return source


def ai_only_parse(user_input: str, workspace: str = None) -> Optional[Dict]:
    """
    纯 AI 解析用户输入（无规则兜底）
    """
    # 预处理："把"字句拆分 → 两次API调用分别解析
    parts = _split_ba_construction(user_input)
    if parts and len(parts) == 2:
        content1 = _call_api(_build_prompt(parts[0]))
        content2 = _call_api(_build_prompt(parts[1]))
        if content1 and content2:
            try:
                json1 = json.loads(_extract_json(content1))
                json2 = json.loads(_extract_json(content2))

                def normalize(act):
                    filters = _normalize_filters(act.get("filters", []))
                    return {
                        "action": act.get("action"),
                        "source": _resolve_source_path(act.get("source", ""), workspace),
                        "target": act.get("target"),
                        "filters": filters,
                        "params": act.get("params", {}),
                    }

                return {
                    "original": user_input,
                    "actions": [normalize(json1), normalize(json2)],
                    "action": None,
                    "summary": f"{json1.get('summary', '')}，然后{json2.get('summary', '')}",
                    "parser": "ai_only",
                }
            except Exception as e:
                print(f"[AI Parser] 把字句拆分解析失败: {e}，回退整体解析")

    # 常规解析
    content = _call_api(_build_prompt(user_input))
    if not content:
        return None

    json_str = _extract_json(content)
    if not json_str:
        return None

    result = json.loads(json_str)

    if "actions" in result and result["actions"]:
        actions = []
        for act in result["actions"]:
            filters = _normalize_filters(act.get("filters", []))
            actions.append({
                "action": act.get("action"),
                "source": _resolve_source_path(act.get("source", ""), workspace),
                "target": act.get("target"),
                "filters": filters,
                "params": act.get("params", {}),
            })
        return {
            "original": user_input,
            "actions": actions,
            "action": None,
            "summary": result.get("summary", ""),
            "parser": "ai_only",
        }

    filters = _normalize_filters(result.get("filters", []))
    return {
        "original": user_input,
        "action": result.get("action"),
        "source": _resolve_source_path(result.get("source", ""), workspace),
        "target": result.get("target"),
        "filters": filters,
        "params": result.get("params", {}),
        "summary": result.get("summary", ""),
        "parser": "ai_only",
    }


def _normalize_filters(filters: list) -> list:
    """
    标准化过滤器值，兼容 AI 返回的各种格式

    处理以下情况：
    - extension: "jpg,jpeg,png"（逗号分隔字符串）→ ["jpg", "jpeg", "png"]
    - extension: "txt"（单字符串）→ ["txt"]
    - value 已在嵌套 dict 里 → 提取出来
    """
    if not filters:
        return []

    normalized = []
    for f in filters:
        ftype = f.get("type", "")
        val = f.get("value", "")

        # 处理嵌套的 {"value": ...} 结构
        if isinstance(val, dict) and "value" in val:
            val = val["value"]

        # 标准化 extension 类型：字符串→列表
        if ftype == "extension":
            if isinstance(val, str):
                # 可能是逗号分隔，也可能AI返回了列表的JSON字符串
                val = [v.strip().lower().lstrip(".") for v in val.split(",") if v.strip()]
            elif isinstance(val, list):
                val = [v.strip().lower().lstrip(".") if isinstance(v, str) else str(v) for v in val]

        normalized.append({"type": ftype, "value": val})

    return normalized


def _extract_json(text: str) -> Optional[str]:
    """从文本中提取 JSON（处理 markdown 代码块等情况）"""
    text = text.strip()

    # 去掉 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])  # 去掉第一行 ```
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    # 尝试直接解析
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 尝试找到 JSON 对象
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    return None


class AIOnlyParser:
    """纯 AI 解析器封装"""

    def parse(self, text: str, workspace: str = None) -> Dict:
        result = ai_only_parse(text, workspace=workspace)
        if result is None:
            return {
                "original": text,
                "action": None,
                "source": None,
                "target": None,
                "filters": [],
                "params": {},
                "summary": "AI解析失败",
                "parser": "ai_only",
            }
        return result
