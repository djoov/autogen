import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import requests
from config import (
    OLLAMA_API_URL, OLLAMA_MODEL, CHROMA_DB_PATH, EMBEDDING_MODEL, RAG_TOP_K
)

print(f"\n[DEBUG] Ollama URL: {OLLAMA_API_URL}")
print(f"[DEBUG] ChromaDB Path: {CHROMA_DB_PATH.absolute()}")

#CHROMADB SETUP
print("[INFO] Loading embedding model...")
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
collection = chroma_client.get_or_create_collection(
    name="agent_memory",
    embedding_function=embedding_fn
)

print(f"[INFO] Database berisi {collection.count()} dokumen.\n")

#RAG FUNCTIONS

def simpan(teks: str) -> str:
    """Simpan teks ke database."""
    if not teks.strip():
        return "[ERROR] Teks kosong!"
    
    doc_id = f"doc_{collection.count() + 1}"
    collection.add(
        documents=[teks],
        ids=[doc_id],
        metadatas=[{"source": "user"}]
    )
    print(f">>> [SAVED] ID: {doc_id}")
    return f"Berhasil disimpan! (ID: {doc_id}, Total: {collection.count()} dokumen)"

def cari(query: str, top_k: int = 3) -> str:
    """Cari dokumen relevan."""
    if collection.count() == 0:
        return ""
    
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count())
    )
    
    if not results['documents'][0]:
        return ""
    
    output = "KONTEKS DARI MEMORY:\n"
    for i, doc in enumerate(results['documents'][0]):
        output += f"- {doc}\n"
    
    print(f">>> [SEARCH] Ditemukan {len(results['documents'][0])} dokumen")
    return output

def lihat_semua() -> str:
    """Tampilkan semua dokumen."""
    if collection.count() == 0:
        return "Database masih kosong."
    
    all_docs = collection.get()
    output = f"Total {len(all_docs['ids'])} dokumen:\n"
    for doc_id, doc in zip(all_docs['ids'], all_docs['documents']):
        output += f"- [{doc_id}] {doc}\n"
    return output

def tanya_llm(prompt: str, context: str = "") -> str:
    """Kirim pertanyaan ke Ollama LLM."""
    full_prompt = prompt
    if context:
        full_prompt = f"{context}\n\nBerdasarkan informasi di atas, jawab pertanyaan ini:\n{prompt}"
    
    try:
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=120
        )
        return response.json().get("response", "[ERROR] Tidak ada respons")
    except Exception as e:
        return f"[ERROR] Gagal menghubungi LLM: {e}"

# --- AUTO-RAG LOGIC ---

def detect_intent(user_input: str) -> str:
    """Deteksi intent user secara sederhana."""
    lower = user_input.lower()
    
    # Intent: SIMPAN
    save_keywords = ["ingat", "simpan", "catat", "remember", "save", "note"]
    if any(kw in lower for kw in save_keywords):
        return "SAVE"
    
    # Intent: LIHAT SEMUA
    list_keywords = ["semua", "list", "tampilkan", "apa saja", "daftar"]
    if any(kw in lower for kw in list_keywords):
        return "LIST"
    
    # Intent: TANYA (default)
    return "ASK"

def process_input(user_input: str) -> str:
    """Proses input user dengan Auto-RAG."""
    intent = detect_intent(user_input)
    print(f">>> [INTENT] {intent}")
    
    if intent == "SAVE":
        # Ekstrak informasi yang perlu disimpan
        # Hapus kata kunci penyimpanan
        cleaned = user_input
        for kw in ["ingat", "simpan", "catat", "bahwa", "remember", "save", "note", "that"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if cleaned:
            result = simpan(cleaned)
            return f"OK! {result}\nSaya akan mengingat: '{cleaned}'"
        else:
            return "Apa yang ingin Anda simpan?"
    
    elif intent == "LIST":
        return lihat_semua()
    
    else:  # ASK
        # Cari konteks dari database
        context = cari(user_input)
        
        # Tanya LLM dengan konteks
        if context:
            return tanya_llm(user_input, context)
        else:
            # Tidak ada konteks, tanya langsung
            return tanya_llm(user_input)

# --- MAIN LOOP ---

def main():
    print("=" * 60)
    print("AUTO-RAG AGENT (Tanpa Function Calling)")
    print("=" * 60)
    print(f"Database: {CHROMA_PATH.absolute()}")
    print(f"Dokumen tersimpan: {collection.count()}")
    print("\nContoh:")
    print("  - 'Ingat ulang tahun saya 5 Mei'")
    print("  - 'Kapan ulang tahun saya?'")
    print("  - 'Tampilkan semua'")
    print("  - 'exit' untuk keluar\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Bye!")
                break
            
            response = process_input(user_input)
            print(f"\nAgent: {response}\n")
            
        except KeyboardInterrupt:
            print("\nBye!")
            break

if __name__ == "__main__":
    main()
