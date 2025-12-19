import os
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

# Папка для инструментов
TOOLS_DIR = os.getenv("TOOLS_DIR", "created_tools")
if not os.path.exists(TOOLS_DIR):
    os.makedirs(TOOLS_DIR)

@tool
def write_to_file(filename: str, content: str) -> str:
    """Writes content to a file in the tools directory. Use this to save Python code."""
    try:
        # Сохраняем в папку tools/
        filepath = os.path.join(TOOLS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully saved code to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"

@tool
def read_file(filename: str) -> str:
    """Reads the content of a file from the tools directory."""
    try:
        # Читаем из папки tools/
        filepath = os.path.join(TOOLS_DIR, filename)
        if not os.path.exists(filepath):
            return f"Error: File {filename} does not exist in {TOOLS_DIR}."
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def list_files() -> str:
    """Lists all Python files in the tools directory."""
    try:
        if not os.path.exists(TOOLS_DIR):
            return "Tools directory is empty."
        files = [f for f in os.listdir(TOOLS_DIR) if f.endswith('.py')]
        if not files:
            return "No Python files found in tools directory."
        return ", ".join(files)
    except Exception as e:
        return f"Error listing files: {e}"

# Списки инструментов
dev_tools = [write_to_file]
analyst_tools = [list_files, read_file]