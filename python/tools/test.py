import cv2
import numpy as np

def nothing(x: int) -> None:
    """Trackbar 需要的回呼函式，此處不需執行任何動作"""
    pass

def main() -> None:
    stream_source: str = "http://10.8.0.101:5000/api/WebCam/stream"
    cap: cv2.VideoCapture = cv2.VideoCapture(stream_source)

    if not cap.isOpened():
        print("無法開啟影像串流")
        return

    # 建立一個名為 "Trackbars" 的視窗來放置滑桿
    cv2.namedWindow("Trackbars")

    # 建立 HSV 下限與上限的調整滑桿
    # 根據你的影像，預先設定一個可能更容易抓到淺綠色的初始值
    cv2.createTrackbar("Lower H", "Trackbars", 25, 179, nothing) # 色相稍微往下調以包含黃綠色
    cv2.createTrackbar("Lower S", "Trackbars", 30, 255, nothing) # 降低飽和度門檻
    cv2.createTrackbar("Lower V", "Trackbars", 40, 255, nothing)
    
    cv2.createTrackbar("Upper H", "Trackbars", 85, 179, nothing)
    cv2.createTrackbar("Upper S", "Trackbars", 255, 255, nothing)
    cv2.createTrackbar("Upper V", "Trackbars", 255, 255, nothing)

    while True:
        ret: bool
        frame: np.ndarray
        ret, frame = cap.read()

        if not ret:
            print("無法讀取影像幀")
            break

        hsv_frame: np.ndarray = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 讀取滑桿目前的數值
        l_h: int = cv2.getTrackbarPos("Lower H", "Trackbars")
        l_s: int = cv2.getTrackbarPos("Lower S", "Trackbars")
        l_v: int = cv2.getTrackbarPos("Lower V", "Trackbars")
        u_h: int = cv2.getTrackbarPos("Upper H", "Trackbars")
        u_s: int = cv2.getTrackbarPos("Upper S", "Trackbars")
        u_v: int = cv2.getTrackbarPos("Upper V", "Trackbars")

        # 組合 HSV 邊界值
        lower_bound: np.ndarray = np.array([l_h, l_s, l_v], dtype=np.uint8)
        upper_bound: np.ndarray = np.array([u_h, u_s, u_v], dtype=np.uint8)

        # 產生遮罩
        mask: np.ndarray = cv2.inRange(hsv_frame, lower_bound, upper_bound)
        
        # 計算面積並繪製文字
        area: int = cv2.countNonZero(mask)
        cv2.putText(
            frame,
            f"Plant Area: {area} pixels",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2
        )

        # 顯示結果：觀察 Mask 視窗，目標是讓植物變成全白，背景全黑
        cv2.imshow("Original Stream", frame)
        cv2.imshow("Mask", mask)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()