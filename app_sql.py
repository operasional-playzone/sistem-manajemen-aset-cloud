import streamlit as st
import mysql.connector
import pandas as pd
import os
import io
import time
from datetime import date, timedelta
from dotenv import load_dotenv

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Manajemen Aset Mesin",
    page_icon="🏭",
    layout="wide"
)

# Load Environment Variables
load_dotenv(override=True)

# ==========================================
# 🔐 SISTEM LOGIN (SESSION STATE)
# ==========================================
# Inisialisasi status login jika belum ada
if 'status_login' not in st.session_state:
    st.session_state['status_login'] = False

# Fungsi untuk Login
def proses_login():
    user_env = os.getenv("ADMIN_USER", "admin") # Default admin jika env error
    pass_env = os.getenv("ADMIN_PASS", "admin")
    
    if st.session_state['input_user'] == user_env and st.session_state['input_pass'] == pass_env:
        st.session_state['status_login'] = True
    else:
        st.error("❌ Username atau Password salah!")

# Fungsi Logout
def proses_logout():
    st.session_state['status_login'] = False
    st.rerun()

# --- LOGIKA TAMPILAN LOGIN ---
if not st.session_state['status_login']:
    st.markdown("## 🔒 Login Sistem Aset")
    st.info("Silakan login untuk mengakses data perusahaan.")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.text_input("Username", key="input_user")
        st.text_input("Password", type="password", key="input_pass")
        st.button("Masuk", on_click=proses_login)
    
    # Hentikan program di sini jika belum login (Security Gate)
    st.stop()

# ==========================================
# APLIKASI UTAMA (Hanya muncul jika Login Sukses)
# ==========================================

# --- FUNGSI KONEKSI DATABASE ---
@st.cache_resource
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database="manajemen_aset"
    )

