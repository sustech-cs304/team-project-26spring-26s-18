from typing import List, Dict, Any
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 文档加载与分块
def load_documents(directory_path: str) -> Dict[str, str]:
    """加载目录下的文件，支持 txt/md/pdf/docx/pptx"""
    documents = {}
    path = Path(directory_path)
    
    if not path.exists():
        path.mkdir(parents=True)
        print(f"已创建文档目录: {directory_path}")
        return documents
    
    # 文本文件直接读取
    for ext in ["*.txt", "*.md"]:
        for file_path in path.glob(ext):
            with open(file_path, 'r', encoding='utf-8') as f:
                documents[file_path.name] = f.read()
    
    # PDF 文件
    for file_path in path.glob("*.pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            documents[file_path.name] = text
            print(f"已解析PDF: {file_path.name}")
        except ImportError:
            print(f"跳过PDF {file_path.name}，需要安装: pip install pypdf")
        except Exception as e:
            print(f"PDF解析失败 {file_path.name}: {e}")
    
    # DOCX 文件
    for file_path in path.glob("*.docx"):
        try:
            from docx import Document
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            documents[file_path.name] = text
            print(f"已解析DOCX: {file_path.name}")
        except ImportError:
            print(f"跳过DOCX {file_path.name}，需要安装: pip install python-docx")
        except Exception as e:
            print(f"DOCX解析失败 {file_path.name}: {e}")
    
    # PPTX 文件
    for file_path in path.glob("*.pptx"):
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            text = "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
            documents[file_path.name] = text
            print(f"已解析PPTX: {file_path.name}")
        except ImportError:
            print(f"跳过PPTX {file_path.name}，需要安装: pip install python-pptx")
        except Exception as e:
            print(f"PPTX解析失败 {file_path.name}: {e}")
    
    return documents


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


def load_and_chunk_documents(directory_path: str) -> List[Dict[str, Any]]:
    """加载文档并切块"""
    documents = load_documents(directory_path)
    all_chunks = []
    
    for filename, content in documents.items():
        chunks = split_into_chunks(content)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "content": chunk,
                "source": filename,
                "chunk_id": i
            })
    
    return all_chunks


# 向量化服务
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


# 向量数据库
import chromadb
from chromadb.config import Settings

class VectorStore:
    def __init__(self, collection_name: str = "campus_handbook"):
        self.client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        try:
            self.client.delete_collection(collection_name)
        except:
            pass
        self.collection = self.client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print("向量数据库初始化完成")
    
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


# LLM服务
from dashscope import Generation
from http import HTTPStatus

class LLMService:
    def __init__(self, model_name: str = "qwen-turbo"):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")
        dashscope.api_key = self.api_key
        self.model_name = model_name
        print(f"LLM服务: {self.model_name}")
    
    def generate(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        context_text = ""
        for chunk in context_chunks[:3]:
            context_text += f"\n[来源: {chunk['source']}]\n{chunk['content']}\n"
        
        prompt = f"""你是南方科技大学的校园助手。根据以下内容回答问题。

检索到的内容：
{context_text}

用户问题：{query}

要求：只使用上述内容回答，没有就说找不到。回答简洁。

回答："""
        
        try:
            response = Generation.call(
                model=self.model_name,
                prompt=prompt,
                result_format='text'
            )
            if response.status_code == HTTPStatus.OK:
                return response.output.text
            else:
                return f"API调用失败: {response.message}"
        except Exception as e:
            return f"生成失败: {e}"


# RAG主类
class CampusEncyclopediaRAG:
    def __init__(self, documents_dir: str = "./campus_docs"):
        print("RAG系统初始化")
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.reranker = Reranker()
        self.llm_service = LLMService()
        self._index_documents(documents_dir)
    
    def _index_documents(self, documents_dir: str):
        print(f"\n文档目录: {documents_dir}")
        
        chunks = load_and_chunk_documents(documents_dir)
        print(f"共加载 {len(chunks)} 个文档块")
        
        if not chunks:
            print("没有找到文档，请把文件放进 ./campus_docs 目录")
            return
        
        print("正在生成向量...")
        texts = [chunk['content'] for chunk in chunks]
        embeddings = self.embedding_service.embed_batch(texts)
        self.vector_store.add_chunks(chunks, embeddings)
        print("索引完成\n")
    
    def ask(self, query: str, use_rerank: bool = True) -> Dict[str, Any]:
        query_embedding = self.embedding_service.embed(query)
        retrieved = self.vector_store.search(query_embedding, top_k=5)
        
        if not retrieved:
            return {"query": query, "answer": "抱歉，没有找到相关信息。", "sources": []}
        
        print(f"找到 {len(retrieved)} 个相关片段")
        for r in retrieved:
            print(f"  - {r['source']} (相似度: {r['score']:.2f})")
        
        if use_rerank:
            print("正在重排序...")
            retrieved = self.reranker.rerank(query, retrieved, top_k=3)
        
        answer = self.llm_service.generate(query, retrieved)
        return {"query": query, "answer": answer, "sources": retrieved}


# 主程序
def main():
    rag = CampusEncyclopediaRAG()
    print("\n输入问题，输入 quit 退出\n")
    
    while True:
        query = input("请提问: ").strip()
        if query.lower() in ['quit', 'exit', 'q']:
            print("退出")
            break
        if not query:
            continue
        result = rag.ask(query)
        print("\n" + "=" * 50)
        print(f"回答: {result['answer']}")
        print("=" * 50)


if __name__ == "__main__":
    main()