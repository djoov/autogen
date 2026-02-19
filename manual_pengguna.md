# 📘 Panduan Pengguna Bot Super AI

Selamat datang di **Bot Super AI**! Ini adalah asisten cerdas yang memiliki "otak ganda":
1. **Memory (ChromaDB)**: Mengingat isi dokumen PDF yang Anda upload.
2. **Knowledge Graph (Neo4j)**: Memahami hubungan antar entitas (siapa kenal siapa, organisasi apa milik siapa).

---

## 🚀 1. Persiapan Awal (Instalasi)

Sebelum menggunakan, pastikan komputer Anda sudah siap.

### Prasyarat:
1. **Install Python** (versi 3.10 ke atas)
2. **Install Docker Desktop** (untuk database Neo4j)
3. **Install Ollama** (untuk otak AI-nya)

### Langkah Instalasi Pertama Kali:
1. Buka folder project ini di Terminal/CMD.
2. Install library yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```
3. Download model AI (pilih salah satu):
   ```bash
   ollama pull llama3.1:8b    # Ringan & Cepat (RAM 8GB+)
   ollama pull qwen2.5:14b    # Lebih Pintar (RAM 16GB+)
   ```
4. Jalankan Database Neo4j (Wajib jalan di background):
   ```bash
   docker-compose up -d neo4j
   ```

---

## 🖥️ 2. Menjalankan Aplikasi

Anda bisa menggunakan Web UI yang ramah pengguna.

1. Buka Terminal/CMD di folder project.
2. Ketik perintah:
   ```bash
   streamlit run web_ui.py
   ```
3. Browser akan otomatis terbuka di alamat: `http://localhost:8501`

---

## 💡 3. Fitur Utama & Cara Pakai

### A. Sidebar (Menu Kiri)
Di sini Anda bisa melihat status sistem dan melakukan aksi.

- **Status Sistem**: Indikator 🟢 (Hijau) artinya OK.
  - **Ollama**: Otak AI siap.
  - **ChromaDB**: Ingatan dokumen siap.
  - **Neo4j**: Knowledge Graph siap.
  *- Jika ada yang 🔴 (Merah), cek bagian Troubleshooting.*

- **Upload PDF**:
  - Drag & drop file PDF ke kotak upload.
  - Tunggu proses "chunking" & "extracting".
  - Setelah selesai, teks PDF masuk ke ingatan bot, dan entitasnya masuk ke graph.

- **Backup & Migrasi**:
  - Tombol **📤 Export All**: Untuk backup semua data (Memory + Graph).
  - Menu **📥 Import**: Untuk mengembalikan data dari backup di komputer lain.

### B. Chat Area (Tengah)
Tempat Anda bertanya jawab.

- **Ketik Pertanyaan**: "Apa isi bab 3 dari dokumen A?"
- **Lihat Proses**: Bot akan menampilkan `⏳ Sedang berpikir...`.
- **Sumber Jawaban**: Di bawah jawaban, bot memberi tahu dapat info dari mana:
  - 📍 `Sumber: ChromaDB` (dari teks dokumen)
  - 📍 `Sumber: Neo4j` (dari hubungan data)
  - 📍 `Sumber: ChromaDB + Neo4j` (gabungan keduanya)

### C. Knowledge Graph (Tab Kanan)
Klik tab **"🔗 Knowledge Graph"** di atas chat untuk melihat visualisasi.
- **Bulatan Warna-warni**: Mewakili entitas (Orang, Organisasi, Lokasi).
- **Garis Panah**: Menunjukkan hubungan antar mereka.
- Anda bisa zoom, geser, dan klik untuk eksplorasi.

---

## ❓ 4. Tips Bertanya yang Efektif

Agar jawaban AI maksimal, gunakan gaya bertanya yang sesuai:

| Tipe Pertanyaan | Contoh | Keterangan |
|-----------------|--------|------------|
| **Spesifik Dokumen** | *"Apa kesimpulan dari laporan keuangan tahun 2023?"* | AI akan mencari di teks PDF. |
| **Hubungan/Relasi** | *"Siapa saja yang bekerja sama dengan PT. Maju Mundur?"* | AI akan mencari di Knowledge Graph. |
| **Eksplorasi** | *"Jelaskan tentang proyek Alpha dan siapa manajernya?"* | AI menggabungkan info teks + relasi graph. |
| **Umum** | *"Buatkan email penawaran produk"* | AI menggunakan pengetahuan umumnya sendiri. |

---

## 🛠️ 5. Troubleshooting (Masalah Umum)

**Q: Chat responnya lama sekali / Timeout?**
- **Sebab**: Model AI sedang dimuat ke RAM (loading awal), atau PC lambat.
- **Solusi**: Tunggu 3-5 menit. Jika masih error, refresh halaman. Pastikan spesifikasi PC memadai (RAM minimal 16GB disarankan).

**Q: Muncul error `[ERROR] LLM status: 404`?**
- **Sebab**: Model yang disetting di `config.py` belum di-download di PC ini.
- **Solusi**: Buka terminal, jalankan `ollama pull [nama_model]` (misal `ollama pull llama3.1:8b`).

**Q: Indikator Neo4j Merah (🔴)?**
- **Sebab**: Docker container Neo4j mati atau belum dinyalakan.
- **Solusi**: Buka terminal, jalankan `docker-compose up -d neo4j`. Tunggu 10 detik lalu refresh web.

**Q: Jawaban "Saya tidak tahu" padahal ada di PDF?**
- **Sebab**: Dokumen mungkin belum ter-index sempurna atau pertanyaan terlalu singkat.
- **Solusi**: Coba upload ulang PDF-nya, atau gunakan pertanyaan yang lebih spesifik dengan kata kunci yang ada di dokumen.

---

## 🔄 6. Cara Pindah Komputer (Migrasi)

Ingin memindahkan "otak" bot ke laptop lain? Mudah!

1. **Di PC Lama**: Klik tombol **📤 Export All** di sidebar. Folder backup akan muncul di folder `coding_output`.
2. **Copy Data**: Salin folder backup tersebut ke PC Baru (letakkan di folder yang sama).
3. **Di PC Baru**: Buka Web UI, pilih folder backup di menu **📥 Import**, lalu klik **Import**.
4. **Selesai**: Semua ingatan dan knowledge graph sudah berpindah!

---
*Selamat bekerja dengan Asisten Cerdas Anda!* 🤖✨
