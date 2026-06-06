import json
import argparse
from typing import List, Dict, Any
from pymilvus import connections, Collection, utility
from sentence_transformers import SentenceTransformer


class MilvusSearcher:
    """Milvus 搜尋工具類別，供其他模組調用"""

    def __init__(self, config_path: str = "web2milvus.json"):
        self.config = self.load_config(config_path)
        self.milvus_host = self.config.get("milvus_host", "localhost")
        self.milvus_port = self.config.get("milvus_port", "19530")
        self.collection_name = self.config.get(
            "collection_name", "web_content")

        # 初始化模型 (建議使用 CPU 或檢查 CUDA 是否可用)
        self.model = SentenceTransformer(
            'intfloat/multilingual-e5-small', device='cuda')
        self.collection = None
        self._connect()

    def _connect(self):
        """建立連線並載入 Collection"""
        try:
            connections.connect("default", host=self.milvus_host,
                                port=self.milvus_port, db_name="ksu_project")
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                self.collection.load()
            else:
                print(f"警告: Collection {self.collection_name} 不存在")
        except Exception as e:
            print(f"Milvus 連線失敗: {e}")

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """載入 JSON 設定檔"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """對外提供的搜尋介面"""
        if not self.collection:
            return []
        return self.search_milvus(query, top_k)

    def close(self):
        """釋放資源"""
        if self.collection:
            self.collection.release()
        try:
            connections.disconnect("default")
        except:
            pass

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

        # 2. 定義搜尋參數
        # nprobe 決定要搜尋多少個 cluster，值越大越準確但越慢
        search_params: Dict[str, Any] = {
            "metric_type": "L2",
            "params": {"nprobe": 16},
        }

        # 3. 執行搜尋
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["url", "content"]  # 指定回傳的欄位
        )

        # 4. 整理並回傳結果
        search_results: List[Dict[str, Any]] = []
        if results:
            for hit in results[0]:
                search_results.append({
                    "id": hit.id,
                    "distance": hit.distance,  # 相似度分數 (L2 距離，越小越相似)
                    "url": hit.entity.get('url'),
                    "content": hit.entity.get('content')
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

    # 載入設定
    config: Dict[str, Any] = load_config(args.config)
    milvus_host: str = config.get("milvus_host", "localhost")
    milvus_port: str = config.get("milvus_port", "19530")
    collection_name: str = config.get("collection_name", "web_content")

    # 初始化嵌入模型
    print("正在載入模型...")
    model: SentenceTransformer = SentenceTransformer(
        'intfloat/multilingual-e5-small', device='cuda')

    # 連線至 Milvus
    try:
        print(f"正在連線至 Milvus ({milvus_host}:{milvus_port})...")
        connections.connect("default", host=milvus_host,
                            port=milvus_port, db_name="ksu_project")

        if not utility.has_collection(collection_name):
            print(f"錯誤: Collection '{collection_name}' 不存在。")
            return

        collection: Collection = Collection(collection_name)
        collection.load()  # 載入 Collection 至記憶體以進行搜尋

    except Exception as e:
        print(f"連線或載入 Milvus Collection 失敗: {e}")
        return

    # 執行搜尋
    print(f"\n正在以 '{args.query}' 進行搜尋...")
    search_results: List[Dict[str, Any]] = search_milvus(
        collection, model, args.query, args.top_k)

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

    # 釋放 Collection 並中斷連線
    collection.release()
    connections.disconnect("default")


if __name__ == "__main__":
    main()
