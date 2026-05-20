"""
推荐资源工具：网络搜索 + RAG 知识库检索
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import asyncio
import json
import os
import re
import urllib.parse
from functools import partial

import httpx
from openai import OpenAI

# 项目根目录路径（用于检查文件是否存在）
PROJECT_ROOT = Path(__file__).parent.parent.parent
CAMPUS_DOCS_DIR = PROJECT_ROOT / "campus_docs"

print(f"[recommend_resources_util] CAMPUS_DOCS_DIR: {CAMPUS_DOCS_DIR}")
print(f"[recommend_resources_util] CAMPUS_DOCS_DIR exists: {CAMPUS_DOCS_DIR.exists()}")


# 课程名称到代码的映射（用于语义理解）
COURSE_NAME_MAPPING = {
    "计算理论导论": ["CS338", "CS 338"],
    "软件工程": ["CS304", "CS 304", "CS409", "CS 409"],
    "人工智能": ["CS303", "CS 303", "CS303B"],
    "计算机网络": ["CS305", "CS 305", "CS305B"],
    "数据挖掘": ["CS306", "CS 306"],
    "数据库": ["CS307", "CS 307"],
    "计算机视觉": ["CS308", "CS 308"],
    "操作系统": ["CS202", "CS 202", "CS302"],
    "数据结构": ["CS203", "CS 203"],
    "算法": ["CS201", "CS 201"],
    "程序设计": ["CS101", "CS 101", "CS102", "CS 102"],
    "计算机系统": ["CS110", "CS 110"],
}

# 反向映射：代码到课程名
COURSE_CODE_TO_NAME = {}
for name, codes in COURSE_NAME_MAPPING.items():
    for code in codes:
        COURSE_CODE_TO_NAME[code.lower().replace(" ", "")] = name


def extract_course_codes(query: str) -> Set[str]:
    """从查询中提取课程代码（如CS338）和课程名称"""
    codes = set()
    query_lower = query.lower()

    # 1. 直接匹配课程代码格式（CSxxx, CS xxx, csxxx）
    code_pattern = r'\b(cs)\s*(\d{3}[a-z]?)\b'
    matches = re.findall(code_pattern, query_lower)
    for _, num in matches:
        codes.add(f"cs{num}")

    # 2. 匹配课程名称关键词
    for course_name, course_codes in COURSE_NAME_MAPPING.items():
        if course_name.lower() in query_lower:
            # 添加该课程的所有代码变体
            for code in course_codes:
                codes.add(code.lower().replace(" ", ""))
            # 同时添加课程名本身作为匹配依据
            codes.add(course_name.lower())

    return codes


def calculate_course_match_score(filename: str, query_codes: Set[str]) -> float:
    """计算文件名与查询课程代码的匹配分数"""
    if not query_codes:
        return 0.0

    filename_lower = filename.lower()
    score = 0.0

    for code in query_codes:
        code_clean = code.replace(" ", "")
        # 精确匹配课程代码（如CS338）
        if code_clean in filename_lower:
            # 越靠前的匹配越重要
            if filename_lower.startswith(code_clean):
                score += 0.5  # 开头匹配（如CS338-Slides.pdf）
            else:
                score += 0.3  # 包含匹配

        # 课程名称匹配（如"计算理论导论"）
        if code in COURSE_NAME_MAPPING:
            for course_code in COURSE_NAME_MAPPING[code]:
                if course_code.lower().replace(" ", "") in filename_lower:
                    score += 0.4

    return min(score, 1.0)  # 最高1.0


def expand_query_with_course_info(query: str) -> str:
    """扩展查询，添加课程代码信息以增强检索"""
    codes = extract_course_codes(query)
    if not codes:
        return query

    # 将提取到的课程代码添加到查询中
    code_list = sorted(codes)
    expanded = f"{query} {' '.join(code_list)}"
    return expanded


# 国内可访问平台搜索（无需翻墙）
_DOMESTIC_SEARCH_PLATFORMS = [
    ("哔哩哔哩", "https://search.bilibili.com/all?keyword={q}"),
    ("知乎", "https://www.zhihu.com/search?type=content&q={q}"),
    ("CSDN", "https://so.csdn.net/so/search?q={q}"),
    ("中国大学MOOC", "https://www.icourse163.org/search/{q}"),
    ("百度", "https://www.baidu.com/s?wd={q}"),
]


def search_web_domestic(query: str, max_items: int = 5) -> List[Dict[str, Any]]:
    """聚合国内平台搜索链接（无搜索 API 时的降级方案）。"""
    q = (query or "").strip()
    if not q:
        return []
    encoded = urllib.parse.quote(q)
    out: List[Dict[str, Any]] = []
    for platform, url_tpl in _DOMESTIC_SEARCH_PLATFORMS[:max_items]:
        out.append(
            {
                "title": f"在{platform}搜索：{q}",
                "url": url_tpl.format(q=encoded),
                "snippet": f"国内平台检索「{q}」，点击前往{platform}查看结果。",
                "source": "domestic-search-fallback",
                "platform": platform,
                "is_specific_url": False,
            }
        )
    return out


_PLATFORM_URL_TEMPLATES = {
    "bilibili": ("哔哩哔哩", "https://search.bilibili.com/all?keyword={q}"),
    "zhihu": ("知乎", "https://www.zhihu.com/search?type=content&q={q}"),
    "csdn": ("CSDN", "https://so.csdn.net/so/search?q={q}"),
    "icourse163": ("中国大学MOOC", "https://www.icourse163.org/search/{q}"),
    "mooc": ("中国大学MOOC", "https://www.icourse163.org/search/{q}"),
    "baidu": ("百度", "https://www.baidu.com/s?wd={q}"),
}


def search_web_domestic_from_plan(plan: Dict[str, Any], max_items: int = 5) -> List[Dict[str, Any]]:
    """根据 Agent 搜索计划生成国内平台搜索链接（API 不可用时的降级）。"""
    queries = plan.get("queries") or []
    if not queries:
        return search_web_domestic(plan.get("intent_summary") or "", max_items=max_items)

    out: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()

    for q_item in queries[:2]:
        text = (q_item.get("text") or "").strip()
        if not text:
            continue
        encoded = urllib.parse.quote(text)
        platforms = q_item.get("platforms") or ["bilibili", "zhihu"]
        for pkey in platforms[:3]:
            tpl = _PLATFORM_URL_TEMPLATES.get(str(pkey).lower())
            if not tpl:
                continue
            label, url_tpl = tpl
            url = url_tpl.format(q=encoded)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            expected = q_item.get("expected_result") or ""
            out.append(
                {
                    "title": f"{label}：{text[:40]}",
                    "url": url,
                    "snippet": expected or f"在{label}搜索「{text}」",
                    "source": "domestic-search-fallback",
                    "platform": label,
                    "is_specific_url": False,
                }
            )
            if len(out) >= max_items:
                return out
    return out[:max_items]


# Agent：规划国内网络检索（不限于关键词，可含多 query、平台、资源类型）
SEARCH_PLAN_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "plan_web_search",
            "description": "根据用户学习问题，规划在国内平台（B站、知乎、MOOC等）上的检索方案",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent_summary": {
                        "type": "string",
                        "description": "用户真实学习意图，一句话",
                    },
                    "course": {"type": "string", "description": "课程号或课名，如 CS338"},
                    "topic": {"type": "string", "description": "知识点或主题"},
                    "resource_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["video", "mooc", "article", "slides", "exercise", "exam"],
                        },
                    },
                    "queries": {
                        "type": "array",
                        "description": "1~3 条检索任务，每条针对不同检索角度",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "面向搜索引擎的查询句，精炼，勿粘贴用户整段闲聊",
                                },
                                "platforms": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": [
                                            "bilibili",
                                            "zhihu",
                                            "csdn",
                                            "icourse163",
                                            "baidu",
                                        ],
                                    },
                                },
                                "expected_result": {
                                    "type": "string",
                                    "description": "期望找到的资源类型，如期末复习视频",
                                },
                            },
                            "required": ["text", "platforms"],
                        },
                        "minItems": 1,
                        "maxItems": 3,
                    },
                    "exclude": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "应排除的无关主题",
                    },
                },
                "required": ["intent_summary", "queries"],
            },
        },
    }
]


def search_web_duckduckgo(query: str, max_items: int = 8) -> List[Dict[str, Any]]:
    """兼容旧调用：改为国内平台搜索。"""
    return search_web_domestic(query, max_items=min(max_items, 5))


def categorize_file(filename: str) -> str:
    """根据文件名判断文件类别"""
    low = filename.lower()
    # 课件/教材相关
    if any(k in low for k in ['slide', 'lecture', 'l0', 'l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7', 'l8', 'l9', 'chapter', 'ch', '教材', '课件', 'ppt']):
        return "lecture"
    # 实验/作业/习题相关
    if any(k in low for k in ['lab', 'lab', 'experiment', 'assignment', 'hw', 'homework', 'exercise', 'problem', 'quiz', 'exam', 'test', '实验', '作业', '习题', '练习', '测试', '考试']):
        return "exercise"
    # 参考资料/其他
    if any(k in low for k in ['ref', 'reference', 'material', 'note', 'handout', '阅读', '参考', '资料']):
        return "reference"
    return "other"


def _file_type_from_name(src: str) -> str:
    low = src.lower()
    if low.endswith(".pdf"):
        return "pdf"
    if low.endswith(".docx"):
        return "docx"
    if low.endswith(".pptx"):
        return "pptx"
    if low.endswith(".md"):
        return "markdown"
    if low.endswith(".txt"):
        return "text"
    return "unknown"


def _build_file_info(src: str, vector_score: float, course_match_score: float, preview: str) -> Dict[str, Any]:
    combined = vector_score * 0.6 + course_match_score * 0.4 if course_match_score else vector_score
    file_type = _file_type_from_name(src)
    return {
        "source": src,
        "vector_score": round(vector_score, 4),
        "course_match_score": round(course_match_score, 4),
        "score": round(combined, 4),
        "preview": (preview or "")[:400],
        "file_type": file_type,
        "is_pdf": file_type == "pdf",
        "category": categorize_file(src),
        "file_exists": (CAMPUS_DOCS_DIR / src).exists(),
        "is_original_file": True,
        "download_url": f"/rag/download/{src}",
        "preview_url": f"/rag/preview/{src}",
    }


def _rag_recall_candidates(query: str, top_k: int = 20, min_score: float = 0.28) -> List[Dict[str, Any]]:
    """向量召回 + 按文件聚合最高分 + 可选重排序。"""
    q = (query or "").strip()
    if not q:
        return []

    query_codes = extract_course_codes(q)
    expanded_query = expand_query_with_course_info(q)
    print(f"[_rag_recall] 课程代码: {query_codes}, 扩展查询: {expanded_query}")

    try:
        from utils.rag_util import EmbeddingService, Reranker, VectorStore

        emb = EmbeddingService()
        vs = VectorStore()
        hits = vs.search(emb.embed(expanded_query), top_k=top_k)

        file_map: Dict[str, Dict[str, Any]] = {}
        for h in hits:
            src = str(h.get("source") or "unknown")
            vector_score = float(h.get("score", 0))
            preview = str(h.get("content") or "")
            course_match_score = calculate_course_match_score(src, query_codes)

            if src not in file_map or vector_score > file_map[src]["vector_score"]:
                file_map[src] = _build_file_info(src, vector_score, course_match_score, preview)
            elif vector_score == file_map[src]["vector_score"] and len(preview) > len(file_map[src].get("preview", "")):
                file_map[src]["preview"] = preview[:400]

        candidates = sorted(file_map.values(), key=lambda x: x["score"], reverse=True)
        candidates = [c for c in candidates if c["score"] >= min_score][:12]

        if len(candidates) >= 2:
            try:
                reranker = Reranker()
                rerank_input = [
                    {**c, "content": f"{c['source']}\n{c.get('preview', '')}"}
                    for c in candidates
                ]
                reranked = reranker.rerank(q, rerank_input, top_k=min(8, len(rerank_input)))
                for item in reranked:
                    if "rerank_score" in item:
                        item["score"] = round(float(item["rerank_score"]), 4)
                candidates = reranked
            except Exception as e:
                print(f"[_rag_recall] 重排序跳过: {e}")

        print(f"[_rag_recall] 候选文件 {len(candidates)} 个")
        return candidates
    except Exception as e:
        print(f"[_rag_recall] 错误: {e}")
        import traceback
        traceback.print_exc()
        return []


def _categorize_rag_files(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    categorized: Dict[str, List] = {
        "lecture": [],
        "exercise": [],
        "reference": [],
        "other": [],
        "all": [],
    }
    for f in files:
        categorized["all"].append(f)
        categorized[f["category"]].append(f)
    return categorized


def _get_llm_client() -> Optional[OpenAI]:
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def _cot_filter_rag_sync(query: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """CoT 相关性过滤：剔除向量靠前但答非所问的本地资料。"""
    if not candidates:
        return {"rag_confident": False, "relevant_indices": [], "reason": "知识库无候选文件"}

    client = _get_llm_client()
    if client is None:
        indices = [i for i, c in enumerate(candidates) if c.get("score", 0) >= 0.42]
        return {
            "rag_confident": len(indices) > 0,
            "relevant_indices": indices,
            "reason": "未配置 DASHSCOPE_API_KEY，已按相关度分数过滤",
        }

    lines = []
    for i, c in enumerate(candidates[:8]):
        lines.append(
            f"[{i}] 文件: {c.get('source', '')} | 分数: {c.get('score', 0)} | "
            f"摘要: {c.get('preview', '')[:180]}"
        )
    prompt = f"""用户问题：{query}

