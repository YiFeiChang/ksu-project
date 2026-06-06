import grpc
import cv2
import numpy as np
import webcam_pb2
import webcam_pb2_grpc

def run():
    # 連線至 gRPC 伺服器
    channel = grpc.insecure_channel('localhost:50051')
    stub = webcam_pb2_grpc.WebCamServiceStub(channel)

    request = webcam_pb2.StreamRequest(start=True)
    
    auto_focus = True
    focus_value = 0

    try:
        print("正在接收影像串流...\n操作說明：\n [q] 結束\n [a] 自動對焦\n [m] 手動對焦\n [f] 增加手動焦距\n [g] 減少手動焦距")
        # 迭代接收伺服器傳來的 stream Frame
        for response in stub.StreamVideo(request):
            # 將 bytes 資料轉換為 numpy array
            np_arr = np.frombuffer(response.data, np.uint8)
            # 將 numpy array 解碼為影像格式
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is not None:
                cv2.imshow('gRPC WebCam Stream', frame)

            # 監聽鍵盤事件
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('a'):
                auto_focus = True
                stub.SetFocus(webcam_pb2.FocusRequest(auto_focus=True, focus_value=focus_value))
                print(">> 攝影機切換為：自動對焦")
            elif key == ord('m'):
                auto_focus = False
                stub.SetFocus(webcam_pb2.FocusRequest(auto_focus=False, focus_value=focus_value))
                print(f">> 攝影機切換為：手動對焦 (數值: {focus_value})")
            elif key == ord('f') and not auto_focus:
                focus_value += 5  # 依您的鏡頭支援的數值可修改步進大小
                stub.SetFocus(webcam_pb2.FocusRequest(auto_focus=False, focus_value=focus_value))
                print(f">> 增加焦距: {focus_value}")
            elif key == ord('g') and not auto_focus:
                focus_value = max(0, focus_value - 5)
                stub.SetFocus(webcam_pb2.FocusRequest(auto_focus=False, focus_value=focus_value))
                print(f">> 減少焦距: {focus_value}")
                
    except grpc.RpcError as e:
        print(f"連線中斷或發生 gRPC 錯誤: {e.details()}")
    finally:
        # 關閉視窗與通道
        cv2.destroyAllWindows()
        channel.close()

if __name__ == '__main__':
    run()
