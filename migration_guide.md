# Panduan Migrasi Knowledge Base AI Agent

Dokumen ini menjelaskan cara memindahkan seluruh "otak" AI Agent (Knowledge Base) dari satu komputer ke komputer lain.

## Apa yang Dimigrasikan?
System ini menggunakan **Hybrid Database**, jadi ada 2 komponen yang harus dipindahkan:
1. **ChromaDB** (Vector Database) - Berisi teks dari PDF yang sudah di-chunk dan di-embed.
2. **Neo4j** (Graph Database) - Berisi entitas dan relasi yang diekstrak oleh LLM.

## Persiapan
Pastikan kedua komputer (Lama & Baru) sudah terinstall:
- Python & Dependencies (`pip install -r requirements.txt`)
- Docker Desktop (untuk Neo4j)
- Ollama (untuk model LLM)

---

## 📤 Tahap 1: Export dari Komputer Lama

Anda bisa menggunakan **Web UI** (lebih mudah) atau Terminal.

### Cara export via Web UI:
1. Jalankan Web UI: 
   ```bash
   streamlit run web_ui.py
   ```
2. Buka browser di `http://localhost:8501`.
3. Di Sidebar sebelah kiri, cari bagian **💾 Backup & Migrasi**.
4. Klik tombol **📤 Export All**.
5. Tunggu proses selesai. Akan muncul pesan sukses: "📦 backup_YYYYMMDD_HHMMSS".
6. Folder backup akan tersimpan di dalam folder project:
   `coding_output/backup_YYYYMMDD_HHMMSS/`

### Apa isi folder backup?
- `chromadb.zip` (Database vektor)
- `neo4j_graph.json` (Database graph dalam format JSON portabel)

---

## 🚚 Tahap 2: Pindahkan Data

1. Buka folder project di Komputer Lama.
2. Masuk ke folder `coding_output`.
3. Copy folder `backup_YYYYMMDD_HHMMSS` yang baru dibuat.
4. Pindahkan folder tersebut ke **Komputer Baru**, letakkan di lokasi yang sama:
   `[Project Folder]/coding_output/backup_YYYYMMDD_HHMMSS/`

---

## 📥 Tahap 3: Import di Komputer Baru

### Cara import via Web UI:
1. Pastikan docker Neo4j sudah jalan di Komputer Baru:
   ```bash
   docker-compose up -d neo4j
   ```
2. Jalankan Web UI:
   ```bash
   streamlit run web_ui.py
   ```
3. Di Sidebar, cari bagian **💾 Backup & Migrasi**.
4. Lihat dropdown **📥 Import dari Backup**.
5. Pilih folder backup yang sudah Anda copy tadi.
6. Klik tombol **⬇️ Import Backup Ini**.
7. Tunggu hingga proses selesai dan halaman akan refresh otomatis.

### Verifikasi Hasil:
- Cek **Status Sistem** di sidebar: pastikan ChromaDB dan Neo4j berwarna hijau 🟢.
- Cek **Metrics**: Jumlah dokumen dan nodes harusnya sudah kembali seperti semula.
- Cek **Knowledge Graph** tab: Visualisasi graph harusnya muncul.

---

## ⚠️ Troubleshooting

**Q: Neo4j gagal konek saat import?**
A: Pastikan container Neo4j jalan. Cek `docker ps`. Jika belum, `docker-compose up -d neo4j`. Tunggu 10-20 detik agar database siap.

**Q: Import berhasil tapi Chat kosong?**
A: History chat tersimpan di session browser (sementara). Migrasi ini hanya memindahkan **Knowledge Base** (isi otak), bukan history percakapan.

**Q: Apakah model LLM ikut termigrasi?**
A: Tidak. Di komputer baru, Anda perlu pull model lagi jika belum ada:
   ```bash
   ollama pull llama3.1:8b  # atau model yg Anda pakai
   ```
