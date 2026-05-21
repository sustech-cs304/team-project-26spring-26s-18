"""
AI Parser - 百炼大模型意图解析兜底模块

当规则解析失败或结果不可信时，调用百炼AI进行意图理解。
"""
import json
import os
import re
from typing import Dict, Optional

# 百炼 API Key（优先读环境变量，fallback 到硬编码）
DASHSCOPE_API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY",
    "sk-446b58d9cfc5424aade01a05e396f13c"
)

# 可用的模型列表（按推荐顺序）
MODELS = {
    "qwen_turbo": "qwen-turbo",          # 最快最便宜
    "qwen_plus": "qwen-plus",             # 更准确
    "qwen_max": "qwen-max",              # 最强（贵）
}

SYSTEM_PROMPT = """你是一个文件管理助手的意图解析器。
用户会用自然语言描述文件操作需求，你需要将其解析为结构化的JSON。

输出必须是纯JSON，不要有任何其他文字或markdown标记。

JSON格式：
{
  "action": "search" | "move" | "copy" | "delete" | "rename" | "organize" | "clean" | "analyze",
  "source": "路径或null",
  "target": "目标路径或null",
  "filters": [
    {"type": "extension", "value": [".pdf", ".docx"]},
    {"type": "name_contains", "value": "关键词"},
    {"type": "size", "min": 字节数, "max": 字节数},
    {"type": "date", "days_ago": 天数},
    {"type": "temp", "value": true},
    {"type": "empty", "value": true}
  ],
  "params": {
    "recursive": true/false,
    "organize_mode": "type" | "date" | "size" | "month" | "year",
    "prefix": "前缀字符串",
    "suffix": "后缀字符串",
    "numbering": true/false
  },
  "confidence": 0.0~1.0,
  "summary": "用中文一句话描述理解结果"
}

action 说明：
- search: 搜索/查找/列出文件
- move: 移动/转移/搬到/放到
- copy: 复制/拷贝/备份
- delete: 删除/删掉/移除/清理
- rename: 重命名/改名/加前缀/加后缀/编号
- organize: 整理/分类/按类型/按日期归档
- clean: 清理临时文件/垃圾文件/空文件/旧文件
- analyze: 分析/统计/查看目录信息

注意：
1. filters 数组可以为空
2. 数值单位：1KB=1024, 1MB=1048576, 1GB=1073741824
3. confidence 表示你对解析结果的信心，0.0~1.0
4. 如果用户说"所有文件"，filters 为空数组
5. source 如果未指定，输出 null（后续使用当前目录）
"""

def ai_parse(text: str, model: str = "qwen_turbo") -> Optional[Dict]:
    """
    调用百炼AI解析用户意图
    
    Args:
        text: 用户输入的自然语言
        model: 使用的模型，可选 qwen_turbo / qwen_plus / qwen_max
        
    Returns:
        解析结果字典，失败返回 None
    """
    try:
        import dashscope
        from dashscope import Generation
    except ImportError:
        print("[AI Parser] dashscope 未安装，请运行: pip install dashscope")
        return None

    dashscope.api_key = DASHSCOPE_API_KEY
    model_name = MODELS.get(model, "qwen-turbo")

    try:
        response = Generation.call(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"用户说：{text}"}
            ],
            result_format="message",
            max_tokens=500,
            temperature=0.1,  # 低温度，更确定
        )

        if response.status_code != 200:
            print(f"[AI Parser] API调用失败: {response.code} - {response.message}")
            return None

        content = response.output.choices[0].message.content

        # 提取 JSON（可能包含 markdown 代码块）
        json_str = _extract_json(content)
        if not json_str:
            print(f"[AI Parser] 无法从返回结果中提取JSON: {content}")
            return None

        result = json.loads(json_str)

        # 规范化结果
        result = _normalize_result(result, text)
        return result

    except Exception as e:
        print(f"[AI Parser] 解析失败: {e}")
        return None


def _extract_json(text: str) -> Optional[str]:
    """从返回文本中提取JSON字符串"""
    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)

    # 尝试直接找 JSON
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)

    return None


def _normalize_result(result: Dict, original_text: str) -> Dict:
    """规范化AI返回的结果，确保格式一致"""
    # 确保必要字段存在
    normalized = {
        "original": original_text,
        "action": result.get("action", "search"),
        "source": result.get("source"),
        "target": result.get("target"),
        "filters": result.get("filters", []),
        "params": result.get("params", {}),
        "confidence": result.get("confidence", 0.8),
        "summary": result.get("summary", ""),
        "parser": "ai",  # 标记来源
    }

    # 规范化 filters
    normalized["filters"] = _normalize_filters(normalized["filters"])

    # 规范化 action
    action_map = {
        "搜索": "search", "查找": "search", "找": "search",
        "移动": "move", "移到": "move", "搬": "move",
        "复制": "copy", "拷贝": "copy",
        "删除": "delete", "清理": "clean",
        "重命名": "rename", "改名": "rename",
        "整理": "organize", "分类": "organize",
        "分析": "analyze", "统计": "analyze",
    }
    action = normalized["action"]
    normalized["action"] = action_map.get(action, action)

    return normalized


def _normalize_filters(filters: list) -> list:
    """规范化 filters 列表"""
    normalized = []
    for f in filters:
        if not isinstance(f, dict):
            continue
        ftype = f.get("type", "")
        # 确保 type 值规范
        type_map = {
            "extension": "extension", "ext": "extension",
            "name_contains": "name_contains", "name": "name_contains", "关键词": "name_contains",
            "size": "size", "大小": "size",
            "date": "date", "时间": "date",
            "temp": "temp", "临时": "temp",
            "empty": "empty", "空": "empty",
        }
        f["type"] = type_map.get(ftype, ftype)
        normalized.append(f)
    return normalized


def test_ai_parse():
    """测试AI解析功能"""
    test_cases = [
        "把上周改过的Word文档移到归档文件夹",
        "找出所有大于100MB的视频文件",
        "给所有PDF文件加上今天的日期前缀",
        "按文件类型整理桌面",
        "清理下载文件夹里超过30天的临时文件",
        "把文件名里的空格都换成下划线",
    ]

    print("=" * 60)
    print("AI 意图解析测试")
    print("=" * 60)

    for text in test_cases:
        print(f"\n输入: {text}")
        result = ai_parse(text)
        if result:
            print(f"  [OK] action: {result['action']}")
            print(f"  filters: {result['filters']}")
            print(f"  params: {result['params']}")
            print(f"  summary: {result['summary']}")
            print(f"  confidence: {result['confidence']}")
        else:
            print("  [FAIL] 解析失败")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_ai_parse()
