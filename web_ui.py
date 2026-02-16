import streamlit as st
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Import fungsi dari bot_super (tanpa menjalankan main loop)
# menghindari warmup_model loop di sini
os.environ.setdefault("STREAMLIT_MODE", "1")

#PAGE CONFIG ---
st.set_page_config(
    page_title="Bot Super - AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

#CSS STYLING
st.markdown("""
<style>
    /* Global */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Chat messages */
    .user-msg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 80%;
        float: right;
        clear: both;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    
    .bot-msg {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #e0e0e0;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 80%;
        float: left;
        clear: both;
        border: 1px solid #2a2a4a;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    
    .clearfix { clear: both; }
    
    /* Status indicators */
    .status-online { color: #00e676; font-weight: 600; }
    .status-offline { color: #ff5252; font-weight: 600; }
    
    /* Sidebar styling */
    .sidebar-header {
        font-size: 1.2em;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    
    /* Action buttons */
    .stButton>button {
        border-radius: 10px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem;
        font-weight: 700;
    }
    
    /* Chat container */
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)


#LAZY IMPORT BOT FUNCTIONS
@st.cache_resource
def init_bot():
    """Initialize bot components (cached)."""
    import chromadb
    from chromadb.utils import embedding_functions
    from config import (
        OLLAMA_API_URL, OLLAMA_MODEL, CHROMA_DB_PATH, EMBEDDING_MODEL, RAG_TOP_K,
        CODING_OUTPUT_DIR
    )
    
    #Setup ChromaDB
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    collection = chroma_client.get_or_create_collection(
        name="agent_memory",
        embedding_function=embedding_fn
    )
    
    # Neo4j
    neo4j_available = False
    try:
        from neo4j_graph import get_graph
        neo4j_available = True
    except ImportError:
        pass
    
    return {
        "collection": collection,
        "chroma_client": chroma_client,
        "embedding_fn": embedding_fn,
        "neo4j_available": neo4j_available,
        "ollama_url": OLLAMA_API_URL,
        "ollama_model": OLLAMA_MODEL,
        "chroma_path": CHROMA_DB_PATH,
        "output_dir": CODING_OUTPUT_DIR,
        "top_k": RAG_TOP_K
    }


def check_ollama(url):
    """Cek apakah Ollama berjalan."""
    import requests
    try:
        r = requests.get(f"{url}/api/tags", timeout=3)
        return r.status_code == 200
    except:
        return False



def check_neo4j():
    """Cek apakah Neo4j berjalan."""
    try:
        from neo4j_graph import get_graph
        graph = get_graph()
        return graph.connect()
    except:
        return False


def warmup_ollama(url, model):
    """Pemanasan model (load ke RAM)."""
    import requests
    try:
        # Cek apakah model sudah loaded
        r = requests.post(f"{url}/api/show", json={"name": model}, timeout=3)
        if r.status_code == 200:
            # Kirim empty request untuk trigger load
            requests.post(
                f"{url}/api/generate",
                json={"model": model, "prompt": "hi", "stream": False},
                timeout=5
            )
            return True
    except:
        pass
    return False



def tanya_llm_web(prompt, context, bot):
    """Kirim ke Ollama LLM."""
    import requests
    full_prompt = prompt
    if context:
        full_prompt = f"{context}\n\nBerdasarkan informasi di atas, jawab:\n{prompt}"
    
    try:
        response = requests.post(
            f"{bot['ollama_url']}/api/generate",
            json={"model": bot['ollama_model'], "prompt": full_prompt, "stream": False},
            timeout=300  # Timeout 5 menit
        )
        if response.status_code == 200:
            return response.json().get("response", "[No response]")
        return f"[ERROR] LLM status: {response.status_code}"
    except Exception as e:
        return f"[ERROR] LLM: {e}"


def cari_memory_web(query, bot):
    """Cari konteks dari ChromaDB."""
    collection = bot["collection"]
    if collection.count() == 0:
        return ""
    
    results = collection.query(
        query_texts=[query],
        n_results=min(bot["top_k"], collection.count())
    )
    
    if not results['ids'][0]:
        return ""
    
    context = "KONTEKS DARI MEMORY:\n"
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        source = meta.get('source', 'manual')
        context += f"\n[{source}] {doc}\n"
    
    return context


def cari_graph_web(query):
    """Cari konteks dari Neo4j."""
    try:
        from neo4j_graph import get_graph
        graph = get_graph()
        if graph.connect():
            return graph.search_graph(query)
    except:
        pass
    return ""


def hybrid_search(query, bot):
    """Gabungkan ChromaDB + Neo4j search."""
    # ChromaDB
    chroma_context = cari_memory_web(query, bot)
    
    # Neo4j
    graph_context = ""
    if bot["neo4j_available"]:
        graph_context = cari_graph_web(query)
    
    full_context = ""
    if chroma_context:
        full_context += chroma_context
    if graph_context:
        full_context += "\n\n" + graph_context
    
    sources = []
    if chroma_context:
        sources.append("ChromaDB")
    if graph_context:
        sources.append("Neo4j")
    
    return full_context, sources


def load_pdf_web(filepath, bot):
    """Load PDF ke ChromaDB."""
    from pypdf import PdfReader
    from config import CODING_OUTPUT_DIR
    
    path = Path(filepath)
    if not path.exists():
        path = Path("documents") / filepath
    
    if not path.exists():
        return f"File tidak ditemukan: {filepath}"
    
    try:
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        if not text.strip():
            return "PDF kosong atau tidak bisa dibaca."
        
        # Chunk text
        words = text.split()
        chunks = []
        for i in range(0, len(words), 350):
            chunk = " ".join(words[i:i+400])
            if chunk:
                chunks.append(chunk)
        
        collection = bot["collection"]
        saved = 0
        for i, chunk in enumerate(chunks):
            doc_id = f"pdf_{path.name}_{i+1}"
            existing = collection.get(ids=[doc_id])
            if existing['ids']:
                continue
            collection.add(
                documents=[chunk],
                ids=[doc_id],
                metadatas=[{
                    "source": "pdf",
                    "filename": path.name,
                    "chunk": i + 1,
                    "total_chunks": len(chunks),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }]
            )
            saved += 1
        
        # Extract entities ke Neo4j
        entity_msg = ""
        if bot["neo4j_available"]:
            try:
                from neo4j_graph import get_graph, extract_entities_with_llm, save_entities_to_graph
                graph = get_graph()
                if graph.connect():
                    extracted = extract_entities_with_llm(text[:3000])
                    entity_msg = save_entities_to_graph(graph, extracted)
            except:
                entity_msg = "Entity extraction gagal"
        
        result = f"✅ **{path.name}** berhasil dimuat!\n"
        result += f"- 📄 {len(reader.pages)} halaman\n"
        result += f"- 📦 {len(chunks)} chunks ({saved} baru)\n"
        if entity_msg:
            result += f"- 🔗 {entity_msg}"
        
        return result
    except Exception as e:
        return f"❌ Error: {e}"


def get_graph_summary_web():
    """Get graph summary."""
    try:
        from neo4j_graph import get_graph
        graph = get_graph()
        if graph.connect():
            return graph.get_graph_summary()
    except:
        pass
    return "Graph tidak tersedia"


def get_graph_data_web():
    """Get all nodes and relationships for visualization."""
    try:
        from neo4j_graph import get_graph
        graph = get_graph()
        if not graph.connect():
            return [], []
        
        # Get all nodes
        nodes_result = graph.run_query(
            "MATCH (n) RETURN id(n) as id, labels(n) as labels, n.name as name"
        )
        
        # Get all relationships
        rels_result = graph.run_query(
            "MATCH (a)-[r]->(b) RETURN id(a) as from_id, type(r) as rel_type, id(b) as to_id"
        )
        
        return nodes_result, rels_result
    except:
        return [], []


# --- INITIALIZE ---
bot = init_bot()

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================
# SIDEBAR
# ============================
with st.sidebar:
    st.markdown('<div class="sidebar-header">🤖 Bot Super</div>', unsafe_allow_html=True)
    st.caption("RAG + Knowledge Graph + PDF Hybrid")
    
    st.divider()
    
    # --- STATUS ---
    st.markdown("### 📡 Status Sistem")
    
    col1, col2, col3 = st.columns(3)
    
    ollama_ok = check_ollama(bot["ollama_url"])
    neo4j_ok = check_neo4j() if bot["neo4j_available"] else False
    
    with col1:
        if ollama_ok:
            st.markdown("🟢 **Ollama**")
            # Auto-warmup di background jika belum
            if "model_warmed_up" not in st.session_state:
                with st.spinner("🔥 Warming up..."):
                    if warmup_ollama(bot["ollama_url"], bot["ollama_model"]):
                        st.session_state.model_warmed_up = True
                        st.toast(f"Model {bot['ollama_model']} siap!", icon="🔥")
        else:
            st.markdown("🔴 **Ollama**")
    
    with col2:
        st.markdown(f"🟢 **ChromaDB**")
    
    with col3:
        if neo4j_ok:
            st.markdown("🟢 **Neo4j**")
        else:
            st.markdown("🔴 **Neo4j**")
    
    st.divider()
    
    # --- METRICS ---
    st.markdown("### 📊 Database")
    m1, m2 = st.columns(2)
    m1.metric("Dokumen", bot["collection"].count())
    
    pdf_count = len(list(Path("documents").glob("*.pdf")))
    m2.metric("PDF Files", pdf_count)
    
    st.divider()
    
    # --- UPLOAD PDF ---
    st.markdown("### 📄 Upload PDF")
    uploaded = st.file_uploader(
        "Drag & drop PDF di sini",
        type=["pdf"],
        accept_multiple_files=False,
        label_visibility="collapsed"
    )
    
    if uploaded:
        # Simpan ke folder documents/
        save_path = Path("documents") / uploaded.name
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())
        
        with st.spinner(f"Loading {uploaded.name}..."):
            result = load_pdf_web(str(save_path), bot)
        
        st.success(result)
        st.rerun()
    
    # List PDFs with titles
    docs_path = Path("documents")
    pdfs = list(docs_path.glob("*.pdf"))
    if pdfs:
        with st.expander(f"📚 PDF Files ({len(pdfs)})", expanded=False):
            for pdf in pdfs:
                size_kb = pdf.stat().st_size / 1024
                # Try to get PDF title
                title = pdf.stem
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(pdf))
                    meta = reader.metadata
                    if meta and meta.title:
                        title = meta.title
                    elif reader.pages:
                        # Ambil baris pertama sebagai judul
                        first_text = (reader.pages[0].extract_text() or "").strip()
                        first_line = first_text.split('\n')[0].strip()[:60]
                        if first_line:
                            title = first_line
                except:
                    pass
                st.markdown(f"📎 **{title}**")
                st.caption(f"{pdf.name} • {size_kb:.0f} KB • {len(reader.pages) if 'reader' in dir() else '?'} halaman")
    
    st.divider()
    
    # --- KNOWLEDGE GRAPH ---
    if neo4j_ok:
        with st.expander("🔗 Knowledge Graph", expanded=False):
            summary = get_graph_summary_web()
            st.text(summary)
    
    st.divider()
    
    # --- MIGRATION / BACKUP ---
    st.markdown("### 💾 Backup & Migrasi")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        if st.button("� Export All", use_container_width=True, help="Backup ChromaDB + Neo4j"):
            import json
            import zipfile
            
            folder_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_folder = bot["output_dir"] / folder_name
            export_folder.mkdir(exist_ok=True)
            
            results = []
            
            # 1. ChromaDB ZIP
            try:
                chroma_zip = export_folder / "chromadb.zip"
                with zipfile.ZipFile(chroma_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in bot["chroma_path"].rglob('*'):
                        if file.is_file():
                            zipf.write(file, file.relative_to(bot["chroma_path"]))
                results.append(f"✓ ChromaDB: {bot['collection'].count()} docs")
            except Exception as e:
                results.append(f"✗ ChromaDB: {e}")
            
            # 2. Neo4j JSON
            if bot["neo4j_available"]:
                try:
                    from neo4j_graph import get_graph
                    graph = get_graph()
                    if graph.connect():
                        nodes = graph.run_query("MATCH (n) RETURN labels(n) as labels, properties(n) as props")
                        rels = graph.run_query("""
                            MATCH (a)-[r]->(b) 
                            RETURN a.name as from_name, labels(a)[0] as from_type,
                                   type(r) as rel_type, properties(r) as rel_props,
                                   b.name as to_name, labels(b)[0] as to_type
                        """)
                        
                        export_data = {
                            "exported_at": datetime.now().isoformat(),
                            "format_version": "2.0",
                            "nodes": nodes,
                            "relationships": rels
                        }
                        neo4j_file = export_folder / "neo4j_graph.json"
                        with open(neo4j_file, 'w', encoding='utf-8') as f:
                            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
                        results.append(f"✓ Neo4j: {len(nodes)} nodes, {len(rels)} rels")
                except Exception as e:
                    results.append(f"✗ Neo4j: {e}")
            
            st.success(f"📦 **{folder_name}**\n\n" + "\n".join(results))
    
    with col_b:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # --- IMPORT ---
    backup_folders = [d for d in bot["output_dir"].iterdir() if d.is_dir() and d.name.startswith('backup_')]
    
    if backup_folders:
        backup_folders.sort(key=lambda x: x.name, reverse=True)
        with st.expander(f"📥 Import dari Backup ({len(backup_folders)} tersedia)", expanded=False):
            selected = st.selectbox(
                "Pilih backup:",
                options=[f.name for f in backup_folders],
                key="import_select"
            )
            
            if selected:
                sel_folder = bot["output_dir"] / selected
                # Show contents
                contents = list(sel_folder.iterdir())
                st.caption(f"Isi: {', '.join([f.name for f in contents])}")
                
                if st.button("⬇️ Import Backup Ini", use_container_width=True, type="primary"):
                    import json
                    import zipfile
                    import chromadb
                    from chromadb.utils import embedding_functions
                    from config import CHROMA_DB_PATH, EMBEDDING_MODEL
                    
                    results = []
                    
                    # 1. Import ChromaDB
                    chroma_zip = sel_folder / "chromadb.zip"
                    if chroma_zip.exists():
                        try:
                            import shutil
                            if CHROMA_DB_PATH.exists():
                                shutil.rmtree(CHROMA_DB_PATH)
                            CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
                            
                            with zipfile.ZipFile(chroma_zip, 'r') as zipf:
                                zipf.extractall(CHROMA_DB_PATH)
                            
                            # Reload client
                            new_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
                            new_embedding = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
                            new_collection = new_client.get_or_create_collection(name="agent_memory", embedding_function=new_embedding)
                            bot["collection"] = new_collection
                            bot["chroma_client"] = new_client
                            
                            results.append(f"✓ ChromaDB: {new_collection.count()} docs restored")
                        except Exception as e:
                            results.append(f"✗ ChromaDB: {e}")
                    else:
                        results.append("- ChromaDB: tidak ada di backup")
                    
                    # 2. Import Neo4j
                    neo4j_file = sel_folder / "neo4j_graph.json"
                    if neo4j_file.exists() and bot["neo4j_available"]:
                        try:
                            from neo4j_graph import get_graph
                            graph = get_graph()
                            if graph.connect():
                                result = graph.import_graph(str(neo4j_file))
                                results.append(f"✓ Neo4j: {result}")
                        except Exception as e:
                            results.append(f"✗ Neo4j: {e}")
                    elif neo4j_file.exists():
                        results.append("- Neo4j: module tidak tersedia")
                    else:
                        results.append("- Neo4j: tidak ada di backup")
                    
                    st.success("**Import selesai!**\n\n" + "\n".join(results))
                    st.rerun()
    
    st.divider()
    st.caption(f"Model: `{bot['ollama_model']}`")
    st.caption(f"ChromaDB: `{bot['chroma_path']}`")


# ============================
# MAIN AREA - TABS
# ============================
tab_chat, tab_graph = st.tabs(["💬 Chat", "🔗 Knowledge Graph"])

# ============================
# TAB 1: CHAT
# ============================
with tab_chat:
    st.caption("Tanya apapun — jawaban dari ChromaDB + Knowledge Graph")
    
    # --- PANDUAN ---
    with st.expander("📖 Panduan Cara Bertanya", expanded=False):
        st.markdown("""
        ### 💡 Tips Bertanya
        
        | Jenis | Contoh | Keterangan |
        |-------|--------|------------|
        | **Tanya umum** | `Apa itu machine learning?` | Jawab dari LLM + konteks |
        | **Tanya dari PDF** | `Jelaskan bab 3 dari dokumen` | Cari di PDF yang sudah diload |
        | **Tanya relasi** | `Siapa yang membuat GPT-4?` | Cari dari Knowledge Graph |
        | **Bahasa bebas** | `Ceritakan tentang OpenAI` | Bisa Bahasa Indonesia/Inggris |
        
        ### 🔍 Cara Kerja Hybrid Search
        1. **ChromaDB** — Mencari teks yang mirip secara semantik
        2. **Neo4j** — Mencari entitas & hubungan terkait
        3. **Gabungkan** — Kirim ke LLM sebagai konteks
        
        ### 📄 Upload PDF
        - Drag & drop PDF di sidebar kiri
        - Bot otomatis memecah teks dan menyimpan ke database
        - Entitas otomatis diekstrak ke Knowledge Graph
        
        ### ⚠️ Catatan
        - Pastikan **Ollama** aktif (🟢) sebelum bertanya
        - Semakin banyak PDF dimuat, semakin kaya konteksnya
        - Jawaban ditandai sumber: `ChromaDB`, `Neo4j`, atau keduanya
        """)
    
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])
            if msg.get("sources"):
                src_text = " + ".join(msg["sources"])
                st.caption(f"📍 Sumber: {src_text}")
    
    # Chat input
    if prompt := st.chat_input("Ketik pertanyaan..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"⏳ Sedang berpikir... (Model: {bot['ollama_model']})"):
                # Hybrid search
                context, sources = hybrid_search(prompt, bot)
                
                # Tanya LLM
                answer = tanya_llm_web(prompt, context, bot)
            
            st.markdown(answer)
            
            if sources:
                src_text = " + ".join(sources)
                st.caption(f"📍 Sumber: {src_text}")
        
        # Save to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources
        })

# ============================
# TAB 2: KNOWLEDGE GRAPH
# ============================
with tab_graph:
    st.caption("Visualisasi entitas dan relasi dari Neo4j Knowledge Graph")
    
    if not bot["neo4j_available"]:
        st.warning("⚠️ Neo4j module tidak tersedia. Install: `pip install neo4j`")
    elif not check_neo4j():
        st.warning("⚠️ Neo4j tidak terhubung. Jalankan: `docker-compose up -d neo4j`")
    else:
        # Refresh button
        if st.button("🔄 Refresh Graph", key="refresh_graph"):
            st.rerun()
        
        nodes_data, rels_data = get_graph_data_web()
        
        if not nodes_data:
            st.info("🔗 Graph masih kosong. Load PDF untuk mengekstrak entitas otomatis.")
        else:
            # Color palette per label
            label_colors = {
                "person": "#FF6B6B",
                "organization": "#4ECDC4",
                "technology": "#45B7D1",
                "product": "#96CEB4",
                "location": "#FFEAA7",
                "concept": "#DDA0DD",
                "event": "#98D8C8",
                "entity": "#B0B0B0",
            }
            
            try:
                from streamlit_agraph import agraph, Node, Edge, Config
                
                # Build nodes
                vis_nodes = []
                node_ids = set()
                for n in nodes_data:
                    nid = str(n.get("id", ""))
                    name = n.get("name", "?")
                    labels = n.get("labels", ["Entity"])
                    label = labels[0] if labels else "Entity"
                    
                    color = label_colors.get(label.lower(), "#667eea")
                    
                    vis_nodes.append(Node(
                        id=nid,
                        label=name,
                        size=25,
                        color=color,
                        font={"color": "white", "size": 14},
                        title=f"{label}: {name}"
                    ))
                    node_ids.add(nid)
                
                # Build edges
                vis_edges = []
                for r in rels_data:
                    from_id = str(r.get("from_id", ""))
                    to_id = str(r.get("to_id", ""))
                    rel_type = r.get("rel_type", "RELATED")
                    
                    if from_id in node_ids and to_id in node_ids:
                        vis_edges.append(Edge(
                            source=from_id,
                            target=to_id,
                            label=rel_type,
                            color="#888888",
                            font={"size": 10, "color": "#cccccc"}
                        ))
                
                # Graph config
                config = Config(
                    width="100%",
                    height=500,
                    directed=True,
                    physics=True,
                    hierarchical=False,
                    nodeHighlightBehavior=True,
                    highlightColor="#F7A7A6",
                    collapsible=False,
                    node={"labelProperty": "label"},
                    link={"labelProperty": "label", "renderLabel": True}
                )
                
                # Render graph
                agraph(nodes=vis_nodes, edges=vis_edges, config=config)
                
                # Stats
                st.divider()
                col1, col2, col3 = st.columns(3)
                col1.metric("🔵 Nodes", len(vis_nodes))
                col2.metric("🔗 Relationships", len(vis_edges))
                
                # Unique labels
                unique_labels = set()
                for n in nodes_data:
                    labels = n.get("labels", [])
                    if labels:
                        unique_labels.add(labels[0])
                col3.metric("🏷️ Tipe Entitas", len(unique_labels))
                
                # Legend
                with st.expander("🎨 Legenda Warna", expanded=False):
                    for label in sorted(unique_labels):
                        color = label_colors.get(label.lower(), "#667eea")
                        st.markdown(f"<span style='color:{color}; font-size:20px;'>●</span> **{label}**", unsafe_allow_html=True)
                
            except ImportError:
                st.error("Install visualisasi: `pip install streamlit-agraph`")
            except Exception as e:
                st.error(f"Error rendering graph: {e}")
