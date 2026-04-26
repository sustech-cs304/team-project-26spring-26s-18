import time
print(f"[启动分析] routers/session.py 开始导入 {time.time()}")
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DBSession
from typing import Dict, List, Optional
from schemas.session import Session as SessionSchema, SessionContent as SessionContentSchema
from utils.Result import Result
from schemas.session import Session as SessionSchema, SessionContent as SessionContentSchema
from crud.session import (
    get_sessions_by_user_id,
    get_content_by_session_id,
    create_session,
    create_content,
    delete_content_by_session_id,
    delete_session_by_id,
    update_session_title_by_id,
    get_last_n_content_by_session_id
)
from config.db_config import get_db
from utils.ai_util import ai_chat, ai_chat_stream
from fastapi.responses import StreamingResponse
from models.session import Session as SessionModel, SessionContent
from utils.recommend_resources_util import extract_session_links, search_rag_sources
from utils.ai_resource_recommender import generate_resource_recommendations
from utils.url_verifier import verify_and_get_urls

router = APIRouter(prefix="/session", tags=["session"])

@router.get("/user/{user_id}")
async def api_get_sessions_by_user_id(user_id: int, db: DBSession = Depends(get_db)):
    data = await get_sessions_by_user_id(db, user_id)
    data = [SessionSchema.model_validate(obj) for obj in data]
    return Result.success(data)

@router.get("/{session_id}/content")
async def api_get_content_by_session_id(session_id: int, db: DBSession = Depends(get_db)):
    data = await get_content_by_session_id(db, session_id)
    data = [SessionContentSchema.model_validate(obj) for obj in data]
    return Result.success(data)

@router.post("/create")
async def api_create_session(
    user_id: int = Body(..., embed=True),
    title: str = Body(None, embed=True),
    db: DBSession = Depends(get_db)
):
    obj = await create_session(db, user_id, title)
    data = SessionSchema.model_validate(obj)
    return Result.success(data)



# 原同步接口保留
@router.post("/aicontent")
async def api_create_ai_content(
    session_id: int = Body(..., embed=True),
    content: str = Body(..., embed=True),
    files: Optional[List[str]] = Body(None, embed=True),         # base64内容数组
    file_types: Optional[List[str]] = Body(None, embed=True),    # 文件类型数组
    file_names: Optional[List[str]] = Body(None, embed=True),    # 文件名数组
    db: DBSession = Depends(get_db)
):
    t0 = time.time()
    print(f"[api_create_ai_content] 开始调用 ai_chat {t0}")
    msgs = await ai_chat(
        db=db,
        session_id=session_id,
        content=content,
        files=files,
        file_types=file_types,
        file_names=file_names
    )
    t1 = time.time()
    print(f"[api_create_ai_content] ai_chat 总耗时: {t1-t0:.2f}s")
    from schemas.session import SessionContent as SessionContentSchema
    return Result.success([
        SessionContentSchema.model_validate(m) for m in msgs
    ])
# 新增流式接口
@router.post("/aicontent/stream")
async def api_create_ai_content_stream(
    session_id: int = Body(..., embed=True),
    content: str = Body(..., embed=True),
    files: Optional[List[str]] = Body(None, embed=True),
    file_types: Optional[List[str]] = Body(None, embed=True),
    file_names: Optional[List[str]] = Body(None, embed=True),
    db: DBSession = Depends(get_db)
):
    async def event_generator():
        async for chunk in ai_chat_stream(
            db=db,
            session_id=session_id,
            content=content,
            files=files,
            file_types=file_types,
            file_names=file_names
        ):
            yield chunk
    return StreamingResponse(event_generator(), media_type="text/plain")
#新增流式接口：更少历史+更多RAG检索，用于校园助手功能
@router.post("/aicontent/stream_less_history_more_rag")
async def api_create_ai_content_stream_less_history_more_rag(
    session_id: int = Body(..., embed=True),
    content: str = Body(..., embed=True),
    files: Optional[List[str]] = Body(None, embed=True),
    file_types: Optional[List[str]] = Body(None, embed=True),
    file_names: Optional[List[str]] = Body(None, embed=True),
    db: DBSession = Depends(get_db)
):
    async def event_generator():
        from utils.ai_util import ai_chat_stream_less_history_more_rag
        async for chunk in ai_chat_stream_less_history_more_rag(
            db=db,
            session_id=session_id,
            content=content,
            files=files,
            file_types=file_types,
            file_names=file_names
        ):
            yield chunk
    return StreamingResponse(event_generator(), media_type="text/plain")

