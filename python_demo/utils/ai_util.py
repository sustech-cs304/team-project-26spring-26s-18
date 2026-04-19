from openai import OpenAI
import os
import base64
import uuid
import time
from utils.oss_util import OSSUtil
from crud.session import create_content, get_last_n_content_by_session_id
import asyncio
from functools import partial
from utils.pdf_util import extract_pdf_text
from utils.rag_util import EmbeddingService, VectorStore
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 该接口是最最原始的接口，已经废弃不用了，目前都是使用下面的流式调用接口
async def ai_chat(
    db,
    session_id: int,
    content: str,
    files=None,
    file_types=None,
    file_names=None
):
    """
    通用AI对话接口，支持文本和图片。
    自动插入用户文本、图片、AI回复到数据库，返回所有消息对象。
    """
    msg_content = []
    user_msgs = []

    t0 = time.time()
    print(f"[ai_chat] step0: 开始, t={t0}")
    # 1. 查询历史消息（最近5条，按时间升序）
    t1 = time.time()
    history_msgs = await get_last_n_content_by_session_id(db, session_id, n=5)
    t2 = time.time()
    print(f"[ai_chat] step1: 查询历史消息耗时: {t2-t1:.2f}s")
    history_contents = []
    for msg in history_msgs:
        content_list = []
        if msg.content_type == "text":
            content_list.append({"type": "text", "text": msg.content})
        elif msg.content_type == "image":
            content_list.append({"type": "image_url", "image_url": {"url": msg.content}})
        elif msg.content_type == "pdf":
            content_list.append({"type": "text", "text": f"pdf不是连接，而是下面的内容: {msg.content}"})
        elif msg.content_type == "markdown":
            content_list.append({"type": "text", "text": f"md不是连接，而是下面的内容: {msg.content}"})
        history_contents.append({"role": msg.role, "content": content_list})

    # 2. 处理本次用户文本和文件
    t3 = time.time()
    user_msg = await create_content(db, session_id, "user", content, content_type="text", name=None)
    user_msgs.append(user_msg)
    t4 = time.time()
    print(f"[ai_chat] step2: 存储用户文本耗时: {t4-t3:.2f}s")
    if files and file_types:
        for idx, (f, t) in enumerate(zip(files, file_types)):
            name = file_names[idx] if file_names and idx < len(file_names) else None
            if t.startswith("image/"):
                ext = t.split("/")[-1]
                file_name = f"photos/{uuid.uuid4()}.{ext}"
                img_bytes = base64.b64decode(f)
                url = OSSUtil.upload(img_bytes, file_name)
                img_msg = await create_content(db, session_id, "user", url, content_type="image", name=name)
                user_msgs.append(img_msg)
                msg_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            elif t == "application/pdf":
                pdf_text = extract_pdf_text(f, max_len=5000)
                pdf_msg = await create_content(db, session_id, "user", pdf_text, content_type="pdf", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"pdf不是连接，而是下面的内容: {pdf_text}"
                })
                user_msgs.append(pdf_msg)
            elif t == "text/markdown":
                md_text = base64.b64decode(f).decode("utf-8")
                md_msg = await create_content(db, session_id, "user", md_text, content_type="markdown", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"md不是连接，而是下面的内容: {md_text}"
                })
                user_msgs.append(md_msg)
    t5 = time.time()
    print(f"[ai_chat] step3: 处理文件耗时: {t5-t4:.2f}s")
    msg_content.append({"type": "text", "text": content})


    # 3 用向量数据库检索与本次问题最相关的3条数据
    t6 = time.time()
    try:
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        t6_1 = time.time()
        query_embedding = embedding_service.embed(content)
        t6_2 = time.time()
        print(f"[ai_chat] step4: query embedding耗时: {t6_2-t6_1:.2f}s")
        related = vector_store.search(query_embedding, top_k=3)
        t6_3 = time.time()
        print(f"[ai_chat] step5: 向量检索耗时: {t6_3-t6_2:.2f}s")
        related_context = []
        for chunk in related:
            related_context.append({
                "role": "system",
                "content": [{"type": "text", "text": f"[相关历史] {chunk['content']}"}]
            })
    except Exception as e:
        print(f"[ai_chat] 检索相关内容失败: {e}")
        related_context = []
    t7 = time.time()
    print(f"[ai_chat] step6: 检索相关历史总耗时: {t7-t6:.2f}s")

    # 4. 拼装最终 messages
    messages = []
    for h in history_contents:
        messages.append({"role": h["role"], "content": h["content"]})
    # 插入向量数据库中相关内容
    messages.extend(related_context)
    messages.append({"role": "user", "content": msg_content})

    t8 = time.time()
    print(f"[ai_chat] step7: 拼装messages耗时: {t8-t7:.2f}s")
    # 5. 调用大模型
    loop = asyncio.get_event_loop()
    t9 = time.time()
    print(f"[ai_chat] step8: 开始调用大模型, t={t9}")
    completion = await loop.run_in_executor(
        None,
        partial(
            client.chat.completions.create,
            model="qwen3.6-plus",
            messages=messages,
        )
    )
    t10 = time.time()
    print(f"[ai_chat] step9: 大模型回复耗时: {t10-t9:.2f}s")
    ai_reply = completion.choices[0].message.content
    # 5. 插入AI回复
    t11 = time.time()
    ai_msg = await create_content(db, session_id, "assistant", ai_reply, content_type="text")
    t12 = time.time()
    print(f"[ai_chat] step10: 存储AI回复耗时: {t12-t11:.2f}s")
    print(f"[ai_chat] 总耗时: {t12-t0:.2f}s")
    # 6. 返回所有消息对象
    return user_msgs + [ai_msg]

