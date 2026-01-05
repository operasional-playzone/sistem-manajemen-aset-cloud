# 🏭 Sistem Manajemen Aset Mesin

Dokumentasi lengkap untuk **instalasi, konfigurasi, pemrosesan data (ETL), dan deployment**
aplikasi **Dashboard Aset Mesin (Streamlit)** pada lingkungan **Windows (Local Deployment)**.

---

## 📌 Deskripsi Singkat

Aplikasi ini digunakan untuk:
- Mengelola data aset mesin
- Melakukan proses ETL dari Excel ke MySQL
- Menyajikan dashboard interaktif menggunakan Streamlit

---

## 🛠️ 1. Persiapan Awal (Prerequisites)

Pastikan software berikut sudah terinstal:

1. **XAMPP** (Disarankan PHP 8.x ke atas)
2. **Python** (Versi 3.9 atau lebih baru)
3. **Visual Studio Code**

---

## ⚙️ Konfigurasi Kritis MySQL (WAJIB)

Agar upload data besar tidak gagal (`Error: Packet too large`), lakukan konfigurasi berikut:

1. Buka **XAMPP Control Panel**
2. Klik **Config** pada MySQL → pilih **my.ini**
3. Cari parameter berikut:
   ```ini
   max_allowed_packet
4. Ubah nilainya menjadi:
max_allowed_packet=64M
5. Simpan file dan restart MySQL & Apache

6. Pastikan status MySQL Running (Hijau)

## 🐍 2. Instalasi Environment Python

Jalankan perintah berikut di **Terminal VS Code** (di folder proyek).

### A. Membuat Virtual Environment
```bash
python -m venv env_aset_mesin

B. Mengaktifkan Virtual Environment

Command Prompt (cmd):
```bash
env_aset_mesin\Scripts\activate


PowerShell (VS Code Default):
```bash
.\env_aset_mesin\Scripts\Activate.ps1


Pastikan muncul (env_aset_mesin) di terminal.

C. Instalasi Library

Buat file requirements.txt dengan isi berikut:
streamlit
pandas
mysql-connector-python
python-dotenv
openpyxl
xlsxwriter
jupyter

Install dependency:
pip install -r requirements.txt

D. Konfigurasi Database (.env)

Buat file .env di root project:
DB_HOST=localhost
DB_USER=root
DB_PASS=

⚠️ Catatan Keamanan
File .env tidak disarankan di-push ke GitHub.
Tambahkan ke .gitignore.

---

## 📂 3. Struktur File Proyek

Pastikan susunan folder dan nama file Anda **sesuai dengan struktur berikut** agar pipeline berjalan normal.

```plaintext
Project_Aset_Mesin/
├── env_aset_mesin/                    # Virtual Environment Python
├── .env                               # Konfigurasi Database
├── requirements.txt                   # Daftar Library Python
├── README.md                          # Dokumentasi Proyek
│
├── [DATA MENTAH]
│   ├── Database_Aset_Lengkap.xlsx     # Data Wilayah Jabodetabek
│   └── Database_Luar_Jabodetabek.xlsx # Data Luar Jabodetabek
│
├── [SCRIPTS]
│   ├── 1_ekstrak_master.py
│   ├── 2_ekstrak_history_with_category.py
│   ├── cleaning_data.ipynb
│   ├── 3_upload_ke_mysql.py
│   └── app.py


🚀 4. Eksekusi Pipeline Data (Migrasi)

Tahapan ini WAJIB dijalankan secara berurutan untuk mengubah data Excel mentah menjadi database MySQL yang bersih dan siap dashboard.

🔹 Langkah A: Ekstraksi Data Mentah

Script ini berfungsi untuk:

Menggabungkan beberapa file Excel

Menyamakan struktur kolom

Memisahkan data Master Aset dan Riwayat Log

Perintah Terminal:
```bash
python 1_ekstrak_master.py
python 2_ekstrak_history_with_category.py

✅ Output Berhasil:

1_Master_Aset_Aktif.xlsx

2_Riwayat_Log_Fix.xlsx

🔹 Langkah B: Cleaning & Mapping (WAJIB)

Tahap ini bertujuan untuk:

Memperbaiki typo lokasi (contoh: R20 → R020 Ciputat)

Standarisasi kategori mesin

Mapping nama yang tidak konsisten

Langkah:

Buka file cleaning_data.ipynb di VS Code

Klik Run All

Pastikan tidak ada error di cell terakhir

Simpan notebook jika ada perubahan mapping

✅ Output Berhasil:

File dengan akhiran _Cleaned.xlsx

🔹 Langkah C: Upload ke Database MySQL

Script ini:

Mengupload data ke MySQL (XAMPP)

Menggunakan Batch Insert (1000 baris per batch) agar aman untuk data besar

Perintah Terminal:
```bash
python 3_upload_ke_mysql.py
🎉 SELAMAT! Migrasi Database Selesai Sempurna.

🌐 5. Menjalankan Aplikasi (Deploy Local)

Setelah database berhasil terisi, jalankan dashboard Streamlit.

Perintah Terminal:
```bash
streamlit run app.py
📌 Hasil:

Browser otomatis terbuka di:
* http://localhost:8501
*Gunakan Sidebar untuk:
**Navigasi halaman
**Filter data
**Input mutasi & likuidasi aset

💡 Troubleshooting & Maintenance
🔴 Masalah: MySQL Shutdown Unexpectedly (XAMPP)

Biasanya terjadi karena:

* Upload data besar tanpa konfigurasi my.ini

* Komputer mati mendadak

Solusi (Factory Reset Database):

1. Stop MySQL di XAMPP
2. Buka folder:
```bash
C:\xampp\mysql\
3. Rename folder data → data_old
4. Buat folder baru bernama data
5. Copy seluruh isi dari:
C:\xampp\mysql\backup
ke folder data baru
6. Start MySQL kembali
7. Jalankan ulang:
```bash
python 3_upload_ke_mysql.py

🟡 Masalah: Menambah Data Excel Baru

Jika ada update data dari tim lapangan:

1. Ganti file Excel lama dengan file terbaru
2. Jalankan ulang seluruh Tahap 4

* Langkah A

* Langkah B

* Langkah C

3. Refresh Streamlit (F5)

🔵 Maintenance: Menambah Mapping Typo Baru

Jika muncul lokasi atau kategori baru:

1. Buka audit_data.ipynb

2. Edit:

*MAP_LOKASI

*MAP_KATEGORI

*Klik Run All

Jalankan ulang:
```bash
python 3_upload_ke_mysql.py


👨‍💻 Kredit

Dibuat oleh:
Abrar Argya Adana

Last Updated:
Januari 2026