# 新增流式接口：更多历史+不使用RAG，用于学习助手功能
@router.post("/aicontent/stream_more_history_no_rag")
async def api_create_ai_content_stream_more_history_no_rag(
    session_id: int = Body(..., embed=True),
    content: str = Body(..., embed=True),
    files: Optional[List[str]] = Body(None, embed=True),
    file_types: Optional[List[str]] = Body(None, embed=True),
    file_names: Optional[List[str]] = Body(None, embed=True),
    db: DBSession = Depends(get_db)
):
    async def event_generator():
        from utils.ai_util import ai_chat_stream_more_history_no_rag
        async for chunk in ai_chat_stream_more_history_no_rag(
            db=db,
            session_id=session_id,
            content=content,
            files=files,
            file_types=file_types,
            file_names=file_names
        ):
            yield chunk
    return StreamingResponse(event_generator(), media_type="text/plain")

# 新增流式接口：推荐模式专用，精简回复
@router.post("/aicontent/stream_recommend")
async def api_create_ai_content_stream_recommend(
    session_id: int = Body(..., embed=True),
    content: str = Body(..., embed=True),
    files: Optional[List[str]] = Body(None, embed=True),
    file_types: Optional[List[str]] = Body(None, embed=True),
    file_names: Optional[List[str]] = Body(None, embed=True),
    db: DBSession = Depends(get_db)
):
    async def event_generator():
        from utils.ai_util import ai_chat_stream_recommend
        async for chunk in ai_chat_stream_recommend(
            db=db,
            session_id=session_id,
            content=content,
            files=files,
            file_types=file_types,
            file_names=file_names
        ):
            yield chunk
    return StreamingResponse(event_generator(), media_type="text/plain")

# Agent模式，实现自主选择工具
@router.post("/aicontent/agent")
async def api_create_ai_content_agent(
    session_id: int = Body(..., embed=True),
    content: str = Body(..., embed=True),
    # mode: str = Body("agent", embed=True),      
    files: Optional[List[str]] = Body(None, embed=True),
    file_types: Optional[List[str]] = Body(None, embed=True),
    file_names: Optional[List[str]] = Body(None, embed=True),
    db: DBSession = Depends(get_db)
):
    async def event_generator():
        from utils.ai_util import agent_chat_stream
        async for chunk in agent_chat_stream(
            db=db,
            session_id=session_id,
            content=content,
            files=files,
            file_types=file_types,
            file_names=file_names
        ):
            yield chunk
    return StreamingResponse(event_generator(), media_type="text/plain")


