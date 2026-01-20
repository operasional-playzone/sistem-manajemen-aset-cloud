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
        
        # Filter Lokasi
        list_lokasi = sorted(df_master['lokasi_toko'].unique().tolist())
        pilih_lokasi = st.sidebar.multiselect("Pilih Lokasi:", list_lokasi)
        
        # Filter Kategori
        list_kategori = sorted(df_master['kategori'].unique().tolist())
        pilih_kategori = st.sidebar.multiselect("Pilih Kategori:", list_kategori)
        
        # Search
        keyword = st.text_input("🔍 Cari Nama Mesin / No Registrasi / ID:", "")
        
        # Apply Filter
        df_tampil = df_master.copy()
        if pilih_lokasi:
            df_tampil = df_tampil[df_tampil['lokasi_toko'].isin(pilih_lokasi)]
        if pilih_kategori:
            df_tampil = df_tampil[df_tampil['kategori'].isin(pilih_kategori)]
        if keyword:
            df_tampil = df_tampil[
                df_tampil['nama_mesin'].str.contains(keyword, case=False, na=False) |
                df_tampil['id'].str.contains(keyword, case=False, na=False) |
                df_tampil['no_registrasi'].astype(str).str.contains(keyword, case=False, na=False)
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
        # Cek kolom wajib
        if 'tanggal' not in df_base.columns:
            st.error("Kolom 'tanggal' tidak ditemukan di Excel Log!")
            st.stop()

        # --- Filter Sidebar ---
        st.sidebar.subheader("Filter History")
        tampil_semua = st.sidebar.checkbox("Tampilkan Semua Tanggal", value=False)
        
        # Konversi ke Datetime untuk filtering
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
            
        # Rapikan Format Tanggal Tampilan
        df_history['tanggal'] = df_history['tanggal_filter'].dt.strftime('%Y-%m-%d').fillna("-")
        
        # Sorting (Urutkan dari ID Log terbesar/terbaru)
        if 'id' in df_history.columns:
            df_history['id_num'] = pd.to_numeric(df_history['id'], errors='coerce')
            df_history = df_history.sort_values(by='id_num', ascending=False).drop(columns=['id_num'])

        if not df_history.empty:
            col_lok = 'lokasi_asal' if 'lokasi_asal' in df_history.columns else 'lokasi'
            
            list_lokasi_hist = sorted(df_history[col_lok].astype(str).unique().tolist())
            pilih_lokasi_hist = st.sidebar.multiselect("Pilih Lokasi Asal:", list_lokasi_hist)
            
            list_aksi = sorted(df_history['jenis_aksi'].astype(str).unique().tolist())
            pilih_aksi = st.sidebar.multiselect("Jenis Aksi:", list_aksi)
            
            # --- FITUR PENCARIAN (UPDATED) ---
            keyword_hist = st.text_input("🔍 Cari (Nama Mesin / No Registrasi):", "")
            
            df_hist_tampil = df_history.copy()
            
            # Filter Filter Sidebar
            if pilih_lokasi_hist:
                df_hist_tampil = df_hist_tampil[df_hist_tampil[col_lok].isin(pilih_lokasi_hist)]
            if pilih_aksi:
                df_hist_tampil = df_hist_tampil[df_hist_tampil['jenis_aksi'].isin(pilih_aksi)]
            
            # Filter Pencarian Ganda (Nama ATAU No Registrasi)
            if keyword_hist:
                df_hist_tampil = df_hist_tampil[
                    df_hist_tampil['nama_mesin'].str.contains(keyword_hist, case=False, na=False) |
                    df_hist_tampil['no_registrasi'].astype(str).str.contains(keyword_hist, case=False, na=False)
                ]

            # URUTAN KOLOM TAMPILAN
            target_cols = ['tanggal', 'jenis_aksi', 'nama_mesin', 'lokasi_asal', 'keterangan', 'harga_beli', 'no_registrasi', 'no_reg_system']
            final_cols = [c for c in target_cols if c in df_hist_tampil.columns]

            # === FITUR DOWNLOAD (BARU) ===
            col_kiri, col_kanan = st.columns([4, 1])
            with col_kiri:
                st.info(f"Menampilkan {len(df_hist_tampil)} catatan sejarah.")
            with col_kanan:
                excel_data = convert_df_to_excel(df_hist_tampil[final_cols])
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data,
                    file_name='riwayat_log_aset.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

            st.dataframe(df_hist_tampil[final_cols], use_container_width=True, hide_index=True)
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
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "➕ Input Baru", 
        "✏️ Edit Detail",     
        "🚚 Mutasi (Pindah)", 
        "🗑️ Likuidasi (Hapus)",
        "🛠️ Koreksi Log (Undo)"
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

    # --- TAB 2: EDIT ---
    with tab2:
        st.subheader("Edit Data Aset")
        pilih_aset_edit = st.selectbox("Pilih Aset untuk Diedit:", 
                                       df_master['nama_mesin'] + " | " + df_master['id'] + " | " + df_master['lokasi_toko'],
                                       key="sel_edit")
        
        if pilih_aset_edit:
            id_edit = pilih_aset_edit.split(" | ")[1]
            data_lama = df_master[df_master['id'] == id_edit].iloc[0]
            
            with st.form("form_edit"):
                new_nama = st.text_input("Nama Mesin", value=data_lama['nama_mesin'])
                new_harga = st.number_input("Harga Beli", value=int(data_lama['harga_beli']) if pd.notna(data_lama['harga_beli']) and str(data_lama['harga_beli']).isdigit() else 0)
                new_noreg = st.text_input("No Registrasi", value=str(data_lama['no_registrasi']) if pd.notna(data_lama['no_registrasi']) else "-")
                ket_edit = st.text_area("Alasan Perubahan (Masuk ke Log)", "Update data aset")
                
                if st.form_submit_button("Update Data"):
                    try:
                        cell = ws_master.find(id_edit)
                        row_idx = cell.row
                        
                        ws_master.update_cell(row_idx, 4, new_nama)
                        ws_master.update_cell(row_idx, 5, new_harga)
                        ws_master.update_cell(row_idx, 6, new_noreg)
                        
                        log_id = generate_id("riwayat_log")
                        tgl_skrg = datetime.now().strftime("%Y-%m-%d")
                        
                        row_log = [
                            log_id,
                            data_lama['lokasi_toko'],
                            data_lama['kategori'],
                            "Edit Data",
                            tgl_skrg,
                            new_nama,
                            new_harga,
                            new_noreg,
                            id_edit,
                            ket_edit
                        ]
                        ws_log.append_row(row_log)
                        
                        st.success("Data berhasil diupdate!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal update: {e}")

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