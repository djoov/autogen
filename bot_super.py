"""
Bot Super - Hybrid Agent dengan RAG + SilverBullet + PDF + Knowledge Graph
===================================================================
Menggabungkan:
1. ChromaDB untuk semantic search (memori vektor)
2. Neo4j untuk knowledge graph (entitas & relasi)
3. SilverBullet untuk catatan visual (Markdown files)
4. Playwright untuk browser automation (opsional)
5. PDF Document Loading untuk knowledge base
"""
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import requests
from datetime import datetime
import os
from config import (
    OLLAMA_API_URL, OLLAMA_MODEL, CHROMA_DB_PATH, EMBEDDING_MODEL, RAG_TOP_K,
    SILVERBULLET_URL, BROWSER_HEADLESS, BROWSER_SLOW_MO, CODING_OUTPUT_DIR
)

#Path untuk documents
DOCS_PATH = Path("documents")
DOCS_PATH.mkdir(exist_ok=True)

#Path untuk notes SilverBullet (sesuai docker-compose volume)
NOTES_PATH = Path("notes")
NOTES_PATH.mkdir(exist_ok=True)

print(f"\n[DEBUG] Ollama URL: {OLLAMA_API_URL}")
print(f"[DEBUG] ChromaDB Path: {CHROMA_DB_PATH.absolute()}")
print(f"[DEBUG] Notes Path: {NOTES_PATH.absolute()}")

#Neo4j Knowledge Graph (optional - will connect on demand)
try:
    from neo4j_graph import (
        get_graph, extract_entities_with_llm, save_entities_to_graph
    )
    NEO4J_AVAILABLE = True
    print("[INFO] Neo4j module loaded.")
except ImportError as e:
    NEO4J_AVAILABLE = False
    print(f"[WARN] Neo4j module not available: {e}")

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

print(f"[INFO] Database berisi {collection.count()} dokumen.")

# --- MODEL WARM-UP ---

def warmup_model(max_retries: int = 3) -> bool:
    """Pre-load Ollama model dengan mengirim request sederhana."""
    import time
    
    print(f"\n[INFO] Warming up model '{OLLAMA_MODEL}'...")
    print(f"[INFO] Koneksi ke: {OLLAMA_API_URL}")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[WARMUP] Attempt {attempt}/{max_retries}...", end=" ", flush=True)
            
            response = requests.post(
                f"{OLLAMA_API_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": "Hi",
                    "stream": False
                },
                timeout=120 
            )
            
            if response.status_code == 200:
                print("OK ✓")
                print(f"[INFO] Model '{OLLAMA_MODEL}' siap digunakan!\n")
                return True
            elif response.status_code == 404:
                print(f"GAGAL")
                print(f"[ERROR] Model '{OLLAMA_MODEL}' tidak ditemukan!")
                print(f"[ERROR] Jalankan: ollama pull {OLLAMA_MODEL}")
                return False
            else:
                print(f"Error {response.status_code}")
                if attempt < max_retries:
                    print(f"[WARMUP] Retry dalam 5 detik...")
                    time.sleep(5)
                    
        except requests.exceptions.ConnectionError:
            print("Connection Error")
            print(f"[ERROR] Tidak bisa konek ke Ollama di {OLLAMA_API_URL}")
            print(f"[ERROR] Pastikan Ollama berjalan: ollama serve")
            if attempt < max_retries:
                print(f"[WARMUP] Retry dalam 5 detik...")
                time.sleep(5)
                
        except requests.exceptions.Timeout:
            print("Timeout")
            if attempt < max_retries:
                print(f"[WARMUP] Model mungkin masih loading, retry...")
                time.sleep(3)
    
    print(f"\n[WARN] Gagal warm-up model setelah {max_retries} percobaan.")
    print(f"[WARN] Bot tetap berjalan, tapi LLM mungkin lambat saat pertama kali.\n")
    return False

# Warm-up saat startup
_model_ready = warmup_model()

# --- FUNGSI UTILITAS ---

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def slugify(text: str) -> str:
    """Ubah teks jadi nama file yang aman."""
    return "".join(c if c.isalnum() or c in " -_" else "" for c in text).strip().replace(" ", "_")[:50]

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Pecah teks panjang jadi chunks yang lebih kecil."""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks if chunks else [text]

#FUNGSI PDF

def load_pdf(filepath: str) -> dict:
    """Ekstrak teks dari PDF."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"error": "pypdf tidak terinstall. Jalankan: pip install pypdf"}
    
    path = Path(filepath)
    if not path.exists():
        # Coba cari di folder documents/
        path = DOCS_PATH / filepath
        if not path.exists():
            return {"error": f"File tidak ditemukan: {filepath}"}
    
    try:
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        return {
            "filename": path.name,
            "pages": len(reader.pages),
            "text": text.strip(),
            "path": str(path.absolute())
        }
    except Exception as e:
        return {"error": f"Gagal membaca PDF: {e}"}

