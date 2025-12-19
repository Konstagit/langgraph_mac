from langgraph.graph import StateGraph, START, END
from agents import AgentState, manager_node, architect_node, developer_node, analyst_node

# --- СБОРКА ГРАФА ---

# Логика роутера для Менеджера
def manager_router(state: AgentState):
    action = state["next_action"]
    if action == "ARCHITECT": return "architect"
    if action == "ANALYST": return "analyst"
    return END

# Роутер после Архитектора
def architect_router(state: AgentState):
    # Если задача на кодинг -> идем к Developer
    if state.get("is_coding_task", False):
        return "developer"
    # Если просто дизайн -> заканчиваем (отдаем ответ Архитектора юзеру)
    else:
        return END

workflow = StateGraph(AgentState)

# Узлы
workflow.add_node("manager", manager_node)
workflow.add_node("architect", architect_node)
workflow.add_node("developer", developer_node)
workflow.add_node("analyst", analyst_node)

# Ребра
workflow.add_edge(START, "manager")

# 1. От менеджера 
workflow.add_conditional_edges(
    "manager",
    manager_router
)

# 2. От архитектора 
workflow.add_conditional_edges(
    "architect",
    architect_router,
    {
        "developer": "developer",
        END: END
    }
)

workflow.add_edge("developer", END)
workflow.add_edge("analyst", END)

app = workflow.compile()