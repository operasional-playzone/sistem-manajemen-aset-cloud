import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import io
import time
import json # <--- TAMBAHKAN INI
from datetime import date, timedelta, datetime
from dotenv import load_dotenv

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Manajemen Aset Mesin (Cloud)",
    page_icon="☁️",
    layout="wide"
)

# Load Environment Variables
load_dotenv(override=True)

# Load Environment Variables
load_dotenv(override=True)

# ==========================================
# ☁️ KONFIGURASI KHUSUS CLOUD (STREAMLIT)
# ==========================================
# Jika file credentials.json tidak ada (karena di Cloud),
# Maka buat file tersebut dari st.secrets
if not os.path.exists("credentials.json"):
    # Cek apakah ada secrets bernama 'gcp_service_account'
    if "gcp_service_account" in st.secrets:
        # Tulis isi secrets ke file json sementara
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
    
    # Rename kolom tanggal manual jika ada
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

def generate_id():
    # Load data master untuk cek ID terakhir
    sh = get_gsheet_connection()
    worksheet = sh.worksheet("master_aset")
    
    # Ambil kolom pertama (ID)
    ids = worksheet.col_values(1) 
    
    # Hapus header "id" dari list jika ada
    if ids and ids[0].lower() == 'id':
        ids.pop(0)
    
    # Jika data masih kosong, mulai dari 1
    if not ids:
        return "1"
    
    # Ubah semua ID jadi angka (integer) untuk cari yang terbesar
    # Filter hanya yang angka saja (biar tidak error jika ada ID aneh)
    numeric_ids = [int(x) for x in ids if str(x).isdigit()]
    
    if not numeric_ids:
        return "1"
    
    # Ambil ID terbesar + 1
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
    "📘 Panduan Pengguna"
])
st.sidebar.markdown("---")

# ==========================================
# HALAMAN 1: MASTER ASET
# ==========================================
if menu == "Master Aset (Aktif)":
    st.title("🏭 Sistem Manajemen Aset Mesin (Cloud)")
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

    df_master = load_data("master_aset")
    
    if not df_master.empty:
        st.sidebar.subheader("Filter Master Aset")
        
        list_lokasi = sorted(df_master['lokasi_toko'].unique().tolist())
        pilih_lokasi = st.sidebar.multiselect("Pilih Lokasi:", list_lokasi)
        
        list_kategori = sorted(df_master['kategori'].unique().tolist())
        pilih_kategori = st.sidebar.multiselect("Pilih Kategori:", list_kategori)
        
        keyword = st.text_input("🔍 Cari Nama Mesin / No Registrasi / ID:", "")
        
        df_tampil = df_master.copy()
        if pilih_lokasi:
            df_tampil = df_tampil[df_tampil['lokasi_toko'].isin(pilih_lokasi)]
        if pilih_kategori:
            df_tampil = df_tampil[df_tampil['kategori'].isin(pilih_kategori)]
        if keyword:
            df_tampil = df_tampil[
                df_tampil['nama_mesin'].str.contains(keyword, case=False, na=False) |
                df_tampil['id'].str.contains(keyword, case=False, na=False)
            ]

        col_kiri, col_kanan = st.columns([4, 1])
        with col_kiri:
            st.write(f"**Total Data:** {len(df_tampil)} Unit")
        with col_kanan:
            excel_data = convert_df_to_excel(df_tampil)
            st.download_button("📥 Download Excel", data=excel_data, file_name='data_aset.xlsx')

        st.dataframe(df_tampil, use_container_width=True, hide_index=True, height=600)
    else:
        st.warning("Data Master Aset kosong.")