def simpan_pdf_ke_memory(filepath: str) -> str:
    """Load PDF dan simpan semua chunks ke ChromaDB + ekstrak entitas ke Neo4j."""
    result = load_pdf(filepath)
    
    if "error" in result:
        return result["error"]
    
    text = result["text"]
    if not text:
        return "[ERROR] PDF kosong atau tidak bisa dibaca teksnya."
    
    #Pecah jadi chunks
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    
    saved_count = 0
    for i, chunk in enumerate(chunks):
        doc_id = f"pdf_{result['filename']}_{i+1}"
        
        #Cek apakah sudah ada
        existing = collection.get(ids=[doc_id])
        if existing['ids']:
            continue  #Skip jika sudah ada
        
        collection.add(
            documents=[chunk],
            ids=[doc_id],
            metadatas=[{
                "source": "pdf",
                "filename": result['filename'],
                "chunk": i + 1,
                "total_chunks": len(chunks),
                "timestamp": timestamp()
            }]
        )
        saved_count += 1
    
    print(f">>> [PDF] Loaded: {result['filename']} ({result['pages']} pages, {len(chunks)} chunks)")
    
    #Auto-extract entities ke Neo4j
    entity_result = ""
    if NEO4J_AVAILABLE:
        try:
            print(f">>> [NEO4J] Extracting entities from PDF...")
            graph = get_graph()
            if graph.connect():
                # Ekstrak entitas dari summary text (max 3000 chars)
                extracted = extract_entities_with_llm(text[:3000])
                entity_result = save_entities_to_graph(graph, extracted)
                print(f">>> [NEO4J] {entity_result}")
        except Exception as e:
            print(f">>> [NEO4J] Entity extraction failed: {e}")
            entity_result = f"(Entity extraction gagal: {e})"
    
    output = f"PDF '{result['filename']}' berhasil dimuat!\\n"
    output += f"- {result['pages']} halaman\\n"
    output += f"- {len(chunks)} chunks disimpan ke ChromaDB\\n"
    output += f"- {saved_count} chunks baru (sisanya sudah ada)"
    
    if entity_result:
        output += f"\\n- Knowledge Graph: {entity_result}"
    
    return output

def list_pdf_files() -> str:
    """List semua PDF di folder documents/."""
    pdfs = list(DOCS_PATH.glob("*.pdf"))
    if not pdfs:
        return f"Folder {DOCS_PATH}/ masih kosong. Taruh file PDF di sana."
    
    output = f"=== PDF FILES ({len(pdfs)}) ===\n"
    for pdf in pdfs:
        size_kb = pdf.stat().st_size / 1024
        output += f"- {pdf.name} ({size_kb:.1f} KB)\n"
    return output

def simpan_memory(teks: str) -> str:
    """Simpan ke ChromaDB."""
    if not teks.strip():
        return "[ERROR] Teks kosong!"
    
    doc_id = f"doc_{collection.count() + 1}"
    collection.add(
        documents=[teks],
        ids=[doc_id],
        metadatas=[{"source": "user", "timestamp": timestamp()}]
    )
    print(f">>> [CHROMA] Saved: {doc_id}")
    return doc_id

def cari_memory(query: str, top_k: int = RAG_TOP_K) -> str:
    """Cari di ChromaDB (semua dokumen)."""
    if collection.count() == 0:
        return ""
    
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count())
    )
    
    if not results['documents'][0]:
        return ""
    
    output = "KONTEKS DARI MEMORY:\n"
    for doc in results['documents'][0]:
        output += f"- {doc}\n"
    
    print(f">>> [CHROMA] Found {len(results['documents'][0])} docs")
    return output

def cari_pdf_only(query: str, top_k: int = 5) -> str:
    """Cari HANYA di dokumen PDF."""
    if collection.count() == 0:
        return ""
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"source": "pdf"}
        )
        
        if not results['documents'][0]:
            return ""
        
        output = "KONTEKS DARI PDF:\n"
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i] if results['metadatas'][0] else {}
            filename = meta.get('filename', 'unknown')
            output += f"\n[{filename}]:\n{doc}\n"
        
        print(f">>> [PDF SEARCH] Found {len(results['documents'][0])} chunks")
        return output
    except Exception as e:
        print(f">>> [PDF SEARCH] Error: {e}")
        return ""

def reset_database() -> str:
    """Hapus semua dokumen dari ChromaDB."""
    global collection
    try:
        chroma_client.delete_collection("agent_memory")
        collection = chroma_client.get_or_create_collection(
            name="agent_memory",
            embedding_function=embedding_fn
        )
        return "[OK] Database di-reset. Semua dokumen dihapus."
    except Exception as e:
        return f"[ERROR] Gagal reset: {e}"

def export_database(filename: str = None) -> str:
    """Export ChromaDB ke file ZIP untuk dibagikan."""
    import shutil
    from datetime import datetime
    
    if not filename:
        filename = f"knowledge_base_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    if not filename.endswith('.zip'):
        filename += '.zip'
    
    export_path = CODING_OUTPUT_DIR / filename
    
    try:
        # Pastikan data tersimpan
        # ChromaDB PersistentClient otomatis persist
        
        # Zip folder chroma_db
        shutil.make_archive(
            str(export_path).replace('.zip', ''),
            'zip',
            CHROMA_DB_PATH
        )
        
        size_mb = export_path.stat().st_size / (1024 * 1024)
        return f"[OK] Database berhasil diekspor!\nFile: {export_path}\nUkuran: {size_mb:.2f} MB\nDokumen: {collection.count()}"
    except Exception as e:
        return f"[ERROR] Gagal ekspor: {e}"

