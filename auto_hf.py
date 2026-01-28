import autogen
from pathlib import Path
from config import OLLAMA_BASE_URL, CODING_OUTPUT_DIR

# Config khusus untuk Phi-3 model
config_list = [{
    "model": "microsoft/Phi-3-mini-4k-instruct", 
    "base_url": OLLAMA_BASE_URL, 
    "api_key": "ollama", 
}]

llm_config = {
    "config_list": config_list,
    "temperature": 0.1, 
    "timeout": 600,  
    "cache_seed": None, 
}

assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config=llm_config,
    system_message="""Kamu adalah Python Automation Engineer expert yang menggunakan model canggih Fara-7B.
    
    TUGAS UTAMA:
    Menulis script Python untuk browser automation yang LENGKAP, AMAN, dan EFISIEN.
    
    ATURAN CODING:
    1. Kode harus dalam blok ```python ... ```
    2. Import library yang dibutuhkan di dalam script (playwright sync_api).
    3. Selalu gunakan Error Handling (try-except).
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
   - headless=False (Agar user bisa melihat prosesnya)
   - slow_mo=1000 (Simulasi kecepatan manusia)
   - args=['--start-maximized', '--disable-blink-features=AutomationControlled']
3. Set User-Agent browser Chrome biasa.

LANGKAH KERJA:
1. Buka '[https://onlinenotepad.org/notepad](https://onlinenotepad.org/notepad)'.
2. Tunggu halaman loading sempurna (tunggu 3-5 detik).
3. Cari kotak teks utama (biasanya ID '#my-textarea' atau tag 'textarea').
   - Pastikan script meng-klik elemen itu dulu agar fokus.
4. Ketik teks berikut (gunakan \\n untuk baris baru):
   "Halo Dunia!\nIni ditulis oleh Model Microsoft Fara-7B.\nSaya sedang belajar menjadi Agent Computer Use yang hebat."
5. Cari tombol SAVE (tombol dengan tulisan 'Save' atau icon disket) dan Klik.
6. Tunggu 3 detik.
7. Ambil Screenshot 'bukti_fara_menulis.png'.
8. Print: "✅ SUKSES: Fara-7B berhasil menulis dan menyimpan!"
9. Close browser.
10. Di baris TERAKHIR script python, print persis kata ini: "TERMINATE"
"""

Path("coding_output").mkdir(exist_ok=True)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MEMULAI AGENT DENGAN MODEL: Microsoft Fara-7B (via LiteLLM)")
    print("   Pastikan terminal LiteLLM sudah berjalan di port 4000!")
    print("=" * 60)
    
    try:
        user_proxy.initiate_chat(
            assistant, 
            message=task,
            clear_history=True 
        )
    except Exception as e:
        print(f"\n❌ ERROR UTAMA: {e}")
        print("   Tips: Cek apakah server LiteLLM sudah menyala?")