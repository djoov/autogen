# 🤖 Local LLM Agent with AutoGen & Memos RAG

This project is a privacy-focused, 100% offline-capable AI Agent system that runs on your local machine using Docker. It combines **Microsoft AutoGen** for agentic capabilities, **Ollama** for the LLM brain, and **Memos** for long-term memory (RAG).

## 🌟 Features
- **100% Local & Private**: No data sent to OpenAI or cloud. Uses local Llama 3 via Ollama.
- **Source Code Obfuscation**: Ships as compiled Python bytecode (`.pyc`) inside Docker.
- **Browser Automation**: Automated web browsing capabilities using Playwright.
- **Memory (RAG)**: Integration with self-hosted [Memos](https://github.com/usememos/memos) to store and retrieve knowledge.
- **CLI Launcher**: Interactive terminal menu to choose different agent modes.

## 🛠 Prerequisites
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed.
2. [Ollama](https://ollama.com/) installed and running (`ollama serve`).
3. Model pulled: `ollama pull llama3.1:8b`.

## 🚀 Setup & Installation

### 1. Configure Ollama
Ensure Ollama accepts external connections (from Docker):
```powershell
# Windows PowerShell
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0", "User")
# Restart Ollama after this
```

### 2. Build the Docker Image
```bash
docker build -t ag-agent .
```

### 3. Start the System (Agent + Memory)
We use Docker Compose to run the Agent and Memos together.

```bash
docker-compose up -d memos
```
1. Open http://localhost:5230 in your browser.
2. Create an account.
3. Go to **Settings -> Access Tokens** and copy your token.

### 4. Run the Agent
Use the provided batch script for easy launching:
```bash
.\run_agent.bat
```
- Enter your LAN IP Address when prompted (e.g., `192.168.1.x`).
- Choose **Option 5** for Memory Agent.

## 📂 Project Structure
- `launcher.py`: Main entrypoint with menu.
- `bot_autogen.py`: Robust agent with browser automation.
- `bot_memory.py`: Agent with Read/Write access to Memos.
- `docker-compose.yml`: Orchestration for Memos and Agent.

## ⚠️ Note
This project obfuscates source code into `.pyc` files for educational/distribution purposes. The source code is not directly visible inside the container.
