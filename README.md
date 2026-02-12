# 🤖 Local LLM Agent with AutoGen & RAG

This project is a privacy-focused, 100% offline-capable AI Agent system that runs on your local machine. It combines **Microsoft AutoGen** for agentic capabilities, **Ollama** for the LLM brain, **ChromaDB** for vector memory (RAG), and **SilverBullet** for note-taking.

## 🌟 Features
- **100% Local & Private**: No data sent to OpenAI or cloud. Uses local Llama 3 via Ollama.
- **RAG Memory**: Persistent vector database with ChromaDB for semantic search.
- **PDF Support**: Load and query PDF documents.
- **SilverBullet Integration**: Save notes via file system or browser automation.
- **Export/Import**: Share knowledge base between PCs.
- **Browser Automation**: Automated web browsing using Playwright.
- **CLI Launcher**: Interactive terminal menu to choose agent modes.

## 🛠 Prerequisites
1. [Python 3.10-3.12](https://www.python.org/downloads/) installed.
2. [Ollama](https://ollama.com/) installed and running (`ollama serve`).
3. Model pulled: `ollama pull llama3.1:8b`.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/username/autogen-superbot.git
cd autogen-superbot

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run the bot
python bot_super.py
```

## 📂 Project Structure
- `bot_super.py`: Main hybrid agent (RAG + SilverBullet + PDF).
- `bot_rag.py`: Lightweight RAG-only agent.
- `config.py`: Centralized configuration.
- `launcher.py`: CLI menu for selecting agents.
- `coding_output/chroma_db/`: Vector database storage.
- `documents/`: PDF files for RAG processing.
- `notes/`: SilverBullet markdown notes.

## 📦 Database Migration
Need to transfer your knowledge base to another PC? See the complete guide:
- **[📖 Migration Guide](docs/MIGRATION_GUIDE.md)**

Quick commands:
```bash
# Export (on source PC)
export db

# Import (on target PC)
import db knowledge_base_xxxxx.zip
```

## ⚙️ Configuration
Edit `config.py` to change:
- Ollama model (`OLLAMA_MODEL`)
- Ollama URL (`OLLAMA_BASE_URL`)
- SilverBullet URL (`SILVERBULLET_URL`)
- Browser settings (`BROWSER_HEADLESS`, `BROWSER_SLOW_MO`)

## 📜 License
This project is for educational purposes.

