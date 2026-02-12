"""
config.py - Konfigurasi Terpusat untuk Semua Agent Scripts
==========================================================
Edit file ini untuk mengubah pengaturan tanpa perlu edit tiap script.
"""
import os
from pathlib import Path

# ==============================================================================
# MODEL & LLM CONFIGURATION
# ==============================================================================
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")  # Untuk AutoGen (OpenAI-compatible)
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")  # Untuk API native Ollama

# LLM Config untuk AutoGen
LLM_CONFIG = {
    "config_list": [{
        "model": OLLAMA_MODEL,
        "base_url": OLLAMA_BASE_URL,
        "api_key": "ollama",
    }],
    "temperature": 0,
    "timeout": 300,
    "cache_seed": None,
}

# ==============================================================================
# PATHS
# ==============================================================================
BASE_DIR = Path(__file__).parent
CODING_OUTPUT_DIR = BASE_DIR / "coding_output"
CHROMA_DB_PATH = CODING_OUTPUT_DIR / "chroma_db"
MEMORY_DIR = CODING_OUTPUT_DIR / "memory"

# Buat folder jika belum ada
CODING_OUTPUT_DIR.mkdir(exist_ok=True)
CHROMA_DB_PATH.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)

# ==============================================================================
# EXTERNAL SERVICES
# ==============================================================================
SILVERBULLET_URL = os.getenv("SILVERBULLET_URL", "http://localhost:3000")
MEMOS_URL = os.getenv("MEMOS_BASE_URL", "http://localhost:5230")
MEMOS_TOKEN = os.getenv("MEMOS_TOKEN", "")

# Neo4j Knowledge Graph
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

# ==============================================================================
# BROWSER AUTOMATION (Playwright)
# ==============================================================================
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
BROWSER_SLOW_MO = int(os.getenv("BROWSER_SLOW_MO", "300"))
BROWSER_VIEWPORT = {"width": 1280, "height": 800}

# ==============================================================================
# RAG CONFIGURATION
# ==============================================================================
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Model untuk embedding (sentence-transformers)
RAG_TOP_K = 3  # Jumlah dokumen yang diambil saat pencarian

# ==============================================================================
# DEBUG
# ==============================================================================
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

def print_config():
    """Print konfigurasi saat ini (untuk debugging)."""
    print("\n" + "=" * 50)
    print("KONFIGURASI AKTIF")
    print("=" * 50)
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print(f"Output Dir: {CODING_OUTPUT_DIR}")
    print(f"Browser Headless: {BROWSER_HEADLESS}")
    print(f"SilverBullet URL: {SILVERBULLET_URL}")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    print_config()
