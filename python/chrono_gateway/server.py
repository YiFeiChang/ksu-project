import os
import time
import re
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from dotenv import load_dotenv

import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS

# 載入環境變數 (明確指定 .env 路徑並強制覆蓋現有環境變數)
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path, override=True)

# 全域記憶體暫存區與執行緒鎖定
data_cache = {}
cache_lock = threading.Lock()

class DataReceiverHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 產生預設的 HTTP 存取紀錄格式，例如 "10.0.2.4 - - [24/Apr/2026 05:16:27] ..."
        default_log = "%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args)
        
        # 如果已經在 do_POST 解析出 payload，就將其附加在日誌後面
        if hasattr(self, 'received_payload') and self.received_payload:
            print(f"{default_log} | payload: {self.received_payload}")
        else:
            print(default_log)

    def do_POST(self):
        if self.path == '/data':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                self.received_payload = payload  # 存下來供 log_message 顯示
                data_id = payload.get('id')
                data_value = payload.get('value')
                
                if data_id is not None and data_value is not None:
                    # 接收資料並寫入暫存
                    with cache_lock:
                        data_cache[data_id] = data_value
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = {"success": True, "message": "Data cached successfully"}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = {"success": False, "message": "Missing 'id' or 'value'"}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
            except json.JSONDecodeError:
                self.received_payload = f"(Invalid JSON) {post_data.decode('utf-8')}"
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"success": False, "message": "Invalid JSON format"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def influxdb_uploader_task():
    """背景執行緒：負責時間比對與 InfluxDB 上傳"""
    url = os.environ.get("INFLUXDB_URL")
    token = os.environ.get("INFLUXDB_TOKEN")
    org = os.environ.get("INFLUXDB_ORG")
    bucket = os.environ.get("INFLUXDB_BUCKET")
    
    # 初始化 InfluxDB Client
    client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    # 解析正規表示式並建立狀態追蹤字典 (達成「吻合 -> 不吻合 -> 吻合」才觸發的條件)
    regex_strs = os.environ.get("TIME_MATCH_REGEXES", "").split(",")
    patterns = [re.compile(r.strip()) for r in regex_strs if r.strip()]
    trigger_states = {p.pattern: False for p in patterns}

    print(f"背景上傳任務已啟動... 當前套用的上傳時間規則為：{[p.pattern for p in patterns]}")

    while True:
        now = datetime.now()
        # 用於 Log 顯示的完整日期時間 (YYYY-MM-DD HH:mm:ss.fff)
        current_time_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        # 用於正規表示式比對的時間格式 (HH:mm:ss)
        match_time_str = now.strftime("%H:%M:%S")
        should_upload = False

        for p in patterns:
            is_match = bool(p.match(match_time_str))
            
            if is_match and not trigger_states[p.pattern]:
                # 從不吻合變為吻合：觸發上傳並更新狀態
                should_upload = True
                trigger_states[p.pattern] = True
            elif not is_match and trigger_states[p.pattern]:
                # 從吻合變為不吻合：重置狀態，等待下次觸發
                trigger_states[p.pattern] = False

        if should_upload:
            with cache_lock:
                if data_cache:
                    success_count = 0
                    # 逐筆上傳當前數值，不使用批次上傳
                    for data_id, data_value in data_cache.items():
                        point = (
                            Point("sensor_measurement")
                            .tag("device_id", data_id)
                            .field("value", data_value)
                        )
                        try:
                            write_api.write(bucket=bucket, org=org, record=point)
                            success_count += 1
                        except Exception as e:
                            print(f"[{current_time_str}] 寫入 device_id {data_id} 時發生錯誤：{e}")
                    
                    print(f"[{current_time_str}] 已成功上傳 {success_count} 筆當前數值至 InfluxDB。")

        # 稍微暫停以節省 CPU 資源，頻率需足以捕捉到秒數變化
        time.sleep(0.2)

def serve():
    # 啟動背景上傳執行緒
    uploader_thread = threading.Thread(target=influxdb_uploader_task, daemon=True)
    uploader_thread.start()

    # 啟動 HTTP 伺服器
    port = int(os.environ.get("HTTP_PORT", "8080"))
    server_address = ('', port)
    httpd = HTTPServer(server_address, DataReceiverHandler)
    print(f"ChronoGateway HTTP 伺服器已啟動，監聽通訊埠：{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n正在關閉伺服器...")
        httpd.server_close()

if __name__ == '__main__':
    serve()