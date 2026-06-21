import json
import argparse
from typing import List, Dict, Any
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer


def load_config(config_path: str) -> Dict[str, Any]:
    """載入 JSON 設定檔"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


class MilvusSearcher:
    """Milvus 搜尋工具類別，供其他模組調用"""

    def __init__(self, config_path: str = "web2milvus.json"):
        self.config = load_config(config_path)
        self.milvus_host = self.config.get("milvus_host", "localhost")
        self.milvus_port = self.config.get("milvus_port", "19530")
        self.collection_name = self.config.get(
            "collection_name", "web_content")
        self.db_name = "ksu_project"

        # 初始化模型 (建議使用 CPU 或檢查 CUDA 是否可用)
        self.model = SentenceTransformer(
            'intfloat/multilingual-e5-small', device='cuda')
        
        # 初始化 MilvusClient
        self.client = MilvusClient(
            uri=f"http://{self.milvus_host}:{self.milvus_port}",
            db_name=self.db_name
        )
        # 確保 Collection 已載入
        self.client.load_collection(self.collection_name)

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """載入 JSON 設定檔"""
        return load_config(config_path)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """對外提供的搜尋介面"""
        return self.search_milvus(query, top_k)

    def close(self):
        """釋放資源"""
        self.client.close()

    def search_milvus(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        在 Milvus 中執行相似度搜尋

        :param query: 查詢字串
        :param top_k: 回傳最相似的結果數量
        :return: 搜尋結果列表
        """
        # 1. 將查詢字串轉換為向量 (e5 模型建議在查詢前加上 "query: " 前綴)
        query_embedding: List[float] = self.model.encode(
            f"query: {query}").tolist()

        # 2. 執行搜尋
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_embedding],
            anns_field="embedding",
            limit=top_k,
            output_fields=["url", "content"],
            search_params={"metric_type": "L2", "params": {"nprobe": 16}}
        )

        # 3. 整理並回傳結果
        search_results: List[Dict[str, Any]] = []
        if results:
            for hit in results[0]:
                search_results.append({
                    "id": hit['id'],
                    "distance": hit['distance'],  # 相似度分數 (L2 距離，越小越相似)
                    "url": hit['entity'].get('url'),
                    "content": hit['entity'].get('content')
                })
        return search_results


def main() -> None:
    """主執行函數"""
    parser = argparse.ArgumentParser(description="在 Milvus 中搜尋網頁內容")
    parser.add_argument("query", type=str, help="要搜尋的關鍵字或句子")
    parser.add_argument("-c", "--config", type=str,
                        default="web2milvus.json", help="設定檔路徑")
    parser.add_argument("-k", "--top_k", type=int, default=3, help="回傳的結果數量")
    args = parser.parse_args()

    # 初始化搜尋器
    searcher = MilvusSearcher(args.config)

    # 執行搜尋
    print(f"\n正在以 '{args.query}' 進行搜尋...")
    search_results: List[Dict[str, Any]] = searcher.search(args.query, args.top_k)

    # 顯示結果
    if not search_results:
        print("找不到相關結果。")
    else:
        print(f"\n找到 {len(search_results)} 個最相關的結果：")
        for i, res in enumerate(search_results):
            print(f"\n--- 結果 {i+1} ---")
            print(f"相似度 (L2 Distance): {res['distance']:.4f}")
            print(f"URL: {res['url']}")
            print(f"內容片段: {res['content'][:200]}...")  # 顯示部分內容

    # 釋放資源
    searcher.close()


if __name__ == "__main__":
    main()
