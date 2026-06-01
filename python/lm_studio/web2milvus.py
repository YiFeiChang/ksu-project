import os
from dotenv import load_dotenv
import json
import requests
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from sentence_transformers import SentenceTransformer
from google import genai

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path, override=True)

def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_webpage_text(url: str) -> str:
    try:
        response: requests.Response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status()
        soup: BeautifulSoup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除 script 與 style 元素以取得純文字
        for script_or_style in soup(["script", "style"]):
            script_or_style.extract()
            
        text: str = soup.get_text(separator=' ', strip=True)
        return text
    except Exception as e:
        print(f"擷取 {url} 失敗: {e}")
        return ""

def init_milvus_collection(collection_name: str, dim: int) -> Collection:
    if utility.has_collection(collection_name):
        return Collection(collection_name)
    
    fields: List[FieldSchema] = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="url", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
    ]
    
    schema: CollectionSchema = CollectionSchema(fields=fields, description="Web content embeddings")
    collection: Collection = Collection(name=collection_name, schema=schema)
    
    # 建立索引
    index_params: Dict[str, Any] = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    return collection

def main() -> None:
    config_path: str = "web2milvus.json"
    config: Dict[str, Any] = load_config(config_path)
    
    urls: List[str] = config.get("urls", [])
    milvus_host: str = config.get("milvus_host", "localhost")
    milvus_port: str = config.get("milvus_port", "19530")
    collection_name: str = config.get("collection_name", "web_content")
    
    gemini_client = genai.Client(
        api_key=os.getenv("GOOGLE_API_KEY", "")
    )
    
    # 初始化嵌入模型 (intfloat/multilingual-e5-small 輸出維度為 384)
    model: SentenceTransformer = SentenceTransformer('intfloat/multilingual-e5-small', device='cuda')
    vector_dim: int = model.get_embedding_dimension()
    
    # 連線至 Milvus
    connections.connect("default", host=milvus_host, port=milvus_port, db_name="ksu_project")
    collection: Collection = init_milvus_collection(collection_name, vector_dim)
    
    for url in urls:
        # 下載網頁內容
        print(f"正在處理: {url}")
        text: str = fetch_webpage_text(url)
        if text:
            print(f"正在總結內容: {url}...")
            prompt = f"將以下網頁內容總結至 1000 字以內，保留關鍵資訊，直接輸出總結內容：\n\n{text}"
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt
                )
                summary = response.text
            except Exception as e:
                print(f"總結失敗，改用截斷方式: {e}")
                summary = text[:1000]
            
            # 轉換為向量 (e5 模型建議在查詢前加上 "passage: " 前綴)
            print(f"正在生成向量: {url}...")
            embedding = model.encode([f"passage: {summary}"]).tolist()
            
            # 立即寫入 Milvus
            print(f"正在寫入 Milvus: {url}...")
            insert_data = [
                [url],
                [summary],
                embedding
            ]
            collection.insert(insert_data)

    collection.flush()
    print(f"所有處理程序已完成，資料已同步至 Collection '{collection_name}'。")

if __name__ == "__main__":
    main()