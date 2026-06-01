import os
import grpc
import json
import threading
from concurrent import futures
import google.generativeai as genai
from dotenv import load_dotenv

import chat_pb2
import chat_pb2_grpc

# 載入 .env 檔案中的環境變數
load_dotenv()

# 設定 Gemini API Key (請確保你已經設定了環境變數 GEMINI_API_KEY)
# 你可以到 Google AI Studio 申請免費的 API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("請設定環境變數 GEMINI_API_KEY")

genai.configure(api_key=api_key)

# 設定儲存歷史紀錄的資料夾
HISTORY_DIR = "chat_histories"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

class ChatServiceServicer(chat_pb2_grpc.ChatServiceServicer):
    def __init__(self):
        # 初始化 Gemini 模型
        # 從環境變數取得模型名稱，預設使用 gemini-2.5-flash
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(model_name)
        # 使用字典來管理不同 client 的對話階段
        self.chat_sessions = {}
        # 確保對字典操作時的執行緒安全
        self.lock = threading.Lock()

    def _get_history_file(self, user_id):
        # 簡單過濾一下 user_id 避免路徑問題，並確保有預設值
        safe_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        if not safe_id:
            safe_id = "default"
        return os.path.join(HISTORY_DIR, f"{safe_id}.json")

    def _load_history(self, user_id):
        filepath = self._get_history_file(user_id)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[警告] 讀取歷史紀錄失敗 {user_id}: {e}")
        return []

    def _save_history(self, user_id, chat_session):
        filepath = self._get_history_file(user_id)
        history_data = []
        # 將 Gemini 歷史紀錄格式化為 JSON 支援的形式
        for msg in chat_session.history:
            parts = []
            for part in msg.parts:
                if hasattr(part, 'text') and part.text:
                    parts.append(part.text)
                elif hasattr(part, 'inline_data') and part.inline_data:
                    parts.append("[圖片資料]")
                elif isinstance(part, str):
                    parts.append(part)
            history_data.append({
                "role": msg.role,
                "parts": parts
            })
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 儲存歷史紀錄失敗 {user_id}: {e}")

    def SendMessage(self, request, context):
        # 取得客戶端的連線位址作為識別 (例如: 'ipv4:127.0.0.1:54321')
        client_id = context.peer()
        user_id = request.user_id or "anonymous"
        user_message = request.text
        platform = request.platform or "console"

        print(f"[收到來自 {client_id} (Platform: {platform}, User: {user_id}) 的訊息] {user_message}")
        
        # 針對 LINE 平台訊息可以做的特殊處理，讓 Gemini 更好理解這是一則 LINE 訊息
        if platform.lower() == "line" and request.HasField("line_metadata"):
            line_meta = request.line_metadata
            print(f"[LINE 專屬資訊] Reply Token: {line_meta.reply_token}, Type: {line_meta.message_type}")
            # 在提示詞前加上上下文，讓 Gemini 更能以 LINE 聊天情境回應
            if line_meta.message_type == "sticker":
                # 若為貼圖，將 sticker_id 與對應的關鍵字提示給 Gemini
                user_message = f"【這是一則來自 LINE 平台的貼圖訊息 (Sticker ID: {line_meta.sticker_id})】\n用戶傳送了貼圖，其隱含的內容或關鍵字為: {user_message}"
            else:
                user_message = f"【這是一則來自 LINE 平台的 {line_meta.message_type} 訊息】\n{user_message}"
            
        # 支援多模態：準備傳送給 Gemini 的內容陣列
        message_parts = [user_message]
        if request.image_data:
            mime_type = request.image_mime_type or "image/jpeg"
            message_parts.append({
                "mime_type": mime_type,
                "data": request.image_data
            })
            print(f"[收到圖片資料] 大小: {len(request.image_data)} bytes, 類型: {mime_type}")

        # 改為使用 user_id 建立與管理 chat_session
        with self.lock:
            if user_id not in self.chat_sessions:
                history = self._load_history(user_id)
                self.chat_sessions[user_id] = self.model.start_chat(history=history)
            chat_session = self.chat_sessions[user_id]

        try:
            # 將訊息 (包含可能的圖片) 傳送給 Gemini
            response = chat_session.send_message(message_parts)
            print(f"[{user_id} 回覆訊息] {response.text}")
            
            # 儲存對話紀錄到 JSON
            with self.lock:
                self._save_history(user_id, chat_session)

            # 回傳包裝好的 gRPC 回應
            return chat_pb2.ChatReply(text=response.text)
            
        except Exception as e:
            error_msg = str(e).lower()
            # 判斷是否為用量限制 (Quota) 或資源耗盡 (Exhausted / 429) 的錯誤
            if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                print(f"[{user_id} 觸發用量限制] {str(e)}")
                return chat_pb2.ChatReply(text="不好意思，我的 API 用量暫時達到上限了，請稍後再跟我聊天吧！")
            
            # 其他未預期的系統錯誤處理機制
            context.set_details(f'Gemini API 發生錯誤: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return chat_pb2.ChatReply()

def serve():
    # 建立 gRPC 伺服器，設定最多 10 個 Worker
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServiceServicer(), server)
    
    # 取得監聽位址，預設為 [::]:50051
    bind_address = os.environ.get("GRPC_BIND_ADDRESS", "[::]:50051")
    server.add_insecure_port(bind_address)
    print(f"gRPC 伺服器已啟動，監聽 {bind_address}...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