# 流式AI对话接口
async def ai_chat_stream(
    db,
    session_id: int,
    content: str,
    files=None,
    file_types=None,
    file_names=None
):
    """
    通用AI对话接口（流式），支持文本和图片。
    自动插入用户文本、图片到数据库，流式yield AI回复内容。
    """
    msg_content = []
    user_msgs = []

    t0 = time.time()
    print(f"[ai_chat_stream] step0: 开始, t={t0}")
    # 1. 查询历史消息（最近5条，按时间升序）
    t1 = time.time()
    history_msgs = await get_last_n_content_by_session_id(db, session_id, n=5)
    t2 = time.time()
    print(f"[ai_chat_stream] step1: 查询历史消息耗时: {t2-t1:.2f}s")
    history_contents = []
    for msg in history_msgs:
        content_list = []
        if msg.content_type == "text":
            content_list.append({"type": "text", "text": msg.content})
        elif msg.content_type == "image":
            content_list.append({"type": "image_url", "image_url": {"url": msg.content}})
        elif msg.content_type == "pdf":
            content_list.append({"type": "text", "text": f"pdf不是连接，而是下面的内容: {msg.content}"})
        elif msg.content_type == "markdown":
            content_list.append({"type": "text", "text": f"md不是连接，而是下面的内容: {msg.content}"})
        history_contents.append({"role": msg.role, "content": content_list})

    # 2. 处理本次用户文本和文件
    t3 = time.time()
    user_msg = await create_content(db, session_id, "user", content, content_type="text", name=None)
    user_msgs.append(user_msg)
    t4 = time.time()
    print(f"[ai_chat_stream] step2: 存储用户文本耗时: {t4-t3:.2f}s")
    if files and file_types:
        for idx, (f, t) in enumerate(zip(files, file_types)):
            name = file_names[idx] if file_names and idx < len(file_names) else None
            if t.startswith("image/"):
                ext = t.split("/")[-1]
                file_name = f"photos/{uuid.uuid4()}.{ext}"
                img_bytes = base64.b64decode(f)
                url = OSSUtil.upload(img_bytes, file_name)
                img_msg = await create_content(db, session_id, "user", url, content_type="image", name=name)
                user_msgs.append(img_msg)
                msg_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            elif t == "application/pdf":
                pdf_text = extract_pdf_text(f, max_len=5000)
                pdf_msg = await create_content(db, session_id, "user", pdf_text, content_type="pdf", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"pdf不是连接，而是下面的内容: {pdf_text}"
                })
                user_msgs.append(pdf_msg)
            elif t == "text/markdown":
                md_text = base64.b64decode(f).decode("utf-8")
                md_msg = await create_content(db, session_id, "user", md_text, content_type="markdown", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"md不是连接，而是下面的内容: {md_text}"
                })
                user_msgs.append(md_msg)
    t5 = time.time()
    print(f"[ai_chat_stream] step3: 处理文件耗时: {t5-t4:.2f}s")
    msg_content.append({"type": "text", "text": content})

    # 3 用向量数据库检索与本次问题最相关的3条数据
    t6 = time.time()
    try:
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        t6_1 = time.time()
        query_embedding = embedding_service.embed(content)
        t6_2 = time.time()
        print(f"[ai_chat_stream] step4: query embedding耗时: {t6_2-t6_1:.2f}s")
        related = vector_store.search(query_embedding, top_k=3)
        t6_3 = time.time()
        print(f"[ai_chat_stream] step5: 向量检索耗时: {t6_3-t6_2:.2f}s")
        related_context = []
        for chunk in related:
            related_context.append({
                "role": "system",
                "content": [{"type": "text", "text": f"[相关历史] {chunk['content']}"}]
            })
    except Exception as e:
        print(f"[ai_chat_stream] 检索相关内容失败: {e}")
        related_context = []
    t7 = time.time()
    print(f"[ai_chat_stream] step6: 检索相关历史总耗时: {t7-t6:.2f}s")

    # 4. 拼装最终 messages
    messages = []
    for h in history_contents:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.extend(related_context)
    messages.append({"role": "user", "content": msg_content})

    t8 = time.time()
    print(f"[ai_chat_stream] step7: 拼装messages耗时: {t8-t7:.2f}s")
    # 5. 调用大模型（流式）
    t9 = time.time()
    print(f"[ai_chat_stream] step8: 开始调用大模型, t={t9}")
    # openai流式接口为同步生成器，这里用线程池包装
    def stream_gen():
        return client.chat.completions.create(
            model="qwen3.6-plus",
            messages=messages,
            stream=True,
            stream_options={"include_usage": True}
        )
    loop = asyncio.get_event_loop()
    completion = await loop.run_in_executor(None, stream_gen)
    full_reply = ""
    for chunk in completion:
        if chunk.choices:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
                full_reply += delta
    # 6. 插入AI回复到数据库
    ai_msg = await create_content(db, session_id, "assistant", full_reply, content_type="text")
    print(f"[ai_chat_stream] AI回复已存储，长度: {len(full_reply)}")

