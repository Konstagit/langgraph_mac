import sys
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from graph import app
from tools import TOOLS_DIR

def print_agent_message(agent_name, message_content):
    """Красивый вывод сообщений от разных агентов."""
    # Словарь заголовков
    headers = {
        "manager": "🧠 MANAGER DECISION",
        "architect": "📐 ARCHITECT DESIGN",
        "developer": "🔨 DEVELOPER OUTPUT",
        "analyst": "🧐 ANALYST EXPLANATION"
    }
    
    header = headers.get(agent_name, f"🤖 {agent_name.upper()}")
    separator = "-" * 40
    
    print(f"\n{separator}")
    print(f"[{header}]")
    print(f"{separator}")
    print(f"{message_content.strip()}")
    print(f"{separator}\n")

def main():
    print("\n=== ToolForge AI Terminal ===")
    print(f"Working directory: ./{TOOLS_DIR}/")
    print("Можете попробовать такие команды:")
    print("1. 'Создай инструмент password_gen который создает пароли'")
    print("2. 'Каковы основные принципы lancghain&'")
    print("3. 'Кратко расскажи какие инстурменты созданы и для чего'")
    print("Для выхода введите: 'quit', 'exit'")
    
    chat_history = []

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit"]:
                print("Goodbye!")
                break
            
            chat_history.append(HumanMessage(content=user_input))
            
            initial_state = {
                "messages": chat_history,
                "tool_spec": "",
                "next_action": "",
                "is_coding_task": False 
            }
            
            print("\n--- 🚀 Processing Request ---")
            
            # будем использовать stream, чтобы получать обновления в реальном времени
            for event in app.stream(initial_state):
                for node_name, state_update in event.items():
                    
                    # 1. Если это Manager, выводим его решение
                    if node_name == "manager":
                        action = state_update.get("next_action", "UNKNOWN")
                        print_agent_message("manager", f"Routing to: {action}")
                        
                        # Если Manager решил ответить сам (CHAT), его сообщение в messages
                        if "messages" in state_update:
                             msg = state_update["messages"][-1]
                             print_agent_message("manager", msg.content)

                    # 2. Обработка остальных агентов (Architect, Developer, Analyst)
                    elif "messages" in state_update:
                        new_msgs = state_update["messages"]
                        if not new_msgs:
                            continue
                            
                        # Берем последнее сообщение
                        last_msg = new_msgs[-1]
                        
                        if isinstance(last_msg, AIMessage) and last_msg.content:
                            print_agent_message(node_name, last_msg.content)
                        
            pass 


        except Exception as e:
            print(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()