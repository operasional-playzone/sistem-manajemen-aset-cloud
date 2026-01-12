# 🏭 Sistem Manajemen Aset Mesin (Cloud Edition)

Aplikasi manajemen aset berbasis web yang terintegrasi langsung dengan **Google Sheets**. Sistem ini menggantikan versi Database SQL lokal, memungkinkan akses data yang lebih fleksibel, *real-time*, dan kolaboratif tanpa biaya server (Serverless).

## 🚀 Fitur Utama

* **Cloud Database:** Menggunakan Google Sheets sebagai backend database.
* **CRUD Lengkap:** Input Aset Baru, Edit Detail, Mutasi (Pindah Lokasi), dan Likuidasi (Hapus).
* **Riwayat & Log (Audit Trail):** Mencatat setiap aktivitas user (siapa, kapan, dan apa yang diubah).
* **Fitur Undo:** Membatalkan kesalahan mutasi atau menghapus data secara instan.
* **Generate ID Otomatis:** Sistem ID numerik yang urut dan rapi.
* **Export Data:** Download laporan dalam format Excel `.xlsx`.
* **Login Admin:** Keamanan akses menggunakan username/password sederhana.

## 🛠️ Teknologi yang Digunakan

* **Bahasa:** Python 3.9+
* **Framework UI:** Streamlit
* **Database:** Google Sheets (via Google Drive API)
* **Library Utama:** `pandas`, `gspread`, `oauth2client`

---

## ⚙️ Persiapan (Instalasi)

Ikuti langkah ini untuk menjalankan aplikasi di komputer lokal atau server baru.

### 1. Clone Repository
```bash
git clone git@github.com:operasional-playzone/sistem-manajemen-aset-cloud.git
cd sistem-manajemen-aset-cloud
```

### 2. Setup Virtual Environment (Opsional tapi Disarankan)
```bash
python -m venv env_gsheet
# Windows:
env_gsheet\Scripts\activate
# Mac/Linux:
source env_gsheet/bin/activate
``` 

3. Install Dependencies
```bash
pip install -r requirements.txt
``` 

### 🔑 Konfigurasi Rahasia (Wajib!)
1. File credentials.json
Ini adalah kunci akses "Service Account" Google Cloud Platform.

2. Letakkan file credentials.json di folder utama (satu level dengan app_gsheet.py).

3. Pastikan email service account di dalam file ini sudah di-invite sebagai Editor di Google Sheet target.

4. File .env
Buat file bernama .env di folder utama, lalu isi konfigurasi berikut:
# Konfigurasi Login Admin Aplikasi

```
ADMIN_USER=
ADMIN_PASS=
```

📂 Struktur Google Sheets

* Pastikan Google Sheet target memiliki nama file DB_MANAJEMEN_ASET_MESIN dan memiliki 2 Tab (Worksheet):

Tab master_aset (Header huruf kecil semua):

* id, lokasi_toko, kategori, nama_mesin, harga_beli, no_registrasi, status

Tab riwayat_log:

* id, lokasi_asal, kategori, nama_mesin, jenis_aksi, tanggal, harga_beli, no_registrasi, keterangan

▶️ Cara Menjalankan Aplikasi
Setelah instalasi dan konfigurasi selesai, jalankan perintah:
```bash
streamlit run app_gsheet.py
```

Aplikasi akan otomatis terbuka di browser (biasanya di http://localhost:8501).

🔄 Cara Update Data Massal (Migrasi)
Jika ada data Excel baru yang ingin di-upload ulang (Reset Database):

1. Siapkan file Excel bersih dengan nama 1_Master_Aset_Cleaned.xlsx dan 2_Riwayat_Log_Cleaned.xlsx.

2. Jalankan script migrasi:
```bash
python migrasi_ke_gsheet.py
```

3. Peringatan: Script ini akan menghapus seluruh isi Google Sheet dan menggantinya dengan data Excel baru

Siapkan file Excel bersih dengan nama 

* 1_Master_Aset_Cleaned.xlsx dan 
* 2_Riwayat_Log_Cleaned.xlsx.

Jalankan script migrasi:

```bash
python migrasi_ke_gsheet.py
```

Peringatan: Script ini akan menghapus seluruh isi Google Sheet dan menggantinya dengan data Excel baru.

🛡️ Keamanan
1. Jangan pernah upload file .env atau credentials.json ke GitHub Public.

2. Pastikan .gitignore selalu aktif.

-----------------------------------------------
Developer: [Abrar Argya Adana / Operasional] 

Last Updated: Januari 2026
