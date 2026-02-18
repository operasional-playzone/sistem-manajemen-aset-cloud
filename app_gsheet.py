import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import io
import time
import json
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
import matplotlib.pyplot as plt

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Manajemen Aset Mesin (Cloud)",
    page_icon="☁️",
    layout="wide"
)

# Load Environment Variables
load_dotenv(override=True)

# ==========================================
# ☁️ KONFIGURASI KHUSUS CLOUD (STREAMLIT)
# ==========================================
if not os.path.exists("credentials.json"):
    if "gcp_service_account" in st.secrets:
        with open("credentials.json", "w") as f:
            json.dump(dict(st.secrets["gcp_service_account"]), f)

# ==========================================
# 🔐 KONEKSI GOOGLE SHEETS
# ==========================================
@st.cache_resource
def get_gsheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if os.path.exists("credentials.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    else:
        st.error("⚠️ File 'credentials.json' tidak ditemukan!")
        st.stop()
        
    client = gspread.authorize(creds)
    try:
        sh = client.open("DB_MANAJEMEN_ASET_MESIN") 
        return sh
    except Exception as e:
        st.error(f"Gagal koneksi ke Google Sheets: {e}")
        st.stop()

# --- FUNGSI BANTUAN (HELPER) ---
def load_data(sheet_name):
    sh = get_gsheet_connection()
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Standarisasi header jadi huruf kecil semua
    df.columns = df.columns.str.lower()
    
    # Rename kolom tanggal manual jika ada variasi nama
    rename_map = {
        'tgl': 'tanggal',
        'date': 'tanggal',
        'tanggal_kejadian': 'tanggal'
    }
    df.rename(columns=rename_map, inplace=True)

    # Pastikan ID jadi string
    if not df.empty and 'id' in df.columns:
        df['id'] = df['id'].astype(str)
        
    return df

def generate_id(sheet_name="master_aset"):
    """Generate ID numerik baru berdasarkan sheet tertentu"""
    sh = get_gsheet_connection()
    worksheet = sh.worksheet(sheet_name)
    ids = worksheet.col_values(1)  # Ambil kolom pertama (ID)
    
    # Bersihkan header 'id' jika ikut terambil
    if ids and ids[0].lower() == 'id':
        ids.pop(0)
        
    if not ids:
        return "1"
        
    # Cari angka terbesar
    numeric_ids = [int(x) for x in ids if str(x).isdigit()]
    if not numeric_ids:
        return "1"
        
    new_id = max(numeric_ids) + 1
    return str(new_id)

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

# ==========================================
# 🔐 SISTEM LOGIN
# ==========================================
if 'status_login' not in st.session_state:
    st.session_state['status_login'] = False

def proses_login():
    user_env = os.getenv("ADMIN_USER", "admin")
    pass_env = os.getenv("ADMIN_PASS", "admin")
    
    if st.session_state['input_user'] == user_env and st.session_state['input_pass'] == pass_env:
        st.session_state['status_login'] = True
    else:
        st.error("❌ Username atau Password salah!")

def proses_logout():
    st.session_state['status_login'] = False
    st.rerun()

if not st.session_state['status_login']:
    st.markdown("## 🔒 Login Sistem Aset (Cloud)")
    st.info("Silakan login untuk mengakses data perusahaan.")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.text_input("Username", key="input_user")
        st.text_input("Password", type="password", key="input_pass")
        st.button("Masuk", on_click=proses_login)
    st.stop()

# ==========================================
# APLIKASI UTAMA
# ==========================================
st.sidebar.title("🎛️ Menu Navigasi")
st.sidebar.write(f"Login sebagai: **{os.getenv('ADMIN_USER')}**")

if st.sidebar.button("🚪 Logout"):
    proses_logout()

st.sidebar.markdown("---")
menu = st.sidebar.radio("Pilih Halaman:", [
    "Master Aset (Aktif)", 
    "Riwayat Log (History)",
    "⚡ Kelola Aset (Admin)",
    "📊 Rekap Aset Aktif"
])
st.sidebar.markdown("---")

# ==========================================
# HALAMAN 1: MASTER ASET (DENGAN SIDEBAR FORM)
# ==========================================
if menu == "Master Aset (Aktif)":
    st.title("🏭 Sistem Manajemen Aset Mesin (Cloud)")
    
    # Ambil Data Master Aset
    df_master = load_data("master_aset")

    # --- 1. FILTER FORM (SIDEBAR) ---
    with st.sidebar.form("filter_master_form"):
        st.header("🎛️ Filter Master Aset")
        
        # Siapkan opsi filter
        opt_lokasi = sorted(df_master['lokasi_toko'].unique().tolist()) if not df_master.empty else []
        opt_kategori = sorted(df_master['kategori'].unique().tolist()) if not df_master.empty else []
        
        # Input Filter
        sel_lokasi = st.multiselect("Lokasi (Kosong = Semua)", opt_lokasi, default=[])
        sel_kategori = st.multiselect("Kategori (Kosong = Semua)", opt_kategori, default=[])
        keyword = st.text_input("🔍 Cari (Nama / ID / No Reg)", placeholder="Ketik kata kunci...")
        
        # Tombol Eksekusi
        btn_filter_master = st.form_submit_button("🚀 Terapkan Filter")

    # --- 2. LOGIKA FILTERING ---
    if not df_master.empty:
        # Mulai dengan semua data
        df_tampil = df_master.copy()
        
        # Filter Lokasi (Jika dipilih)
        if sel_lokasi:
            df_tampil = df_tampil[df_tampil['lokasi_toko'].isin(sel_lokasi)]
            
        # Filter Kategori (Jika dipilih)
        if sel_kategori:
            df_tampil = df_tampil[df_tampil['kategori'].isin(sel_kategori)]
            
        # Filter Pencarian (Keyword)
        if keyword:
            df_tampil = df_tampil[
                df_tampil['nama_mesin'].str.contains(keyword, case=False, na=False) |
                df_tampil['id'].str.contains(keyword, case=False, na=False) |
                df_tampil['no_registrasi'].astype(str).str.contains(keyword, case=False, na=False)
            ]
        
        # --- 3. KPI DASHBOARD ---
        total_unit = len(df_tampil)
        # Hitung Estimasi Aset (Handling Error Data Kotor)
        try:
            if 'harga_beli' in df_tampil.columns:
                series_harga = df_tampil['harga_beli'].astype(str).str.replace(r'[^\d]', '', regex=True)
                series_harga = pd.to_numeric(series_harga, errors='coerce').fillna(0)
                total_nilai = series_harga.sum()
            else:
                total_nilai = 0
        except:
            total_nilai = 0

        str_nilai = f"Rp {total_nilai:,.0f}".replace(",", ".")
        
        # Tampilkan KPI
        k1, k2, k3 = st.columns(3)
        k1.metric("📦 Unit Tampil", f"{total_unit} Unit")
        k2.metric("💰 Nilai Estimasi", str_nilai)
        k3.metric("📍 Lokasi Terkait", f"{df_tampil['lokasi_toko'].nunique()} Titik")
        st.markdown("---")

        # --- 4. TABEL DATA ---
        col_kiri, col_kanan = st.columns([4, 1])
        with col_kiri:
            if btn_filter_master:
                st.success("Filter berhasil diterapkan.")
        with col_kanan:
            excel_data = convert_df_to_excel(df_tampil)
            st.download_button("📥 Download Excel", data=excel_data, file_name='data_aset_filtered.xlsx')

        # Formatting Tampilan (Rupiah)
        df_display = df_tampil.copy()
        if 'harga_beli' in df_display.columns:
            try:
                # Bersihkan & Format
                clean_series = df_display['harga_beli'].astype(str).str.replace(r'[^\d]', '', regex=True)
                df_display['harga_beli'] = pd.to_numeric(clean_series, errors='coerce').fillna(0)
                df_display['harga_beli'] = df_display['harga_beli'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            except:
                pass

        st.dataframe(df_display, use_container_width=True, hide_index=True, height=600)
    else:
        st.warning("Data Master Aset kosong.")
# ==========================================
# HALAMAN 2: RIWAYAT LOG (DENGAN SIDEBAR FORM)
# ==========================================
elif menu == "Riwayat Log (History)":
    st.title("📜 Riwayat Mutasi & Likuidasi Mesin")
    
    # Load Data
    df_base = load_data("riwayat_log")
    
    if not df_base.empty:
        # Pre-processing Tanggal untuk filter
        if 'tanggal' in df_base.columns:
            df_base['tanggal_filter'] = pd.to_datetime(df_base['tanggal'], errors='coerce')
        else:
            st.error("Kolom 'tanggal' hilang dari data log.")
            st.stop()

        # --- 1. FILTER FORM (SIDEBAR) ---
        with st.sidebar.form("filter_history_form"):
            st.header("🎛️ Filter History")
            
            # Filter Tanggal
            tampil_semua = st.checkbox("Tampilkan Semua Tanggal", value=False)
            
            today = date.today()
            last_month = today - timedelta(days=30)
            filter_tgl = st.date_input("Rentang Tanggal", (last_month, today))
            
            st.markdown("---")
            
            # Filter Lokasi & Aksi
            # Ambil opsi unik
            col_lok = 'lokasi_asal' if 'lokasi_asal' in df_base.columns else 'lokasi'
            opt_lokasi = sorted(df_base[col_lok].astype(str).unique().tolist())
            opt_aksi = sorted(df_base['jenis_aksi'].astype(str).unique().tolist())
            
            sel_lokasi_hist = st.multiselect("Lokasi Asal (Kosong = Semua)", opt_lokasi, default=[])
            sel_aksi = st.multiselect("Jenis Aksi (Kosong = Semua)", opt_aksi, default=[])
            
            # Search
            keyword_hist = st.text_input("🔍 Cari (Nama / No Reg)", placeholder="Ketik keyword...")
            
            # Tombol Eksekusi
            btn_filter_hist = st.form_submit_button("🚀 Terapkan Filter")

        # --- 2. LOGIKA FILTERING ---
        df_history = df_base.copy()
        
        # A. Filter Tanggal
        if not tampil_semua:
            if isinstance(filter_tgl, tuple) and len(filter_tgl) == 2:
                start_date, end_date = filter_tgl
                start_ts = pd.Timestamp(start_date)
                end_ts = pd.Timestamp(end_date)
                
                df_history = df_history[
                    (df_history['tanggal_filter'] >= start_ts) & 
                    (df_history['tanggal_filter'] <= end_ts)
                ]
        
        # B. Filter Lokasi (Jika dipilih)
        if sel_lokasi_hist:
            df_history = df_history[df_history[col_lok].isin(sel_lokasi_hist)]
            
        # C. Filter Aksi (Jika dipilih)
        if sel_aksi:
            df_history = df_history[df_history['jenis_aksi'].isin(sel_aksi)]
            
        # D. Filter Keyword
        if keyword_hist:
            df_history = df_history[
                df_history['nama_mesin'].str.contains(keyword_hist, case=False, na=False) |
                df_history['no_registrasi'].astype(str).str.contains(keyword_hist, case=False, na=False)
            ]
            
        # --- 3. TAMPILAN TABEL ---
        # Rapikan Tanggal untuk View
        df_history['tanggal'] = df_history['tanggal_filter'].dt.strftime('%Y-%m-%d').fillna("-")
        
        # Sorting (Terbaru di atas)
        if 'id' in df_history.columns:
            df_history['id_num'] = pd.to_numeric(df_history['id'], errors='coerce')
            df_history = df_history.sort_values(by='id_num', ascending=False).drop(columns=['id_num'])

        if not df_history.empty:
            # Kolom yang akan ditampilkan
            target_cols = ['tanggal', 'jenis_aksi', 'nama_mesin', 'lokasi_asal', 'keterangan', 'harga_beli', 'no_registrasi', 'no_reg_system']
            final_cols = [c for c in target_cols if c in df_history.columns]
            
            # Header Info & Download
            c_info, c_btn = st.columns([4, 1])
            with c_info:
                st.info(f"Menampilkan **{len(df_history)}** catatan sejarah.")
            with c_btn:
                excel_hist = convert_df_to_excel(df_history[final_cols])
                st.download_button("📥 Download Excel", data=excel_hist, file_name='riwayat_log.xlsx')
            
            # Formatting Rupiah untuk View
            df_hist_display = df_history[final_cols].copy()
            if 'harga_beli' in df_hist_display.columns:
                try:
                    clean_s = df_hist_display['harga_beli'].astype(str).str.replace(r'[^\d]', '', regex=True)
                    df_hist_display['harga_beli'] = pd.to_numeric(clean_s, errors='coerce').fillna(0)
                    df_hist_display['harga_beli'] = df_hist_display['harga_beli'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                except:
                    pass

            st.dataframe(df_hist_display, use_container_width=True, hide_index=True)
        else:
            st.warning("Tidak ada data history yang cocok dengan filter ini.")

    else:
        st.warning("Data History Kosong.")

# ==========================================
# HALAMAN 3: KELOLA ASET (ADMIN)
# ==========================================
elif menu == "⚡ Kelola Aset (Admin)":
    st.title("⚡ Menu Admin (Mode Cloud)")
    
    sh = get_gsheet_connection()
    ws_master = sh.worksheet("master_aset")
    ws_log = sh.worksheet("riwayat_log")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "➕ Input Baru", 
        "✏️ Edit Detail Mesin Aktif",     
        "🚚 Mutasi (Pindah)", 
        "🗑️ Likuidasi (Hapus)",
        "🛠️ Koreksi History Log",
        "♻️ Restore / Batal"
    ])
    
    # Ambil Data Master Terbaru
    df_master = load_data("master_aset")
    
    # --- TAB 1: INPUT BARU ---
    with tab1:
        st.subheader("Tambah Aset Mesin Baru")
        
        list_lok = sorted(df_master['lokasi_toko'].unique().tolist()) if not df_master.empty else []
        list_kat = sorted(df_master['kategori'].unique().tolist()) if not df_master.empty else []
        
        with st.form("form_input", clear_on_submit=True):
            c1, c2 = st.columns(2)
            pilihan_lokasi = c1.selectbox("Pilih Lokasi", list_lok + ["++ Tambah Baru ++"])
            input_lokasi_baru = c1.text_input("Nama Lokasi Baru (Jika pilih ++ Tambah Baru ++)", key="in_lok_baru")
            
            pilihan_kategori = c2.selectbox("Pilih Kategori", list_kat + ["++ Tambah Baru ++"])
            input_kategori_baru = c2.text_input("Nama Kategori Baru (Jika pilih ++ Tambah Baru ++)", key="in_kat_baru")
            
            st.markdown("---")
            input_nama = st.text_input("Nama Mesin")
            c3, c4 = st.columns(2)
            input_harga = c3.number_input("Harga Beli (Rp)", min_value=0, step=1000)
            input_noreg = c4.text_input("No Registrasi (Manual/Opsional)")
            
            btn_submit = st.form_submit_button("💾 Simpan Data Baru")
            
            if btn_submit:
                if not input_nama:
                    st.error("Nama Mesin wajib diisi!")
                else:
                    final_lokasi = input_lokasi_baru if pilihan_lokasi == "++ Tambah Baru ++" else pilihan_lokasi
                    final_kategori = input_kategori_baru if pilihan_kategori == "++ Tambah Baru ++" else pilihan_kategori
                    
                    if not final_lokasi or not final_kategori:
                        st.error("Lokasi dan Kategori harus diisi!")
                    else:
                        with st.spinner("Menyimpan ke Cloud..."):
                            try:
                                # 1. Generate ID Baru (Master)
                                new_id = generate_id("master_aset")
                                
                                # 2. Append ke Master Aset
                                row_master = [new_id, final_lokasi, final_kategori, input_nama, input_harga, input_noreg, "Aktif"]
                                ws_master.append_row(row_master)
                                
                                # 3. Append ke Log (INPUT BARU)
                                log_id = generate_id("riwayat_log")
                                tgl_skrg = datetime.now().strftime("%Y-%m-%d")
                                
                                row_log = [
                                    log_id,             # 1. id
                                    final_lokasi,       # 2. lokasi_asal
                                    final_kategori,     # 3. kategori
                                    "Input Baru",       # 4. jenis_aksi
                                    tgl_skrg,           # 5. tanggal
                                    input_nama,         # 6. nama_mesin
                                    input_harga,        # 7. harga_beli
                                    input_noreg,        # 8. no_registrasi
                                    new_id,             # 9. no_reg_system
                                    "Penambahan aset baru" # 10. keterangan
                                ]
                                ws_log.append_row(row_log)
                                
                                st.success(f"Berhasil! Aset '{input_nama}' ditambahkan dengan ID {new_id}")
                                time.sleep(1)
                                st.cache_data.clear()
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Terjadi kesalahan: {e}")

    # --- TAB 2: EDIT DETAIL (SAFE MODE) ---
    with tab2:
        st.subheader("✏️ Edit Detail Aset")
        st.info("Cari aset berdasarkan **Nomor Registrasi** (Manual) atau ID. ID System tidak dapat diubah untuk menjaga integritas data.")
        
        # 1. Fitur Pencarian
        cari_noreg = st.text_input("🔍 Ketik No Registrasi / ID System:", placeholder="Contoh: REG-001 atau 105")
        
        # Wadah hasil pencarian
        aset_ditemukan = pd.DataFrame()
        
        if cari_noreg:
            # Cari di kolom No Registrasi ATAU ID (Case Insensitive)
            aset_ditemukan = df_master[
                df_master['no_registrasi'].astype(str).str.contains(cari_noreg, case=False, na=False) |
                df_master['id'].astype(str).str.contains(cari_noreg, case=False, na=False)
            ]
        
        id_pilih = None
        
        # 2. Tampilkan Dropdown Hasil Pencarian
        if not aset_ditemukan.empty:
            st.success(f"Ditemukan {len(aset_ditemukan)} aset.")
            
            # Format tampilan dropdown: Nama | Lokasi | Reg | ID
            opsi_aset = aset_ditemukan.apply(
                lambda x: f"{x['nama_mesin']} | {x['lokasi_toko']} | Reg: {x['no_registrasi']} | ID: {x['id']}", axis=1
            )
            
            pilih_aset = st.selectbox("Pilih Aset yang akan diedit:", opsi_aset)
            
            if pilih_aset:
                # Ambil ID dari string pilihan (Elemen terakhir setelah "| ID: ")
                id_pilih = pilih_aset.split("| ID: ")[1].strip()
        
        elif cari_noreg and aset_ditemukan.empty:
            st.warning("Data tidak ditemukan.")

        # 3. Form Edit (Muncul setelah aset dipilih)
        if id_pilih:
            # Ambil data eksisting dari DataFrame
            data_lama = df_master[df_master['id'] == id_pilih].iloc[0]
            
            st.markdown("---")
            with st.form("form_edit_safe"):
                st.write(f"Sedang Mengedit: **{data_lama['nama_mesin']}**")
                
                c_kiri, c_kanan = st.columns(2)
                
                with c_kiri:
                    # NAMA MESIN (Bisa Diedit)
                    new_nama = st.text_input("Nama Mesin", value=data_lama['nama_mesin'])
                    
                    # HARGA (Bisa Diedit - Bersihkan dulu jadi int)
                    harga_raw = str(data_lama['harga_beli'])
                    harga_clean = ''.join(filter(str.isdigit, harga_raw)) # Ambil angka saja
                    harga_int = int(harga_clean) if harga_clean else 0
                    new_harga = st.number_input("Harga Beli (Rp)", value=harga_int, step=1000)
                    
                    # NO REGISTRASI MANUAL (Bisa Diedit)
                    new_noreg = st.text_input("No. Registrasi (Manual/Fisik)", value=str(data_lama['no_registrasi']))

                with c_kanan:
                    # ID SYSTEM (READ ONLY / TIDAK BISA DIEDIT)
                    st.text_input("No. Registrasi System (ID Unik)", value=str(data_lama['id']), disabled=True, help="ID ini dibuat otomatis oleh sistem dan tidak bisa diubah.")
                    
                    # LOKASI (DROPDOWN - Mencegah Typo)
                    # Ambil list lokasi unik dari seluruh data master
                    list_lok_master = sorted(df_master['lokasi_toko'].unique().tolist())
                    # Pastikan lokasi saat ini ada di list, biar bisa jadi default index
                    curr_lok = data_lama['lokasi_toko']
                    idx_lok = list_lok_master.index(curr_lok) if curr_lok in list_lok_master else 0
                    
                    new_lokasi = st.selectbox("Lokasi Toko / Gudang", list_lok_master, index=idx_lok)

                    # KATEGORI (DROPDOWN - Mencegah Typo)
                    list_kat_master = sorted(df_master['kategori'].unique().tolist())
                    curr_kat = data_lama['kategori']
                    idx_kat = list_kat_master.index(curr_kat) if curr_kat in list_kat_master else 0
                    
                    new_kategori = st.selectbox("Kategori Mesin", list_kat_master, index=idx_kat)

                # ALASAN (Wajib)
                ket_edit = st.text_area("Alasan Perubahan (Wajib untuk Log)", placeholder="Contoh: Koreksi salah input harga, Update lokasi fisik, dll.")

                # TOMBOL SUBMIT
                submit = st.form_submit_button("💾 Simpan Perubahan")
                
                if submit:
                    if not ket_edit:
                        st.error("Mohon isi alasan perubahan untuk keperluan audit/log.")
                    else:
                        try:
                            # Cari baris di Google Sheet berdasarkan ID
                            cell = ws_master.find(str(id_pilih))
                            r = cell.row
                            
                            # UPDATE DATA (Kolom 1 ID dilewati)
                            # Urutan Kolom GSheet: 1.ID, 2.Lokasi, 3.Kategori, 4.Nama, 5.Harga, 6.NoReg
                            
                            ws_master.update_cell(r, 2, new_lokasi)   # Update Lokasi
                            ws_master.update_cell(r, 3, new_kategori) # Update Kategori
                            ws_master.update_cell(r, 4, new_nama)     # Update Nama
                            ws_master.update_cell(r, 5, new_harga)    # Update Harga
                            ws_master.update_cell(r, 6, new_noreg)    # Update No Reg Manual
                            
                            # CATAT LOG HISTORY
                            log_id = generate_id("riwayat_log")
                            tgl_skrg = datetime.now().strftime("%Y-%m-%d")
                            
                            row_log = [
                                log_id,
                                data_lama['lokasi_toko'], # Lokasi SEBELUM edit
                                data_lama['kategori'],
                                "Edit Detail",
                                tgl_skrg,
                                new_nama,
                                new_harga,
                                new_noreg,
                                id_pilih,                 # ID System Tetap
                                f"Update Data. {ket_edit}"
                            ]
                            ws_log.append_row(row_log)
                            
                            st.success(f"Data aset {new_nama} berhasil diperbarui!")
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Gagal menyimpan: {e}")

    # --- TAB 3: MUTASI ---
    with tab3:
        st.subheader("Mutasi (Pindah Lokasi)")
        pilih_aset_mutasi = st.selectbox("Pilih Aset untuk Dipindah:", 
                                         df_master['nama_mesin'] + " | " + df_master['id'] + " | " + df_master['lokasi_toko'],
                                         key="sel_mutasi")
        
        if pilih_aset_mutasi:
            id_mutasi = pilih_aset_mutasi.split(" | ")[1]
            data_asal = df_master[df_master['id'] == id_mutasi].iloc[0]
            
            st.info(f"Lokasi Saat Ini: **{data_asal['lokasi_toko']}**")
            
            with st.form("form_mutasi"):
                tujuan_lokasi = st.selectbox("Pilih Lokasi Tujuan", list_lok + ["++ Tambah Baru ++"])
                input_tujuan_baru = st.text_input("Lokasi Baru (Opsional)", key="in_tuj_baru")
                tgl_mutasi = st.date_input("Tanggal Pindah", value=date.today())
                ket_mutasi = st.text_area("Keterangan", "Rotasi mesin reguler")
                
                if st.form_submit_button("🚚 Proses Mutasi"):
                    final_tujuan = input_tujuan_baru if tujuan_lokasi == "++ Tambah Baru ++" else tujuan_lokasi
                    
                    if not final_tujuan or final_tujuan == data_asal['lokasi_toko']:
                        st.error("Lokasi tujuan tidak valid atau sama dengan lokasi asal.")
                    else:
                        try:
                            cell = ws_master.find(id_mutasi)
                            ws_master.update_cell(cell.row, 2, final_tujuan)
                            
                            log_id = generate_id("riwayat_log")
                            row_log = [
                                log_id,
                                data_asal['lokasi_toko'], # Lokasi ASAL
                                data_asal['kategori'],
                                "Mutasi",
                                tgl_mutasi.strftime("%Y-%m-%d"),
                                data_asal['nama_mesin'],
                                int(data_asal['harga_beli']) if pd.notna(data_asal['harga_beli']) else 0,
                                str(data_asal['no_registrasi']),
                                id_mutasi,
                                f"Pindah ke {final_tujuan}. {ket_mutasi}"
                            ]
                            ws_log.append_row(row_log)
                            
                            st.success(f"Berhasil dipindah ke {final_tujuan}")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    # --- TAB 4: LIKUIDASI ---
    with tab4:
        st.subheader("Likuidasi (Hapus/Jual Aset)")
        pilih_aset_hapus = st.selectbox("Pilih Aset:", 
                                        df_master['nama_mesin'] + " | " + df_master['id'] + " | " + df_master['lokasi_toko'],
                                        key="sel_hapus")
        
        if pilih_aset_hapus:
            id_hapus = pilih_aset_hapus.split(" | ")[1]
            data_hapus = df_master[df_master['id'] == id_hapus].iloc[0]
            
            st.warning(f"⚠️ Anda akan menghapus **{data_hapus['nama_mesin']}** secara permanen dari Master Aset.")
            
            with st.form("form_hapus"):
                alasan_hapus = st.selectbox("Jenis Aksi", ["Likuidasi (Dijual)", "Rusak/Musnah", "Hilang", "Donasi"])
                ket_hapus = st.text_area("Detail Keterangan", "Mesin sudah tua/rusak")
                
                if st.form_submit_button("🗑️ Konfirmasi Hapus"):
                    try:
                        cell = ws_master.find(id_hapus)
                        ws_master.delete_rows(cell.row)
                        
                        log_id = generate_id("riwayat_log")
                        tgl_skrg = datetime.now().strftime("%Y-%m-%d")
                        row_log = [
                            log_id,
                            data_hapus['lokasi_toko'],
                            data_hapus['kategori'],
                            alasan_hapus,
                            tgl_skrg,
                            data_hapus['nama_mesin'],
                            int(data_hapus['harga_beli']) if pd.notna(data_hapus['harga_beli']) else 0,
                            str(data_hapus['no_registrasi']),
                            id_hapus,
                            ket_hapus
                        ]
                        ws_log.append_row(row_log)
                        
                        st.success("Data berhasil dihapus dari Master dan dicatat di History.")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # --- TAB 5: KOREKSI LOG (UNDO) ---
    with tab5:
        st.subheader("🛠️ Koreksi / Edit Riwayat Log")
        st.info("Fitur ini digunakan jika ada kesalahan penulisan di Riwayat (Log), bukan untuk mengembalikan barang.")

        # 1. Filter Tanggal
        tgl_filter_log = st.date_input("Pilih Tanggal Kejadian", value=date.today())
        
        # 2. Ambil Data Log
        df_log = load_data("riwayat_log")
        
        # Filter berdasarkan tanggal string
        df_log['tanggal_str'] = pd.to_datetime(df_log['tanggal'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_target = df_log[df_log['tanggal_str'] == tgl_filter_log.strftime('%Y-%m-%d')]
        
        if not df_target.empty:
            # 3. Pilih ID Log
            pilihan_log = st.selectbox("Pilih Log untuk Diedit:", 
                df_target['id'].astype(str) + " | " + df_target['nama_mesin'] + " | " + df_target['jenis_aksi'])
            
            if pilihan_log:
                id_log_pilih = pilihan_log.split(" | ")[0]
                # Ambil data spesifik
                data_log = df_target[df_target['id'].astype(str) == id_log_pilih].iloc[0]
                
                with st.form("form_edit_log"):
                    st.write(f"**ID Log:** {id_log_pilih}")
                    
                    edit_tgl = st.date_input("Tanggal", value=pd.to_datetime(data_log['tanggal']).date())
                    edit_nama = st.text_input("Nama Mesin", value=data_log['nama_mesin'])
                    edit_aksi = st.text_input("Jenis Aksi", value=data_log['jenis_aksi'])
                    edit_lokasi = st.text_input("Lokasi Asal", value=data_log['lokasi_asal'])
                    edit_ket = st.text_area("Keterangan", value=data_log['keterangan'])
                    
                    c_del, c_save = st.columns([1, 4])
                    
                    # Tombol Hapus (Undo Total)
                    delete_btn = c_del.form_submit_button("🗑️ Hapus Log")
                    
                    # Tombol Simpan Perubahan
                    save_btn = c_save.form_submit_button("💾 Simpan Perubahan")
                    
                    if save_btn:
                        try:
                            # Cari baris berdasarkan ID Log
                            cell = ws_log.find(id_log_pilih)
                            r = cell.row
                            
                            # Update kolom spesifik
                            ws_log.update_cell(r, 2, edit_lokasi) # lokasi_asal
                            ws_log.update_cell(r, 4, edit_aksi)   # jenis_aksi
                            ws_log.update_cell(r, 5, edit_tgl.strftime("%Y-%m-%d")) # tanggal
                            ws_log.update_cell(r, 6, edit_nama)   # nama_mesin
                            ws_log.update_cell(r, 10, edit_ket)   # keterangan
                            
                            st.success("Log berhasil dikoreksi!")
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                            
                    if delete_btn:
                        try:
                            cell = ws_log.find(id_log_pilih)
                            ws_log.delete_rows(cell.row)
                            st.success("Log berhasil dihapus permanen!")
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error hapus: {e}")

        else:
            st.warning("Tidak ada aktivitas log pada tanggal ini.")
    # --- TAB 6: RESTORE / REVERT TRANSACTION (UPDATED) ---
    with tab6:
        st.subheader("♻️ Restore & Batalkan Aksi")
        st.info("Fitur ini mengembalikan kondisi aset ke status sebelum aksi dilakukan (Revert Transaction).")

        # 1. Load Data Log Full
        df_log_full = load_data("riwayat_log")
        
        # Filter awal: Hanya ambil jenis aksi yang valid untuk di-revert
        aksi_revertable = ["Mutasi", "Likuidasi (Dijual)", "Rusak/Musnah", "Hilang", "Donasi"]
        
        # Pastikan kolom tanggal ada dan bertipe datetime
        if 'tanggal' in df_log_full.columns:
            df_log_full['tanggal_dt'] = pd.to_datetime(df_log_full['tanggal'], errors='coerce')
        
        df_revert = df_log_full[df_log_full['jenis_aksi'].isin(aksi_revertable)].copy()

        # 2. FORM FILTER PENCARIAN
        if not df_revert.empty:
            with st.expander("🔍 Filter Pencarian Log (Klik untuk Buka/Tutup)", expanded=True):
                with st.form("form_filter_restore"):
                    c_filter1, c_filter2 = st.columns(2)
                    
                    with c_filter1:
                        # Filter Tanggal
                        today = date.today()
                        last_month = today - timedelta(days=90) # Default 3 bulan
                        input_tgl = st.date_input("Rentang Tanggal Kejadian", (last_month, today))
                        
                        # Filter Lokasi
                        opt_lok = sorted(df_revert['lokasi_asal'].astype(str).unique().tolist())
                        input_lok = st.multiselect("Lokasi Asal (Kosong = Semua)", opt_lok)

                    with c_filter2:
                        # Filter Kategori
                        opt_kat = sorted(df_revert['kategori'].astype(str).unique().tolist())
                        input_kat = st.multiselect("Kategori (Kosong = Semua)", opt_kat)
                        
                        # Filter Jenis Aksi
                        opt_aksi = sorted(df_revert['jenis_aksi'].astype(str).unique().tolist())
                        input_aksi = st.multiselect("Jenis Aksi (Kosong = Semua)", opt_aksi)

                    # Tombol Apply Filter
                    submit_filter = st.form_submit_button("🔎 Cari Transaksi")

            # 3. LOGIKA FILTERING DATA
            # Default: Tampilkan semua jika belum difilter, atau sesuaikan jika tombol ditekan
            df_display_rev = df_revert.copy()

            # Filter Tanggal
            if isinstance(input_tgl, tuple) and len(input_tgl) == 2:
                start_d, end_d = input_tgl
                df_display_rev = df_display_rev[
                    (df_display_rev['tanggal_dt'] >= pd.Timestamp(start_d)) & 
                    (df_display_rev['tanggal_dt'] <= pd.Timestamp(end_d))
                ]
            
            # Filter Multiselect
            if input_lok:
                df_display_rev = df_display_rev[df_display_rev['lokasi_asal'].isin(input_lok)]
            if input_kat:
                df_display_rev = df_display_rev[df_display_rev['kategori'].isin(input_kat)]
            if input_aksi:
                df_display_rev = df_display_rev[df_display_rev['jenis_aksi'].isin(input_aksi)]

            # Urutkan dari yang terbaru (ID terbesar)
            if 'id' in df_display_rev.columns:
                df_display_rev['id_num'] = pd.to_numeric(df_display_rev['id'], errors='coerce')
                df_display_rev = df_display_rev.sort_values(by='id_num', ascending=False)

            # 4. DROPDOWN PILIHAN
            if not df_display_rev.empty:
                st.markdown(f"**Ditemukan {len(df_display_rev)} riwayat transaksi.**")
                
                pilih_log_revert = st.selectbox(
                    "Pilih Transaksi yang akan dibatalkan:",
                    df_display_rev.apply(
                        lambda x: f"{x['tanggal']} | {x['jenis_aksi']} | {x['nama_mesin']} (ID Log: {x['id']})", 
                        axis=1
                    )
                )
                
                if pilih_log_revert:
                    # Ambil ID Log
                    id_log_rev = pilih_log_revert.split("(ID Log: ")[1].replace(")", "")
                    data_log = df_display_rev[df_display_rev['id'].astype(str) == id_log_rev].iloc[0]
                    
                    # 5. TAMPILAN DETAIL (Update: Ada No Registrasi)
                    st.markdown("---")
                    st.info("Silakan cek detail di bawah sebelum melakukan Restore.")
                    
                    st.write("**Detail Transaksi Asal:**")
                    col_det1, col_det2 = st.columns(2)
                    with col_det1:
                        st.write(f"- **Aksi:** {data_log['jenis_aksi']}")
                        st.write(f"- **Aset:** {data_log['nama_mesin']}")
                        st.write(f"- **Kategori:** {data_log['kategori']}")
                        st.write(f"- **ID System:** `{data_log['no_reg_system']}`")
                        # TAMBAHAN SESUAI REQUEST
                        st.write(f"- **No Registrasi:** `{data_log['no_registrasi']}`") 
                        
                    with col_det2:
                        st.write(f"- **Tanggal:** {data_log['tanggal']}")
                        st.write(f"- **Lokasi Asal (Di Log):** {data_log['lokasi_asal']}")
                        st.write(f"- **Harga Beli:** Rp {int(data_log['harga_beli'] if pd.notna(data_log['harga_beli']) and str(data_log['harga_beli']).isdigit() else 0):,.0f}")
                        st.write(f"- **Keterangan:** {data_log['keterangan']}")
                    
                    st.markdown("---")
                    st.warning(f"⚠️ Apakah Anda yakin ingin membatalkan aksi **{data_log['jenis_aksi']}** ini?")
                    
                    # Tombol Eksekusi (Harus di luar form filter)
                    btn_revert = st.button("♻️ Proses Pemulihan (Restore)")
                    
                    if btn_revert:
                        try:
                            tgl_skrg = datetime.now().strftime("%Y-%m-%d")
                            id_aset_target = str(data_log['no_reg_system'])
                            
                            # --- SKENARIO 1: BATAL MUTASI ---
                            if "Mutasi" in data_log['jenis_aksi']:
                                cell = ws_master.find(id_aset_target)
                                if cell:
                                    ws_master.update_cell(cell.row, 2, data_log['lokasi_asal'])
                                    
                                    log_id_new = generate_id("riwayat_log")
                                    row_log = [
                                        log_id_new, "System Restore", data_log['kategori'], "Batal Mutasi",
                                        tgl_skrg, data_log['nama_mesin'], data_log['harga_beli'],
                                        data_log['no_registrasi'], id_aset_target,
                                        f"Mengembalikan mutasi Log ID {id_log_rev}. Kembali ke {data_log['lokasi_asal']}."
                                    ]
                                    ws_log.append_row(row_log)
                                    st.success(f"Berhasil! Aset dikembalikan ke lokasi: {data_log['lokasi_asal']}")
                                    time.sleep(2)
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error("Gagal: Aset tidak ditemukan di Master (mungkin sudah dihapus).")

                            # --- SKENARIO 2: BATAL LIKUIDASI ---
                            else:
                                try:
                                    cek_duplikat = ws_master.find(id_aset_target)
                                    if cek_duplikat:
                                        st.error(f"Gagal: Aset ID {id_aset_target} SUDAH AKTIF. Tidak perlu restore.")
                                        st.stop()
                                except gspread.exceptions.CellNotFound:
                                    pass 
                                
                                row_restore = [
                                    id_aset_target, data_log['lokasi_asal'], data_log['kategori'],
                                    data_log['nama_mesin'], data_log['harga_beli'], data_log['no_registrasi'], "Aktif"
                                ]
                                ws_master.append_row(row_restore)
                                
                                log_id_new = generate_id("riwayat_log")
                                row_log = [
                                    log_id_new, "Non-Aktif", data_log['kategori'], "Restore Aset",
                                    tgl_skrg, data_log['nama_mesin'], data_log['harga_beli'],
                                    data_log['no_registrasi'], id_aset_target,
                                    f"Pembatalan {data_log['jenis_aksi']} (Log ID {id_log_rev}). Aset aktif kembali."
                                ]
                                ws_log.append_row(row_log)
                                st.success(f"Berhasil! Aset {data_log['nama_mesin']} telah dipulihkan.")
                                time.sleep(2)
                                st.cache_data.clear()
                                st.rerun()

                        except Exception as e:
                            st.error(f"Terjadi kesalahan saat restore: {e}")
            else:
                st.warning("Tidak ada transaksi yang cocok dengan filter pencarian.")
        else:
            st.info("Belum ada riwayat Mutasi atau Likuidasi yang bisa dibatalkan.")
# ==========================================
# HALAMAN 4: REKAP ASET (UX BARU)
# ==========================================
elif menu == "📊 Rekap Aset Aktif":
    # 1. Load Data
    df = load_data("master_aset")

    # --- SIDEBAR FILTER (GAYA DASHBOARD) ---
    with st.sidebar.form("filter_rekap_form"):
        st.header("🎛️ Filter Rekap")
        
        # Ambil list unik (Sorted)
        opt_lokasi = sorted(df['lokasi_toko'].unique().tolist()) if not df.empty else []
        opt_kategori = sorted(df['kategori'].unique().tolist()) if not df.empty else []
        
        # Multiselect dengan placeholder "Kosong = Semua"
        # Kita biarkan default=[] (kosong) agar UX-nya bersih
        sel_lokasi = st.multiselect("Pilih Lokasi (Kosong = Semua)", opt_lokasi, default=[])
        sel_kategori = st.multiselect("Pilih Kategori (Kosong = Semua)", opt_kategori, default=[])
        
        # Tombol Submit
        btn_terapkan = st.form_submit_button("🚀 Terapkan Filter")

    # --- LOGIKA FILTERING ---
    # Jika tombol ditekan atau halaman baru dimuat
    df_filtered = df.copy()
    
    # Logika: Jika list TIDAK kosong, maka filter. Jika kosong, abaikan (ambil semua).
    if sel_lokasi:
        df_filtered = df_filtered[df_filtered['lokasi_toko'].isin(sel_lokasi)]
    
    if sel_kategori:
        df_filtered = df_filtered[df_filtered['kategori'].isin(sel_kategori)]

    # --- TAMPILAN UTAMA ---
    st.title("📊 Dashboard Rekapitulasi Aset")
    
    # Tampilkan label filter aktif agar user sadar
    lbl_lok = "Semua Lokasi" if not sel_lokasi else f"{len(sel_lokasi)} Lokasi Terpilih"
    lbl_kat = "Semua Kategori" if not sel_kategori else f"{len(sel_kategori)} Kategori Terpilih"
    st.caption(f"Filter Aktif: **{lbl_lok}** | **{lbl_kat}**")

    if not df_filtered.empty:
        # --- METRIK RINGKAS (TANPA NILAI RUPIAH) ---
        total_aset_view = len(df_filtered)
        total_lokasi_view = df_filtered['lokasi_toko'].nunique()
        total_kategori_view = df_filtered['kategori'].nunique()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("📦 Total Unit Aset", f"{total_aset_view}")
        m2.metric("📍 Jumlah Lokasi", f"{total_lokasi_view}")
        m3.metric("🏷️ Jumlah Kategori", f"{total_kategori_view}")
        st.markdown("---")
        
        # --- PIVOT TABLE (HEATMAP) ---
        st.subheader("📋 Peta Persebaran Aset")
        
        # Buat Pivot Table
        pivot_data = pd.crosstab(
            index=df_filtered['lokasi_toko'], 
            columns=df_filtered['kategori'],
            margins=True,
            margins_name="TOTAL"
        )
        
        # Tampilkan dengan Heatmap (Warna Biru)
        st.dataframe(
            pivot_data.style.background_gradient(cmap="Blues", axis=None).format("{:.0f}"),
            use_container_width=True
        )
        
        # --- DOWNLOAD BUTTON ---
        excel_data = convert_df_to_excel(pivot_data)
        st.download_button(
            label="📥 Download Rekap Excel",
            data=excel_data,
            file_name='rekap_aset_dashboard.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # --- GRAFIK VISUALISASI ---
        st.markdown("---")
        st.subheader("📊 Grafik Komposisi")
        
        # Hapus baris/kolom 'TOTAL' agar grafik tidak rusak
        chart_data = pivot_data.drop("TOTAL", axis=0, errors='ignore').drop("TOTAL", axis=1, errors='ignore')
        
        # Tampilkan Bar Chart
        st.bar_chart(chart_data)

    else:
        st.warning("Data tidak ditemukan dengan kombinasi filter tersebut.")