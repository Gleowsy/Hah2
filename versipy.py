import streamlit as st
import pandas as pd
import math
import re


st.set_page_config(page_title="AI Hospital Locator", page_icon="🚑", layout="wide")

# --- 1. LOAD DATA (LOGIKA KAMU) ---
@st.cache_data # Cache biar ngebut gak loading ulang terus
def load_and_prep_data():
    try:
        # Baca CSV
        df = pd.read_csv('HospInfo.csv', encoding='latin1')
        
        # LOGIKA FILTERING (Sesuai kodinganmu)
        # Ambil hanya yang kolom Location-nya ada tanda kurung "("
        df_bersih = df[df['Location'].str.contains(r'\(', na=False)]
        
        database_rs = []
        
        for index, row in df_bersih.iterrows():
            loc_text = str(row['Location'])
            # Regex untuk ambil koordinat
            match = re.search(r'\(([-+]?\d+\.\d+),\s*([-+]?\d+\.\d+)\)', loc_text)
            
            if match:
                real_lat = float(match.group(1))
                real_long = float(match.group(2))
                
                # LOGIKA BED DARI RATING (Sesuai requestmu)
                try:
                    stok_bed = int(row['Hospital overall rating'])
                except:
                    stok_bed = 0 # Kalau error/not available dianggap 0
                
                database_rs.append({
                    "nama": row['Hospital Name'],
                    "tipe": row['Hospital Type'],
                    "lat": real_lat,  # Kita pisah biar bisa dibaca Peta Streamlit
                    "lon": real_long, # Kita pisah biar bisa dibaca Peta Streamlit
                    "bed_kosong": stok_bed,
                    "ada_ugd": row['Emergency Services']
                })
        
        # Kembalikan sebagai DataFrame biar mudah diolah Streamlit
        return pd.DataFrame(database_rs)

    except Exception as e:
        return pd.DataFrame()

# --- 2. RUMUS JARAK ---
def hitung_jarak(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# --- 3. LOGIKA URGENSI ---
def cek_urgensi(keluhan):
    keluhan = keluhan.lower()
    if any(x in keluhan for x in ["jantung", "sesak", "pingsan", "darah", "kritis", "kecelakaan", "mati"]):
        return 1, "🔴 DARURAT (Butuh Penanganan Segera)"
    elif any(x in keluhan for x in ["patah", "demam", "muntah", "luka", "sakit"]):
        return 2, "🟡 SEDANG (Butuh Dokter)"
    else:
        return 3, "🟢 RINGAN (Rawat Jalan)"

# --- 4. TAMPILAN WEBSITE (FRONTEND) ---

st.title("🚑 AI Hospital Recommendation System")
st.markdown("Sistem pencarian Rumah Sakit cerdas berbasis **Urgensi & Jarak Terdekat** (Full Dataset).")
st.divider()

# --- SIDEBAR (INPUT LOKASI USER) ---
with st.sidebar:
    st.header("📍 Lokasi Pasien")
    # Default Florida (Sesuai dataset yang valid)
    user_lat = st.number_input("Latitude", value=27.3364, format="%.4f")
    user_long = st.number_input("Longitude", value=-82.5307, format="%.4f")
    st.info("Koordinat default diset ke Florida karena data RS valid banyak di sana.")

# --- AREA UTAMA (INPUT KELUHAN) ---
col1, col2 = st.columns([2, 1])
with col1:
    keluhan_input = st.text_input("Masukkan Keluhan / Gejala Pasien:", placeholder="Contoh: Patah tulang, sesak napas...")

# --- TOMBOL CARI & EKSEKUSI ---
if st.button("🔍 CARI RUMAH SAKIT", type="primary"):
    
    # 1. Load Data
    df_rs = load_and_prep_data()
    
    if df_rs.empty:
        st.error("Gagal memuat database RS! Pastikan file HospInfo.csv ada.")
    elif not keluhan_input:
        st.warning("Mohon isi keluhan terlebih dahulu.")
    else:
        # 2. Cek Urgensi
        urgensi, label_status = cek_urgensi(keluhan_input)
        
        # Tampilkan Status Urgensi
        if urgensi == 1: st.error(f"STATUS AI: {label_status}")
        elif urgensi == 2: st.warning(f"STATUS AI: {label_status}")
        else: st.success(f"STATUS AI: {label_status}")
        
        # 3. Filtering & Hitung Jarak
        candidates = []
        
        # Kita iterasi dataframe hasil load tadi
        for index, row in df_rs.iterrows():
            
            # Filter UGD (Jika Darurat)
            if urgensi == 1 and not row['ada_ugd']:
                continue
            
            # Filter Bed
            if row['bed_kosong'] > 0:
                jarak = hitung_jarak(user_lat, user_long, row['lat'], row['lon'])
                
                # Filter Radius Masuk Akal (misal < 100km)
                if jarak < 100:
                    row['jarak_user'] = jarak
                    candidates.append(row)
        
        # 4. Sorting & Tampilkan Hasil
        if candidates:
            # Ubah ke DataFrame lagi biar gampang disort & dipeta
            df_hasil = pd.DataFrame(candidates)
            df_hasil = df_hasil.sort_values(by='jarak_user')
            
            # Ambil 3 Teratas
            top_3 = df_hasil.head(3)
            
            st.subheader(f"🏥 Ditemukan {len(candidates)} RS Terdekat (Top 3):")
            
            # Kolom untuk Text Result & Map
            c_text, c_map = st.columns([1, 1])
            
            with c_text:
                for idx, rs in top_3.iterrows():
                    with st.container(border=True):
                        st.markdown(f"### {rs['nama']}")
                        st.write(f"📏 Jarak: **{rs['jarak_user']:.2f} KM**")
                        st.write(f"🛏️ Sisa Bed: **{rs['bed_kosong']}**")
                        st.caption(f"Tipe: {rs['tipe']}")
            
            with c_map:
                st.subheader("Peta Lokasi")
                # Tampilkan Peta RS Terpilih
                st.map(top_3, zoom=10)
                
        else:
            st.error("MAAF: Tidak ditemukan RS yang sesuai kriteria di radius 100 KM.")