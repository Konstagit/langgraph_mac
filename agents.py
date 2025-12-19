import os
import operator
from typing import Annotated, List, TypedDict
from dotenv import load_dotenv
from langchain_deepseek.chat_models import ChatDeepSeek
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, ToolMessage, AIMessage
from tools import dev_tools, analyst_tools

# Подгружаем ллм
load_dotenv()
BASE_URL = os.getenv("LITELLM_BASE_URL", "http://a6k2.dgx:34000/v1")
API_KEY = os.getenv("LITELLM_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-32b")
    
def get_llm() -> ChatDeepSeek:
    return ChatDeepSeek(
        api_base=BASE_URL,
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL_NAME,
        streaming=True,
        temperature=0,
    )
    
llm = get_llm()

# состояние
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    tool_spec: str
    next_action: str
    is_coding_task: bool 

# Manager Node
def manager_node(state: AgentState) -> dict:
    messages = state["messages"]
    last_msg = messages[-1].content
    
    system_prompt = (
        "You are the Manager. Analyze the user request to determine the next step.\n"
        "Options:\n"
        "1. 'IMPLEMENT': If the user wants to WRITE, CREATE, or CODE a tool (requires Developer).\n"
        "2. 'DESIGN': If the user wants to DESIGN, PLAN, or ASK architecture questions (No coding needed).\n"
        "3. 'ANALYST': If the user wants to list files or explain existing tools.\n"
        "4. 'CHAT': General conversation.\n"
        "Output ONLY the single word decision."
    )
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=last_msg)])
    decision = response.content.strip().upper()
    
    is_coding = False
    
    if "IMPLEMENT" in decision:
        next_act = "ARCHITECT"
        is_coding = True # Идем к архитектору, а потом к разрабу
    elif "DESIGN" in decision:
        next_act = "ARCHITECT"
        is_coding = False # Идем к архитектору, но потом СТОП
    elif "ANALYST" in decision:
        next_act = "ANALYST"
    else:
        next_act = "CHAT"

    if next_act == "CHAT":
        chat_resp = llm.invoke([SystemMessage(content="You are a helpful assistant.")] + messages)
        return {"messages": [chat_resp], "next_action": "STOP", "is_coding_task": False}
    
    # Возвращаем решение и флаг кодинга
    return {"next_action": next_act, "is_coding_task": is_coding}


# Агент-проектировщик инструментов
def architect_node(state: AgentState) -> dict:
    messages = state["messages"]
    is_coding = state.get("is_coding_task", False)
    
    if is_coding:
        system_prompt = (
            "You are a Software Architect. The user wants to IMPLEMENT a tool.\n"
            "Design the Python function signature and docstring.\n"
            "CRITICAL: DO NOT write implementation code. Use 'pass' in the body.\n"
            "Output valid Python code only."
        )
    else:
        system_prompt = (
            "You are a Software Architect. The user asked for a DESIGN or theoretical answer.\n"
            "Provide a detailed technical explanation, architectural patterns, or a high-level design plan.\n"
            "Do NOT write Python code with 'pass'. Write for a human reader."
        )
    
    response = llm.invoke([SystemMessage(content=system_prompt)] + messages)
    
    return {
        "tool_spec": response.content,
        "messages": [response] 
    }

# Агент - разработчик
def developer_node(state: AgentState) -> dict:
    spec = state["tool_spec"]
    messages = state["messages"]
    
    system_prompt = (
        "You are a Developer. Write Python code based on the spec using LangChain's @tool decorator. "
        "Use the 'write_to_file' tool to save it. "
        "After saving, output a confirmation message to the user in Russian."
    )
    
    llm_with_tools = llm.bind_tools(dev_tools)
    
    # Первый вызов: Модель должна сгенерировать tool_call
    ai_msg_1 = llm_with_tools.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Implement this spec:\n{spec}")
    ])
    
    new_messages = [ai_msg_1]
    
    # --- ЛОГИКА ВЫПОЛНЕНИЯ ИНСТРУМЕНТА ---
    if ai_msg_1.tool_calls:
        tool_outputs = []
        for call in ai_msg_1.tool_calls:
            # Находим и выполняем функцию
            tool_func = {t.name: t for t in dev_tools}[call["name"]]
            res = tool_func.invoke(call["args"])
            # Создаем сообщение с результатом
            tool_outputs.append(ToolMessage(tool_call_id=call["id"], content=str(res)))
        
        new_messages.extend(tool_outputs)
        
        # Второй вызов: Модель получает результат выполнения и формирует ответ для юзера
        ai_msg_2 = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=f"Spec:\n{spec}")] + 
            new_messages
        )
        new_messages.append(ai_msg_2)
            
    return {"messages": new_messages}

# Агент - аналитик
def analyst_node(state: AgentState) -> dict:
    """Агент, который смотрит файлы и объясняет их."""
    messages = state["messages"]
    
    system_prompt = (
        "You are a Code Analyst. "
        "Use your tools ('list_files', 'read_file') to inspect the 'tools' directory if needed. "
        "If you see a tool_call, you MUST wait for the result. "
        "Once you have the file content, explain it clearly to the user in Russian."
    )
    
    llm_with_tools = llm.bind_tools(analyst_tools)
    
    # Первый запрос к модели
    ai_msg_1 = llm_with_tools.invoke([SystemMessage(content=system_prompt)] + messages)
    new_messages = [ai_msg_1]
    
    # Если модель решила вызвать инструмент (например, read_file)
    if ai_msg_1.tool_calls:
        tool_outputs = []
        for call in ai_msg_1.tool_calls:
            print(f"   [System] Executing tool: {call['name']} args: {call['args']}")
            tool_func = {t.name: t for t in analyst_tools}[call["name"]]
            res = tool_func.invoke(call["args"])
            tool_outputs.append(ToolMessage(tool_call_id=call["id"], content=str(res)))
        
        new_messages.extend(tool_outputs)
        
        # ВТОРОЙ запрос к модели: подаем историю + запрос + tool_call + tool_output
        ai_msg_2 = llm.invoke(
            [SystemMessage(content=system_prompt)] + messages + new_messages
        )
        new_messages.append(ai_msg_2)    
    return {"messages": new_messages}