候选本地学习资料（按相关度排序）：
{chr(10).join(lines)}

请逐步思考：
1. 用户真正想学什么（课程/知识点/需要什么类型的资料）
2. 判断每条候选的关联性（关键规则）：
   - 【课程匹配优先】如果文件名中的课程代码/名称与用户查询的课程一致（如CS338），即使具体主题不完全重合，也应视为相关并保留
   - 课件(slides/lecture)、习题(exercise)、参考资料(reference)只要是同一课程，对用户学习都有帮助价值
   - 仅当课程完全不同且内容完全无关时才判定为不相关
   - 期末/期中复习场景下，该课程的所有资料都具有参考价值
3. 综合判断：只要有课程匹配的资料，就应当保留，不应过于严格

只输出 JSON，不要其他文字：
{{"rag_confident": true或false, "relevant_indices": [相关条目编号整数], "reason": "说明保留了哪些课程的资料及原因"}}"""

    try:
        resp = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是学习资料相关性审核助手，只输出合法 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        data = json.loads(text)
        indices = [int(i) for i in data.get("relevant_indices", []) if isinstance(i, (int, float))]
        indices = [i for i in indices if 0 <= i < len(candidates)]
        confident = bool(data.get("rag_confident")) and len(indices) > 0
        return {
            "rag_confident": confident,
            "relevant_indices": indices if confident else [],
            "reason": str(data.get("reason", "")),
        }
    except Exception as e:
        print(f"[cot_filter_rag] 失败，返回空由网络搜索兜底: {e}")
        # CoT 失败时直接返回空，由网络搜索(web)作为兜底
        return {
            "rag_confident": False,
            "relevant_indices": [],
            "reason": "本地资料相关性审核失败，将使用网络搜索补充资源",
        }


async def cot_filter_rag(query: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_cot_filter_rag_sync, query, candidates)
    )


def _fallback_search_plan(query: str) -> Dict[str, Any]:
    """无 LLM 时的搜索计划降级。"""
    codes = extract_course_codes(query)
    course = " ".join(sorted(codes)) if codes else ""
    search_text = expand_query_with_course_info(query)
    if len(search_text) > 80:
        search_text = search_text[:80]
    topic = course or search_text[:40]
    return {
        "intent_summary": query[:120],
        "course": course,
        "topic": topic,
        "queries": [
            {
                "text": search_text,
                "platforms": ["bilibili", "icourse163", "zhihu"],
                "expected_result": "课程学习视频或教程",
            }
        ],
        "exclude": [],
    }


def _plan_web_search_sync(query: str) -> Dict[str, Any]:
    """Agent 规划网络检索（function calling）。"""
    client = _get_llm_client()
    if client is None:
        return _fallback_search_plan(query)

    system = (
        "你是学习资源检索规划助手。根据用户问题制定在国内网站上的检索方案。\n"
        "要求：\n"
        "1. 理解用户真正需要什么类型的学习资源（视频、习题、MOOC 等）\n"
        "2. queries 中每条 text 应是精炼检索句，不要复制用户全部口水话\n"
        "3. 含课程号时写入 course，并体现在 query text 中\n"
        "4. 为不同角度拆分 1~3 条 queries（如：期末复习串讲、单知识点讲解）\n"
        "5. 必须调用 plan_web_search 工具返回结果"
    )

    try:
        resp = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ],
            tools=SEARCH_PLAN_TOOL,
            tool_choice={"type": "function", "function": {"name": "plan_web_search"}},
            temperature=0.2,
            max_tokens=800,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            args = json.loads(msg.tool_calls[0].function.arguments)
            if args.get("queries"):
                return args
        content = (msg.content or "").strip()
        if content:
            start, end = content.find("{"), content.rfind("}")
            if start >= 0 and end > start:
                data = json.loads(content[start : end + 1])
                if data.get("queries"):
                    return data
    except Exception as e:
        print(f"[plan_web_search] Agent 规划失败: {e}")

    return _fallback_search_plan(query)


async def plan_web_search(query: str) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_plan_web_search_sync, query))


def execute_domestic_search_sync(plan: Dict[str, Any], max_items: int = 6) -> List[Dict[str, Any]]:
    """
    按 Agent 计划调用国内搜索 API（博查），合并去重。
    无 BOCHA_API_KEY 或结果不足时，用计划中的 query 生成平台搜索链接降级。
    """
    from utils.domestic_search_api import PLATFORM_DOMAINS, bocha_web_search

    queries = plan.get("queries") or []
    if not queries:
        return search_web_domestic_from_plan(plan, max_items=max_items)

    merged: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    from utils.domestic_search_api import _DEFAULT_BOCHA_API_KEY

    api_key = os.getenv("BOCHA_API_KEY", _DEFAULT_BOCHA_API_KEY).strip()
    has_api = bool(api_key)

    if has_api:
        for q_item in queries[:2]:
            text = (q_item.get("text") or "").strip()
            if not text:
                continue
            platforms = [str(p).lower() for p in (q_item.get("platforms") or ["bilibili"])][:2]

            for pkey in platforms:
                domain = PLATFORM_DOMAINS.get(pkey)
                hits = bocha_web_search(text, count=3, include_domain=domain)
                for h in hits:
                    url = h.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        if q_item.get("expected_result"):
                            h["snippet"] = f"{q_item['expected_result']} | {h.get('snippet', '')}"[:500]
                        merged.append(h)
                    if len(merged) >= max_items:
                        return merged[:max_items]

            if len(merged) < max_items:
                general = bocha_web_search(text, count=3)
                for h in general:
                    url = h.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        merged.append(h)
                    if len(merged) >= max_items:
                        break

        if merged:
            print(f"[execute_domestic_search] 博查 API 返回 {len(merged)} 条具体结果")
            return merged[:max_items]

    fallback = search_web_domestic_from_plan(plan, max_items=max_items)
    print(f"[execute_domestic_search] 使用计划降级链接 {len(fallback)} 条")
    return fallback


async def execute_domestic_search(plan: Dict[str, Any], max_items: int = 6) -> List[Dict[str, Any]]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(execute_domestic_search_sync, plan, max_items)
    )


async def resolve_recommend_context(query: str) -> Dict[str, Any]:
    """
    统一推荐上下文：RAG 召回 → CoT 过滤 → 无命中则仅国内网络搜索。
    卡片接口与流式对话接口均应调用此函数。
    """
    q = (query or "").strip()
    empty = {
        "query_used": q,
        "should_show_recommendation": False,
        "lecture": [],
        "exercise": [],
        "reference": [],
        "other": [],
        "all": [],
        "web": [],
        "has_local": False,
        "has_web": False,
        "cot_reason": "",
        "search_plan": None,
    }
    if not q:
        return empty

    candidates = _rag_recall_candidates(q)
    cot = await cot_filter_rag(q, candidates)

    if cot.get("rag_confident") and cot.get("relevant_indices"):
        idx_set = set(cot["relevant_indices"])
        filtered = [candidates[i] for i in sorted(idx_set) if 0 <= i < len(candidates)]
    else:
        filtered = []

    rag_part = _categorize_rag_files(filtered)
    web: List[Dict[str, Any]] = []
    search_plan: Optional[Dict[str, Any]] = None
    web_reason = ""

    # 总是执行网络搜索（本地+网络同时展示），但控制数量避免卡片过多
    search_plan = await plan_web_search(q)
    # 本地有命中时减少网络结果数量，避免卡片过多
    web_max_items = 3 if filtered else 6
    web = await execute_domestic_search(search_plan, max_items=web_max_items)
    intent = search_plan.get("intent_summary", "")
    query_texts = [qi.get("text", "") for qi in (search_plan.get("queries") or []) if qi.get("text")]
    web_reason = f"意图：{intent}"
    if query_texts:
        web_reason += f"；检索：{'；'.join(query_texts[:3])}"
    if filtered:
        print(f"[resolve_recommend_context] 本地命中 {len(filtered)} 个，补充网络搜索 {len(web)} 条")
    else:
        print(f"[resolve_recommend_context] 本地无命中，网络搜索 {len(web)} 条")

    cot_reason = cot.get("reason", "")
    if web_reason:
        cot_reason = f"{cot_reason}；{web_reason}".strip("；")

    should_show = bool(filtered) or bool(web)
    return {
        "query_used": q,
        "should_show_recommendation": should_show,
        "cot_reason": cot_reason,
        "search_plan": search_plan,
        "web": web,
        "has_local": len(filtered) > 0,
        "has_web": len(web) > 0,
        **rag_part,
    }


def build_recommend_prompt_messages(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """将统一推荐上下文转为模型 system 消息（与资源卡片一致）。"""
    system = """你是课程学习助手。请用完整、清晰的段落回答问题（可多段，可分点），结合对话中已展示的资源卡片作答，不要刻意缩短。

