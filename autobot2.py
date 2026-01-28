import autogen
from pathlib import Path
from config import LLM_CONFIG, OLLAMA_MODEL, OLLAMA_BASE_URL, CODING_OUTPUT_DIR

# Debug print
print(f"\n[DEBUG] Using Ollama URL: {OLLAMA_BASE_URL}")
print(f"[DEBUG] Model: {OLLAMA_MODEL}\n")

llm_config = LLM_CONFIG.copy()
llm_config["timeout"] = 120

# 2. Assistant
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config=llm_config,
    system_message="""Kamu adalah Python Automation Engineer expert.
    Tugasmu hanya satu: Menulis script Python yang LENGKAP dan AMAN.
    
    ATURAN:
    1. Kode harus dalam blok ```python ... ```
    2. Import library yang dibutuhkan di dalam script.
    3. Gunakan 'sync_playwright'.
    4. Pastikan script Python-mu melakukan print('TERMINATE') HANYA jika berhasil selesai.
    """
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=1, 
    
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", "") and "```" not in x.get("content", ""),
    
    code_execution_config={
        "work_dir": "coding_output",
        "use_docker": False,
        "timeout": 300, 
    },
)

task = """
Buatkan script Python browser automation (Playwright Sync API).

REQUIREMENTS:
1. Gunakan `sync_playwright`.
2. Launch Chromium dengan:
   - headless=True (Wajib terlihat)
   - slow_mo=1000 (Biar terlihat mengetik)
   - args=['--start-maximized']
3. Set User-Agent browser biasa.

LANGKAH KERJA (Skenario Notepad):
1. Buka 'https://onlinenotepad.org/notepad'.
2. Tunggu halaman loading sempurna (tunggu 3 detik).
3. Cari kotak teks utama. 
   - Note: Biasanya selectornya adalah ID '#my-textarea' atau tag 'textarea'. 
   - Gunakan `page.click('selector')` dulu untuk fokus.
4. Ketik teks berikut (gunakan \\n untuk baris baru):
   "Halo! Ini adalah pesan otomatis dari AutoGen.\nSaya sedang belajar mengendalikan browser.\nHari ini hari yang indah untuk coding Python!"
5. Cari tombol SAVE (biasanya ada tombol dengan tulisan 'Save' atau icon disket). Klik tombol itu.
6. Tunggu 3 detik (untuk melihat efek save).
7. Ambil Screenshot 'bukti_nulis_notepad.png'.
8. Print: "✅ SUKSES: Catatan berhasil ditulis dan disimpan!"
9. Close browser.
10. Di baris terakhir script python, print persis kata ini: "TERMINATE"
"""

# 5. Persiapan Folder Output
Path("coding_output").mkdir(exist_ok=True)

# 6. Execute
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 MEMULAI MISI: MENULIS DI ONLINE NOTEPAD")
    print("=" * 50)
    
    try:
        user_proxy.initiate_chat(
            assistant, 
            message=task,
            clear_history=True 
        )
    except Exception as e:
        print(f"\n❌ ERROR: {e}")