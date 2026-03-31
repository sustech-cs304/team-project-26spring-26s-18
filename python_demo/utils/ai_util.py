from openai import OpenAI
import os
import base64
import uuid
from utils.oss_util import OSSUtil
from crud.session import create_content
import asyncio
from functools import partial
from utils.pdf_util import extract_pdf_text
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
    # 1. 插入用户文本消息
    user_msg = await create_content(db, session_id, "user", content, content_type="text", name=None)
    user_msgs.append(user_msg)
    # 2. 处理图片，插入图片消息
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
                pdf_text = extract_pdf_text(f, max_len=10000)
                pdf_msg = await create_content(db, session_id, "user", pdf_text, content_type="pdf", name=name)
                msg_content.append({
                    "type": "text",
                    "text": f"pdf不是连接，而是下面的内容: {pdf_text}"
                })
                user_msgs.append(pdf_msg)
    # 3. 组装文本内容
    msg_content.append({"type": "text", "text": content})
    # 4. 调用大模型
    loop = asyncio.get_event_loop()
    completion = await loop.run_in_executor(
        None,
        partial(
            client.chat.completions.create,
            model="qwen3.5-plus",
            messages=[
                {
                    "role": "user",
                    "content": msg_content,
                },
            ],
        )
    )
    ai_reply = completion.choices[0].message.content
    # 5. 插入AI回复
    ai_msg = await create_content(db, session_id, "assistant", ai_reply, content_type="text")
    # 6. 返回所有消息对象
    return user_msgs + [ai_msg]