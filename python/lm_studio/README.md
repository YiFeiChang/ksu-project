# LM Studio LangGraph gRPC Chatbot

這是一個結合 LM Studio、LangGraph、gRPC 和 LINE Bot 的聊天機器人專案。透過 gRPC 架構，可以將終端機客戶端 (`client.py`) 或 LINE Bot 應用程式 (`line_bot.py`) 的訊息傳送到後端服務 (`langchain_service.py`)。後端服務使用 LangGraph 建構一個具備工具使用能力的 AI 代理 (Agent)，並向本地端的 LM Studio 請求 AI 模型生成回覆。

## 專案結構

- `server.py`: 專案主啟動腳本，負責同時啟動 gRPC 伺服器與 LINE Bot 伺服器。
- `langchain_service.py`: gRPC 服務的核心實作。使用 LangGraph 建構一個 Agent，負責處理對話邏輯、呼叫 LM Studio AI 模型，並具備使用工具的能力。同時也處理對話歷史的儲存與讀取。
- `client.py`: 終端機 gRPC 客戶端，供使用者直接在命令列與模型對話。
- `line_bot.py`: 基於 Flask 的 LINE Bot Webhook 應用程式，接收 LINE 訊息後轉發給 gRPC 伺服器。
- `test_model.py`: 測試腳本，用來確認是否能成功連線至 LM Studio 的 Local Server。
- `chat.proto`: 定義 gRPC 服務與訊息格式的 Protocol Buffers 檔案。
- `chat_pb2.py`, `chat_pb2_grpc.py`: 由 `chat.proto` 編譯生成的 Python 檔案。

## 安裝套件

執行本專案前，請確認安裝了相關的 Python 依賴套件。您可以使用以下指令安裝：

```bash
pip install dotenv grpcio grpcio-tools protobuf openai langchain langchain-openai langchain-core python-dotenv flask langgraph
```

## 環境變數設定 (`.env`)

請在專案根目錄下建立 `.env` 檔案，並填入以下設定檔內容：

```dotenv
# ==========================================
# LM Studio 相關設定
# ==========================================
# LM Studio Local Server 啟動的 API 網址，請確認 Port 號 (常見為 1234 或 5500)
LM_STUDIO_BASE_URL=http://127.0.0.1:5500/v1

# API 金鑰，使用 LM Studio 時通常不需要嚴格驗證，預設填入 lm-studio 即可
LM_STUDIO_API_KEY=lm-studio

# 模型名稱，請填入您在 LM Studio 中載入的 Model Identifier
LM_STUDIO_MODEL=google/gemma-4-e2b

# API 請求等待的超時秒數，對於本機跑較大的模型可以設定長一點以防 Timeout
LM_STUDIO_TIMEOUT=120

# ==========================================
# gRPC 伺服器設定
# ==========================================
# gRPC 伺服器的監聽位址與埠號，預設為本機所有介面的 50051 Port
GRPC_BIND_ADDRESS=[::]:50051

# ==========================================
# LINE Bot 相關設定
# ==========================================
# line_app.py 運行的 Webhook Port 號
PORT=5000

# 請從 LINE Developers Console 中取得以下資訊並填入
LINE_CHANNEL_ID=您的_LINE_CHANNEL_ID
LINE_CHANNEL_SECRET=您的_LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN=您的_LINE_CHANNEL_ACCESS_TOKEN
```

## 執行步驟

### 1. 啟動 LM Studio
1. 開啟 LM Studio 應用程式。
2. 載入您想使用的模型 (確保名稱與 `.env` 中的 `LM_STUDIO_MODEL` 吻合)。
3. 進入「Local Server」分頁，確認 Port 號與 `.env` 設定一致，點擊 **Start Server**。

### 2. (選用) 測試連線
執行測試腳本，確保程式能與 LM Studio 正常溝通：
```bash
python test_model.py
```

### 3. 啟動對話服務
- **啟動 gRPC Server**：先啟動後端伺服器接收對話請求。
  `python server.py`
- **啟動終端機聊天**：(新開一個終端機視窗) 啟動命令列介面互動。
  `python client.py`
- **啟動 LINE Bot**：(新開一個終端機視窗) 啟動 Flask 應用接收 LINE 訊息。
  `python line_app.py`