# --- FUNGSI SQL EKSEKUTOR ---
def run_query(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return True, cursor.rowcount
    except Exception as e:
        return False, str(e)
    finally:
        cursor.close()

def load_data(query, params=None):
    conn = get_db_connection()
    try:
        if params:
            df = pd.read_sql(query, conn, params=params)
        else:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Error Database: {e}")
        return pd.DataFrame()

# --- FUNGSI EXPORT EXCEL ---
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

# --- SIDEBAR NAVIGASI ---
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
    st.title("🏭 Sistem Manajemen Aset Mesin (Aktif)")
    
    df_master = load_data("SELECT * FROM master_aset")
    
    if not df_master.empty:
        # --- FILTER ---
        st.sidebar.subheader("Filter Master Aset")
        
        list_lokasi = sorted(df_master['lokasi_toko'].dropna().unique().tolist())
        pilih_lokasi = st.sidebar.multiselect("Pilih Lokasi:", list_lokasi)
        
        list_kategori = sorted(df_master['kategori'].dropna().unique().tolist())
        pilih_kategori = st.sidebar.multiselect("Pilih Kategori:", list_kategori)
        
        keyword = st.text_input("🔍 Cari Nama Mesin / No Registrasi / ID:", "")
        
        # Logika Filter
        df_tampil = df_master.copy()
        if pilih_lokasi:
            df_tampil = df_tampil[df_tampil['lokasi_toko'].isin(pilih_lokasi)]
        if pilih_kategori:
            df_tampil = df_tampil[df_tampil['kategori'].isin(pilih_kategori)]
        if keyword:
            df_tampil['id_str'] = df_tampil['id'].astype(str)
            df_tampil = df_tampil[
                df_tampil['nama_mesin'].str.contains(keyword, case=False, na=False) |
                df_tampil['no_registrasi'].str.contains(keyword, case=False, na=False) |
                df_tampil['id_str'].str.contains(keyword, case=False, na=False)
            ]
            df_tampil = df_tampil.drop(columns=['id_str'])

        # --- DOWNLOAD BUTTON ---
        col_kiri, col_kanan = st.columns([4, 1])
        with col_kiri:
            st.write(f"**Total Data:** {len(df_tampil)} Unit")
        with col_kanan:
            excel_data = convert_df_to_excel(df_tampil)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name='data_aset_terfilter.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        st.dataframe(df_tampil, use_container_width=True, hide_index=True, height=600)
    else:
        st.warning("Data Master Aset kosong. Silakan cek database.")

# ==========================================
# HALAMAN 2: RIWAYAT LOG
# ==========================================
elif menu == "Riwayat Log (History)":
    st.title("📜 Riwayat Mutasi & Likuidasi Mesin")
    
    st.sidebar.subheader("Filter History")
    
    # 1. FILTER TANGGAL
    st.sidebar.markdown("### 📅 Filter Waktu")
    tampil_semua = st.sidebar.checkbox("Tampilkan Semua Tanggal (All Time)", value=False)
    
    if not tampil_semua:
        today = date.today()
        last_month = today - timedelta(days=30)
        filter_tgl = st.sidebar.date_input("Rentang Tanggal:", (last_month, today))
        start_date, end_date = today, today
        if isinstance(filter_tgl, tuple) and len(filter_tgl) == 2:
            start_date, end_date = filter_tgl
        
        query_hist = "SELECT * FROM riwayat_log WHERE tanggal_kejadian BETWEEN %s AND %s ORDER BY created_at DESC"
        df_history = load_data(query_hist, (start_date, end_date))
    else:
        df_history = load_data("SELECT * FROM riwayat_log ORDER BY created_at DESC")
    
    if not df_history.empty:
        list_lokasi_hist = sorted(df_history['lokasi_asal'].dropna().unique().tolist())
        pilih_lokasi_hist = st.sidebar.multiselect("Pilih Lokasi Asal:", list_lokasi_hist)
        
        list_kategori_hist = sorted(df_history['kategori'].dropna().unique().tolist())
        pilih_kategori_hist = st.sidebar.multiselect("Pilih Kategori:", list_kategori_hist)
        
        list_aksi = sorted(df_history['jenis_aksi'].dropna().unique().tolist())
        pilih_aksi = st.sidebar.multiselect("Jenis Aksi:", list_aksi)
        
        keyword_hist = st.text_input("🔍 Cari History (Nama Mesin):", "")
        
        df_hist_tampil = df_history.copy()
        if pilih_lokasi_hist:
            df_hist_tampil = df_hist_tampil[df_hist_tampil['lokasi_asal'].isin(pilih_lokasi_hist)]
        if pilih_kategori_hist:
            df_hist_tampil = df_hist_tampil[df_hist_tampil['kategori'].isin(pilih_kategori_hist)]
        if pilih_aksi:
            df_hist_tampil = df_hist_tampil[df_hist_tampil['jenis_aksi'].isin(pilih_aksi)]
        if keyword_hist:
            df_hist_tampil = df_hist_tampil[df_hist_tampil['nama_mesin'].str.contains(keyword_hist, case=False, na=False)]

        col_kiri, col_kanan = st.columns([4, 1])
        with col_kiri:
            st.info(f"Menampilkan {len(df_hist_tampil)} catatan sejarah.")
        with col_kanan:
            excel_hist = convert_df_to_excel(df_hist_tampil)
            st.download_button(
                label="📥 Download Excel",
                data=excel_hist,
                file_name='data_history.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        st.dataframe(df_hist_tampil, use_container_width=True, hide_index=True)
    else:
        st.warning("Tidak ada data sejarah yang ditemukan.")

# ==========================================
# HALAMAN 3: KELOLA ASET (ADMIN)
# ==========================================
elif menu == "⚡ Kelola Aset (Admin)":
    st.title("⚡ Menu Admin: Kelola Data Mesin")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "➕ Input Baru", 
        "✏️ Edit Detail",     
        "🚚 Mutasi (Pindah)", 
        "🗑️ Likuidasi (Hapus)",
        "🕵️ Jejak Aset",
        "↩️ Undo Kesalahan"
    ])
    
    # --- TAB 1: INPUT BARU (DENGAN AUTO RESET) ---
    with tab1:
        st.subheader("Tambah Aset Mesin Baru")
        
        df_lok_db = load_data("SELECT DISTINCT lokasi_toko FROM master_aset WHERE lokasi_toko IS NOT NULL ORDER BY lokasi_toko ASC")
        opsi_lokasi = df_lok_db['lokasi_toko'].tolist() + ["++ Tambah Lokasi Baru ++"] if not df_lok_db.empty else ["++ Tambah Lokasi Baru ++"]

        df_kat_db = load_data("SELECT DISTINCT kategori FROM master_aset WHERE kategori IS NOT NULL ORDER BY kategori ASC")
        opsi_kategori = df_kat_db['kategori'].tolist() + ["++ Tambah Kategori Baru ++"] if not df_kat_db.empty else ["++ Tambah Kategori Baru ++"]

        with st.form("form_input"):
            c1, c2 = st.columns(2)
            pilihan_lokasi = c1.selectbox("Pilih Lokasi Toko", opsi_lokasi)
            # KEY DITAMBAHKAN UNTUK RESET
            input_lokasi_baru = c1.text_input("Nama Lokasi Baru (Isi JIKA pilih 'Tambah Baru')", placeholder="Contoh: R099 CABANG BARU", key="in_lok_baru")
            
            pilihan_kategori = c2.selectbox("Pilih Kategori Mesin", opsi_kategori)
            # KEY DITAMBAHKAN UNTUK RESET
            input_kategori_baru = c2.text_input("Nama Kategori Baru (Isi JIKA pilih 'Tambah Baru')", placeholder="Contoh: VR GAME", key="in_kat_baru")
            
            st.markdown("---")
            # KEY DITAMBAHKAN UNTUK RESET
            input_nama = st.text_input("Nama Mesin (Wajib Diisi)", key="in_nama")
            c3, c4 = st.columns(2)
            input_harga = c3.text_input("Harga Beli (Opsional)", key="in_harga")
            input_noreg = c4.text_input("No Registrasi (Opsional)", key="in_noreg")
            
            submitted = st.form_submit_button("Simpan Aset Baru")
            
            if submitted:
                final_lokasi = input_lokasi_baru.upper() if pilihan_lokasi == "++ Tambah Lokasi Baru ++" else pilihan_lokasi
                final_kategori = input_kategori_baru.upper() if pilihan_kategori == "++ Tambah Kategori Baru ++" else pilihan_kategori

                if final_lokasi and final_kategori and input_nama:
                    query = """
                    INSERT INTO master_aset (lokasi_toko, kategori, nama_mesin, harga_beli, no_registrasi, status)
                    VALUES (%s, %s, %s, %s, %s, 'Aktif')
                    """
                    sukses, info = run_query(query, (final_lokasi, final_kategori, input_nama.upper(), input_harga, input_noreg))
                    if sukses:
                        st.success(f"✅ Berhasil! {input_nama} ditambahkan ke {final_lokasi}.")
                        time.sleep(1)
                        # === LOGIKA RESET FORM ===
                        # Kosongkan Session State berdasarkan Key
                        st.session_state['in_nama'] = ""
                        st.session_state['in_harga'] = ""
                        st.session_state['in_noreg'] = ""
                        if 'in_lok_baru' in st.session_state: st.session_state['in_lok_baru'] = ""
                        if 'in_kat_baru' in st.session_state: st.session_state['in_kat_baru'] = ""
                        
                        st.rerun() # Refresh halaman dengan form bersih
                    else:
                        st.error(f"❌ Database Error: {info}")
                else:
                    st.warning("⚠️ Lokasi, Kategori, dan Nama Mesin wajib diisi!")

    # --- TAB 2: EDIT DETAIL ---
    with tab2:
        st.subheader("✏️ Edit Detail Aset (Koreksi Data)")
        st.info("Gunakan menu ini jika ada **Kesalahan Penulisan**.")
        
        id_edit = st.text_input("Masukkan ID Aset untuk Edit:", placeholder="Contoh: 154")
        
        if id_edit:
            df_curr = load_data(f"SELECT * FROM master_aset WHERE id = '{id_edit}'")
            
            if not df_curr.empty:
                curr_row = df_curr.iloc[0]
                st.write(f"**Sedang Mengedit:** :blue[{curr_row['nama_mesin']}] di {curr_row['lokasi_toko']}")
                
                df_kat_all = load_data("SELECT DISTINCT kategori FROM master_aset ORDER BY kategori ASC")
                list_kat = df_kat_all['kategori'].tolist()
                try: idx_kat = list_kat.index(curr_row['kategori'])
                except: idx_kat = 0

                with st.form("form_edit"):
                    col_e1, col_e2 = st.columns(2)
                    new_kat = col_e1.selectbox("Kategori", list_kat, index=idx_kat)
                    new_nama = col_e2.text_input("Nama Mesin", value=curr_row['nama_mesin'])
                    
                    col_e3, col_e4 = st.columns(2)
                    val_harga = curr_row['harga_beli'] if curr_row['harga_beli'] else ""
                    val_noreg = curr_row['no_registrasi'] if curr_row['no_registrasi'] else ""
                    new_harga = col_e3.text_input("Harga Beli", value=val_harga)
                    new_noreg = col_e4.text_input("No Registrasi", value=val_noreg)
                    
                    tombol_simpan = st.form_submit_button("💾 Simpan Perubahan")
                    
                    if tombol_simpan:
                        q_update_detail = """
                        UPDATE master_aset 
                        SET kategori=%s, nama_mesin=%s, harga_beli=%s, no_registrasi=%s 
                        WHERE id=%s
                        """
                        sukses_upd, msg = run_query(q_update_detail, (new_kat, new_nama.upper(), new_harga, new_noreg, id_edit))
                        
                        if sukses_upd:
                            q_log_edit = """
                            INSERT INTO riwayat_log (lokasi_asal, kategori, nama_mesin, jenis_aksi, tanggal_kejadian, keterangan)
                            VALUES (%s, %s, %s, 'Koreksi Data', CURDATE(), 'Update Detail Mesin (Admin)')
                            """
                            run_query(q_log_edit, (curr_row['lokasi_toko'], new_kat, new_nama.upper()))
                            st.success("✅ Data berhasil diperbarui!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Gagal Update: {msg}")
            else:
                st.error("❌ ID tidak ditemukan.")

    # --- TAB 3: MUTASI ---
    with tab3:
        st.subheader("Mutasi Aset (Pindah Lokasi)")
        id_cari_mut = st.text_input("Masukkan ID Aset (Mutasi):", placeholder="Contoh: 154")
        aset_ditemukan = None
        
        if id_cari_mut:
            df_cek = load_data(f"SELECT * FROM master_aset WHERE id = '{id_cari_mut}'")
            if not df_cek.empty:
                aset_ditemukan = df_cek.iloc[0]
                st.write(f"**Ditemukan:** :blue[{aset_ditemukan['nama_mesin']}] di :red[{aset_ditemukan['lokasi_toko']}]")
            else:
                st.error("❌ ID tidak ditemukan.")
        
        if aset_ditemukan is not None:
            df_lok_mutasi = load_data("SELECT DISTINCT lokasi_toko FROM master_aset ORDER BY lokasi_toko ASC")
            list_lok_mutasi = df_lok_mutasi['lokasi_toko'].tolist()
            
            with st.form("form_mutasi"):
                lokasi_baru = st.selectbox("Pindah ke Lokasi Mana?", list_lok_mutasi)
                keterangan_mutasi = st.text_area("Keterangan Mutasi", "Mutasi Reguler")
                tombol_mutasi = st.form_submit_button("🚀 Proses Mutasi")
                
                if tombol_mutasi:
                    if lokasi_baru == aset_ditemukan['lokasi_toko']:
                        st.warning("⚠️ Lokasi baru sama dengan lokasi lama!")
                    else:
                        q_update = "UPDATE master_aset SET lokasi_toko = %s WHERE id = %s"
                        sukses_up, _ = run_query(q_update, (lokasi_baru, id_cari_mut))
                        
                        if sukses_up:
                            q_hist = """
                            INSERT INTO riwayat_log (lokasi_asal, kategori, nama_mesin, jenis_aksi, tanggal_kejadian, keterangan)
                            VALUES (%s, %s, %s, 'Mutasi', CURDATE(), %s)
                            """
                            ket_lengkap = f"Pindah dari {aset_ditemukan['lokasi_toko']} ke {lokasi_baru}. {keterangan_mutasi}"
                            run_query(q_hist, (aset_ditemukan['lokasi_toko'], aset_ditemukan['kategori'], aset_ditemukan['nama_mesin'], ket_lengkap))
                            st.success(f"✅ Sukses! {aset_ditemukan['nama_mesin']} dipindah ke {lokasi_baru}")
                            time.sleep(2)
                            st.rerun()

    # --- TAB 4: LIKUIDASI ---
    with tab4:
        st.subheader("Likuidasi Aset (Hapus dari Master)")
        id_likuidasi = st.text_input("Masukkan ID Aset (Likuidasi):", placeholder="Contoh: 154")
        aset_hapus = None
        
        if id_likuidasi:
            df_cek_hapus = load_data(f"SELECT * FROM master_aset WHERE id = '{id_likuidasi}'")
            if not df_cek_hapus.empty:
                aset_hapus = df_cek_hapus.iloc[0]
                st.write(f"**Akan dihapus:** :blue[{aset_hapus['nama_mesin']}] - {aset_hapus['lokasi_toko']}")
            else:
                st.error("❌ ID tidak ditemukan.")

        if aset_hapus is not None:
            with st.form("form_likuidasi"):
                alasan = st.selectbox("Jenis Aksi", ["Likuidasi", "Musnah", "Terjual", "Hilang"])
                ket_hapus = st.text_area("Keterangan Tambahan", "Aset sudah tidak layak pakai")
                tombol_hapus = st.form_submit_button("🗑️ Konfirmasi Hapus")
                
                if tombol_hapus:
                    h_beli = aset_hapus['harga_beli'] if aset_hapus['harga_beli'] else ""
                    n_reg = aset_hapus['no_registrasi'] if aset_hapus['no_registrasi'] else ""

                    q_hist_del = """
                    INSERT INTO riwayat_log (lokasi_asal, kategori, nama_mesin, jenis_aksi, tanggal_kejadian, harga_beli, no_registrasi, keterangan)
                    VALUES (%s, %s, %s, %s, CURDATE(), %s, %s, %s)
                    """
                    run_query(q_hist_del, (aset_hapus['lokasi_toko'], aset_hapus['kategori'], aset_hapus['nama_mesin'], alasan.upper(), h_beli, n_reg, ket_hapus))
                    
                    q_del = "DELETE FROM master_aset WHERE id = %s"
                    sukses_del, _ = run_query(q_del, (id_likuidasi,))
                    if sukses_del:
                        st.success(f"✅ Data berhasil dilikuidasi.")
                        time.sleep(2)
                        st.rerun()

    # --- TAB 5: JEJAK ASET ---
    with tab5:
        st.subheader("🕵️ Jejak Pergerakan Data")
        cari_jejak = st.text_input("Masukkan Nama Mesin (Jejak):", placeholder="Contoh: PUMP IT UP")
        
        if cari_jejak:
            query_trace = "SELECT * FROM riwayat_log WHERE nama_mesin LIKE %s ORDER BY created_at DESC"
            df_trace = load_data(query_trace, (f"%{cari_jejak}%",))
            
            if not df_trace.empty:
                st.write(f"Ditemukan **{len(df_trace)}** catatan untuk: *{cari_jejak}*")
                for index, row in df_trace.iterrows():
                    role = "user" if row['jenis_aksi'] == "Mutasi" else "assistant"
                    with st.chat_message(role):
                        st.markdown(f"**{row['tanggal_kejadian']}** - **{row['jenis_aksi']}**")
                        st.markdown(f"📍 Lokasi: `{row['lokasi_asal']}` | Kat: `{row['kategori']}`")
                        st.markdown(f"📝 *{row['keterangan']}*")
            else:
                st.warning("Belum ada riwayat.")

    # --- TAB 6: UNDO KESALAHAN ---
    with tab6:
        st.subheader("↩️ Undo Kesalahan Terakhir")
        st.warning("⚠️ Fitur ini membatalkan aksi terakhir.")
        
        df_last = load_data("SELECT * FROM riwayat_log ORDER BY created_at DESC LIMIT 5")
        
        if not df_last.empty:
            st.write("##### 5 Aktivitas Terakhir:")
            for i, row in df_last.iterrows():
                label_expander = f"{row['jenis_aksi']} - {row['nama_mesin']} ({row['tanggal_kejadian']})"
                with st.expander(label_expander):
                    st.write(f"**Keterangan:** {row['keterangan']}")
                    col_undo, col_info = st.columns([1, 3])
                    
                    if row['jenis_aksi'] == 'Mutasi':
                        if col_undo.button("↩️ BATALKAN MUTASI", key=f"undo_{row['id']}"):
                            q_cek = f"SELECT * FROM master_aset WHERE nama_mesin = '{row['nama_mesin']}'"
                            df_cek_m = load_data(q_cek)
                            if not df_cek_m.empty:
                                q_restore = "UPDATE master_aset SET lokasi_toko = %s WHERE nama_mesin = %s"
                                sukses_undo, msg = run_query(q_restore, (row['lokasi_asal'], row['nama_mesin']))
                                if sukses_undo:
                                    run_query("DELETE FROM riwayat_log WHERE id = %s", (row['id'],))
                                    st.success(f"✅ Mutasi dibatalkan!")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error(f"Gagal restore: {msg}")
                            else:
                                st.error("❌ Gagal Undo: Mesin tidak ditemukan di Master.")

                    elif row['jenis_aksi'] in ['LIKUIDASI', 'MUSNAH', 'TERJUAL', 'HILANG']:
                        if col_undo.button("♻️ RESTORE DATA", key=f"restore_{row['id']}"):
                            q_restore_ins = """
                            INSERT INTO master_aset (lokasi_toko, kategori, nama_mesin, harga_beli, no_registrasi, status)
                            VALUES (%s, %s, %s, %s, %s, 'Aktif')
                            """
                            val_h = row.get('harga_beli') if row.get('harga_beli') else None
                            val_n = row.get('no_registrasi') if row.get('no_registrasi') else None

                            sukses_rest, msg = run_query(q_restore_ins, (row['lokasi_asal'], row['kategori'], row['nama_mesin'], val_h, val_n))
                            if sukses_rest:
                                run_query("DELETE FROM riwayat_log WHERE id = %s", (row['id'],))
                                st.success(f"✅ Data dikembalikan ke Master!")
                                time.sleep(2)
                                st.rerun()
        else:
            st.info("Belum ada aktivitas.")

# ==========================================
# HALAMAN 4: USER GUIDE
# ==========================================
elif menu == "📘 Panduan Pengguna":
    st.title("📘 Panduan Penggunaan Sistem")
    
    with st.expander("📌 Edit Detail Data"):
        st.markdown("""
        Gunakan menu **Edit Detail** di Admin jika:
        1. Nama Mesin salah ketik.
        2. Kategori mesin salah.
        3. Ingin menambahkan Harga/Noreg.
        """)

    with st.expander("📌 Cara Mencari & Filter Data"):
        st.markdown("""
        1. **Master Aset:** Pilih lokasi/kategori di Sidebar.
        2. **Riwayat Log:** Centang kotak 'Tampilkan Semua Tanggal' untuk melihat seluruh data.
        """)