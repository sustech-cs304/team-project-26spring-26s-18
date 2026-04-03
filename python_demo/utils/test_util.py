import os
from openai import OpenAI
import time
from utils.rag_util import EmbeddingService, VectorStore

client = OpenAI(
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    # 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # 各地域配置不同，请根据实际地域修改
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 受控RAG测试：只允许用数据库内容回答
def rag_strict_answer(query: str, top_k: int = 3) -> str:
    """
    检索数据库内容并用受控prompt生成答案，只允许用数据库内容回答。
    """
    t0 = time.time()
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    t1 = time.time()
    query_embedding = embedding_service.embed(query)
    print(f"向量化耗时: {time.time() - t1:.2f}s")
    t2 = time.time()
    retrieved = vector_store.search(query_embedding, top_k=top_k)
    print(f"数据库检索耗时: {time.time() - t2:.2f}s")
    if not retrieved:
        print(f"总耗时: {time.time() - t0:.2f}s")
        return "抱歉，没有找到相关信息。"
    context_text = "".join([
        f"\n[来源: {chunk['source']}]\n{chunk['content']}\n" for chunk in retrieved
    ])
    prompt = f"""你是南方科技大学的校园助手。根据以下内容回答问题。\n\n检索到的内容：\n{context_text}\n用户问题：{query}\n\n要求：只使用上述内容回答，没有就说找不到。回答简洁。\n\n回答："""
    print(prompt.encode('gbk', errors='replace').decode('gbk'))
    t3 = time.time()
    completion = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[{"role": "user", "content": prompt}]
    )
    print(f"大模型生成耗时: {time.time() - t3:.2f}s")
    print(f"总耗时: {time.time() - t0:.2f}s")
    return completion.choices[0].message.content.strip()


def ai_chat_test(question: str) -> str:
    """
    直接用大模型接口测试AI响应速度，不走RAG流程。
    """
    t0 = time.time()
    completion = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[{"role": "user", "content": question}]
    )
    print(f"AI直接生成耗时: {time.time() - t0:.2f}s")
    return completion.choices[0].message.content.strip()