import requests
import schedule
import time
import argparse
import logging
from typing import Dict, Final, Optional, List, Tuple

# 常數定義
API_URL: Final[str] = "http://10.0.2.3:5000/api/Gpio/NodeMCU-32S/Light%201"
HEADERS: Final[Dict[str, str]] = {
    "accept": "*/*",
    "Content-Type": "application/json"
}

# 型別定義
TimePoint = Tuple[int, int]
TimeRange = Tuple[TimePoint, TimePoint]

# 設定 Logging 格式與層級
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_light_state() -> Optional[bool]:
    """
    發送 API 請求以取得目前燈光狀態
    """
    try:
        response: requests.Response = requests.get(
            API_URL,
            headers={"accept": "*/*"},
            timeout=10
        )
        response.raise_for_status()
        data: dict = response.json()
        if data.get("success"):
            return data.get("state")
    except requests.exceptions.RequestException as e:
        logging.error(f"取得燈光狀態失敗: {e}")
    return None


def set_light_state(state: bool) -> None:
    """
    發送 API 請求以控制燈光開關
    :param state: True 為開燈，False 為關燈
    """
    payload: Dict[str, bool] = {"state": state}
    try:
        response: requests.Response = requests.post(
            API_URL,
            json=payload,
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        status: str = "開啟" if state else "關閉"
        logging.info(f"燈光已{status}")
    except requests.exceptions.RequestException as e:
        logging.error(f"API 請求失敗: {e}")


def parse_schedule(schedule_str: str) -> List[TimeRange]:
    """
    解析時間排程字串。
    例如 "23:00~07:00,09:00~10:00"
    """
    ranges: List[TimeRange] = []
    if not schedule_str:
        return ranges
    for part in schedule_str.split(','):
        try:
            start_str, end_str = part.strip().split('~')
            start_h, start_m = map(int, start_str.split(':'))
            end_h, end_m = map(int, end_str.split(':'))
            if not (0 <= start_h <= 23 and 0 <= start_m <= 59 and 0 <= end_h <= 23 and 0 <= end_m <= 59):
                raise ValueError("時間或分鐘超出有效範圍 (小時: 0-23, 分鐘: 0-59)。")
            ranges.append(((start_h, start_m), (end_h, end_m)))
        except ValueError as e:
            logging.warning(f"無效的時間範圍格式 '{part}': {e}。將略過此設定。")
            continue
    return ranges


def is_time_in_schedule(parsed_schedule: List[TimeRange]) -> bool:
    """檢查目前時間是否在排程範圍內"""
    now = time.localtime()
    current_h, current_m = now.tm_hour, now.tm_min

    for start, end in parsed_schedule:
        start_h, start_m = start
        end_h, end_m = end

        # 為了方便比較，將時間轉換為從午夜開始的總分鐘數
        current_total_minutes = current_h * 60 + current_m
        start_total_minutes = start_h * 60 + start_m
        end_total_minutes = end_h * 60 + end_m

        if start_total_minutes <= end_total_minutes:  # 同一天內的範圍 (例如 09:00-17:00)
            if start_total_minutes <= current_total_minutes < end_total_minutes:
                return True
        else:  # 跨午夜的範圍 (例如 23:00-07:00)
            if current_total_minutes >= start_total_minutes or current_total_minutes < end_total_minutes:
                return True
    return False


def check_time(parsed_schedule: List[TimeRange]) -> None:
    """
    檢查現在時間是否應該根據提供的排程開關燈。
    """
    if not parsed_schedule:
        return  # 沒有排程，不執行任何動作

    current_light_state = get_light_state()
    try:
        should_be_on: bool = is_time_in_schedule(parsed_schedule)
        # 如果無法取得目前狀態，或目前狀態與應有狀態不符，則設定燈光
        if current_light_state is None or current_light_state != should_be_on:
            set_light_state(should_be_on)
    except Exception as e:
        logging.error(f"檢查時間發生錯誤: {e}")


def main():
    parser = argparse.ArgumentParser(description="燈光自動化控制程式。")
    parser.add_argument(
        "--schedule",
        type=str,
        default="",
        help='設定開燈時間範圍，格式為 "HH:MM~HH:MM,HH:MM~HH:MM"。例如: "23:00~07:00,09:00~10:00"'
    )
    args = parser.parse_args()

    logging.info("燈光自動化控制程式啟動中...")
    logging.info(f"使用排程: {args.schedule if args.schedule else '無'}")

    parsed_schedule = parse_schedule(args.schedule)

    schedule.every().minutes.at(":00").do(check_time, parsed_schedule=parsed_schedule)

    # 啟動時立即檢查一次
    check_time(parsed_schedule)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
