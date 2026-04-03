from openai import OpenAI
import os
import base64
import uuid
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

    # 1. 查询历史消息（最近5条，按时间升序）
    history_msgs = await get_last_n_content_by_session_id(db, session_id, n=5)
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
    user_msg = await create_content(db, session_id, "user", content, content_type="text", name=None)
    user_msgs.append(user_msg)
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
    msg_content.append({"type": "text", "text": content})


    # 3 用向量数据库检索与本次问题最相关的3条数据
    try:
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        query_embedding = embedding_service.embed(content)
        related = vector_store.search(query_embedding, top_k=3)
        related_context = []
        for chunk in related:
            related_context.append({
                "role": "system",
                "content": [{"type": "text", "text": f"[相关历史] {chunk['content']}"}]
            })
    except Exception as e:
        print(f"[ai_chat] 检索相关历史失败: {e}")
        related_context = []

    # 4. 拼装最终 messages
    messages = []
    for h in history_contents:
        messages.append({"role": h["role"], "content": h["content"]})
    # 插入向量数据库中相关内容
    messages.extend(related_context)
    messages.append({"role": "user", "content": msg_content})

    # 5. 调用大模型
    loop = asyncio.get_event_loop()
    completion = await loop.run_in_executor(
        None,
        partial(
            client.chat.completions.create,
            model="qwen3.5-plus",
            messages=messages,
        )
    )
    ai_reply = completion.choices[0].message.content
    # 5. 插入AI回复
    ai_msg = await create_content(db, session_id, "assistant", ai_reply, content_type="text")
    # 6. 返回所有消息对象
    return user_msgs + [ai_msg]