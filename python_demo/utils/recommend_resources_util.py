"""
推荐资源工具：网络搜索 + RAG 知识库检索
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import httpx
import re

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


def search_web_duckduckgo(query: str, max_items: int = 8) -> List[Dict[str, Any]]:
    """?? DuckDuckGo Instant Answer API??? key?????????????"""
    q = (query or "").strip()
    if not q:
        return []
    out: List[Dict[str, Any]] = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
        }
        with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
            r = client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": q,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
            )
            r.raise_for_status()
            data = r.json()
        if data.get("AbstractURL"):
            out.append(
                {
                    "title": data.get("Heading") or data.get("AbstractURL"),
                    "url": data["AbstractURL"],
                    "snippet": (data.get("AbstractText") or "")[:500],
                }
            )
        for topic in data.get("RelatedTopics") or []:
            if len(out) >= max_items:
                break
            if isinstance(topic, dict) and topic.get("FirstURL"):
                out.append(
                    {
                        "title": (topic.get("Text") or topic["FirstURL"])[:300],
                        "url": topic["FirstURL"],
                        "snippet": "",
                    }
                )
            elif isinstance(topic, dict) and topic.get("Topics"):
                for t in topic["Topics"]:
                    if len(out) >= max_items:
                        break
                    if isinstance(t, dict) and t.get("FirstURL"):
                        out.append(
                            {
                                "title": (t.get("Text") or t["FirstURL"])[:300],
                                "url": t["FirstURL"],
                                "snippet": "",
                            }
                        )
    except Exception as e:
        print(f"[search_web_duckduckgo] {e}")
    return out[:max_items]


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


def search_rag_sources(query: str, top_k: int = 15, score_threshold: float = 0.25) -> Dict[str, Any]:
    """
    智能检索：结合向量相似度 + 课程代码匹配
    返回格式: {
        "should_show_recommendation": bool,
        "lecture": [...],
        "exercise": [...],
        "reference": [...],
        "other": [...],
        "all": [...]
    }
    """
    q = (query or "").strip()
    if not q:
        return {"should_show_recommendation": False, "lecture": [], "exercise": [], "reference": [], "other": [], "all": []}

    # 判断是否是需要推荐的学习相关内容
    study_keywords = ['课程', '课件', '学习', '实验', '作业', '习题', '考试', '复习', '资料',
                      'slide', 'lecture', 'lab', 'homework', 'assignment', 'exam', 'course', 'study',
                      '怎么', '如何', '什么', '哪些', '推荐', '资源', '帮助', '需要', '期末', '期中']
    should_show = any(kw in q.lower() for kw in study_keywords)

    # 提取查询中的课程代码
    query_codes = extract_course_codes(q)
    print(f"[search_rag_sources] 提取到课程代码: {query_codes}")

    try:
        from utils.rag_util import EmbeddingService, VectorStore

        emb = EmbeddingService()
        vs = VectorStore()

        # 使用扩展查询（添加课程代码）进行向量检索
        expanded_query = expand_query_with_course_info(q)
        print(f"[search_rag_sources] 扩展查询: {expanded_query}")

        qe = emb.embed(expanded_query)
        hits = vs.search(qe, top_k=top_k)

        seen: set[str] = set()
        all_files = []

        for h in hits:
            src = str(h.get("source") or "unknown")
            vector_score = float(h.get("score", 0))

            if src in seen:
                continue
            seen.add(src)

            # 计算课程匹配分数
            course_match_score = calculate_course_match_score(src, query_codes)

            # 综合分数 = 向量相似度 * 0.6 + 课程匹配分数 * 0.4
            # 如果查询中没有课程代码，课程匹配分数为0，只看向量相似度
            if query_codes:
                combined_score = vector_score * 0.6 + course_match_score * 0.4
            else:
                combined_score = vector_score

            # 判断文件类型
            low = src.lower()
            if low.endswith(".pdf"):
                file_type = "pdf"
            elif low.endswith(".docx"):
                file_type = "docx"
            elif low.endswith(".pptx"):
                file_type = "pptx"
            elif low.endswith(".md"):
                file_type = "markdown"
            elif low.endswith(".txt"):
                file_type = "text"
            else:
                file_type = "unknown"

            category = categorize_file(src)
            file_path = CAMPUS_DOCS_DIR / src
            file_exists = file_path.exists()

            file_info = {
                "source": src,
                "vector_score": round(vector_score, 4),
                "course_match_score": round(course_match_score, 4),
                "score": round(combined_score, 4),  # 综合分数用于排序
                "file_type": file_type,
                "is_pdf": file_type == "pdf",
                "category": category,
                "file_exists": file_exists,
                "is_original_file": True,
                "download_url": f"/rag/download/{src}",
                "preview_url": f"/rag/preview/{src}",
            }

            all_files.append(file_info)

        # 按综合分数排序
        all_files.sort(key=lambda x: x["score"], reverse=True)

        # 分类并过滤低分结果
        categorized = {
            "lecture": [],
            "exercise": [],
            "reference": [],
            "other": [],
            "all": []
        }

        for f in all_files:
            # 使用综合分数进行阈值判断
            if f["score"] >= score_threshold:
                categorized["all"].append(f)
                categorized[f["category"]].append(f)

        # 调试输出
        print(f"[search_rag_sources] 检索到 {len(categorized['all'])} 个相关文件")
        for cat, files in categorized.items():
            if cat != "all" and files:
                print(f"  - {cat}: {len(files)} 个")

        # 判断是否有足够的内容值得展示推荐卡片
        has_content = len(categorized["all"]) > 0 and (
            len(categorized["lecture"]) > 0 or
            len(categorized["exercise"]) > 0 or
            len(categorized["reference"]) > 0
        )

        return {
            "should_show_recommendation": should_show and has_content,
            **categorized
        }

    except Exception as e:
        print(f"[search_rag_sources] 错误: {e}")
        import traceback
        traceback.print_exc()
        return {"should_show_recommendation": False, "lecture": [], "exercise": [], "reference": [], "other": [], "all": []}


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
