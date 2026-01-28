import autogen
from pathlib import Path
import logging
from config import (
    LLM_CONFIG, OLLAMA_MODEL, OLLAMA_BASE_URL, 
    SILVERBULLET_URL, BROWSER_HEADLESS, BROWSER_SLOW_MO, BROWSER_VIEWPORT,
    CODING_OUTPUT_DIR
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

llm_config = LLM_CONFIG.copy()

print(f"\n[DEBUG] Ollama URL: {OLLAMA_BASE_URL}")
print(f"[DEBUG] SilverBullet URL: {SILVERBULLET_URL}\n")

# Agent
assistant = autogen.AssistantAgent(
    name="NotesWriter",
    llm_config=llm_config,
    system_message="""Kamu adalah Browser Automation Expert.
Tugasmu: Menulis kode Playwright Python untuk berinteraksi dengan SilverBullet notes app.

ATURAN:
1. Gunakan `sync_playwright` dari `playwright.sync_api`.
2. Browser harus headless=False (agar user bisa melihat).
3. Tulis kode yang LENGKAP dan SIAP DIJALANKAN.
4. Setelah selesai, print "TERMINATE".
"""
)

user_proxy = autogen.UserProxyAgent(
    name="Executor",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=2,
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", "") and "```" not in x.get("content", ""),
    code_execution_config={
        "work_dir": "coding_output",
        "use_docker": False,
        "timeout": 300,
    },
)

# Script Template
browser_script_template = f"""
from playwright.sync_api import sync_playwright
import time

SILVERBULLET_URL = "{SILVERBULLET_URL}"
JUDUL = "{{judul}}"
ISI = "{{isi}}"

def tulis_catatan():
    print("Memulai Browser Automation untuk SilverBullet...")
    
    with sync_playwright() as p:
        # headless=False agar browser terlihat!
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={{'width': 1280, 'height': 800}})
        page = context.new_page()
        
        try:
            print(f"Membuka SilverBullet: {{SILVERBULLET_URL}}")
            page.goto(SILVERBULLET_URL, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            
            # SilverBullet: Buat halaman baru dengan nama JUDUL
            # Ketik di URL bar: navigasi ke halaman baru
            page_url = f"{{SILVERBULLET_URL}}/{{JUDUL.replace(' ', '_')}}"
            print(f"Navigasi ke: {{page_url}}")
            page.goto(page_url, wait_until='networkidle')
            page.wait_for_timeout(2000)
            
            # Screenshot halaman
            page.screenshot(path='coding_output/sb_page_loaded.png')
            print("DEBUG: Screenshot halaman disimpan")
            
            # Cari editor (SilverBullet menggunakan CodeMirror)
            editor_selectors = [
                '.cm-content',           # CodeMirror content
                '[contenteditable="true"]',
                '.editor',
                'textarea',
            ]
            
            editor = None
            for sel in editor_selectors:
                try:
                    elem = page.locator(sel).first
                    if elem.is_visible(timeout=2000):
                        editor = elem
                        print(f"DITEMUKAN editor: {{sel}}")
                        break
                except:
                    continue
            
            if editor:
                print("Mengklik editor...")
                editor.click()
                page.wait_for_timeout(500)
                
                # Hapus konten lama (Ctrl+A lalu Delete)
                page.keyboard.press("Control+a")
                page.keyboard.press("Delete")
                page.wait_for_timeout(300)
                
                # Ketik judul dan isi
                content = f"# {{JUDUL}}\\n\\n{{ISI}}"
                print(f"Mengetik konten...")
                
                # Ketik per karakter untuk efek visual
                for char in content:
                    page.keyboard.type(char, delay=20)
                
                page.wait_for_timeout(1000)
                
                # SilverBullet auto-save, tapi kita tekan Ctrl+S untuk memastikan
                print("Menyimpan (Ctrl+S)...")
                page.keyboard.press("Control+s")
                page.wait_for_timeout(1500)
                
                print("[OK] Catatan berhasil disimpan!")
                
            else:
                print("[GAGAL] Editor tidak ditemukan!")
            
            # Screenshot hasil
            page.screenshot(path='coding_output/sb_result.png', full_page=True)
            print("Screenshot hasil disimpan: coding_output/sb_result.png")
            
            # Tunggu sebentar agar user bisa lihat
            print("Menunggu 3 detik sebelum menutup browser...")
            page.wait_for_timeout(3000)
            
        except Exception as e:
            print(f"Error: {{e}}")
            page.screenshot(path='coding_output/sb_error.png')
        finally:
            browser.close()
            print("Browser ditutup.")

if __name__ == "__main__":
    tulis_catatan()
    print("\\nTERMINATE")
"""

def main():
    Path("coding_output").mkdir(exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("SILVERBULLET BROWSER AUTOMATION")
    logger.info("=" * 60)
    print(f"Pastikan SilverBullet sudah jalan di: {SILVERBULLET_URL}")
    print("Jika belum, jalankan: docker-compose up -d silverbullet\n")
    
    # Input dari user
    print("Masukkan JUDUL catatan:")
    judul = input("> ").strip()
    if not judul:
        judul = "Catatan_Baru"
    
    print("\nMasukkan ISI catatan:")
    isi = input("> ").strip()
    if not isi:
        isi = "Ini adalah catatan otomatis dari AutoGen Agent. Timestamp: " + __import__('time').strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate task
    script = browser_script_template.replace("{judul}", judul).replace("{isi}", isi)
    task = f"""Jalankan script Playwright berikut untuk menulis catatan ke SilverBullet.
Output dalam blok ```python ... ``` dan jalankan.

{script}
"""
    
    try:
        user_proxy.initiate_chat(
            assistant,
            message=task,
            clear_history=True
        )
        logger.info("SELESAI!")
        print(f"\nCatatan tersimpan di folder: notes/{judul.replace(' ', '_')}.md")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()