# 下面是修改后的流式接口，使用更多历史会话，不使用RAG检索
async def ai_chat_stream_more_history_no_rag(
    db,
    session_id: int,
    content: str,
    files=None,
    file_types=None,
    file_names=None
):
    """
    通用AI对话接口（流式），支持文本和图片。
    自动插入用户文本、图片到数据库，流式yield AI回复内容。
    """
    msg_content = []
    user_msgs = []

    t0 = time.time()
    print(f"[ai_chat_stream] step0: 开始, t={t0}")
    # 1. 查询历史消息（最近5条，按时间升序）
    t1 = time.time()
    history_msgs = await get_last_n_content_by_session_id(db, session_id, n=10)
    t2 = time.time()
    print(f"[ai_chat_stream] step1: 查询历史消息耗时: {t2-t1:.2f}s")
    history_contents = []
    for msg in history_msgs:
        content_list = []
        if msg.content_type == "text":
            content_list.append({"type": "text", "text": msg.content})
        elif msg.content_type == "image":
            content_list.append({"type": "image_url", "image_url": {"url": msg.content}})
        elif msg.content_type == "pdf":
            content_list.append({"type": "text", "text": f"pdf不是连接，而是下面的内容: {msg.content}"})
        elif msg.content_type == "markdown":
            content_list.append({"type": "text", "text": f"md不是连接，而是下面的内容: {msg.content}"})
        history_contents.append({"role": msg.role, "content": content_list})

    # 2. 处理本次用户文本和文件
    t3 = time.time()
    user_msg = await create_content(db, session_id, "user", content, content_type="text", name=None)
    user_msgs.append(user_msg)
    t4 = time.time()
    print(f"[ai_chat_stream] step2: 存储用户文本耗时: {t4-t3:.2f}s")
    if files and file_types:
        for idx, (f, t) in enumerate(zip(files, file_types)):
            name = file_names[idx] if file_names and idx < len(file_names) else None
            if t.startswith("image/"):
                ext = t.split("/")[-1]
                file_name = f"photos/{uuid.uuid4()}.{ext}"
                img_bytes = base64.b64decode(f)
                url = OSSUtil.upload(img_bytes, file_name)
                img_msg = await create_content(db, session_id, "user", url, content_type="image", name=name)
                user_msgs.append(img_msg)
                msg_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            elif t == "application/pdf":
                pdf_text = extract_pdf_text(f, max_len=5000)
                pdf_msg = await create_content(db, session_id, "user", pdf_text, content_type="pdf", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"pdf不是连接，而是下面的内容: {pdf_text}"
                })
                user_msgs.append(pdf_msg)
            elif t == "text/markdown":
                md_text = base64.b64decode(f).decode("utf-8")
                md_msg = await create_content(db, session_id, "user", md_text, content_type="markdown", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"md不是连接，而是下面的内容: {md_text}"
                })
                user_msgs.append(md_msg)
    t5 = time.time()
    print(f"[ai_chat_stream] step3: 处理文件耗时: {t5-t4:.2f}s")
    msg_content.append({"type": "text", "text": content})

    # 3. 不使用RAG，仅用历史消息
    t6 = time.time()
    # 4. 拼装最终 messages
    messages = []
    for h in history_contents:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": msg_content})
    t7 = time.time()
    print(f"[ai_chat_stream] step6: 拼装messages耗时: {t7-t6:.2f}s")
    # 5. 调用大模型（流式）
    t9 = time.time()
    print(f"[ai_chat_stream] step8: 开始调用大模型, t={t9}")
    # openai流式接口为同步生成器，这里用线程池包装
    def stream_gen():
        return client.chat.completions.create(
            model="qwen3.6-plus",
            messages=messages,
            stream=True,
            stream_options={"include_usage": True}
        )
    loop = asyncio.get_event_loop()
    completion = await loop.run_in_executor(None, stream_gen)
    full_reply = ""
    for chunk in completion:
        if chunk.choices:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
                full_reply += delta
    # 6. 插入AI回复到数据库
    ai_msg = await create_content(db, session_id, "assistant", full_reply, content_type="text")
    print(f"[ai_chat_stream] AI回复已存储，长度: {len(full_reply)}")

