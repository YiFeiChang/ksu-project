import os
import grpc
from flask import Flask, request, abort
from dotenv import load_dotenv

# 引入 line-bot-sdk v3 模組
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    MessagingApiBlob
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
    ImageMessageContent
)

import chat_pb2
import chat_pb2_grpc

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# 初始化 LINE 設定
channel_secret = os.environ.get('LINE_CHANNEL_SECRET')
channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')

if not channel_secret or not channel_access_token:
    raise ValueError("請確認 .env 檔案中已經設定好 LINE_CHANNEL_SECRET 與 LINE_CHANNEL_ACCESS_TOKEN")

configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(channel_secret)

# gRPC 伺服器連線位址
GRPC_SERVER_ADDRESS = os.environ.get("GRPC_BIND_ADDRESS", "localhost:50051").replace("[::]", "localhost")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. 請檢查 Channel Secret 是否正確。")
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=(TextMessageContent, StickerMessageContent, ImageMessageContent))
def handle_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    
    text_content = ""
    image_data = b""
    image_mime_type = ""
    message_type = "text"
    sticker_id = ""

    # 判斷訊息類型
    if isinstance(event.message, TextMessageContent):
        text_content = event.message.text
        message_type = "text"
    elif isinstance(event.message, StickerMessageContent):
        text_content = event.message.keywords[0] if event.message.keywords else "貼圖"
        message_type = "sticker"
        sticker_id = event.message.sticker_id
    elif isinstance(event.message, ImageMessageContent):
        message_type = "image"
        with ApiClient(configuration) as api_client:
            line_bot_blob_api = MessagingApiBlob(api_client)
            image_data = line_bot_blob_api.get_message_content(event.message.id)
            image_mime_type = "image/jpeg"

    # 呼叫 Gemini gRPC 伺服器處理對話
    try:
        with grpc.insecure_channel(GRPC_SERVER_ADDRESS) as channel:
            stub = chat_pb2_grpc.ChatServiceStub(channel)
            line_meta = chat_pb2.LineMetadata(reply_token=reply_token, message_type=message_type, message_id=event.message.id, sticker_id=sticker_id)
            request_msg = chat_pb2.ChatMessage(text=text_content, user_id=user_id, platform="line", line_metadata=line_meta, image_data=image_data, image_mime_type=image_mime_type)
            response = stub.SendMessage(request_msg)
            
            # 將 Gemini 產生的回覆傳回給 LINE 用戶
            with ApiClient(configuration) as api_client:
                MessagingApi(api_client).reply_message(ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=response.text)]))
    except Exception as e:
        print(f"與 gRPC 伺服器通訊時發生錯誤: {e}")

if __name__ == "__main__":
    # 改由環境變數 PORT 決定，若無則預設使用 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port)