def import_database(filepath: str) -> str:
    """Import ChromaDB dari file ZIP."""
    import shutil
    import zipfile
    global collection, chroma_client
    
    zip_path = Path(filepath)
    if not zip_path.exists():
        # Coba cari di coding_output
        zip_path = CODING_OUTPUT_DIR / filepath
        if not zip_path.exists():
            return f"[ERROR] File tidak ditemukan: {filepath}"
    
    try:
        # Backup dulu database lama
        backup_path = CODING_OUTPUT_DIR / "chroma_db_backup"
        if CHROMA_DB_PATH.exists():
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.copytree(CHROMA_DB_PATH, backup_path)
        
        # Hapus database lama
        if CHROMA_DB_PATH.exists():
            shutil.rmtree(CHROMA_DB_PATH)
        CHROMA_DB_PATH.mkdir(exist_ok=True)
        
        # Ekstrak ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(CHROMA_DB_PATH)
        
        # Reload ChromaDB
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collection = chroma_client.get_or_create_collection(
            name="agent_memory",
            embedding_function=embedding_fn
        )
        
        return f"[OK] Database berhasil diimpor!\nDokumen: {collection.count()}\nBackup tersimpan di: {backup_path}"
    except Exception as e:
        return f"[ERROR] Gagal impor: {e}"

def export_json(filename: str = None) -> str:
    """Export database ke JSON (portable, human-readable)."""
    import json
    
    if collection.count() == 0:
        return "[ERROR] Database kosong, tidak ada yang diekspor."
    
    if not filename:
        filename = f"knowledge_base_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    if not filename.endswith('.json'):
        filename += '.json'
    
    export_path = CODING_OUTPUT_DIR / filename
    
    try:
        # Ambil semua data dari ChromaDB
        all_data = collection.get(include=["documents", "metadatas"])
        
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "total_documents": len(all_data['ids']),
            "source": "bot_super.py",
            "documents": []
        }
        
        for i, doc_id in enumerate(all_data['ids']):
            export_data["documents"].append({
                "id": doc_id,
                "content": all_data['documents'][i],
                "metadata": all_data['metadatas'][i] if all_data['metadatas'] else {}
            })
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        size_kb = export_path.stat().st_size / 1024
        return f"[OK] Database berhasil diekspor ke JSON!\nFile: {export_path}\nUkuran: {size_kb:.2f} KB\nDokumen: {len(all_data['ids'])}"
    except Exception as e:
        return f"[ERROR] Gagal ekspor JSON: {e}"

def import_json(filepath: str) -> str:
    """Import database dari JSON (akan di-embed ulang)."""
    import json
    
    json_path = Path(filepath)
    if not json_path.exists():
        json_path = CODING_OUTPUT_DIR / filepath
        if not json_path.exists():
            return f"[ERROR] File tidak ditemukan: {filepath}"
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'documents' not in data:
            return "[ERROR] Format JSON tidak valid. Harus ada key 'documents'."
        
        imported_count = 0
        skipped_count = 0
        
        for doc in data['documents']:
            doc_id = doc.get('id', f"imported_{imported_count + 1}")
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            if not content:
                skipped_count += 1
                continue
            
            # Cek apakah ID sudah ada
            existing = collection.get(ids=[doc_id])
            if existing['ids']:
                skipped_count += 1
                continue
            
            # Tambahkan ke database (akan di-embed otomatis)
            collection.add(
                documents=[content],
                ids=[doc_id],
                metadatas=[metadata]
            )
            imported_count += 1
        
        return f"[OK] Import JSON berhasil!\nDiimpor: {imported_count} dokumen\nDilewati (sudah ada): {skipped_count}\nTotal sekarang: {collection.count()}"
    except Exception as e:
        return f"[ERROR] Gagal impor JSON: {e}"

