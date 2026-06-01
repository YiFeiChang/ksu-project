import os
import grpc
from dotenv import load_dotenv
import json
import requests
import hmac
import hashlib
import base64

from flask import Flask, request, abort

import chat_pb2
import chat_pb2_grpc

from typing import Dict

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path, override=True)

app = Flask(__name__)
channel_secret = os.environ.get('LINE_CHANNEL_SECRET')
channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')

if not channel_secret or not channel_access_token:
    raise ValueError(
        "請確認 .env 檔案中已經設定好 LINE_CHANNEL_SECRET 與 LINE_CHANNEL_ACCESS_TOKEN")

GRPC_SERVER_ADDRESS = os.environ.get("GRPC_BIND_ADDRESS", "localhost:50051").replace("[::]", "localhost")
LINE_PROFILE_API = "https://api.line.me/v2/bot/profile/{userId}"
LINE_MARK_AS_READ_API = "https://api.line.me/v2/bot/chat/markAsRead"
LINE_CONTENT_API="https://api-data.line.me/v2/bot/message/{message_id}/content"


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        hash = hmac.new(channel_secret.encode('utf-8'),
                        body.encode('utf-8'), hashlib.sha256).digest()
        calculated_signature = base64.b64encode(hash).decode('utf-8')
        if calculated_signature != signature:
            raise ValueError("Invalid signature")
    except ValueError:
        app.logger.error("Invalid signature. 請檢查 Channel Secret 是否正確。")
        abort(400)

    events = json.loads(body)['events']
    for event in events:
        if event['type'] == 'message':
            handle_message(event)
    return 'OK'


def handle_message(event):
    message_type = event['message']['type']
    if message_type not in ['text', 'sticker', 'image']:
        app.logger.info(f"忽略不支援的訊息類型: {message_type}")
        return

    user_id = event['source']['userId']
    reply_token = event['replyToken']
    mark_as_read_token = event['message'].get('markAsReadToken')

    user_display_name = ""
    user_profile_json = ""

    if mark_as_read_token:
        try:
            mark_as_read_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {channel_access_token}'
            }
            mark_as_read_data = {"markAsReadToken": mark_as_read_token}
            mark_as_read_response = requests.post(
                LINE_MARK_AS_READ_API, headers=mark_as_read_headers, json=mark_as_read_data)
            mark_as_read_response.raise_for_status()
            app.logger.info(
                f"Marked message as read for user {user_id} using markAsReadToken.")
        except requests.exceptions.RequestException as e:
            app.logger.error(
                f"Failed to mark message as read for user {user_id}: {e}")

    try:
        profile_headers = {
            'Authorization': f'Bearer {channel_access_token}'
        }
        profile_response = requests.get(LINE_PROFILE_API.format(
            userId=user_id), headers=profile_headers)
        profile_response.raise_for_status()
        user_profile = profile_response.json()
        user_display_name = user_profile.get("displayName", "")
        user_profile_json = json.dumps(user_profile, ensure_ascii=False)
        app.logger.info(
            f"Fetched user profile for {user_id}: {user_profile_json}")
    except requests.exceptions.RequestException as e:
        app.logger.error(
            f"Failed to fetch LINE user profile for {user_id}: {e}")
    except json.JSONDecodeError as e:
        app.logger.error(
            f"Failed to decode LINE user profile JSON for {user_id}: {e}")

    # 將 event.message 直接整個傳送給 grpc server
    message_json = json.dumps(event['message'], ensure_ascii=False)

    try:
        with grpc.insecure_channel(GRPC_SERVER_ADDRESS) as channel:
            stub = chat_pb2_grpc.ChatServiceStub(channel)
            line_meta = chat_pb2.LineMetadata(
                reply_token=reply_token,
                message_json=message_json
            )
            request_msg = chat_pb2.ChatMessage(
                text="",  # gRPC 伺服器會自行從 message_json 解析
                user_id=user_id,
                platform="line",
                line_metadata=line_meta,
                user_display_name=user_display_name,
                user_profile_json=user_profile_json
            )
            response = stub.SendMessage(request_msg)

            reply_url = "https://api.line.me/v2/bot/message/reply"
            reply_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {channel_access_token}'
            }
            reply_data = {
                'replyToken': reply_token,
                'messages': [{'type': 'text', 'text': response.text}]
            }
            reply_response = requests.post(
                reply_url, headers=reply_headers, json=reply_data)
            reply_response.raise_for_status()
            app.logger.info(f"Replied to user {user_id} with: {response.text}")

    except Exception as e:
        print(f"與 gRPC 伺服器通訊時發生錯誤: {e}")

def get_line_message_content(message_id: str) -> bytes:
    """
    獲取 LINE 訊息內容影像或檔案。
    """
    url: str = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {channel_access_token}"
    }
    response: requests.Response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content


def start_line_bot():
    port = int(os.environ.get("PORT", 5000))
    print(f"Flask (LINE Bot) 伺服器已啟動，監聽 Port {port}...")
    app.run(host="0.0.0.0", port=port, use_reloader=False)