@router.post("/recommend/resources")
async def api_recommend_resources(
    user_id: int = Body(..., embed=True),
    query: str = Body("", embed=True),
    session_id: Optional[int] = Body(None, embed=True),
    db: DBSession = Depends(get_db),
):
    """
    推荐资料：智能判断是否展示推荐卡片
    返回分类结果：课件(lecture)、习题(exercise)、参考资料(reference)
    新增：MOOC、GitHub、教程等推荐资源
    """
    q = (query or "").strip()
    session_links: List[Dict] = []

    if session_id is not None:
        res = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        sess = res.scalar_one_or_none()
        if not sess or sess.user_id != user_id:
            raise HTTPException(status_code=404, detail="会话不存在或无权访问")
        contents = list(await get_content_by_session_id(db, session_id))
        session_links = extract_session_links(contents)
        if not q:
            for row in reversed(contents):
                if row.role == "user" and row.content_type == "text" and (row.content or "").strip():
                    q = row.content.strip()
                    break

    if not q:
        return Result.error("请输入检索内容，或选择会话后由系统取您最后一条文字消息作为检索词")

    # 1. 知识库检索
    rag_result = search_rag_sources(q, top_k=15, score_threshold=0.15)

    has_local = len(rag_result.get("all", [])) > 0
    
    # 2. 如果本地资源不足，使用 AI 生成推荐资源
    web_results = []
    has_web = False

    # 当本地资源少于3个时，使用 AI 生成推荐
    local_count = len(rag_result.get("all", []))
    if local_count < 3:
        print(f"[api_recommend_resources] 本地资源仅 {local_count} 个，使用 AI 生成推荐...")
        try:
            ai_recommendations = await generate_resource_recommendations(q, rag_result.get("all", []))
            # 验证前3个推荐的真实 URL
            if ai_recommendations:
                print(f"[api_recommend_resources] 开始验证 {min(3, len(ai_recommendations))} 个资源的 URL...")
                ai_recommendations = verify_and_get_urls(ai_recommendations, max_verify=3)
            # 将 AI 推荐转换为 web 格式
            for rec in ai_recommendations[:5]:
                title = rec.get("title", "") or ""
                url = rec.get("url", "") or ""
                platform = rec.get("platform", "") or ""
                desc = rec.get("description", "") or ""
                course_slug = rec.get("course_slug", "") or ""

                # 分析 URL 类型
                is_specific_url = False
                is_search_url = "bing.com" in url.lower() or "search" in url.lower()

                # 如果 URL 包含具体课程路径（如 /learn/ /course/ /video/），认为是具体 URL
                if any(x in url.lower() for x in ["/learn/", "/course/", "/video/", "github.com/", "/tutorial/", "/doc/"]):
                    is_specific_url = True

                # 构建备用搜索链接
                search_query = f"{title} {platform}".replace(" ", "+").replace("&", "%26")[:150]
                search_url = f"https://www.bing.com/search?q={search_query}"

                # 如果 AI 没提供 URL 或提供的是搜索链接，尝试构建标准格式的 URL
                if not url or is_search_url:
                    # 根据平台和 course_slug 构建可能的 URL
                    if course_slug:
                        if "coursera" in platform.lower():
                            url = f"https://www.coursera.org/learn/{course_slug}"
                            is_specific_url = True
                        elif "edx" in platform.lower():
                            url = f"https://www.edx.org/course/{course_slug}"
                            is_specific_url = True
                        elif "bilibili" in platform.lower() or "b站" in platform.lower():
                            # B站使用搜索链接
                            url = f"https://search.bilibili.com/all?keyword={course_slug}"
                        elif "github" in platform.lower():
                            url = f"https://github.com/search?q={course_slug}&type=repositories"
                    else:
                        url = search_url

                # 检查 URL 是否经过搜索验证
                url_verified = rec.get('url_verified', False)
                original_url = rec.get('original_url', url)

                # 构建详细的 snippet
                snippet_parts = []
                snippet_parts.append(f"[{rec.get('type', 'resource').upper()}]")
                if platform:
                    verified_mark = "✓" if url_verified else ""
                    snippet_parts.append(f"平台: {platform} {verified_mark}")
                if desc:
                    snippet_parts.append(desc)
                snippet_parts.append(f"难度: {rec.get('difficulty', 'unknown')}")

                web_results.append({
                    "title": title,
                    "url": url,
                    "snippet": " | ".join(snippet_parts),
                    "source": "ai-generated",
                    "platform": platform,
                    "description": desc,
                    "difficulty": rec.get('difficulty', 'unknown'),
                    "is_specific_url": is_specific_url or url_verified,
                    "url_verified": url_verified,
                    "search_url": search_url  # 备用搜索链接
                })
            has_web = len(web_results) > 0
            print(f"[api_recommend_resources] AI 生成 {len(web_results)} 个推荐")
        except Exception as e:
            print(f"[api_recommend_resources] AI 生成推荐失败: {e}")
    
    # 判断是否应该展示推荐卡片（有本地资源或网络资源即可展示）
    should_show = has_local or has_web

    return Result.success({
        "query_used": q,
        "should_show_recommendation": should_show,
        "lecture": rag_result.get("lecture", []),
        "exercise": rag_result.get("exercise", []),
        "reference": rag_result.get("reference", []),
        "other": rag_result.get("other", []),
        "web": web_results,
        "has_local": has_local,
        "has_web": has_web,
        "session_links": session_links,
    })


@router.delete("/content/{content_id}")
async def api_delete_content(content_id: int, db: DBSession = Depends(get_db)):
    await db.execute(delete(SessionContent).where(SessionContent.id == content_id))
    await db.commit()
    return Result.success()

@router.delete("/{session_id}")
async def api_delete_session(session_id: int, db: DBSession = Depends(get_db)):
    await delete_session_by_id(db, session_id)
    return Result.success()

@router.put("/{session_id}/title")
async def api_update_session_title(session_id: int, new_title: str, db: DBSession = Depends(get_db)):
    await update_session_title_by_id(db, session_id, new_title)
    return Result.success()
