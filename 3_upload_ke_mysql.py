import mysql.connector
import pandas as pd
import os
import numpy as np
import math
from dotenv import load_dotenv

# --- KONFIGURASI ---
load_dotenv(override=True)

DB_CONFIG = {
    'host': os.getenv("DB_HOST", "localhost"),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASS", ""),
}

NAMA_DB = "manajemen_aset"
BATCH_SIZE = 1000  # <-- KITA BATASI KIRIM 1000 BARIS PER TEMBAKAN

# Nama File Bersih
FILE_MASTER = '1_Master_Aset_Cleaned.xlsx'
FILE_HISTORY = '2_Riwayat_Log_Cleaned.xlsx'

def connect_server():
    return mysql.connector.connect(**DB_CONFIG)

def setup_database():
    conn = connect_server()
    cursor = conn.cursor()
    
    print(f"🔨 Menyiapkan Database '{NAMA_DB}'...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {NAMA_DB}")
    cursor.execute(f"USE {NAMA_DB}")
    
    # Drop tabel lama biar bersih
    cursor.execute("DROP TABLE IF EXISTS master_aset")
    cursor.execute("DROP TABLE IF EXISTS riwayat_log")
    
    print("🔨 Membuat Struktur Tabel Baru...")
    
    cursor.execute("""
    CREATE TABLE master_aset (
        id INT AUTO_INCREMENT PRIMARY KEY,
        lokasi_toko VARCHAR(100),
        kategori VARCHAR(100),
        nama_mesin VARCHAR(255),
        harga_beli VARCHAR(100),
        no_registrasi VARCHAR(100),
        no_reg_system VARCHAR(100),
        status VARCHAR(50) DEFAULT 'Aktif',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE riwayat_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        lokasi_asal VARCHAR(100),
        kategori VARCHAR(100),
        nama_mesin VARCHAR(255),
        jenis_aksi VARCHAR(50),
        tanggal_kejadian DATE,
        harga_beli VARCHAR(100),
        no_registrasi VARCHAR(100),
        no_reg_system VARCHAR(100),
        keterangan TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

def batch_upload(cursor, query, data, nama_tabel):
    """Fungsi pembantu untuk memecah data jadi potongan kecil"""
    total = len(data)
    jumlah_batch = math.ceil(total / BATCH_SIZE)
    
    print(f"   📦 Total Data: {total} baris. Akan dikirim dalam {jumlah_batch} batch.")
    
    for i in range(0, total, BATCH_SIZE):
        batch = data[i : i + BATCH_SIZE]
        cursor.executemany(query, batch)
        # Kita commit per batch biar server gak berat
        print(f"      ➡️ Mengupload batch ke-{i//BATCH_SIZE + 1} ({len(batch)} baris)...")
        
    print(f"✅ Selesai upload ke '{nama_tabel}'!")

def upload_data():
    conn = mysql.connector.connect(**DB_CONFIG, database=NAMA_DB)
    cursor = conn.cursor()
    
    # --- 1. UPLOAD MASTER ASET ---
    if os.path.exists(FILE_MASTER):
        print(f"\n🚀 Memproses Data Master: {FILE_MASTER}...")
        df = pd.read_excel(FILE_MASTER)
        df = df.replace({np.nan: None})
        
        query = """
        INSERT INTO master_aset (lokasi_toko, kategori, nama_mesin, harga_beli, no_registrasi, no_reg_system, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'Aktif')
        """
        
        data_insert = []
        for _, row in df.iterrows():
            data_insert.append((
                row.get('lokasi_toko'),
                row.get('kategori'),
                row.get('nama_mesin'),
                str(row.get('harga_beli')) if row.get('harga_beli') else None,
                str(row.get('no_registrasi')) if row.get('no_registrasi') else None,
                str(row.get('no_reg_system')) if row.get('no_reg_system') else None
            ))
            
        # PANGGIL FUNGSI BATCH
        batch_upload(cursor, query, data_insert, "master_aset")
        conn.commit()

    else:
        print(f"❌ GAGAL: File {FILE_MASTER} tidak ditemukan!")

    # --- 2. UPLOAD RIWAYAT LOG ---
    if os.path.exists(FILE_HISTORY):
        print(f"\n🚀 Memproses Data History: {FILE_HISTORY}...")
        df = pd.read_excel(FILE_HISTORY)
        df = df.replace({np.nan: None})
        
        query = """
        INSERT INTO riwayat_log (lokasi_asal, kategori, nama_mesin, jenis_aksi, tanggal_kejadian, harga_beli, no_registrasi, no_reg_system, keterangan)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        data_insert = []
        for _, row in df.iterrows():
            tgl = row.get('tanggal')
            if pd.isna(tgl) or str(tgl) == 'None' or str(tgl) == 'NaT': tgl = None
                
            data_insert.append((
                row.get('lokasi_asal'),
                row.get('kategori'),
                row.get('nama_mesin'),
                row.get('jenis_aksi'),
                tgl,
                str(row.get('harga_beli')) if row.get('harga_beli') else None,
                str(row.get('no_registrasi')) if row.get('no_registrasi') else None,
                str(row.get('no_reg_system')) if row.get('no_reg_system') else None,
                row.get('keterangan')
            ))
            
        # PANGGIL FUNGSI BATCH
        batch_upload(cursor, query, data_insert, "riwayat_log")
        conn.commit()

    else:
        print(f"❌ GAGAL: File {FILE_HISTORY} tidak ditemukan!")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        setup_database()
        upload_data()
        print("\n🎉 SELAMAT! Migrasi Database Selesai Sempurna.")
    except Exception as e:
        print(f"\n💀 TERJADI ERROR: {e}")