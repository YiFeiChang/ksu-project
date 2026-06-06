import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, Annotated, Sequence
import operator
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain.tools import tool
from langgraph.prebuilt import ToolNode

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path, override=True)


# 初始化模型
llm = ChatGoogleGenerativeAI(
    model=os.getenv("GOOGLE_GEMINI_MODEL", "gemini-3.1-flash-lite"),
    google_api_key=os.getenv("GOOGLE_API_KEY", ""),
    temperature=os.getenv("LLM_TEMPERATURE", "0.7"),
    max_output_tokens=os.getenv("LLM_MAX_OUTPUT_TOKENS", "1024")
)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def call_model(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def check_relevance(state: AgentState):
    """判斷問題是否與植物種植相關"""
    messages = state["messages"]
    last_user_message = next(m.content for m in reversed(messages) if isinstance(m, HumanMessage))
    
    prompt = f"判斷以下問題是否與『植物、耕作、園藝、農業』相關。只需回答『yes』或『no』：\n\n{last_user_message}"
    response = llm.invoke([HumanMessage(content=prompt)])
    if "yes" in response.content[0]['text'].lower():
        return "agent"
    return "reject"


@tool
def get_current_time() -> str:
    """取得當前的日期和時間。當需要知道現在時間時使用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


tools = [get_current_time]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)


def reject_node(state: AgentState):
    """婉拒非植物相關問題的節點"""
    return {"messages": [SystemMessage(content="抱歉，我是一個專業的植物學家助理，我只能回答與植物耕作或園藝相關的問題。")]}


def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


# 建立 LangGraph 工作流
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("reject", reject_node)

# 設定進入點先進行判斷
workflow.set_conditional_entry_point(
    check_relevance,
    {
        "agent": "agent",
        "reject": "reject"
    }
)

workflow.add_conditional_edges("agent", should_continue)

workflow.add_edge("tools", "agent")
workflow.add_edge("reject", END)

# 編譯圖
app = workflow.compile()

# 執行並印出結果
inputs = {"messages": [
    HumanMessage(content="說`你好`。")
]}
for output in app.stream(inputs):
    for key, value in output.items():
        print(f"Node '{key}':")
        print(value["messages"][-1].content)
