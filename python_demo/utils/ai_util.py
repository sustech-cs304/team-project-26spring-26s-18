from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def chat_with_ai(
    content: str,
    model: str = "qwen3-max",
    history_messages: list = None,
    related_messages: list = None
) -> str:
    """
    输入一段内容，调用阿里云百炼大模型生成回复。
    :param content: 用户输入内容
    :param model: 使用的模型，默认qwen3-max
    :param history_messages: 聊天历史消息列表，可为None或空
    :param related_messages: 参考资料消息列表，可为None或空
    :return: AI回复内容
    """
    messages = []
    # system 提示
    messages.append({"role": "system", "content": "简明回答，不要说废话"})
    # 拼接历史消息
    if history_messages:
        messages.append({"role": "system", "content": "以下是历史消息"})
        messages.extend(history_messages)
    # 拼接参考资料
    if related_messages:
        messages.append({"role": "system", "content": "以下是参考资料"})
        messages.extend(related_messages)
    # 当前用户输入
    messages.append({"role": "user", "content": content})
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        extra_body={"enable_thinking": True},
        stream=False
    )
    return response.choices[0].message.content.strip()