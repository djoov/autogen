import autogen
from pathlib import Path
from config import LLM_CONFIG, OLLAMA_MODEL, OLLAMA_BASE_URL, CODING_OUTPUT_DIR

# Debug print
print(f"\n[DEBUG] Using Ollama URL: {OLLAMA_BASE_URL}")
print(f"[DEBUG] Model: {OLLAMA_MODEL}\n")

llm_config = LLM_CONFIG.copy()
llm_config["timeout"] = 120  # Override timeout untuk script ini

# 2. Assistant - Improved System Message
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config=llm_config,
    system_message="""Kamu adalah Python Automation Engineer yang expert.

ATURAN KETAT:
- Tulis kode Python yang LENGKAP dan DAPAT LANGSUNG DIJALANKAN
- Gunakan error handling (try-except) untuk stabilitas
- Tambahkan logging untuk debugging
- JANGAN basa-basi, langsung tulis kode
- Setelah kode selesai, akhiri dengan: TERMINATE

STRUKTUR KODE:
1. Import semua library
2. Implementasi fungsi utama dengan try-except
3. Print status eksekusi
4. Return hasil atau error message"""
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,  
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={
        "work_dir": "coding_output",
        "use_docker": False,
        "timeout": 300,  
        "last_n_messages": 2,  
    },
)

task = """
Buatkan script Python browser automation dengan spesifikasi:

LIBRARY: playwright (sync_api)
TARGET: Google Search

REQUIREMENTS:
1. Import: `from playwright.sync_api import sync_playwright`
2. Gunakan context manager untuk resource management
3. Browser: chromium dengan headless=True, slow_mo=1000
4. Steps:
   - Buka https://www.google.com
   - Tunggu selector textarea[name="q"] atau input[name="q"]
   - Input: "Tutorial AutoGen Python Indonesia"
   - Tekan Enter
   - Tunggu 3 detik
   - Screenshot full page → "hasil_browsing.png"
   - Print: "✅ SUKSES: Browsing selesai!"
   - Cleanup & close browser

ERROR HANDLING:
- Wrap dalam try-except-finally
- Handle TimeoutError
- Pastikan browser selalu tertutup

OUTPUT:
- File screenshot: hasil_browsing.png
- Console log: status eksekusi
- Response: TERMINATE
"""

Path("coding_output").mkdir(exist_ok=True)

# 6. Execute
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 MEMULAI DEMO BROWSING AUTOMATION")
    print("=" * 50)
    
    try:
        user_proxy.initiate_chat(
            assistant, 
            message=task,
            clear_history=True  # 
        )
        print("\n" + "=" * 50)
        print("✅ DEMO SELESAI")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("=" * 50)