# ==========================================
# HALAMAN 2: RIWAYAT LOG
# ==========================================
elif menu == "Riwayat Log (History)":
    st.title("📜 Riwayat Mutasi & Likuidasi Mesin")
    
    if st.button("🔄 Refresh History"):
        st.cache_data.clear()

    df_base = load_data("riwayat_log")
    
    if not df_base.empty:
        if 'tanggal' not in df_base.columns:
            st.error("Kolom 'tanggal' tidak ditemukan di Excel Log!")
            st.stop()

        st.sidebar.subheader("Filter History")
        st.sidebar.markdown("### 📅 Filter Waktu")
        tampil_semua = st.sidebar.checkbox("Tampilkan Semua Tanggal", value=False)
        
        # Konversi ke DateTime (NaT handled)
        df_base['tanggal_filter'] = pd.to_datetime(df_base['tanggal'], errors='coerce')
        
        if not tampil_semua:
            today = date.today()
            last_month = today - timedelta(days=30)
            filter_tgl = st.sidebar.date_input("Rentang Tanggal:", (last_month, today))
            
            if isinstance(filter_tgl, tuple) and len(filter_tgl) == 2:
                start_date, end_date = filter_tgl
                start_ts = pd.Timestamp(start_date)
                end_ts = pd.Timestamp(end_date)
                
                df_history = df_base[
                    (df_base['tanggal_filter'] >= start_ts) & 
                    (df_base['tanggal_filter'] <= end_ts)
                ]
            else:
                df_history = df_base.copy()
        else:
            df_history = df_base.copy()
            
        # Format ulang tampilan tanggal
        df_history['tanggal'] = df_history['tanggal_filter'].dt.strftime('%Y-%m-%d').fillna("-")
        df_history = df_history.drop(columns=['tanggal_filter'])
        
        # Sortir jika ada created_at
        if 'created_at' in df_history.columns:
            df_history = df_history.sort_values(by='created_at', ascending=False)

        if not df_history.empty:
            col_lok = 'lokasi_asal' if 'lokasi_asal' in df_history.columns else 'lokasi'
            
            list_lokasi_hist = sorted(df_history[col_lok].astype(str).unique().tolist())
            pilih_lokasi_hist = st.sidebar.multiselect("Pilih Lokasi Asal:", list_lokasi_hist)
            
            list_kategori_hist = sorted(df_history['kategori'].astype(str).unique().tolist())
            pilih_kategori_hist = st.sidebar.multiselect("Pilih Kategori:", list_kategori_hist)

            list_aksi = sorted(df_history['jenis_aksi'].astype(str).unique().tolist())
            pilih_aksi = st.sidebar.multiselect("Jenis Aksi:", list_aksi)
            
            keyword_hist = st.text_input("🔍 Cari History (Nama Mesin):", "")
            
            df_hist_tampil = df_history.copy()
            if pilih_lokasi_hist:
                df_hist_tampil = df_hist_tampil[df_hist_tampil[col_lok].isin(pilih_lokasi_hist)]
            if pilih_kategori_hist:
                df_hist_tampil = df_hist_tampil[df_hist_tampil['kategori'].isin(pilih_kategori_hist)]
            if pilih_aksi:
                df_hist_tampil = df_hist_tampil[df_hist_tampil['jenis_aksi'].isin(pilih_aksi)]
            if keyword_hist:
                df_hist_tampil = df_hist_tampil[df_hist_tampil['nama_mesin'].str.contains(keyword_hist, case=False, na=False)]

            st.info(f"Menampilkan {len(df_hist_tampil)} catatan sejarah.")
            st.dataframe(df_hist_tampil, use_container_width=True, hide_index=True)
        else:
            st.warning("Tidak ada data pada rentang tanggal tersebut.")
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
        "✏️ Edit Detail",     
        "🚚 Mutasi (Pindah)", 
        "🗑️ Likuidasi (Hapus)",
        "🕵️ Jejak Aset",
        "↩️ Undo Kesalahan"
    ])
    
    # --- TAB 1: INPUT BARU ---
    with tab1:
        st.subheader("Tambah Aset Mesin Baru")
        
        df_master = load_data("master_aset")
        list_lok = df_master['lokasi_toko'].unique().tolist() if not df_master.empty else []
        list_kat = df_master['kategori'].unique().tolist() if not df_master.empty else []
        
        with st.form("form_input", clear_on_submit=True):
            c1, c2 = st.columns(2)
            pilihan_lokasi = c1.selectbox("Pilih Lokasi", list_lok + ["++ Tambah Baru ++"])
            input_lokasi_baru = c1.text_input("Nama Lokasi Baru (Jika pilih ++ Tambah Baru ++)", key="in_lok_baru")
            
            pilihan_kategori = c2.selectbox("Pilih Kategori", list_kat + ["++ Tambah Baru ++"])
            input_kategori_baru = c2.text_input("Nama Kategori Baru (Jika pilih ++ Tambah Baru ++)", key="in_kat_baru")
            
            st.markdown("---")
            input_nama = st.text_input("Nama Mesin (Wajib)", key="in_nama")
            c3, c4 = st.columns(2)
            input_harga = c3.text_input("Harga Beli", key="in_harga")
            input_noreg = c4.text_input("No Registrasi", key="in_noreg")
            
            if st.form_submit_button("Simpan ke Cloud"):
                final_lok = input_lokasi_baru.upper() if pilihan_lokasi == "++ Tambah Baru ++" else pilihan_lokasi
                final_kat = input_kategori_baru.upper() if pilihan_kategori == "++ Tambah Baru ++" else pilihan_kategori
                
                if final_lok and final_kat and input_nama:
                    try:
                        new_id = generate_id()
                        row_data = [new_id, final_lok, final_kat, input_nama.upper(), input_harga, input_noreg, "Aktif"]
                        ws_master.append_row(row_data)
                        st.success(f"✅ Berhasil! {input_nama} tersimpan.")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal simpan: {e}")
                else:
                    st.warning("Data wajib diisi semua!")

    # --- TAB 2: EDIT DETAIL ---
    with tab2:
        st.subheader("✏️ Edit Detail Aset")
        id_edit = st.text_input("Masukkan ID Aset (Edit):")
        
        if id_edit:
            cell = ws_master.find(id_edit)
            if cell:
                row_vals = ws_master.row_values(cell.row)
                curr_kat = row_vals[2] if len(row_vals) > 2 else ""
                curr_nama = row_vals[3] if len(row_vals) > 3 else ""
                curr_harga = row_vals[4] if len(row_vals) > 4 else ""
                curr_noreg = row_vals[5] if len(row_vals) > 5 else ""

                st.write(f"Editing: **{curr_nama}**")
                
                with st.form("form_edit"):
                    ed_nama = st.text_input("Nama Mesin", value=curr_nama)
                    ed_kat = st.text_input("Kategori", value=curr_kat)
                    c_e1, c_e2 = st.columns(2)
                    ed_harga = c_e1.text_input("Harga", value=curr_harga)
                    ed_noreg = c_e2.text_input("No Reg", value=curr_noreg)
                    
                    if st.form_submit_button("Update Data"):
                        ws_master.update_cell(cell.row, 3, ed_kat.upper())
                        ws_master.update_cell(cell.row, 4, ed_nama.upper())
                        ws_master.update_cell(cell.row, 5, ed_harga)
                        ws_master.update_cell(cell.row, 6, ed_noreg)
                        
                        log_row = [generate_id(), row_vals[1], ed_kat, ed_nama, "Koreksi Data", str(date.today()), "", "", "Edit Detail Admin", str(datetime.now())]
                        ws_log.append_row(log_row)
                        
                        st.success("Data Terupdate!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.error("ID Tidak Ditemukan.")

    # --- TAB 3: MUTASI ---
    with tab3:
        st.subheader("🚚 Mutasi (Pindah Lokasi)")
        id_mut = st.text_input("Masukkan ID Aset (Mutasi):")
        
        if id_mut:
            cell = ws_master.find(id_mut)
            if cell:
                row_vals = ws_master.row_values(cell.row)
                loc_now = row_vals[1] if len(row_vals) > 1 else "?"
                st.info(f"Lokasi Sekarang: {loc_now}")
                
                df_m = load_data("master_aset")
                list_l = df_m['lokasi_toko'].unique().tolist()
                
                with st.form("form_mutasi"):
                    lok_baru = st.selectbox("Pindah ke:", list_l)
                    ket_mut = st.text_area("Keterangan")
                    
                    if st.form_submit_button("Proses Mutasi"):
                        if lok_baru == loc_now:
                            st.warning("Lokasi sama!")
                        else:
                            ws_master.update_cell(cell.row, 2, lok_baru)
                            
                            nm = row_vals[3] if len(row_vals) > 3 else ""
                            kat = row_vals[2] if len(row_vals) > 2 else ""
                            
                            log_row = [generate_id(), loc_now, kat, nm, "Mutasi", str(date.today()), "", "", f"Ke {lok_baru}. {ket_mut}", str(datetime.now())]
                            ws_log.append_row(log_row)
                            
                            st.success("Berhasil Mutasi!")
                            time.sleep(1)
                            st.rerun()
            else:
                st.error("ID Tidak ditemukan.")

    # --- TAB 4: LIKUIDASI ---
    with tab4:
        st.subheader("🗑️ Hapus Aset (Likuidasi)")
        id_del = st.text_input("Masukkan ID Aset (Hapus):")
        
        if id_del:
            cell = ws_master.find(id_del)
            if cell:
                row_vals = ws_master.row_values(cell.row)
                st.warning(f"Menghapus: {row_vals[3]}")
                
                with st.form("form_del"):
                    alasan = st.selectbox("Alasan", ["Likuidasi", "Musnah", "Terjual", "Hilang"])
                    ket_del = st.text_area("Keterangan")
                    
                    if st.form_submit_button("🔥 Hapus Permanen"):
                        nm = row_vals[3] if len(row_vals) > 3 else ""
                        kat = row_vals[2] if len(row_vals) > 2 else ""
                        loc = row_vals[1] if len(row_vals) > 1 else ""
                        
                        log_row = [generate_id(), loc, kat, nm, alasan.upper(), str(date.today()), "", "", ket_del, str(datetime.now())]
                        ws_log.append_row(log_row)
                        
                        ws_master.delete_rows(cell.row)
                        st.success("Aset dihapus.")
                        time.sleep(1)
                        st.rerun()
            else:
                st.error("ID Tidak ditemukan.")

    # --- TAB 5: JEJAK ASET ---
    with tab5:
        st.subheader("🕵️ Jejak Aset")
        cari_nama = st.text_input("Cari Nama Mesin:")
        
        if cari_nama:
            df_log = load_data("riwayat_log")
            if not df_log.empty:
                df_trace = df_log[df_log['nama_mesin'].str.contains(cari_nama, case=False, na=False)]
                if 'created_at' in df_trace.columns:
                    df_trace = df_trace.sort_values(by='created_at', ascending=False)
                
                if not df_trace.empty:
                    st.write(f"Ditemukan {len(df_trace)} riwayat.")
                    for idx, row in df_trace.iterrows():
                        role = "user" if row['jenis_aksi'] == "Mutasi" else "assistant"
                        with st.chat_message(role):
                            st.write(f"**{row['tanggal']} - {row['jenis_aksi']}**")
                            loc_col = 'lokasi_asal' if 'lokasi_asal' in row else 'lokasi'
                            st.caption(f"📍 {row.get(loc_col, '-')} | {row['keterangan']}")
                else:
                    st.info("Tidak ada riwayat.")

    # --- TAB 6: UNDO KESALAHAN (DIPERBAIKI) ---
    with tab6:
        st.subheader("↩️ Undo Kesalahan Terakhir")
        st.warning("⚠️ Fitur ini membatalkan aksi terakhir.")
        
        df_log_undo = load_data("riwayat_log")
        
        # --- PERBAIKAN LOGIKA DISINI ---
        if not df_log_undo.empty:
            # Jika ada kolom created_at, sort berdasarkan itu
            if 'created_at' in df_log_undo.columns:
                df_log_undo = df_log_undo.sort_values(by='created_at', ascending=False).head(5)
            else:
                # Jika tidak ada, ambil 5 baris terbawah (biasanya data terbaru) dan balik urutannya
                df_log_undo = df_log_undo.tail(5).iloc[::-1]

            st.write("##### 5 Aktivitas Terakhir:")
            for idx, row in df_log_undo.iterrows():
                tgl_show = row['tanggal'] if pd.notna(row['tanggal']) else "-"
                label = f"{row['jenis_aksi']} - {row['nama_mesin']} ({tgl_show})"
                
                with st.expander(label):
                    st.write(f"Ket: {row['keterangan']}")
                    col_u, col_i = st.columns([1, 3])
                    
                    # === UNDO MUTASI ===
                    if row['jenis_aksi'] == 'Mutasi':
                        if col_u.button("↩️ BATALKAN MUTASI", key=f"btn_m_{row['id']}"):
                            with st.spinner("Mengembalikan lokasi..."):
                                try:
                                    # Cari Mesin di Master (in_column=4 untuk Nama Mesin)
                                    cell_m = ws_master.find(row['nama_mesin'], in_column=4)
                                    
                                    if cell_m:
                                        # Kembalikan ke lokasi asal (Col 2)
                                        loc_col_name = 'lokasi_asal' if 'lokasi_asal' in row else 'lokasi'
                                        ws_master.update_cell(cell_m.row, 2, row[loc_col_name])
                                        
                                        # Hapus Log
                                        cell_l = ws_log.find(str(row['id']))
                                        if cell_l: ws_log.delete_rows(cell_l.row)
                                        
                                        st.success(f"✅ Mutasi {row['nama_mesin']} DIBATALKAN.")
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error(f"Gagal: Mesin '{row['nama_mesin']}' tidak ditemukan di Master.")
                                except Exception as e:
                                    st.error(f"Error Undo: {e}")

                    # === UNDO LIKUIDASI (RESTORE) ===
                    elif row['jenis_aksi'] in ['LIKUIDASI', 'MUSNAH', 'TERJUAL', 'HILANG']:
                        if col_u.button("♻️ RESTORE DATA", key=f"btn_r_{row['id']}"):
                            with st.spinner("Mengembalikan data..."):
                                try:
                                    new_id = generate_id()
                                    loc_col_name = 'lokasi_asal' if 'lokasi_asal' in row else 'lokasi'
                                    
                                    restore_row = [
                                        new_id, 
                                        row[loc_col_name], 
                                        row['kategori'], 
                                        row['nama_mesin'], 
                                        row.get('harga_beli', ''), 
                                        row.get('no_registrasi', ''), 
                                        "Aktif"
                                    ]
                                    ws_master.append_row(restore_row)
                                    
                                    cell_l = ws_log.find(str(row['id']))
                                    if cell_l: ws_log.delete_rows(cell_l.row)
                                    
                                    st.success(f"✅ Data {row['nama_mesin']} DIKEMBALIKAN.")
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error Restore: {e}")
        else:
            st.info("Belum ada riwayat aktivitas.")

# ==========================================
# HALAMAN 4: PANDUAN
# ==========================================
elif menu == "📘 Panduan Pengguna":
    st.title("📘 Panduan Pengguna")
    with st.expander("📌 Cara Filter & Cari"):
        st.write("Gunakan Sidebar untuk memfilter Lokasi, Kategori, atau cari nama mesin.")