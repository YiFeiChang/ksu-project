import argparse
import grpc
from dotenv import load_dotenv
import chat_pb2
import chat_pb2_grpc

# 載入 .env 檔案中的環境變數
load_dotenv()

def run(server_address, user_id):
    with grpc.insecure_channel(server_address) as channel:
        stub = chat_pb2_grpc.ChatServiceStub(channel)
        print(f"====== 已連線到 Gemini gRPC 聊天伺服器 ({server_address}) ======")
        print(f"目前登入使用者: {user_id}\n輸入 'quit' 或 'exit' 即可離開\n")
        
        while True:
            text = input("你: ")
            if text.lower() in ['quit', 'exit']:
                print("聊天結束，再見！")
                break
            if not text.strip():
                continue
                
            try:
                # 建立請求並呼叫 RPC
                request = chat_pb2.ChatMessage(text=text, user_id=user_id)
                
                response = stub.SendMessage(request)
                
                print(f"\nGemini: {response.text}\n")
                
            except grpc.RpcError as e:
                # 攔截 gRPC 例外錯誤
                print(f"\n[錯誤] gRPC 呼叫失敗: {e.details()} (狀態碼: {e.code()})\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Gemini gRPC 聊天客戶端")
    parser.add_argument("--server", type=str, default="localhost:50051", help="gRPC 伺服器位址 (預設: localhost:50051)")
    parser.add_argument("--user", type=str, help="使用者 ID")
    args = parser.parse_args()
    
    user_id = args.user
    if not user_id:
        user_id = input("請輸入您的 User ID: ").strip()
    
    if not user_id:
        print("未提供 User ID，將以 'anonymous' 繼續。")
        user_id = "anonymous"
        
    run(args.server, user_id)