def export_all(folder_name: str = None) -> str:
    """Export ChromaDB (ZIP) + Neo4j Graph (JSON) dalam satu folder."""
    import shutil
    import zipfile
    import json
    
    if not folder_name:
        folder_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    export_folder = CODING_OUTPUT_DIR / folder_name
    export_folder.mkdir(exist_ok=True)
    
    results = []
    
    # 1. Export ChromaDB ke ZIP
    try:
        chroma_zip = export_folder / "chromadb.zip"
        with zipfile.ZipFile(chroma_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in CHROMA_DB_PATH.rglob('*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(CHROMA_DB_PATH))
        results.append(f"✓ ChromaDB: {chroma_zip.name} ({collection.count()} docs)")
    except Exception as e:
        results.append(f"✗ ChromaDB: {e}")
    
    # 2. Export Neo4j Graph ke JSON
    if NEO4J_AVAILABLE:
        try:
            graph = get_graph()
            if graph.connect():
                neo4j_json = export_folder / "neo4j_graph.json"
                
                # Get all nodes
                nodes = graph.run_query("MATCH (n) RETURN labels(n) as labels, properties(n) as props")
                
                # Get all relationships
                rels = graph.run_query("""
                    MATCH (a)-[r]->(b) 
                    RETURN a.name as from_name, labels(a)[0] as from_type,
                           type(r) as rel_type, 
                           b.name as to_name, labels(b)[0] as to_type
                """)
                
                export_data = {
                    "exported_at": datetime.now().isoformat(),
                    "nodes": nodes,
                    "relationships": rels
                }
                
                with open(neo4j_json, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
                
                results.append(f"✓ Neo4j: {neo4j_json.name} ({len(nodes)} nodes, {len(rels)} rels)")
            else:
                results.append("✗ Neo4j: Tidak bisa konek")
        except Exception as e:
            results.append(f"✗ Neo4j: {e}")
    else:
        results.append("- Neo4j: Module tidak tersedia")
    
    output = f"[OK] Export All selesai!\n"
    output += f"Folder: {export_folder}\n\n"
    output += "Hasil:\n" + "\n".join(results)
    
    return output

def import_all(folder_path: str) -> str:
    """Import ChromaDB + Neo4j dari folder backup."""
    import shutil
    import zipfile
    
    folder = Path(folder_path)
    if not folder.exists():
        folder = CODING_OUTPUT_DIR / folder_path
        if not folder.exists():
            # List available backup folders
            backups = [d for d in CODING_OUTPUT_DIR.iterdir() if d.is_dir() and d.name.startswith('backup_')]
            if backups:
                listing = "\n".join([f"- {b.name}" for b in backups])
                return f"[ERROR] Folder tidak ditemukan: {folder_path}\n\nBackup tersedia:\n{listing}"
            return f"[ERROR] Folder tidak ditemukan: {folder_path}"
    
    results = []
    global collection, chroma_client
    
    # 1. Import ChromaDB dari ZIP
    chroma_zip = folder / "chromadb.zip"
    if chroma_zip.exists():
        try:
            # Backup existing
            backup_path = CODING_OUTPUT_DIR / "chroma_db_backup_temp"
            if CHROMA_DB_PATH.exists():
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(CHROMA_DB_PATH, backup_path)
            
            # Clear and extract
            if CHROMA_DB_PATH.exists():
                shutil.rmtree(CHROMA_DB_PATH)
            CHROMA_DB_PATH.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(chroma_zip, 'r') as zip_ref:
                zip_ref.extractall(CHROMA_DB_PATH)
            
            # Reload ChromaDB
            chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
            collection = chroma_client.get_or_create_collection(
                name="agent_memory",
                embedding_function=embedding_fn
            )
            
            results.append(f"✓ ChromaDB: {collection.count()} dokumen diimpor")
        except Exception as e:
            results.append(f"✗ ChromaDB: {e}")
    else:
        results.append("- ChromaDB: chromadb.zip tidak ditemukan")
    
    # 2. Import Neo4j dari JSON
    neo4j_json = folder / "neo4j_graph.json"
    if neo4j_json.exists() and NEO4J_AVAILABLE:
        try:
            graph = get_graph()
            if graph.connect():
                with open(neo4j_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                nodes_imported = 0
                rels_imported = 0
                
                # Import nodes
                for node in data.get('nodes', []):
                    labels = node.get('labels', ['Entity'])
                    props = node.get('props', {})
                    if labels and props.get('name'):
                        graph.save_entity(labels[0], props['name'], props)
                        nodes_imported += 1
                
                # Import relationships
                for rel in data.get('relationships', []):
                    from_name = rel.get('from_name', '')
                    from_type = rel.get('from_type', 'Entity')
                    rel_type = rel.get('rel_type', 'RELATED_TO')
                    to_name = rel.get('to_name', '')
                    to_type = rel.get('to_type', 'Entity')
                    
                    if from_name and to_name:
                        graph.save_relationship(from_name, from_type, rel_type, to_name, to_type)
                        rels_imported += 1
                
                results.append(f"✓ Neo4j: {nodes_imported} nodes, {rels_imported} rels diimpor")
            else:
                results.append("✗ Neo4j: Tidak bisa konek")
        except Exception as e:
            results.append(f"✗ Neo4j: {e}")
    elif not NEO4J_AVAILABLE:
        results.append("- Neo4j: Module tidak tersedia")
    else:
        results.append("- Neo4j: neo4j_graph.json tidak ditemukan")
    
    output = f"[OK] Import All selesai!\n"
    output += f"Dari: {folder}\n\n"
    output += "Hasil:\n" + "\n".join(results)
    
    return output

def lihat_semua_memory() -> str:
    """List semua dokumen di ChromaDB."""
    if collection.count() == 0:
        return "Database ChromaDB masih kosong."
    
    all_docs = collection.get()
    output = f"=== CHROMADB ({len(all_docs['ids'])} dokumen) ===\n"
    for doc_id, doc in zip(all_docs['ids'], all_docs['documents']):
        output += f"- [{doc_id}] {doc[:80]}...\n"
    return output

# --- FUNGSI SILVERBULLET (File System) ---

def simpan_ke_silverbullet(judul: str, isi: str) -> str:
    """Simpan langsung ke folder notes/ sebagai Markdown."""
    filename = slugify(judul) + ".md"
    filepath = NOTES_PATH / filename
    
    content = f"# {judul}\n\n{isi}\n\n---\n*Dibuat oleh Agent pada {timestamp()}*\n"
    
    filepath.write_text(content, encoding="utf-8")
    print(f">>> [SILVERBULLET] Saved: {filename}")
    return f"Tersimpan di SilverBullet: {filename}"

def append_ke_journal() -> str:
    """Append catatan ke Journal.md (untuk log harian)."""
    journal_path = NOTES_PATH / "Journal.md"
    
    # Baca isi lama atau buat baru
    if journal_path.exists():
        existing = journal_path.read_text(encoding="utf-8")
    else:
        existing = "# Journal\n\nCatatan harian dari Agent.\n\n"
    
    return journal_path, existing

def lihat_notes() -> str:
    """List semua file di folder notes/."""
    files = list(NOTES_PATH.glob("*.md"))
    if not files:
        return "Folder notes/ masih kosong."
    
    output = f"=== SILVERBULLET NOTES ({len(files)} files) ===\n"
    for f in files:
        output += f"- {f.name}\n"
    return output

# --- FUNGSI BROWSER AUTOMATION ---

def tulis_visual_di_silverbullet(judul: str, isi: str) -> str:
    """Buka browser dan ketik visual di SilverBullet."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "[ERROR] Playwright tidak terinstall. Jalankan: pip install playwright && playwright install"
    
    print(f">>> [BROWSER] Opening SilverBullet...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=BROWSER_HEADLESS, slow_mo=BROWSER_SLOW_MO)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            page_name = slugify(judul)
            page_url = f"{SILVERBULLET_URL}/{page_name}"
            
            print(f">>> [BROWSER] Navigating to: {page_url}")
            page.goto(page_url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            
            # Cari editor
            editor = page.locator('.cm-content').first
            if editor.is_visible(timeout=5000):
                editor.click()
                page.keyboard.press("Control+a")
                page.keyboard.press("Delete")
                page.wait_for_timeout(300)
                
                # Ketik dengan efek visual
                content = f"# {judul}\n\n{isi}"
                for char in content:
                    page.keyboard.type(char, delay=15)
                
                page.keyboard.press("Control+s")
                page.wait_for_timeout(1500)
                
                print(f">>> [BROWSER] Done writing!")
                page.wait_for_timeout(2000)
                
                return f"Berhasil menulis visual di SilverBullet: {page_name}"
            else:
                return "[ERROR] Editor tidak ditemukan"
                
        except Exception as e:
            return f"[ERROR] Browser: {e}"
        finally:
            browser.close()

# --- FUNGSI LLM ---

def tanya_llm(prompt: str, context: str = "") -> str:
    """Kirim ke Ollama LLM."""
    full_prompt = prompt
    if context:
        full_prompt = f"{context}\n\nBerdasarkan informasi di atas, jawab:\n{prompt}"
    
    print(f">>> [LLM] Model: {OLLAMA_MODEL}")
    print(f">>> [LLM] URL: {OLLAMA_API_URL}/api/generate")
    
    try:
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": full_prompt, "stream": False},
            timeout=180
        )
        
        if response.status_code != 200:
            return f"[ERROR] Ollama status {response.status_code}: {response.text[:200]}"
        
        data = response.json()
        answer = data.get("response", "")
        
        if not answer:
            # Debug: tampilkan response mentah
            print(f">>> [LLM DEBUG] Raw response: {data}")
            return f"[ERROR] Response kosong. Cek apakah model '{OLLAMA_MODEL}' sudah ter-download. Jalankan: ollama pull {OLLAMA_MODEL}"
        
        return answer
        
    except requests.exceptions.Timeout:
        return f"[ERROR] Timeout! Model '{OLLAMA_MODEL}' mungkin terlalu lambat atau belum siap."
    except requests.exceptions.ConnectionError:
        return f"[ERROR] Tidak bisa konek ke Ollama di {OLLAMA_API_URL}. Pastikan Ollama berjalan!"
    except Exception as e:
        return f"[ERROR] LLM: {e}"

# --- AUTO-RAG + SILVERBULLET LOGIC ---

def detect_intent(user_input: str) -> str:
    """Deteksi intent user."""
    lower = user_input.lower()
    
    # Intent: SHOW GRAPH (knowledge graph summary)
    if any(kw in lower for kw in ["show graph", "tampilkan graph", "lihat graph", "graph summary"]):
        return "SHOW_GRAPH"
    
    # Intent: QUERY GRAPH
    if any(kw in lower for kw in ["query graph", "cari graph", "relasi"]):
        return "QUERY_GRAPH"
    
    # Intent: EXPORT GRAPH
    if any(kw in lower for kw in ["export graph", "ekspor graph"]):
        return "EXPORT_GRAPH"
    
    # Intent: IMPORT GRAPH
    if any(kw in lower for kw in ["import graph", "impor graph"]):
        return "IMPORT_GRAPH"
    
    # Intent: EXPORT ALL (ChromaDB + Neo4j)
    if any(kw in lower for kw in ["export all", "ekspor semua", "backup all", "backup semua"]):
        return "EXPORT_ALL"
    
    # Intent: IMPORT ALL
    if any(kw in lower for kw in ["import all", "impor semua", "restore all"]):
        return "IMPORT_ALL"
    
    # Intent: EXPORT JSON
    if any(kw in lower for kw in ["export json", "ekspor json"]):
        return "EXPORT_JSON"
    
    # Intent: IMPORT JSON
    if any(kw in lower for kw in ["import json", "impor json"]):
        return "IMPORT_JSON"
    
    # Intent: EXPORT DATABASE (ZIP)
    if any(kw in lower for kw in ["export db", "ekspor db", "ekspor database", "export database", "backup db"]):
        return "EXPORT_DB"
    
    # Intent: IMPORT DATABASE (ZIP)
    if any(kw in lower for kw in ["import db", "impor db", "impor database", "import database", "restore db"]):
        return "IMPORT_DB"
    
    # Intent: RESET DATABASE
    if any(kw in lower for kw in ["reset database", "hapus semua", "clear db", "reset db"]):
        return "RESET_DB"
    
    # Intent: TANYA PDF (hanya dari PDF)
    if any(kw in lower for kw in ["tanya pdf", "ask pdf", "dari pdf"]):
        return "ASK_PDF"
    
    # Intent: TANYA VISUAL (Q&A dengan output ke browser)
    if any(kw in lower for kw in ["tanya visual", "jawab visual", "ask visual"]):
        return "ASK_VISUAL"
    
    # Intent: LOAD PDF
    if any(kw in lower for kw in ["load pdf", "baca pdf", "muat pdf", "import pdf"]):
        return "LOAD_PDF"
    
    # Intent: LIST PDF
    if any(kw in lower for kw in ["list pdf", "daftar pdf"]):
        return "LIST_PDF"
    
    # Intent: SIMPAN ke memori
    if any(kw in lower for kw in ["ingat", "simpan memori", "remember"]):
        return "SAVE_MEMORY"
    
    # Intent: TULIS ke SilverBullet
    if any(kw in lower for kw in ["tulis", "buat catatan", "write", "catat di"]):
        return "WRITE_NOTE"
    
    # Intent: TULIS VISUAL (browser)
    if any(kw in lower for kw in ["ketik visual", "buka browser", "tulis visual"]):
        return "WRITE_VISUAL"
    
    # Intent: LIHAT SEMUA
    if any(kw in lower for kw in ["semua", "list", "tampilkan", "daftar"]):
        return "LIST"
    
    # Default: TANYA
    return "ASK"

def process_input(user_input: str) -> str:
    """Proses input dengan hybrid logic."""
    intent = detect_intent(user_input)
    print(f">>> [INTENT] {intent}")
    
    # === KNOWLEDGE GRAPH COMMANDS ===
    
    if intent == "SHOW_GRAPH":
        if not NEO4J_AVAILABLE:
            return "[ERROR] Neo4j module tidak tersedia. Install neo4j: pip install neo4j"
        try:
            graph = get_graph()
            if not graph.connect():
                return "[ERROR] Tidak bisa konek ke Neo4j. Pastikan Neo4j berjalan (docker-compose up neo4j)"
            return graph.get_graph_summary()
        except Exception as e:
            return f"[ERROR] Graph: {e}"
    
    elif intent == "QUERY_GRAPH":
        if not NEO4J_AVAILABLE:
            return "[ERROR] Neo4j module tidak tersedia."
        
        cleaned = user_input
        for kw in ["query graph", "cari graph", "relasi"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if not cleaned:
            return "Format: 'query graph [nama entitas]'\nContoh: 'query graph OpenAI'"
        
        try:
            graph = get_graph()
            if not graph.connect():
                return "[ERROR] Tidak bisa konek ke Neo4j."
            return graph.query_relationships(cleaned)
        except Exception as e:
            return f"[ERROR] Graph query: {e}"
    
    elif intent == "EXPORT_GRAPH":
        if not NEO4J_AVAILABLE:
            return "[ERROR] Neo4j module tidak tersedia."
        
        cleaned = user_input
        for kw in ["export graph", "ekspor graph"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        filename = cleaned if cleaned else None
        
        try:
            graph = get_graph()
            if not graph.connect():
                return "[ERROR] Tidak bisa konek ke Neo4j."
            return graph.export_graph(filename)
        except Exception as e:
            return f"[ERROR] Export graph: {e}"
    
    elif intent == "IMPORT_GRAPH":
        if not NEO4J_AVAILABLE:
            return "[ERROR] Neo4j module tidak tersedia."
        
        cleaned = user_input
        for kw in ["import graph", "impor graph"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if not cleaned:
            # List available graph JSON files
            jsons = [f for f in CODING_OUTPUT_DIR.glob("*.json") if "graph" in f.name.lower()]
            if jsons:
                listing = "\n".join([f"- {j.name}" for j in jsons])
                return f"Format: 'import graph [file.json]'\n\nFile tersedia:\n{listing}"
            return "Format: 'import graph [file.json]'\nTidak ada file graph JSON."
        
        try:
            graph = get_graph()
            if not graph.connect():
                return "[ERROR] Tidak bisa konek ke Neo4j."
            return graph.import_graph(cleaned)
        except Exception as e:
            return f"[ERROR] Import graph: {e}"
    
    elif intent == "EXPORT_ALL":
        cleaned = user_input
        for kw in ["export all", "ekspor semua", "backup all", "backup semua"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        folder_name = cleaned if cleaned else None
        return export_all(folder_name)
    
    elif intent == "IMPORT_ALL":
        cleaned = user_input
        for kw in ["import all", "impor semua", "restore all"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if not cleaned:
            # List backup folders
            backups = [d for d in CODING_OUTPUT_DIR.iterdir() if d.is_dir() and d.name.startswith('backup_')]
            if backups:
                listing = "\n".join([f"- {b.name}" for b in backups])
                return f"Format: 'import all [folder_backup]'\n\nBackup tersedia:\n{listing}"
            return "Format: 'import all [folder_backup]'\nTidak ada folder backup."
        
        return import_all(cleaned)
    
    # === CHROMADB EXPORT/IMPORT ===
    
    elif intent == "EXPORT_JSON":
        # Ekspor database ke JSON
        cleaned = user_input
        for kw in ["export json", "ekspor json"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        filename = cleaned if cleaned else None
        return export_json(filename)
    
    elif intent == "IMPORT_JSON":
        # Impor database dari JSON
        cleaned = user_input
        for kw in ["import json", "impor json"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if not cleaned:
            jsons = list(CODING_OUTPUT_DIR.glob("*.json"))
            if jsons:
                listing = "\n".join([f"- {j.name}" for j in jsons])
                return f"Format: 'import json [namafile.json]'\n\nFile tersedia:\n{listing}"
            return "Format: 'import json [namafile.json]'\nTidak ada file JSON di folder coding_output/"
        
        return import_json(cleaned)
    
    elif intent == "EXPORT_DB":
        # Ekspor database ke ZIP
        cleaned = user_input
        for kw in ["export db", "ekspor database", "export database", "backup db"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        filename = cleaned if cleaned else None
        return export_database(filename)
    
    elif intent == "IMPORT_DB":
        # Impor database dari ZIP
        cleaned = user_input
        for kw in ["import db", "impor database", "import database", "restore db"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if not cleaned:
            # List file ZIP yang tersedia
            zips = list(CODING_OUTPUT_DIR.glob("*.zip"))
            if zips:
                listing = "\n".join([f"- {z.name}" for z in zips])
                return f"Format: 'import db [namafile.zip]'\n\nFile tersedia:\n{listing}"
            return "Format: 'import db [namafile.zip]'\nTidak ada file ZIP di folder coding_output/"
        
        return import_database(cleaned)
    
    elif intent == "RESET_DB":
        return reset_database()
    
    elif intent == "ASK_PDF":
        # Tanya HANYA dari PDF
        cleaned = user_input
        for kw in ["tanya pdf", "ask pdf", "dari pdf"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if not cleaned:
            return "Format: 'tanya pdf [pertanyaan Anda]'"
        
        context = cari_pdf_only(cleaned)
        if not context:
            return "Tidak ada dokumen PDF di database. Gunakan 'load pdf [file.pdf]' dulu."
        
        answer = tanya_llm(cleaned, context)
        return f"{answer}\n\n---\n*Sumber: Dokumen PDF*"
    
    elif intent == "ASK_VISUAL":
        # Tanya dengan output visual ke browser (HANYA dari PDF)
        cleaned = user_input
        for kw in ["tanya visual", "jawab visual", "ask visual"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if not cleaned:
            return "Format: 'tanya visual [pertanyaan Anda]'"
        
        # Cari konteks HANYA dari PDF
        context = cari_pdf_only(cleaned)
        if not context:
            context = cari_memory(cleaned)  # Fallback ke semua memory
        
        answer = tanya_llm(cleaned, context)
        
        # Generate judul
        judul = "QA_" + slugify(cleaned[:25])
        isi = f"**Pertanyaan:**\n{cleaned}\n\n**Jawaban:**\n{answer}"
        
        if context:
            isi += f"\n\n**Konteks:**\n{context[:500]}..."
        
        # Tulis visual di browser
        result = tulis_visual_di_silverbullet(judul, isi)
        return f"{answer}\n\n---\n{result}"
    
    elif intent == "LOAD_PDF":
        # Ekstrak nama file dari input
        cleaned = user_input
        for kw in ["load pdf", "baca pdf", "muat pdf", "import pdf"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if cleaned:
            return simpan_pdf_ke_memory(cleaned)
        else:
            # List available PDFs
            return f"Nama file PDF tidak disebutkan.\n\n{list_pdf_files()}\n\nGunakan: 'load pdf [namafile.pdf]'"
    
    elif intent == "LIST_PDF":
        return list_pdf_files()
    
    elif intent == "SAVE_MEMORY":
        # Simpan ke ChromaDB
        cleaned = user_input
        for kw in ["ingat", "simpan", "bahwa", "remember", "memori"]:
            cleaned = cleaned.lower().replace(kw, "").strip()
        
        if cleaned:
            doc_id = simpan_memory(cleaned)
            return f"OK! Disimpan ke memori (ID: {doc_id})\nSaya akan mengingat: '{cleaned}'"
        return "Apa yang ingin disimpan?"
    
    elif intent == "WRITE_NOTE":
        # Simpan ke SilverBullet via file system
        parts = user_input.split(":", 1)
        if len(parts) == 2:
            judul = parts[0].replace("tulis", "").replace("buat catatan", "").strip()
            isi = parts[1].strip()
        else:
            judul = "Catatan_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            isi = user_input.replace("tulis", "").replace("buat catatan", "").strip()
        
        # Simpan ke KEDUA tempat
        simpan_memory(f"{judul}: {isi}")
        result = simpan_ke_silverbullet(judul, isi)
        return f"OK! {result}\n(Juga disimpan ke memori RAG)"
    
    elif intent == "WRITE_VISUAL":
        # Buka browser untuk visual typing
        parts = user_input.split(":", 1)
        if len(parts) == 2:
            judul = parts[0].replace("ketik visual", "").replace("tulis visual", "").strip()
            isi = parts[1].strip()
        else:
            return "Format: 'ketik visual [judul]: [isi]'"
        
        return tulis_visual_di_silverbullet(judul, isi)
    
    elif intent == "LIST":
        memory_list = lihat_semua_memory()
        notes_list = lihat_notes()
        return f"{memory_list}\n\n{notes_list}"
    
    else:  # ASK
        # Cari konteks dari memory
        context = cari_memory(user_input)
        answer = tanya_llm(user_input, context)
        
        # Jika jawaban berasal dari PDF, simpan ke SilverBullet
        if context and "KONTEKS DARI MEMORY" in context:
            # Cek apakah konteks dari PDF
            pdf_results = collection.query(
                query_texts=[user_input],
                n_results=1,
                where={"source": "pdf"}
            )
            
            if pdf_results['ids'][0]:  # Ada hasil dari PDF
                # Generate judul dari pertanyaan
                judul = "Hasil_" + slugify(user_input[:30])
                isi = f"**Pertanyaan:** {user_input}\n\n**Jawaban:**\n{answer}\n\n**Sumber:** PDF Documents"
                
                simpan_ke_silverbullet(judul, isi)
                return f"{answer}\n\n---\n*Jawaban juga disimpan di SilverBullet: {judul}.md*"
        
        return answer

# --- MAIN LOOP ---

def main():
    print("=" * 60)
    print("BOT SUPER - RAG + Knowledge Graph + SilverBullet + PDF")
    print("=" * 60)
    print(f"ChromaDB: {collection.count()} dokumen")
    print(f"Notes: {len(list(NOTES_PATH.glob('*.md')))} files")
    print(f"PDFs: {len(list(DOCS_PATH.glob('*.pdf')))} files")
    
    # Check Neo4j connection
    if NEO4J_AVAILABLE:
        try:
            graph = get_graph()
            if graph.connect():
                print(f"Neo4j: Connected ✓")
            else:
                print("Neo4j: Not connected (run: docker-compose up neo4j)")
        except:
            print("Neo4j: Error connecting")
    else:
        print("Neo4j: Module not available")
    
    print("\n=== PERINTAH ===")
    print("\n📄 PDF & Memori:")
    print("  - 'Load pdf [file]'       -> Muat PDF + ekstrak entitas")
    print("  - 'List pdf'              -> Daftar file PDF")
    print("  - 'Tanya pdf [?]'         -> Tanya HANYA dari PDF")
    print("  - 'Tampilkan semua'       -> List memori & notes")
    
    print("\n🔗 Knowledge Graph:")
    print("  - 'Show graph'            -> Lihat ringkasan graph")
    print("  - 'Query graph [entity]'  -> Cari relasi entitas")
    print("  - 'Export graph'          -> Ekspor graph ke JSON")
    print("  - 'Import graph [file]'   -> Impor graph dari JSON")
    
    print("\n💾 Backup & Migrasi:")
    print("  - 'Export all'            -> Backup ChromaDB + Neo4j")
    print("  - 'Import all [folder]'   -> Restore dari backup")
    print("  - 'Export db'             -> Ekspor ChromaDB saja (ZIP)")
    print("  - 'Import db [file]'      -> Impor ChromaDB saja")
    
    print("\n🖥️ SilverBullet:")
    print("  - 'Tanya visual [?]'      -> Tanya & ketik di browser")
    
    print("\n  - [pertanyaan]            -> Tanya dengan konteks")
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
