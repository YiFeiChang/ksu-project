import os
import grpc
from dotenv import load_dotenv

# 載入新模組的啟動函式
from langchain_service import serve_grpc
from line_bot import start_line_bot

# 明確指定 .env 路徑並強制覆蓋系統變數，確保正確讀取設定
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path, override=True)

if __name__ == '__main__':
    try:
        grpc_server: grpc.Server = serve_grpc()
        start_line_bot()
    finally:
        grpc_server.stop(0)