# 下面是修改后的流式接口，使用更少历史会话，使用更多RAG检索
async def ai_chat_stream_less_history_more_rag(
    db,
    session_id: int,
    content: str,
    files=None,
    file_types=None,
    file_names=None
):
    """
    通用AI对话接口（流式），支持文本和图片。
    自动插入用户文本、图片到数据库，流式yield AI回复内容。
    """
    msg_content = []
    user_msgs = []

    t0 = time.time()
    print(f"[ai_chat_stream] step0: 开始, t={t0}")
    # 1. 查询历史消息（最近5条，按时间升序）
    t1 = time.time()
    history_msgs = await get_last_n_content_by_session_id(db, session_id, n=2)
    t2 = time.time()
    print(f"[ai_chat_stream] step1: 查询历史消息耗时: {t2-t1:.2f}s")
    history_contents = []
    for msg in history_msgs:
        content_list = []
        if msg.content_type == "text":
            content_list.append({"type": "text", "text": msg.content})
        elif msg.content_type == "image":
            content_list.append({"type": "image_url", "image_url": {"url": msg.content}})
        elif msg.content_type == "pdf":
            content_list.append({"type": "text", "text": f"pdf不是连接，而是下面的内容: {msg.content}"})
        elif msg.content_type == "markdown":
            content_list.append({"type": "text", "text": f"md不是连接，而是下面的内容: {msg.content}"})
        history_contents.append({"role": msg.role, "content": content_list})

    # 2. 处理本次用户文本和文件
    t3 = time.time()
    user_msg = await create_content(db, session_id, "user", content, content_type="text", name=None)
    user_msgs.append(user_msg)
    t4 = time.time()
    print(f"[ai_chat_stream] step2: 存储用户文本耗时: {t4-t3:.2f}s")
    if files and file_types:
        for idx, (f, t) in enumerate(zip(files, file_types)):
            name = file_names[idx] if file_names and idx < len(file_names) else None
            if t.startswith("image/"):
                ext = t.split("/")[-1]
                file_name = f"photos/{uuid.uuid4()}.{ext}"
                img_bytes = base64.b64decode(f)
                url = OSSUtil.upload(img_bytes, file_name)
                img_msg = await create_content(db, session_id, "user", url, content_type="image", name=name)
                user_msgs.append(img_msg)
                msg_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            elif t == "application/pdf":
                pdf_text = extract_pdf_text(f, max_len=5000)
                pdf_msg = await create_content(db, session_id, "user", pdf_text, content_type="pdf", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"pdf不是连接，而是下面的内容: {pdf_text}"
                })
                user_msgs.append(pdf_msg)
            elif t == "text/markdown":
                md_text = base64.b64decode(f).decode("utf-8")
                md_msg = await create_content(db, session_id, "user", md_text, content_type="markdown", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"md不是连接，而是下面的内容: {md_text}"
                })
                user_msgs.append(md_msg)
    t5 = time.time()
    print(f"[ai_chat_stream] step3: 处理文件耗时: {t5-t4:.2f}s")
    msg_content.append({"type": "text", "text": content})

    # 3 用向量数据库检索与本次问题最相关的3条数据
    t6 = time.time()
    try:
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        t6_1 = time.time()
        query_embedding = embedding_service.embed(content)
        t6_2 = time.time()
        print(f"[ai_chat_stream] step4: query embedding耗时: {t6_2-t6_1:.2f}s")
        related = vector_store.search(query_embedding, top_k=10)
        t6_3 = time.time()
        print(f"[ai_chat_stream] step5: 向量检索耗时: {t6_3-t6_2:.2f}s")
        related_context = []
        for chunk in related:
            related_context.append({
                "role": "system",
                "content": [{"type": "text", "text": f"[相关历史] {chunk['content']}"}]
            })
    except Exception as e:
        print(f"[ai_chat_stream] 检索相关内容失败: {e}")
        related_context = []
    t7 = time.time()
    print(f"[ai_chat_stream] step6: 检索相关历史总耗时: {t7-t6:.2f}s")

    # 4. 拼装最终 messages
    messages = []
    for h in history_contents:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.extend(related_context)
    messages.append({"role": "user", "content": msg_content})

    t8 = time.time()
    print(f"[ai_chat_stream] step7: 拼装messages耗时: {t8-t7:.2f}s")
    # 5. 调用大模型（流式）
    t9 = time.time()
    print(f"[ai_chat_stream] step8: 开始调用大模型, t={t9}")
    # openai流式接口为同步生成器，这里用线程池包装
    def stream_gen():
        return client.chat.completions.create(
            model="qwen3.6-plus",
            messages=messages,
            stream=True,
            stream_options={"include_usage": True}
        )
    loop = asyncio.get_event_loop()
    completion = await loop.run_in_executor(None, stream_gen)
    full_reply = ""
    for chunk in completion:
        if chunk.choices:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
                full_reply += delta
    # 6. 插入AI回复到数据库
    ai_msg = await create_content(db, session_id, "assistant", full_reply, content_type="text")
    print(f"[ai_chat_stream] AI回复已存储，长度: {len(full_reply)}")


