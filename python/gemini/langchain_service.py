import os
import grpc
import json
import threading
from concurrent import futures
import base64
from datetime import datetime
from dotenv import load_dotenv
import requests
from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional
from enum import Enum
from light_control import set_light_state
import subprocess
import sys

# --- LangChain 與 Google Gemini 相關導入 ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import (
    HumanMessage, AIMessage, SystemMessage, ToolMessage, messages_from_dict, messages_to_dict, BaseMessage
)
from langchain.tools import tool

# --- LangGraph 相關導入 ---
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# --- gRPC 相關導入 ---
import chat_pb2
import chat_pb2_grpc

# --- 自訂向量資料庫導入 ---
from milvusearch import MilvusSearcher
from line_bot import get_line_message_content

# 明確指定 .env 路徑並強制覆蓋系統變數，確保正確讀取設定
env_path: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path, override=True)

# 設定儲存歷史紀錄的資料夾
HISTORY_DIR: str = "chat_histories"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)


class LightControlMode(Enum):
    Auto = "Auto"
    Manual = "Manual"


class AgentState(TypedDict):
    """
    定義 Agent 在圖中流動的狀態。
    Attributes:
        messages: 對話訊息列表，新訊息會被添加進來。
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]


class ChatServiceServicer(chat_pb2_grpc.ChatServiceServicer):
    def __init__(self) -> None:
        self.searcher: MilvusSearcher = MilvusSearcher()

        # 從環境變數取得 Google Gemini 設定
        self.model_name: str = os.environ.get(
            "GOOGLE_GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.api_key: str = os.environ.get("GOOGLE_API_KEY", "")

        try:
            self.temperature: float = float(
                os.environ.get("LLM_TEMPERATURE", "0.7"))
        except ValueError:
            self.temperature = 0.7

        try:
            self.max_tokens: int = int(
                os.environ.get("LLM_MAX_OUTPUT_TOKENS", "1024"))
        except ValueError:
            self.max_tokens = 1024

        # 設定對話歷史總結的長度門檻
        try:
            self.max_history_length: int = int(
                os.environ.get("MAX_HISTORY_LENGTH", "5"))
        except ValueError:
            self.max_history_length = 5

        # 初始化 LangChain ChatGoogleGenerativeAI 客戶端
        self.llm: ChatGoogleGenerativeAI = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens
        )
        self.light_process: Optional[subprocess.Popen] = None

        # 確保對檔案操作時的執行緒安全
        self.lock: threading.Lock = threading.Lock()

        @tool
        def get_strawberry_knowledge(query: str) -> List[Dict[str, Any]]:
            """
            取得與草莓相關的知識及參考資料連結。
            Args:
                query (str): 關於草莓的特定問題或搜尋關鍵字。
            Returns:
                List[Dict[str, Any]]: 從 Milvus 向量資料庫查詢到的草莓知識內容。
            """
            print(f"[INFO] 呼叫工具 (get_strawberry_knowledge)，搜尋關鍵字: {query}")
            results: List[Dict[str, Any]] = []
            results = self.searcher.search(query)
            return results

        @tool
        def control_light(mode: LightControlMode, onoff: Optional[bool] = None, schedule: Optional[str] = None) -> str:
            """
            控制植物燈開啟、關閉或排程。
            Args:
                mode (LightControlMode): 控制模式，"Auto"或"Manual"。
                onoff (Optional[bool]): 開啟或關閉植物燈，"Manual"模式才需要設定。
                schedule (Optional[str]): 排程時間，格式為 HH:MM~HH:MM，"Auto"模式才需要設定。
            Returns:
                str: 控制的結果描述。
            """
            print(
                f"[INFO] 呼叫工具 (control_light)，模式: {mode}, 開關: {onoff}, 排程: {schedule}")

            mode_str: str = mode.value if isinstance(
                mode, LightControlMode) else str(mode)

            if mode_str == LightControlMode.Manual.value:
                if onoff is None:
                    return "操作失敗：Manual 模式必須提供 onoff 參數 (True 或 False)。"

                # 停止目前的排程子程序
                if self.light_process and self.light_process.poll() is None:
                    print("[INFO] 終止目前的燈光排程子程序...")
                    self.light_process.terminate()
                    try:
                        self.light_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.light_process.kill()
                    self.light_process = None

                # 手動控制燈光
                try:
                    set_light_state(onoff)
                    state_tw: str = "開啟" if onoff else "關閉"
                    return f"已手動將植物燈{state_tw}。"
                except Exception as e:
                    return f"手動控制失敗：{str(e)}"

            elif mode_str == LightControlMode.Auto.value:
                if not schedule:
                    return "操作失敗：Auto 模式必須提供 schedule 參數 (例如 '23:00~07:00')。"

                # 停止舊的排程子程序
                if self.light_process and self.light_process.poll() is None:
                    print("[INFO] 終止舊的燈光排程子程序...")
                    self.light_process.terminate()
                    try:
                        self.light_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.light_process.kill()

                # 啟動新的排程子程序
                script_path: str = os.path.join(os.path.dirname(
                    os.path.abspath(__file__)), "light_control.py")
                try:
                    self.light_process = subprocess.Popen(
                        [sys.executable, script_path, "--schedule", schedule]
                    )
                    return f"已成功設定自動排程模式，排程為：{schedule}。"
                except Exception as e:
                    return f"啟動排程失敗：{str(e)}"
            else:
                return f"未知的模式：{mode_str}"

        # === Tools Setup ===
        self.tools: List[Any] = [get_strawberry_knowledge, control_light]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        tool_node = ToolNode(self.tools)

        # === LangGraph Setup ===
        def debug(state: AgentState) -> Dict[str, List[BaseMessage]]:
            """呼叫 DEBUG 節點"""
            print("[INFO] 執行 DEBUG 節點")
            return {"messages": []}

        def check_if_plant_image(state: AgentState) -> str:
            """判斷是否為植物影像"""
            print("[INFO] 執行條件判斷 (check_if_plant_image)")
            messages: Sequence[BaseMessage] = state["messages"]
            last_message: BaseMessage = messages[-1]

            try:
                # 判斷是否為包含 type: image 的 JSON 字串
                if isinstance(last_message.content, str):
                    message_content: Dict[str, Any] = json.loads(
                        last_message.content)

                    if message_content.get("type") == "image":
                        message_id: str = message_content.get("id")
                        print(f"[INFO] 偵測到圖片訊息 ID: {message_id}，開始下載與分析...")

                        # 1. 下載圖片並轉換為 base64
                        image_bytes: bytes = get_line_message_content(
                            message_id)
                        image_base64: str = base64.b64encode(
                            image_bytes).decode('utf-8')

                        # 2. 準備給 LLM 判斷的 Prompt
                        vision_prompt: str = (
                            "請判斷這張圖片中是否包含植物、農作物或植物的病蟲害特徵。\n"
                            "請嚴格以 JSON 格式回傳，必須包含兩個欄位：\n"
                            "1. \"is_plant\": \"yes\" 或 \"no\"\n"
                            "2. \"description\": \"對圖片的簡短描述\"\n"
                        )

                        vision_message = HumanMessage(
                            content=[
                                {"type": "text", "text": vision_prompt},
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"}}
                            ]
                        )

                        # 3. 呼叫 LLM 進行初步視覺判斷
                        response = self.llm.invoke([vision_message])
                        response_text: str = response.content[0]['text']

                        # 清理可能包含的 Markdown 標記
                        if response_text.startswith("```json"):
                            response_text = response_text[7:-3].strip()
                        elif response_text.startswith("```"):
                            response_text = response_text[3:-3].strip()

                        # 解析結果
                        is_plant: str = "no"
                        description: str = "無法辨識的圖片。"
                        try:
                            analysis_result: Dict[str, Any] = json.loads(
                                response_text)
                            is_plant = analysis_result.get(
                                "is_plant", "no").lower()
                            description = analysis_result.get(
                                "description", "無法辨識的圖片。")
                        except json.JSONDecodeError:
                            print("[警告] 解析 LLM 回傳的 JSON 失敗，嘗試字串比對。")
                            if "yes" in response_text.lower():
                                is_plant = "yes"
                            description = response_text

                        print(
                            f"[INFO] 影像分析結果 -> 是否為植物: {is_plant}, 描述: {description}")

                        # 4. 更新原本的訊息內容，將圖片與描述放入，供後續節點直接使用
                        last_message.content = [
                            {"type": "text", "text": f"使用者上傳了一張圖片。系統初步判定描述為：{description}\n請根據圖片內容與描述回答使用者的問題。"},
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]

                        if is_plant == "yes":
                            return "disease_check"
                        else:
                            return "agent"

            except json.JSONDecodeError:
                # 若不是 JSON，代表是普通文字，直接進入 agent
                pass
            except Exception as e:
                print(f"[錯誤] check_if_plant_image 執行失敗: {e}")

            return "agent"

        def disease_check(state: AgentState) -> Dict[str, List[BaseMessage]]:
            """呼叫 疫病檢查 節點"""
            print("[INFO] 執行 疫病檢查 節點")
            messages: Sequence[BaseMessage] = state["messages"]
            last_message: BaseMessage = messages[-1]

            # 從 last_message 提取準備好的 Base64 圖片
            image_base64: Optional[str] = None
            if isinstance(last_message.content, list):
                for item in last_message.content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        url: str = item.get("image_url", {}).get("url", "")
                        if url.startswith("data:image/jpeg;base64,"):
                            image_base64 = url.split(",")[1]
                            break

            if not image_base64:
                print("[警告] 疫病檢查節點找不到可用的圖片。")
                return {"messages": []}

            try:
                # 將 Base64 解碼回 bytes 以供上傳
                image_bytes: bytes = base64.b64decode(image_base64)

                print("[INFO] 傳送圖片至植物疫病辨識服務 (http://127.0.0.1:5001/image)...")

                # 透過 POST 請求以 multipart/form-data 格式將圖片送至辨識端點
                response: requests.Response = requests.post(
                    "http://127.0.0.1:5001/image",
                    files={"imageData": (
                        "image.jpg", image_bytes, "image/jpeg")},
                    timeout=30
                )
                response.raise_for_status()

                prediction_result: str = response.text
                print(f"[INFO] 疫病辨識結果: {prediction_result}")

                # 將辨識結果作為系統訊息加入，引導 Agent 利用此資訊進行回答
                result_message: BaseMessage = SystemMessage(
                    content=f"這是外部植物疫病辨識服務回傳的結果：\n{prediction_result}\n請根據此辨識結果與使用者提供的圖片，向使用者詳細說明病情，並給予對應的改善與照護建議。"
                )
                return {"messages": [result_message]}

            except Exception as e:
                print(f"[錯誤] 呼叫疫病辨識服務失敗: {e}")
                error_message: BaseMessage = SystemMessage(
                    content="（系統提示：目前外部的植物疫病辨識服務暫時無法連線。請告訴使用者系統目前無法進行自動疫病分析，但您會盡可能根據圖片與描述提供幫助。）"
                )
                return {"messages": [error_message]}

        def call_model(state: AgentState) -> Dict[str, List[BaseMessage]]:
            """呼叫 LLM 節點"""
            print("[INFO] 執行 LLM 節點")
            response = self.llm_with_tools.invoke(state["messages"])
            return {"messages": [response]}

        def should_use_tool(state: AgentState) -> str:
            """判斷是否需要執行工具"""
            print("[INFO] 執行條件判斷 (should_use_tool)")
            messages = state["messages"]
            last_message = messages[-1]
            if getattr(last_message, 'tool_calls', None):
                return "tools"
            return END

        # 建立 StateGraph 工作流
        workflow = StateGraph(AgentState)

        # 加入節點
        workflow.add_node("debug", debug)
        workflow.add_node("disease_check", disease_check)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)

        # 設定圖的流程邊緣
        workflow.add_edge(START, "debug")
        workflow.add_conditional_edges(
            "debug", 
            check_if_plant_image,
            {
                "disease_check": "disease_check",
                "agent": "agent"
            }
        )
        workflow.add_edge("disease_check", "agent")
        workflow.add_conditional_edges(
            "agent", 
            should_use_tool,
            {
                "tools": "tools",
                END: END
            }
        )
        workflow.add_edge("tools", "agent")

        # 編譯圖
        self.app = workflow.compile()

        # 將 workflow 儲存成 png
        try:
            self.app.get_graph().draw_mermaid_png(output_file_path="workflow.png")
            print("[INFO] 工作流圖表已儲存至 workflow.png")
        except Exception as e:
            print(f"[警告] 無法產生工作流圖表: {e}")

        print("[INFO] LangGraph Agent 已成功建立並編譯完成。")

    def _get_history_file(self, user_id: str) -> str:
        """取得對應使用者的歷史紀錄檔案路徑"""
        safe_id: str = "".join(
            c for c in user_id if c.isalnum() or c in ("-", "_"))
        if not safe_id:
            safe_id = "default"
        return os.path.join(HISTORY_DIR, f"{safe_id}.json")

    def _load_history(self, user_id: str) -> List[BaseMessage]:
        """從本地端 JSON 讀取並還原歷史訊息"""
        filepath: str = self._get_history_file(user_id)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    history_dicts = json.load(f)
                return messages_from_dict(history_dicts)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"[警告] 讀取或解析歷史紀錄失敗 {user_id}: {e}。將建立新的對話歷史。")
        return []

    def _save_history(self, user_id: str, history_messages: Sequence[BaseMessage]) -> None:
        """將 LangChain 歷史訊息序列化並儲存至本地端 JSON"""
        filepath: str = self._get_history_file(user_id)
        try:
            history_dicts = messages_to_dict(history_messages)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_dicts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 儲存歷史紀錄失敗 {user_id}: {e}")

    def _summarize_if_needed(self, user_id: str, history: List[BaseMessage]) -> List[BaseMessage]:
        """
        如果對話歷史過長，則進行總結。
        """
        if len(history) <= self.max_history_length:
            return history

        print(
            f"[INFO] 對話歷史紀錄超過 {self.max_history_length} 則，開始為 {user_id} 進行總結...")

        messages_to_keep_count: int = 4
        if len(history) <= messages_to_keep_count:
            return history

        messages_to_summarize = history[:-messages_to_keep_count]
        kept_messages = history[-messages_to_keep_count:]

        def message_to_string(message: BaseMessage) -> str:
            if isinstance(message, HumanMessage):
                if isinstance(message.content, list):
                    text_content = " ".join(part.get("text", "") for part in message.content if isinstance(
                        part, dict) and part.get("type") == "text")
                    return f"使用者: {text_content}"
                return f"使用者: {message.content}"
            elif isinstance(message, AIMessage):
                content = message.content or ""
                if getattr(message, 'tool_calls', None):
                    tool_calls_str = ", ".join(
                        [f"{tc.get('name', 'tool')}(...)" for tc in message.tool_calls])
                    return f"AI: [呼叫工具: {tool_calls_str}] {content}"
                return f"AI: {content}"
            elif isinstance(message, ToolMessage):
                tool_name = getattr(message, 'name', 'tool_output')
                return f"工具 ({tool_name}): {message.content}"
            elif isinstance(message, SystemMessage):
                return f"系統: {message.content}"
            return ""

        history_text: str = "\n".join(
            filter(None, [message_to_string(m) for m in messages_to_summarize]))

        summarization_prompt: str = (
            "你是一個擅長總結對話的 AI 助理。"
            "請根據以下對話歷史，產生一個字數在 2048 以內的摘要，這個摘要將作為未來對話的上下文參考。"
            "摘要應包含所有關鍵訊息、使用者偏好和已解決的問題。\n\n"
            f"=== 對話歷史 ===\n{history_text}\n\n=== 摘要 ==="
        )

        try:
            summary_response = self.llm.invoke(
                [HumanMessage(content=summarization_prompt)])
            summary_text: str = summary_response.content.strip() if isinstance(
                summary_response.content, str) else str(summary_response.content)

            if not summary_text:
                print(f"[警告] 為 {user_id} 產生的總結為空，將保留最近的訊息。")
                return kept_messages

            print(f"[INFO] 為 {user_id} 產生的對話總結：{summary_text}")
            summary_message = SystemMessage(
                content=f"這是先前對話的摘要：\n{summary_text}")
            return [summary_message] + kept_messages

        except Exception as e:
            print(f"[警告] 為 {user_id} 總結對話時發生錯誤: {e}。將只保留最近的訊息。")
            return kept_messages

    def SendMessage(self, request: chat_pb2.ChatMessage, context: grpc.ServicerContext) -> chat_pb2.ChatReply:
        client_id: str = context.peer()
        user_id: str = request.user_id or "anonymous"
        user_message: str = request.text
        platform: str = request.platform or "console"
        user_display_name: str = request.user_display_name or "朋友"
        user_profile_json: str = request.user_profile_json

        # 處理 LINE 平台特定邏輯
        if platform.lower() == "line" and request.HasField("line_metadata"):
            line_meta = request.line_metadata
            # 如果傳入了 message_json，直接餵給 LLM Agent
            if getattr(line_meta, "message_json", ""):
                user_message = line_meta.message_json
            else:
                # 若沒有 message_json，則 fallback 到普通文字訊息
                user_message = request.text

        print(
            f"[INFO] 收到來自 {client_id} (Platform: {platform}, User: {user_id}, DisplayName: {user_display_name}) 的訊息: {user_message}")

        try:
            user_language: str = "zh-TW"
            if user_profile_json:
                try:
                    profile_data: Dict[str, Any] = json.loads(
                        user_profile_json)
                    user_language = profile_data.get("language", "zh-TW")
                except json.JSONDecodeError:
                    print(f"[警告] 解析使用者個人資料 JSON 失敗: {user_profile_json}")

            current_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            system_prompt: str = (
                f"現在的時間：{current_time}\n"
                "你是一個專業且親切的植物學家。你的任務是只回答跟植物耕作相關的問題。\n"
                f"請用親切的語氣稱呼使用者，可以依據「{user_display_name}」想一個暱稱。\n"
                f"使用者的 language 代碼為「{user_language}」，請優先使用此語言回答。\n"
                "若對話與時間、農業耕作無關，請堅持並委婉地拒絕。\n"
                "回答盡可能簡短講重點。"
                "Tool 使用以使用者最後一次的要求為主，不要管之前的對話歷史中 Tool 的使用紀錄。"
                "知識庫搜尋結果，須附上參考資料連結，查無資料則不需要。"
            )

            # 載入並處理對話歷史
            with self.lock:
                chat_history: List[BaseMessage] = self._load_history(user_id)
                chat_history = self._summarize_if_needed(user_id, chat_history)

            # 組合完整的對話流
            messages: List[BaseMessage] = [
                SystemMessage(content=system_prompt)
            ]
            messages.extend(chat_history)
            messages.append(HumanMessage(content=user_message))

            # --- 使用 LangGraph 執行 Agent ---
            final_state: AgentState = self.app.invoke({"messages": messages})
            final_messages: Sequence[BaseMessage] = final_state['messages']

            # 取得最終 AI 回應
            ai_response_text: str = final_messages[-1].content if final_messages else "我現在無法回答。"
            if isinstance(ai_response_text, list):
                # 處理多模態/複雜結構的回應文字
                ai_response_text = " ".join(part.get("text", "") for part in ai_response_text if isinstance(
                    part, dict) and part.get("type") == "text")

            print(f"[INFO] {user_id} 回覆訊息: {ai_response_text}")

            # 儲存對話紀錄到 JSON，過濾掉當次動態生成的 SystemMessage
            with self.lock:
                history_to_save: List[BaseMessage] = [
                    msg for msg in final_messages if not (isinstance(msg, SystemMessage) and msg.content == system_prompt)
                ]
                self._save_history(user_id, history_to_save)

            return chat_pb2.ChatReply(text=str(ai_response_text))

        except Exception as e:
            print(f"[錯誤] {user_id} 發生例外狀況 - {type(e).__name__}: {str(e)}")
            error_msg: str = str(e).lower()

            # 處理連線錯誤或配額限制 (Quota / 429)
            if "connection error" in error_msg or "timeout" in error_msg or "429" in error_msg or "quota" in error_msg:
                return chat_pb2.ChatReply(text="無法連線至 Google Gemini API，請確認網路狀態或 API 配額是否充足。")

            context.set_details(f'伺服器內部發生錯誤: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return chat_pb2.ChatReply()


def serve_grpc() -> grpc.Server:
    """啟動 gRPC 伺服器"""
    server: grpc.Server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(
        ChatServiceServicer(), server)

    bind_address: str = os.environ.get("GRPC_BIND_ADDRESS", "[::]:50051")
    server.add_insecure_port(bind_address)

    print(f"[INFO] gRPC 伺服器已啟動，監聽位址: {bind_address}...")
    print(
        f"[INFO] 正在使用 Google Gemini 模型: {os.environ.get('GOOGLE_GEMINI_MODEL', 'gemini-3.1-flash-lite')}")

    server.start()
    return server
