import autogen
from pathlib import Path
import logging
from config import LLM_CONFIG, OLLAMA_MODEL, OLLAMA_BASE_URL, CODING_OUTPUT_DIR

# ==============================================================================
# 1. KONFIGURASI LOGGING
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 2. KONFIGURASI MODEL (dari config.py)
# ==============================================================================
llm_config = LLM_CONFIG.copy()
llm_config["timeout"] = 600  # Override timeout untuk script ini

print(f"\n[DEBUG] Using Ollama URL: {OLLAMA_BASE_URL}")
print(f"[DEBUG] Model: {OLLAMA_MODEL}\n")

# ==============================================================================
# 3. DEFINISI AGENT
# ==============================================================================
assistant = autogen.AssistantAgent(
    name="PythonExecutor",
    llm_config=llm_config,
    system_message="""Kamu adalah Python Code Executor yang profesional.

TUGAS UTAMA:
1. Terima kode Python dari user
2. Bungkus kode dalam blok markdown ```python ... ``` TANPA modifikasi
3. JANGAN ubah, tambah, atau kurangi apapun dari kode asli
4. JANGAN berikan penjelasan tambahan, langsung output kode

FORMAT OUTPUT:
```python
[kode asli dari user]
```

PENTING: Outputkan HANYA blok kode, tidak ada teks lain."""
)

def is_valid_termination(msg):
    """
    Fungsi terminasi yang lebih robust.
    Hanya terminate jika:
    1. Ada kata "TERMINATE" DI LUAR blok kode
    2. ATAU eksekusi gagal dengan error fatal
    """
    content = msg.get("content", "")
    
    if "TERMINATE" not in content:
        return False
    
    if "```" in content:
        return False
    
    if "exitcode: 1" in content and "Error" in content:
        logger.error("Terminasi karena error eksekusi")
        return True
    
    return True

user_proxy = autogen.UserProxyAgent(
    name="CodeRunner",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=2,
    is_termination_msg=is_valid_termination,
    code_execution_config={
        "work_dir": "coding_output",
        "use_docker": False,
        "timeout": 300,
        "last_n_messages": 3,
    },
)

# ==============================================================================
# 4. SCRIPT BROWSER AUTOMATION (DIPERBAIKI)
# ==============================================================================
browser_script = """
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time
from pathlib import Path

def setup_browser(playwright):
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=500,
        args=[
            '--start-maximized',
            '--disable-blink-features=AutomationControlled',
        ]
    )
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    return browser, context

def jalankan_bot():
    print("Memulai Browser Automation dengan Playwright...")
    
    # Path("coding_output").mkdir(exist_ok=True) # Tidak perlu karena sudah set di work_dir
    
    with sync_playwright() as p:
        browser, context = setup_browser(p)
        page = context.new_page()
        
        try:
            print("Membuka OnlineNotepad.org...")
            page.goto('https://onlinenotepad.org/notepad', wait_until='networkidle')
            page.wait_for_timeout(1000)
            
            print("Mencari textarea...")
            textarea_selector = '#my-textarea'
            page.wait_for_selector(textarea_selector, state='visible', timeout=10000)
            page.click(textarea_selector)
            
            pesan = "AutoGen Browser Bot\\n\\nPesan ini ditulis otomatis oleh:\\n- Framework: AutoGen\\n- Browser: Playwright (Chromium)\\n- Status: Berhasil Dieksekusi\\n\\nTimestamp: " + time.strftime("%Y-%m-%d %H:%M:%S")
            
            print("Mengetik pesan...")
            page.fill(textarea_selector, pesan)
            page.wait_for_timeout(1000)
            
            try:
                save_button = page.locator('button:has-text("Save")').first
                if save_button.is_visible():
                    print("Menyimpan...")
                    save_button.click()
                    page.wait_for_timeout(2000)
            except Exception as e:
                print("Tombol Save tidak ditemukan/tidak perlu: " + str(e))
            
            screenshot_path = 'hasil_notepad.png'
            page.screenshot(path=screenshot_path, full_page=True)
            print("Screenshot disimpan: " + screenshot_path)
            
            text_value = page.input_value(textarea_selector)
            if pesan in text_value:
                print("Verifikasi: Teks berhasil ditulis dengan benar")
            else:
                print("Warning: Teks mungkin tidak tersimpan dengan sempurna")
            
            print("\\n" + "="*60)
            print("EKSEKUSI BERHASIL!")
            print("="*60)
            
        except PlaywrightTimeout as e:
            print("Timeout Error: " + str(e))
            page.screenshot(path='error_screenshot.png')
            raise
            
        except Exception as e:
            print("Error tidak terduga: " + type(e).__name__ + ": " + str(e))
            page.screenshot(path='error_screenshot.png')
            raise
            
        finally:
            print("Menutup browser...")
            browser.close()

if __name__ == "__main__":
    try:
        jalankan_bot()
        print("\\nTERMINATE")
    except Exception as e:
        print("\\nProgram berhenti dengan error: " + str(e))
        print("\\nTERMINATE")
"""

# ==============================================================================
# 5. FUNGSI UTAMA
# ==============================================================================
def main():
    work_dir = Path("coding_output")
    work_dir.mkdir(exist_ok=True)
    
    logger.info("=" * 70)
    logger.info("MEMULAI AUTOGEN BROWSER AUTOMATION")
    logger.info("=" * 70)
    
    task = """Execute this Python script EXACTLY as provided.
Output it in a python code block for execution.
DO NOT modify the code.

""" + browser_script
    
    try:
        result = user_proxy.initiate_chat(
            assistant, 
            message=task,
            clear_history=True
        )
        
        logger.info("\\n" + "=" * 70)
        logger.info("WORKFLOW SELESAI")
        logger.info("=" * 70)
        
        if work_dir.joinpath("hasil_notepad.png").exists():
            logger.info("Screenshot berhasil dibuat")
        else:
            logger.warning("Screenshot tidak ditemukan")
            
    except Exception as e:
        logger.error("Error dalam workflow: " + str(e))
        raise

if __name__ == "__main__":
    main()