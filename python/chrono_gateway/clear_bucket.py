import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

# 載入環境變數
load_dotenv()

def clear_bucket():
    url = os.environ.get("INFLUXDB_URL")
    token = os.environ.get("INFLUXDB_TOKEN")
    org = os.environ.get("INFLUXDB_ORG")
    bucket = os.environ.get("INFLUXDB_BUCKET")

    if not all([url, token, org, bucket]):
        print("錯誤：無法從 .env 讀取到完整的 InfluxDB 設定。")
        return

    print(f"準備清空 InfluxDB Bucket: {bucket} ...")

    # 建立 InfluxDB Client
    client = InfluxDBClient(url=url, token=token, org=org)
    delete_api = client.delete_api()

    try:
        # 設定刪除的時間範圍
        # 從 1970 年到當前時間 (UTC)
        start = "1970-01-01T00:00:00Z"
        stop = datetime.now(timezone.utc)
        
        # 執行刪除操作
        # predicate="" 代表刪除指定時間範圍內的所有資料
        # 若只需要刪除 server.py 寫入的感測器資料，可改為 predicate='_measurement="sensor_measurement"'
        delete_api.delete(start, stop, predicate="", bucket=bucket, org=org)
        print(f"Bucket '{bucket}' 已經成功清空！")
    except Exception as e:
        print(f"清空 Bucket 時發生錯誤：{e}")
    finally:
        client.close()

if __name__ == '__main__':
    clear_bucket()