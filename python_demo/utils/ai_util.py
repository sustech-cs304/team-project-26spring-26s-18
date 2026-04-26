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

# 推荐模式专用流式接口：精简回复
async def ai_chat_stream_recommend(
    db,
    session_id: int,
    content: str,
    files=None,
    file_types=None,
    file_names=None
):
    """
    推荐模式专用AI对话接口（流式）。
    特点：回复精简，适合与资源推荐卡片配合使用。
    """
    msg_content = []
    user_msgs = []

    t0 = time.time()
    print(f"[ai_chat_stream_recommend] step0: 开始, t={t0}")
    # 1. 查询历史消息（最近3条，保持简短）
    t1 = time.time()
    history_msgs = await get_last_n_content_by_session_id(db, session_id, n=3)
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

    # 2. 处理本次用户文本和文件
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

    # 3. 同时进行向量数据库检索和网络搜索
    t6 = time.time()
    related_context = []
    web_resources = []

    # 3.1 向量数据库检索
    try:
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        t6_1 = time.time()
        query_embedding = embedding_service.embed(content)
        t6_2 = time.time()
        print(f"[ai_chat_stream_recommend] step4: query embedding耗时: {t6_2-t6_1:.2f}s")
        related = vector_store.search(query_embedding, top_k=5)
        t6_3 = time.time()
        print(f"[ai_chat_stream_recommend] step5: 向量检索耗时: {t6_3-t6_2:.2f}s")

        has_knowledge_base_content = len(related) > 0 and any(r.get('score', 0) > 0.3 for r in related)

        if has_knowledge_base_content:
            related_context.append({
                "role": "system",
                "content": [{"type": "text", "text": "[知识库检索结果] 找到以下相关内容："}]
            })
            for i, chunk in enumerate(related[:3], 1):
                if chunk.get('score', 0) > 0.3:
                    related_context.append({
                        "role": "system",
                        "content": [{"type": "text", "text": f"{i}. 来源：{chunk.get('source', '未知')} | 相关内容：{chunk.get('content', '')[:300]}..."}]
                    })
        else:
            related_context.append({
                "role": "system",
                "content": [{"type": "text", "text": "[知识库检索结果] 未在知识库中找到相关内容。"}]
            })
    except Exception as e:
        print(f"[ai_chat_stream_recommend] 向量检索失败: {e}")
        has_knowledge_base_content = False
        related_context.append({
            "role": "system",
            "content": [{"type": "text", "text": "[知识库检索结果] 知识库检索失败。"}]
        })

    # 3.2 网络搜索
    try:
        from utils.recommend_resources_util import search_web_duckduckgo
        web_results = search_web_duckduckgo(content, max_items=5)
        t6_4 = time.time()
        print(f"[ai_chat_stream_recommend] step5b: 网络搜索耗时: {t6_4-t6_3:.2f}s")

        if web_results:
            web_resources.append({
                "role": "system",
                "content": [{"type": "text", "text": "[网络搜索资源] 找到以下相关网页："}]
            })
            for i, result in enumerate(web_results[:3], 1):
                web_resources.append({
                    "role": "system",
                    "content": [{"type": "text", "text": f"{i}. {result.get('title', '无标题')} - {result.get('url', '')}\n摘要：{result.get('snippet', '无摘要')[:150]}"}]
                })
        else:
            web_resources.append({
                "role": "system",
                "content": [{"type": "text", "text": "[网络搜索资源] 未找到相关网络资源。"}]
            })
    except Exception as e:
        print(f"[ai_chat_stream_recommend] 网络搜索失败: {e}")
        web_resources.append({
            "role": "system",
            "content": [{"type": "text", "text": "[网络搜索资源] 网络搜索失败。"}]
        })

    t7 = time.time()
    print(f"[ai_chat_stream_recommend] step6: 检索总耗时: {t7-t6:.2f}s")

    # 4. 拼装最终 messages（添加智能回复的system prompt）
    messages = []
    # 添加智能回复的 system prompt
    system_prompt = """你是学生助手。请遵循以下规则回答问题：

1. 如果[知识库检索结果]中有相关内容，优先基于知识库内容回答，并简要提及相关资源
2. 如果知识库中没有相关内容，但[网络搜索资源]中有，请基于网络资源回答，并在回答末尾提供1-2个最相关的网址链接
3. 如果两者都没有，给出简短建议，并建议用户尝试更换关键词或上传相关资料
4. 回答要精炼（2-3句话），不要重复列举所有资源
5. 提供网址时使用Markdown格式：[标题](URL)"""

    messages.append({
        "role": "system",
        "content": [{"type": "text", "text": system_prompt}]
    })
    for h in history_contents:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.extend(related_context)
    messages.extend(web_resources)
    messages.append({"role": "user", "content": msg_content})

    t8 = time.time()
    print(f"[ai_chat_stream_recommend] step7: 拼装messages耗时: {t8-t7:.2f}s")
    # 5. 调用大模型（流式）
    t9 = time.time()
    print(f"[ai_chat_stream_recommend] step8: 开始调用大模型, t={t9}")
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
    print(f"[ai_chat_stream_recommend] AI回复已存储，长度: {len(full_reply)}")


import json
import asyncio
from functools import partial

