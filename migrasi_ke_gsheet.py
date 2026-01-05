import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

# --- KONFIGURASI FILE ---
FILE_MASTER_EXCEL = '1_Master_Aset_Cleaned.xlsx'
FILE_LOG_EXCEL = '2_Riwayat_Log_Cleaned.xlsx'
NAMA_GOOGLE_SHEET = 'DB_MANAJEMEN_ASET_MESIN' # <--- Pastikan nama ini benar

def connect_gsheet():
    print("🔌 Menghubungkan ke Google Sheets...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if not os.path.exists("credentials.json"):
        print("❌ Error: File 'credentials.json' tidak ditemukan!")
        sys.exit()
        
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    
    try:
        sh = client.open(NAMA_GOOGLE_SHEET)
        return sh
    except Exception as e:
        print(f"❌ Gagal membuka Sheet '{NAMA_GOOGLE_SHEET}'. Pastikan nama benar dan Drive API aktif.")
        sys.exit()

def upload_data(sh, excel_file, tab_name):
    print(f"\n📂 Memproses file: {excel_file} ...")
    
    try:
        df = pd.read_excel(excel_file)
    except FileNotFoundError:
        print(f"⚠️ File Excel {excel_file} tidak ditemukan. Melewati langkah ini.")
        return

    # --- PERBAIKAN: TAMBAH KOLOM ID OTOMATIS ---
    # Cek apakah kolom 'id' sudah ada. Jika belum, buat baru.
    # Kita standarisasi nama kolom jadi huruf kecil semua biar aman
    df.columns = df.columns.str.lower()
    
    if 'id' not in df.columns:
        print(f"⚙️ Membuat kolom ID otomatis untuk {tab_name}...")
        # Buat ID dari angka 1 sampai terakhir
        df.insert(0, 'id', range(1, 1 + len(df)))
    
    # Cleaning standar
    df = df.fillna('')
    df = df.astype(str)
    
    # Akses Tab GSheet
    try:
        worksheet = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        print(f"⚠️ Tab '{tab_name}' tidak ditemukan. Membuat tab baru...")
        worksheet = sh.add_worksheet(title=tab_name, rows=1000, cols=20)

    # Bersihkan & Upload
    print(f"🧹 Membersihkan data lama di tab '{tab_name}'...")
    worksheet.clear()

    data_to_upload = [df.columns.values.tolist()] + df.values.tolist()
    
    print(f"🚀 Mengupload {len(df)} baris data ke Cloud...")
    worksheet.update(data_to_upload)
    
    print(f"✅ Sukses! Data {tab_name} berhasil dimigrasi.")

# --- EKSEKUSI UTAMA ---
if __name__ == "__main__":
    sh = connect_gsheet()
    upload_data(sh, FILE_MASTER_EXCEL, 'master_aset')
    upload_data(sh, FILE_LOG_EXCEL, 'riwayat_log')
    print("\n🎉 SELESAI! Kolom ID sudah dibuat dan data terupload.")