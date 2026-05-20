from typing import List, Dict, Any
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from io import BytesIO
from pypdf import PdfReader
from docx import Document
from pptx import Presentation
load_dotenv()

# 向量化服务,调用第三方API进行文本向量化
import dashscope
from dashscope import TextEmbedding

class EmbeddingService:
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")
        dashscope.api_key = self.api_key
        self.model = "text-embedding-v1"
        self.dimension = 768
        print(f"Embedding模型: {self.model}")
    
    def embed(self, text: str) -> List[float]:
        try:
            resp = TextEmbedding.call(model=self.model, input=text)
            if resp.status_code == 200:
                return resp.output['embeddings'][0]['embedding']
            else:
                print(f"Embedding失败: {resp.message}")
                return [0.0] * self.dimension
        except Exception as e:
            print(f"Embedding异常: {e}")
            return [0.0] * self.dimension
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(text) for text in texts]


# 向量数据库，用来存储和检索文档块的向量表示
import chromadb
from chromadb.config import Settings

class VectorStore:
    def __init__(self, collection_name: str = "campus_handbook"):
        self.client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        # 检查collection是否已存在,没有则创建
        existing_collections = [c.name for c in self.client.list_collections()]
        if collection_name in existing_collections:
            self.collection = self.client.get_collection(collection_name)
            print(f"向量数据库已存在，复用 collection: {collection_name}")
        else:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"新建向量数据库 collection: {collection_name}")
    
    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        ids = [f"{chunk['source']}_{chunk['chunk_id']}" for chunk in chunks]
        documents = [chunk['content'] for chunk in chunks]
        metadatas = [{"source": chunk['source']} for chunk in chunks]
        self.collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        print(f"已添加 {len(chunks)} 个文档块")
    
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        retrieved = []
        for i in range(len(results['documents'][0])):
            retrieved.append({
                "content": results['documents'][0][i],
                "source": results['metadatas'][0][i]['source'],
                "score": 1 - results['distances'][0][i]
            })
        return retrieved


# 重排序服务
class Reranker:
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")
        self.model = "qwen3-vl-rerank"
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
        print(f"重排序服务: {self.model}")
    
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        
        documents = [cand['content'] for cand in candidates]
        payload = {
            "model": self.model,
            "input": {"query": query, "documents": documents},
            "parameters": {"return_documents": True, "top_n": top_k}
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        try:
            response = requests.post(self.url, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                reranked = []
                for item in result.get('output', {}).get('results', []):
                    original_idx = item.get('index', 0)
                    if original_idx < len(candidates):
                        reranked.append({
                            **candidates[original_idx],
                            'rerank_score': item.get('relevance_score', 0)
                        })
                return reranked
            else:
                print(f"重排序失败: {response.status_code}")
                return candidates[:top_k]
        except Exception as e:
            print(f"重排序异常: {e}")
            return candidates[:top_k]
        
# 辅助函数，用于store_document切割文本为块
def split_into_chunks(text: str, chunk_size: int = 500) -> List[str]:
    """切分文本，每块约chunk_size字符"""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    
    return chunks
# 批量存储文档内容到向量数据库
def store_document(files: List[str], file_types: List[str], file_names: List[str], chunk_size: int = 500):
    """
    批量处理文件内容，分块、向量化并存入向量数据库。
    files: 已解码的文件内容数组（str）
    file_types: 文件类型数组（如 'text/plain', 'application/pdf' 等）
    file_names: 文件名数组
    chunk_size: 分块大小
    """
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    total_chunks = 0

    for idx, content in enumerate(files):
        filename = file_names[idx]
        file_type = file_types[idx]
        text = ""
        # 按文件类型解析内容
        if file_type in ["text/plain", "text/markdown"]:
            # 文本类型需decode为str
            text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else content
        elif file_type == "application/pdf":
            try:
                reader = PdfReader(BytesIO(content))
                text = "\n".join([page.extract_text() or "" for page in reader.pages])
            except Exception as e:
                print(f"PDF解析失败 {filename}: {e}")
                text = ""
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                doc = Document(BytesIO(content))
                text = "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                print(f"DOCX解析失败 {filename}: {e}")
                text = ""
        elif file_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            try:
                prs = Presentation(BytesIO(content))
                text = "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
            except Exception as e:
                print(f"PPTX解析失败 {filename}: {e}")
                text = ""
        else:
            print(f"暂不支持的文件类型: {file_type}, 按文本处理")
            text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else content

        chunks = split_into_chunks(text, chunk_size=chunk_size)
        chunk_dicts = [
            {"content": chunk, "source": filename, "chunk_id": i}
            for i, chunk in enumerate(chunks)
        ]
        embeddings = embedding_service.embed_batch([c["content"] for c in chunk_dicts])
        vector_store.add_chunks(chunk_dicts, embeddings)
        total_chunks += len(chunk_dicts)
    print(f"所有文件处理完成，总计分块数: {total_chunks}")