_RECOMMEND_MODE_SYSTEM_PROMPT = (
    "你是「推荐模式」助手，面向校园与学习场景。请结合用户问题以及消息中的[相关历史]检索片段作答。\n"
    "要求：\n"
    "1. 优先给出可执行、可对比的推荐（分点、小标题、必要时给出备选方案）。\n"
    "2. 若检索资料与用户问题关联弱，请说明依据不足，并列出你需要用户补充的关键信息。\n"
    "3. 语气专业、简洁，避免空话套话。"
)


async def ai_chat_stream_recommend(
    db,
    session_id: int,
    content: str,
    files=None,
    file_types=None,
    file_names=None,
):
    """
    推荐模式（流式）：中等对话历史 + RAG + 专用 system 提示，侧重分点推荐与可执行建议。
    """
    msg_content = []
    user_msgs = []

    t0 = time.time()
    print(f"[ai_chat_stream_recommend] step0: 开始, t={t0}")
    t1 = time.time()
    history_msgs = await get_last_n_content_by_session_id(db, session_id, n=4)
    t2 = time.time()
    print(f"[ai_chat_stream_recommend] step1: 查询历史消息耗时: {t2-t1:.2f}s")
    history_contents = []
    for msg in history_msgs:
        content_list = []
        if msg.content_type == "text":
            content_list.append({"type": "text", "text": msg.content})
        elif msg.content_type == "image":
            content_list.append({"type": "image_url", "image_url": {"url": msg.content}})
        elif msg.content_type == "pdf":
            content_list.append({"type": "text", "text": f"pdf不是连接，而是下面的内容: {msg.content}"})
        elif msg.content_type == "markdown":
            content_list.append({"type": "text", "text": f"md不是连接，而是下面的内容: {msg.content}"})
        history_contents.append({"role": msg.role, "content": content_list})

    t3 = time.time()
    user_msg = await create_content(db, session_id, "user", content, content_type="text", name=None)
    user_msgs.append(user_msg)
    t4 = time.time()
    print(f"[ai_chat_stream_recommend] step2: 存储用户文本耗时: {t4-t3:.2f}s")
    if files and file_types:
        for idx, (f, t) in enumerate(zip(files, file_types)):
            name = file_names[idx] if file_names and idx < len(file_names) else None
            if t.startswith("image/"):
                ext = t.split("/")[-1]
                file_name = f"photos/{uuid.uuid4()}.{ext}"
                img_bytes = base64.b64decode(f)
                url = OSSUtil.upload(img_bytes, file_name)
                img_msg = await create_content(db, session_id, "user", url, content_type="image", name=name)
                user_msgs.append(img_msg)
                msg_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            elif t == "application/pdf":
                pdf_text = extract_pdf_text(f, max_len=5000)
                pdf_msg = await create_content(db, session_id, "user", pdf_text, content_type="pdf", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"pdf不是连接，而是下面的内容: {pdf_text}"
                })
                user_msgs.append(pdf_msg)
            elif t == "text/markdown":
                md_text = base64.b64decode(f).decode("utf-8")
                md_msg = await create_content(db, session_id, "user", md_text, content_type="markdown", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"md不是连接，而是下面的内容: {md_text}"
                })
                user_msgs.append(md_msg)
    t5 = time.time()
    print(f"[ai_chat_stream_recommend] step3: 处理文件耗时: {t5-t4:.2f}s")
    msg_content.append({"type": "text", "text": content})

    t6 = time.time()
    try:
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        t6_1 = time.time()
        query_embedding = embedding_service.embed(content)
        t6_2 = time.time()
        print(f"[ai_chat_stream_recommend] step4: query embedding耗时: {t6_2-t6_1:.2f}s")
        related = vector_store.search(query_embedding, top_k=8)
        t6_3 = time.time()
        print(f"[ai_chat_stream_recommend] step5: 向量检索耗时: {t6_3-t6_2:.2f}s")
        related_context = []
        for chunk in related:
            related_context.append({
                "role": "system",
                "content": [{"type": "text", "text": f"[相关历史] {chunk['content']}"}]
            })
    except Exception as e:
        print(f"[ai_chat_stream_recommend] 检索相关内容失败: {e}")
        related_context = []
    t7 = time.time()
    print(f"[ai_chat_stream_recommend] step6: 检索相关历史总耗时: {t7-t6:.2f}s")

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": _RECOMMEND_MODE_SYSTEM_PROMPT}],
        }
    ]
    for h in history_contents:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.extend(related_context)
    messages.append({"role": "user", "content": msg_content})

    t8 = time.time()
    print(f"[ai_chat_stream_recommend] step7: 拼装messages耗时: {t8-t7:.2f}s")
    t9 = time.time()
    print(f"[ai_chat_stream_recommend] step8: 开始调用大模型, t={t9}")

    def stream_gen():
        return client.chat.completions.create(
            model="qwen3.6-plus",
            messages=messages,
            stream=True,
            stream_options={"include_usage": True}
        )
    loop = asyncio.get_event_loop()
    completion = await loop.run_in_executor(None, stream_gen)
    full_reply = ""
    for chunk in completion:
        if chunk.choices:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
                full_reply += delta
    ai_msg = await create_content(db, session_id, "assistant", full_reply, content_type="text")
    print(f"[ai_chat_stream_recommend] AI回复已存储，长度: {len(full_reply)}")