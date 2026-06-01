import grpc
from concurrent import futures
import cv2
import time
import threading
import argparse
import platform
import webcam_pb2
import webcam_pb2_grpc

class CameraManager:
    def __init__(self):
        self.cap = None
        self.latest_frame = None
        self.condition = threading.Condition()
        self.running = False
        self.client_count = 0
        self.lock = threading.Lock()
        self.thread = None
        self.width = 640
        self.height = 480
        self.fps = 60
        self.auto_focus = True
        self.focus_value = 0
        
        # 依據系統自動決定 OpenCV 攝影機後端驅動
        system_os = platform.system()
        # if system_os == 'Windows':
        #     self.backend = cv2.CAP_DSHOW
        # elif system_os == 'Linux':
        #     self.backend = cv2.CAP_V4L2
        # else:
        #     self.backend = cv2.CAP_ANY
        self.backend = cv2.CAP_ANY

    def set_fps(self, fps):
        self.fps = fps

    def set_resolution(self, width, height):
        self.width = width
        self.height = height

    def set_focus(self, auto_focus, focus_value):
        with self.lock:
            self.auto_focus = auto_focus
            self.focus_value = focus_value
            if self.cap and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1 if self.auto_focus else 0)
                if not self.auto_focus:
                    self.cap.set(cv2.CAP_PROP_FOCUS, self.focus_value)

    def add_client(self):
        with self.lock:
            self.client_count += 1
            if self.client_count == 1:
                # 第一個連線，開啟攝影機並啟動執行緒
                # 根據作業系統自動選擇後端並優先使用硬體 MJPEG 壓縮
                self.cap = cv2.VideoCapture(0, self.backend)
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                if not self.cap.isOpened():
                    self.client_count -= 1
                    print("警告: 無法開啟攝影機")
                    return False
                self.running = True
                self.thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.thread.start()
                print("攝影機已開啟，開始擷取影像")
            return True

    def remove_client(self):
        with self.lock:
            if self.client_count > 0:
                self.client_count -= 1
                if self.client_count == 0:
                    # 最後一個連線斷開，停止執行緒並釋放攝影機
                    self.running = False
                    if self.thread:
                        self.thread.join()
                        self.thread = None
                    if self.cap:
                        self.cap.release()
                        self.cap = None
                    
                    with self.condition:
                        self.latest_frame = None
                        self.condition.notify_all()
                    print("所有連線已斷開，WebCam 資源已釋放")

    def _capture_loop(self):
        fail_count = 0
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                fail_count = 0
                # 壓縮影像
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                # 更新最新影像並通知所有等待中的客戶端
                with self.condition:
                    self.latest_frame = buffer.tobytes()
                    self.condition.notify_all()
            else:
                fail_count += 1
                if fail_count % 30 == 0:
                    print(f"警告: 擷取影像失敗 (連續 {fail_count} 次)，嘗試重新連接攝影機...")
                    with self.lock:
                        if self.cap:
                            self.cap.release()
                        self.cap = cv2.VideoCapture(0, self.backend)
                        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        
                        # 重新連接時套用目前的對焦設定
                        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1 if self.auto_focus else 0)
                        if not self.auto_focus:
                            self.cap.set(cv2.CAP_PROP_FOCUS, self.focus_value)
            
            # 控制幀率
            time.sleep(1 / self.fps)

    def get_latest_frame(self):
        with self.condition:
            # 等待新影像產生，設定 timeout 避免死鎖
            self.condition.wait(timeout=0.5)
            return self.latest_frame

    def stop_all(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.cap and self.cap.isOpened():
            self.cap.release()

# 建立一個全域的攝影機管理員，讓所有連線共用同一個影像來源
camera_manager = CameraManager()

class WebCamServicer(webcam_pb2_grpc.WebCamServiceServicer):
    def StreamVideo(self, request, context):
        if not request.start:
            return

        success = camera_manager.add_client()
        if not success:
            context.abort(grpc.StatusCode.INTERNAL, "無法開啟 WebCam")

        try:
            # 當客戶端保持連線時，持續發送最新的影像
            while context.is_active():
                frame_data = camera_manager.get_latest_frame()
                if frame_data:
                    yield webcam_pb2.Frame(data=frame_data)
        finally:
            camera_manager.remove_client()

    def SetFocus(self, request, context):
        camera_manager.set_focus(request.auto_focus, request.focus_value)
        mode_str = "自動" if request.auto_focus else "手動"
        return webcam_pb2.FocusResponse(success=True, message=f"已切換為 {mode_str} 對焦")

def serve(host, port, max_workers):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    webcam_pb2_grpc.add_WebCamServiceServicer_to_server(WebCamServicer(), server)
    server.add_insecure_port(f'{host}:{port}')
    server.start()
    print(f"WebCam gRPC 伺服器已啟動於 {host}:{port} (max_workers={max_workers})...")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n伺服器關閉中...")
    finally:
        camera_manager.stop_all()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="WebCam gRPC Server")
    parser.add_argument('--host', type=str, default='localhost', help="允許連入的 IP (綁定地址，預設為 localhost")
    parser.add_argument('--port', type=int, default=50051, help="伺服器監聽的 Port (預設為 50051)")
    parser.add_argument('--max-workers', type=int, default=1, help="最多支援的同時客戶端連線數 (預設為 1)")
    parser.add_argument('--width', type=int, default=640, help="攝影機畫面寬度 (預設為 640)")
    parser.add_argument('--height', type=int, default=480, help="攝影機畫面高度 (預設為 480)")
    parser.add_argument('--fps', type=int, default=30, help="最高 FPS 限制 (預設為 30)")
    args = parser.parse_args()
    
    camera_manager.set_resolution(args.width, args.height)
    camera_manager.set_fps(args.fps)
    serve(args.host, args.port, args.max_workers)
