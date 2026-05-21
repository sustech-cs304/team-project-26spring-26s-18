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
DASHSCOPE_API_KEY = "sk-66bfacdf2a9a49dc9c7cf6ff4e537eef"
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

    from datetime import date
    today = date.today().isoformat()  # 例如 "2026-05-21"

    prompt = f"""你是文件管理助手。今天日期：{today}。用户说："{user_input}"

请分析用户意图，返回结构化的JSON：

## 单动作命令
如果用户只说了一件事，返回：
{{
  "action": "操作类型，见下方列表",
  "source": "源路径（相对路径或绝对路径，省略则为当前目录）",
  "target": "目标路径（如移动/复制到某处）",
  "filters": [
    {{
      "type": "extension | name_contains | content_contains | name_pattern | size | modified",
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

## 关键词扩展规则（重要！）
**无论用户找的是学术话题还是生活文件类型，只要是在找"与XX有关的文件"，一律使用 content_contains + 关键词扩展！**

触发条件（以下任意一种均触发）：
- "XX相关文件"、"关于XX的文件"、"XX有关的"
- "找所有XX"、"找一下XX"（XX是主题词而非具体文件名）
- "行程单"、"发票"、"合同"、"机票"等文件类型词

此时你必须：
1. 使用 filter type = "content_contains"（不是 name_contains）
2. 把用户说的主题扩展到多个关键词（value 用数组），**5-10个关键词**，包括：
   - 中文原词
   - **英文翻译（必填！学校是英文教学，课件/资料大量是英文）**
   - 核心相关术语（中英文各半，确保中英文资料都能搜到）
   - 同义表达

**唯一使用 name_contains 的情形：用户明确说"文件名包含XX"、"名字叫XX的文件"。**

关键词扩展示例：
- "区块链" → ["区块链","blockchain","智能合约","分布式账本","共识机制","比特币","以太坊","去中心化"]
- "机器学习" → ["机器学习","machine learning","深度学习","神经网络","训练","模型","分类","回归"]
- "操作系统" → ["操作系统","operating system","进程","线程","内存管理","文件系统","调度","死锁"]
- "数据库" → ["数据库","database","SQL","MySQL","PostgreSQL","索引","事务","查询优化"]
- "前端" → ["前端","frontend","React","Vue","JavaScript","CSS","HTML","组件"]
- "行程单" → ["行程单","机票","航班","Booking","Confirmation","Itinerary","flight","E-ticket","boarding pass","出行"]
- "发票" → ["发票","invoice","收据","receipt","报销","税务","开票","金额","付款"]
- "合同" → ["合同","contract","协议","agreement","签约","甲方","乙方","条款"]
- "人工智能" → ["人工智能","AI","artificial intelligence","神经网络","深度学习","GPT","大模型","NLP","计算机视觉"]
- "微积分" → ["微积分","calculus","导数","积分","极限","微分","求导","定积分"]

## delete 操作规则（重要！）
- 用户指定了要删什么文件（有过滤条件）→ 把条件放 filters，**source 设为文件所在目录**，不要把要删的文件名放进 source
- 用户要删某个目录 → source 设为该目录，filters 为空
- 用户要删空文件夹/空目录 → params 里加 `"delete_mode": "empty_dirs"`，filters 为空

示例：
命令："删除 期中.pdf"
返回：{{"action":"delete","source":".","target":"","filters":[{{"type":"name_contains","value":"期中"}},{{"type":"extension","value":["pdf"]}}],"params":{{}},"summary":"删除名为期中的PDF文件"}}

命令："删除 downloads 文件夹"
返回：{{"action":"delete","source":"downloads","target":"","filters":[],"params":{{}},"summary":"删除downloads目录"}}

命令："清理所有空文件夹"
返回：{{"action":"delete","source":".","target":"","filters":[],"params":{{"delete_mode":"empty_dirs"}},"summary":"删除所有空目录"}}

## 注意事项
- 扩展名不要加点号，如 "txt" 不是 ".txt"
- 大小描述：如"大于100MB"→ filters.type="size", value="100MB"
- **日期过滤规则（重要！今天日期已告知，请自行计算具体日期）**：
  - 使用 `filters.type = "modified"`，**必须用 before/after 字段**，不要用 value
  - "2025年前的文件" → `{{"type":"modified","before":"2025-01-01"}}`
  - "2023年的文件" → `{{"type":"modified","after":"2023-01-01","before":"2024-01-01"}}`
  - "去年的文件" → `{{"type":"modified","after":"2025-01-01","before":"2026-01-01"}}`
  - "最近3个月的文件" → `{{"type":"modified","after":"2026-02-21"}}`（从today往前推）
  - "30天前的文件" → `{{"type":"modified","before":"2026-04-21"}}`（today减30天）
- clean 操作必须在 params 里返回 clean_mode 和 days（今天日期已告知，请自行计算）：
  - 清理临时文件/垃圾文件 → `"clean_mode":"temp"`
  - 清理空文件 → `"clean_mode":"empty_files"`
  - 清理空文件夹/空目录 → `"clean_mode":"empty_dirs"`
  - 清理N天前/某年前的文件 → `"clean_mode":"old", "days": <从今天起往前推的天数>`
  - 例："清理2025年以前的文件"，今天2026-05-21 → days = 506（2026-05-21 到 2025-01-01 的天数）
  - 例："清理30天前的文件" → days = 30
  - 例："清理上个月以前的文件"，今天2026-05-21 → days = 51（到2026-04-01）
- 常见多动作模式：
  - "新建X文件夹，然后把Y里的文件复制到X" → mkdir + copy
  - "把A中的文件移到B" → mkdir + move
  - "找到所有pdf，然后删除" → search + delete
- 判断标准：只要命令中出现了表示顺序的连接词（然后、接着、再、先后、最后、把），一律用 actions 数组格式
- 如果无法确定，返回 action=null 并在 summary 里说明
- **重命名规则**：rename 时 source=原路径，target=新名称（不是完整路径）
  - 示例："把名为PDF的文件夹改名为BBF" → source="PDF", target="BBF"
  - 示例："rename D:/file_helper_demo/PDF BBF" → source="D:/file_helper_demo/PDF", target="BBF"

## content_contains 使用场景与示例
只有当用户在寻找"主题相关的文件"时才用 content_contains。如果用户明确在找文件名中包含某个词的文件（如"文件名包含期中"），仍用 name_contains。

## recursive 规则
- 默认 recursive=false，只搜索当前目录
- 只有用户**明确说**"递归"、"所有子文件夹"、"包含子目录"、"全部文件夹"时，才设置 recursive=true
- "所有文件"、"找所有XX"等泛泛表达**不代表**递归，仍用 recursive=false

命令："找到所有区块链相关文件"
返回：{{"action":"search","source":".","target":"","filters":[{{"type":"content_contains","value":["区块链","blockchain","智能合约","分布式账本","共识机制","比特币","以太坊","去中心化"]}}],"params":{{"recursive":false}},"summary":"搜索内容与区块链主题相关的文件"}}

命令："递归搜索所有区块链相关文件"
返回：{{"action":"search","source":".","target":"","filters":[{{"type":"content_contains","value":["区块链","blockchain","智能合约","分布式账本","共识机制","比特币","以太坊","去中心化"]}}],"params":{{"recursive":true}},"summary":"递归搜索内容与区块链主题相关的文件"}}

命令："找机器学习相关的资料"
返回：{{"action":"search","source":".","target":"","filters":[{{"type":"content_contains","value":["机器学习","machine learning","深度学习","神经网络","训练","模型"]}}],"params":{{"recursive":false}},"summary":"搜索内容与机器学习相关的文件"}}

命令："在所有子文件夹中找机器学习相关的资料"
返回：{{"action":"search","source":".","target":"","filters":[{{"type":"content_contains","value":["机器学习","machine learning","深度学习","神经网络","训练","模型"]}}],"params":{{"recursive":true}},"summary":"递归搜索内容与机器学习相关的文件"}}

命令："关于操作系统的文件"
返回：{{"action":"search","source":".","target":"","filters":[{{"type":"content_contains","value":["操作系统","operating system","进程","线程","内存管理","文件系统"]}}],"params":{{"recursive":false}},"summary":"搜索内容与操作系统相关的文件"}}

命令："找到所有的行程单"
返回：{{"action":"search","source":".","target":"","filters":[{{"type":"content_contains","value":["行程单","机票","航班","Booking","Confirmation","Itinerary","flight","E-ticket","boarding pass","出行"]}}],"params":{{"recursive":false}},"summary":"搜索内容与行程单主题相关的文件"}}

命令："找一下发票"
返回：{{"action":"search","source":".","target":"","filters":[{{"type":"content_contains","value":["发票","invoice","收据","receipt","报销","税务","开票","金额"]}}],"params":{{"recursive":false}},"summary":"搜索内容与发票相关的文件"}}

命令："把区块链相关的文件移到归档"
返回：{{"actions":[{{"action":"mkdir","source":"","target":"归档","filters":[],"params":{{}}}},{{"action":"move","source":".","target":"归档","filters":[{{"type":"content_contains","value":["区块链","blockchain","智能合约","分布式账本"]}}],"params":{{"recursive":false}}}}],"summary":"创建归档目录并移动区块链相关文件"}}

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
        print("[DEBUG] 未找到 API Key")
        return None
    try:
        response = Generation.call(
            model=MODEL,
            prompt=prompt,
            api_key=api_key,
            result_format="message",
        )
        if response.status_code != 200:
            print(f"[DEBUG] API 返回错误: status={response.status_code}, body={response}")
            return None
        content = response.output["choices"][0]["message"]["content"]
        return content
    except Exception as e:
        print(f"[DEBUG] API 调用异常: {e}")
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
        print("[DEBUG] API 返回内容为空")
        return None

    json_str = _extract_json(content)
    if not json_str:
        print(f"[DEBUG] 无法从以下内容提取 JSON:\n{content[:500]}")
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

        entry = {"type": ftype, "value": val}
        # 保留 modified 类型的 before/after 字段
        if ftype in ("modified", "date"):
            if "before" in f:
                entry["before"] = f["before"]
            if "after" in f:
                entry["after"] = f["after"]
        normalized.append(entry)

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