规则：
1. 仅引用下方【本轮推荐资源】中出现的本地文件名与网络链接，禁止编造未出现的资料。
2. 若有本地课件/习题：说明如何结合这些资料学习，可点明重点章节或题型。
3. 若有具体网络资源（视频/文章链接）：结合标题与摘要回答，用 Markdown [标题](URL)；若是平台搜索页则说明其用途。
4. 若本地与网络均无有效资料：明确说明知识库未命中，再给出通用学习建议。
5. 不要简单罗列所有资源，重点回答用户问题。"""

    lines = ["【本轮推荐资源】"]
    if ctx.get("all"):
        lines.append("本地资料：")
        for f in ctx["all"][:6]:
            lines.append(f"- {f.get('source', '')}（相关度 {f.get('score', 0)}）")
            if f.get("preview"):
                lines.append(f"  摘要：{f['preview'][:200]}")
    else:
        lines.append("本地资料：无（未命中与问题直接相关的知识库文件）")

    if ctx.get("web"):
        lines.append("网络资源（国内平台）：")
        for w in ctx["web"][:5]:
            lines.append(f"- [{w.get('title', '')}]({w.get('url', '')})")
            if w.get("snippet"):
                lines.append(f"  {w['snippet'][:120]}")
    elif not ctx.get("all"):
        lines.append("网络资源：无")

    if ctx.get("cot_reason"):
        lines.append(f"检索说明：{ctx['cot_reason']}")

    plan = ctx.get("search_plan")
    if plan and plan.get("intent_summary"):
        lines.append(f"检索意图：{plan['intent_summary']}")

    return [
        {"role": "system", "content": [{"type": "text", "text": system}]},
        {"role": "system", "content": [{"type": "text", "text": "\n".join(lines)}]},
    ]


def search_rag_sources(query: str, top_k: int = 15, score_threshold: float = 0.25) -> Dict[str, Any]:
    """同步 RAG 检索（兼容旧调用，不含 CoT）。"""
    files = _rag_recall_candidates(query, top_k=top_k, min_score=score_threshold)
    categorized = _categorize_rag_files(files)
    has_content = len(categorized["all"]) > 0
    return {"should_show_recommendation": has_content, **categorized}


def extract_session_links(contents: List[Any]) -> List[Dict[str, Any]]:
    """
    ????????????????????? OSS ??? URL??
    PDF ??????????????????? URL???????? http(s) ? content?
    """
    found: List[Dict[str, Any]] = []
    seen_url: set[str] = set()
    for row in contents:
        raw = (getattr(row, "content", None) or "").strip().strip("`")
        if not raw or not (raw.startswith("http://") or raw.startswith("https://")):
            continue
        if raw in seen_url:
            continue
        seen_url.add(raw)
        ct = getattr(row, "content_type", None) or "text"
        name = getattr(row, "name", None) or ""
        role = getattr(row, "role", "")
        kind = "image" if ct == "image" else "link"
        title = name or (f"{role} ??????" if role else "??")
        found.append({"kind": kind, "title": title, "url": raw})
    return found