# 定义 Agent 可调用的工具列表（对应已有的专业模式）
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "use_campus_assistant",
            "description": "当用户询问校园生活、政策、设施、校历、活动、选课、宿舍、食堂等与校园相关的问题时调用此工具。它会检索校园知识库并给出详细回答。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_question": {
                        "type": "string",
                        "description": "用户提出的原始问题，将原样传递给校园助手处理"
                    }
                },
                "required": ["user_question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "use_learning_assistant",
            "description": "当用户询问学习、作业、笔记、文献、课程内容、知识点讲解、考试复习等与学习相关的问题时调用此工具。它更注重对话历史的连续性和深度解释。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_question": {
                        "type": "string",
                        "description": "用户提出的原始问题，将原样传递给学习助手处理"
                    }
                },
                "required": ["user_question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "direct_answer",
            "description": "当用户问题比较简单、属于打招呼、常识问答、或者无需调用专业助手即可回答时使用。例如：你好、今天天气、简单计算等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "直接回复用户的内容"
                    }
                },
                "required": ["response"]
            }
        }
    }
]


async def agent_chat_stream(
    db,
    session_id: int,
    content: str,
    files=None,
    file_types=None,
    file_names=None
):
    """
    Agent 调度模式（流式）：
    1. 让千问决定调用哪个工具（campus/learning/direct）
    2. 流式发送决策过程（JSON 行）
    3. 调用对应的子模式函数，将其流式输出透传
    """
    # ---------- 1. 保存用户消息到数据库 ----------
    user_msg = await create_content(db, session_id, "user", content, content_type="text", name=None)
    # 文件处理：直接透传给后续子模式，此处不重复存储
    # （子模式内部会处理文件存储）

    # ---------- 2. 构建第一轮决策对话 ----------
    system_prompt = (
        "你是一个智能调度助手。根据用户的问题，判断应该调用哪个专业工具：\n"
        "- use_campus_assistant: 校园生活、政策、设施、校历、选课、宿舍、食堂等\n"
        "- use_learning_assistant: 学习、作业、笔记、文献、课程内容、知识点讲解等\n"
        "- direct_answer: 简单问候、常识问答、无需专业检索的问题\n"
        "请选择最合适的工具并填写参数，若总结pdf、md文档，则一定调用use_learning_assistant"
    )

    decision_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ]

    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None,
            partial(
                client.chat.completions.create,
                model="qwen-max",      # qwen-max 对 function calling 支持更稳定
                messages=decision_messages,
                tools=AGENT_TOOLS,
                tool_choice="auto"
            )
        )
    except Exception as e:
        # 如果 function calling 失败，降级为直接使用校园助手
        print(f"[Agent] 决策调用失败: {e}，降级为校园助手")
        tool_name = "use_campus_assistant"
        tool_args = {"user_question": content}
        # 发送降级思考信息
        yield json.dumps({
            "type": "thought",
            "content": f"🤔 决策调用失败，默认使用校园助手处理您的问题。",
            "tool_name": tool_name
        }, ensure_ascii=False) + "\n"
    else:
        msg = response.choices[0].message
        tool_calls = msg.tool_calls

        if not tool_calls:
            # 没有工具调用，可能直接回复了（罕见情况）
            reply = msg.content or "好的，请告诉我您需要什么帮助。"
            for char in reply:
                yield char
                await asyncio.sleep(0.01)
            await create_content(db, session_id, "assistant", reply, content_type="text")
            return

        # 取第一个工具调用
        tool_call = tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)

        # 发送思考过程给前端（JSON 行）
        thought_content = f"🤔 分析您的问题后，我将调用【{tool_name}】来处理。"
        yield json.dumps({
            "type": "thought",
            "content": thought_content,
            "tool_name": tool_name,
            "tool_args": tool_args
        }, ensure_ascii=False) + "\n"

    # ---------- 3. 根据工具名调用对应的子模式流式函数 ----------
    # 准备子问题：对于专业工具，传递原始问题；对于 direct_answer，直接返回预设回复
    if tool_name == "use_campus_assistant":
        sub_content = tool_args.get("user_question", content)
        # 调用校园助手流式函数
        async for chunk in ai_chat_stream_less_history_more_rag(
            db=db,
            session_id=session_id,
            content=sub_content,
            files=files,
            file_types=file_types,
            file_names=file_names
        ):
            yield chunk

    elif tool_name == "use_learning_assistant":
        sub_content = tool_args.get("user_question", content)
        async for chunk in ai_chat_stream_more_history_no_rag(
            db=db,
            session_id=session_id,
            content=sub_content,
            files=files,
            file_types=file_types,
            file_names=file_names
        ):
            yield chunk

    elif tool_name == "direct_answer":
        reply = tool_args.get("response", "好的，我明白了。")
        for char in reply:
            yield char
            await asyncio.sleep(0.01)
        await create_content(db, session_id, "assistant", reply, content_type="text")

    else:
        # 未知工具，降级为校园助手
        print(f"[Agent] 未知工具 {tool_name}，降级为校园助手")
        async for chunk in ai_chat_stream_less_history_more_rag(
            db=db,
            session_id=session_id,
            content=content,
            files=files,
            file_types=file_types,
            file_names=file_names
        ):
            yield chunk