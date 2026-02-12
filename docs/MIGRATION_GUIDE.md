# 📦 Panduan Migrasi ChromaDB (Knowledge Base)

Panduan ini menjelaskan cara memindahkan "otak" (vector database) dari satu PC ke PC lain agar bot langsung memahami konteks dan data sebelumnya **tanpa perlu mengirim ulang file PDF atau training ulang**.

---

## 🎯 Kapan Perlu Migrasi?

- Pindah ke PC/laptop baru
- Ingin berbagi knowledge base dengan tim
- Backup database sebelum eksperimen
- Deploy ke server production

---

## 📍 Lokasi Database

Database ChromaDB tersimpan di:
```
[project]/coding_output/chroma_db/
```

---

## 🚀 Metode 1: Export/Import via Bot (Direkomendasikan)

### A. Export di PC Lama (Sumber)

1. Jalankan bot:
   ```bash
   python bot_super.py
   ```

2. Ketik perintah export:
   ```
   export db
   ```
   
3. Bot akan membuat file ZIP:
   ```
   [OK] Database berhasil diekspor!
   File: D:\Project\...\coding_output\knowledge_base_20260201_213000.zip
   Ukuran: 2.45 MB
   Dokumen: 25
   ```

4. **Salin file ZIP** tersebut ke PC baru (via flashdisk, cloud, atau transfer lainnya).

### B. Import di PC Baru (Tujuan)

1. Pastikan project sudah di-clone:
   ```bash
   git clone https://github.com/username/autogen-superbot.git
   cd autogen-superbot
   pip install -r requirements.txt
   ```

2. Taruh file ZIP di folder `coding_output/`:
   ```
   coding_output/
   └── knowledge_base_20260201_213000.zip  <-- taruh di sini
   ```

3. Jalankan bot dan import:
   ```bash
   python bot_super.py
   ```
   
4. Ketik perintah import:
   ```
   import db knowledge_base_20260201_213000.zip
   ```

5. Selesai! Database berhasil dipulihkan:
   ```
   [OK] Database berhasil diimpor!
   Dokumen: 25
   Backup tersimpan di: .../chroma_db_backup
   ```

---

## 📄 Metode 2: Export/Import JSON (Portable)

Format JSON berguna jika:
- Ingin melihat/edit isi database secara manual
- Ingin migrasi ke sistem lain (bukan ChromaDB)
- Perlu merge data dari beberapa sumber

### Export ke JSON
```
export json
```

### Import dari JSON
```
import json knowledge_base_20260201_213000.json
```

> ⚠️ **Catatan:** Import JSON akan melakukan **re-embedding** (lebih lambat dari ZIP).

---

## 📁 Metode 3: Copy Manual Folder

Jika tidak ingin menggunakan bot:

1. **Di PC Lama:** Copy folder `coding_output/chroma_db/`

2. **Di PC Baru:** Paste ke lokasi yang sama, timpa folder yang ada:
   ```
   [project]/
   └── coding_output/
       └── chroma_db/     <-- paste/replace folder ini
   ```

3. Jalankan bot seperti biasa.

---

## 🔧 Troubleshooting

### Error "Database kosong setelah import"
- Pastikan file ZIP tidak corrupt
- Cek apakah folder `chroma_db/` sudah terisi file setelah import

### Error "Versi ChromaDB tidak kompatibel"
- Pastikan versi ChromaDB di kedua PC sama
- Cek dengan: `pip show chromadb`
- Jika berbeda, gunakan **Metode 2 (JSON)** yang lebih portable

### File ZIP terlalu besar untuk dikirim
- Kompres ulang dengan 7-Zip (format .7z)
- Atau gunakan layanan transfer file seperti WeTransfer

---

## 📊 Perbandingan Metode

| Metode | Kecepatan Import | Portable | Bisa Diedit |
|--------|------------------|----------|-------------|
| ZIP    | ⚡ Instan        | ❌ Tidak  | ❌ Tidak     |
| JSON   | 🐢 Lambat (re-embed) | ✅ Ya   | ✅ Ya       |
| Manual | ⚡ Instan        | ❌ Tidak  | ❌ Tidak     |

---

## ✅ Checklist Migrasi

- [ ] Export database di PC lama (`export db` atau `export json`)
- [ ] Transfer file ke PC baru
- [ ] Clone/setup project di PC baru
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Taruh file export di `coding_output/`
- [ ] Import database (`import db [file]` atau `import json [file]`)
- [ ] Test dengan bertanya sesuatu: `tanya pdf apa isi dokumen?`

---

**Selamat! Knowledge base Anda sudah berhasil dipindahkan.** 🎉
