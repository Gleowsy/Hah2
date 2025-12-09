import streamlit as st
import pandas as pd
import math
import re


st.set_page_config(page_title="AI Hospital Locator", page_icon="🚑", layout="wide")


@st.cache_data 
def load_and_prep_data():
    try:
        
        df = pd.read_csv('HospInfo.csv', encoding='latin1')
        
       
        df_bersih = df[df['Location'].str.contains(r'\(', na=False)]
        
        database_rs = []
        
        for index, row in df_bersih.iterrows():
            loc_text = str(row['Location'])
            
            match = re.search(r'\(([-+]?\d+\.\d+),\s*([-+]?\d+\.\d+)\)', loc_text)
            
            if match:
                real_lat = float(match.group(1))
                real_long = float(match.group(2))
                
                
                try:
                    stok_bed = int(row['Hospital overall rating'])
                except:
                    stok_bed = 0 
                
                database_rs.append({
                    "nama": row['Hospital Name'],
                    "tipe": row['Hospital Type'],
                    "lat": real_lat,  
                    "lon": real_long, 
                    "bed_kosong": stok_bed,
                    "ada_ugd": row['Emergency Services']
                })
        
        
        return pd.DataFrame(database_rs)

    except Exception as e:
        return pd.DataFrame()


def hitung_jarak(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def cek_urgensi(keluhan):
    keluhan = keluhan.lower()
    if any(x in keluhan for x in ["jantung", "sesak", "pingsan", "darah", "kritis", "kecelakaan", "mati"]):
        return 1, "🔴 DARURAT (Butuh Penanganan Segera)"
    elif any(x in keluhan for x in ["patah", "demam", "muntah", "luka", "sakit"]):
        return 2, "🟡 SEDANG (Butuh Dokter)"
    else:
        return 3, "🟢 RINGAN (Rawat Jalan)"



st.title("AI Hospital Recommendation System")

st.divider()


with st.sidebar:
    st.header("📍 Lokasi Pasien")
    
    user_lat = st.number_input("Latitude", value=27.3364, format="%.4f")
    user_long = st.number_input("Longitude", value=-82.5307, format="%.4f")
    


col1, col2 = st.columns([2, 1])
with col1:
    keluhan_input = st.text_input("Masukkan Keluhan / Gejala Pasien:", placeholder="Contoh: Patah tulang, sesak napas...")


if st.button("🔍 CARI RUMAH SAKIT", type="primary"):
    
   
    df_rs = load_and_prep_data()
    
    if df_rs.empty:
        st.error
    elif not keluhan_input:
        st.warning("Mohon isi keluhan terlebih dahulu.")
    else:
       
        urgensi, label_status = cek_urgensi(keluhan_input)
        
        
        if urgensi == 1: st.error(f"STATUS AI: {label_status}")
        elif urgensi == 2: st.warning(f"STATUS AI: {label_status}")
        else: st.success(f"STATUS AI: {label_status}")
        
        
        candidates = []
        
        
        for index, row in df_rs.iterrows():
            
           
            if urgensi == 1 and not row['ada_ugd']:
                continue
            
           
            if row['bed_kosong'] > 0:
                jarak = hitung_jarak(user_lat, user_long, row['lat'], row['lon'])
                
                
                if jarak < 100:
                    row['jarak_user'] = jarak
                    candidates.append(row)
        
        
        if candidates:
            
            if candidates:
                df_hasil = pd.DataFrame(candidates)
            
            
            if urgensi == 1:
                
                st.toast("🚨 Mode Darurat: Memprioritaskan lokasi terdekat!")
                df_hasil = df_hasil.sort_values(by='jarak_user', ascending=True)
            else:
                
                st.toast("✅ Mode Normal: Memprioritaskan ketersediaan kamar!")
                df_hasil = df_hasil.sort_values(by='bed_kosong', ascending=False)
            
            
            top_3 = df_hasil.head(3)
            
            st.subheader(f"🏥 Ditemukan {len(candidates)} RS Terdekat (Top 3):")
            
           
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
                
                
                peta_rs = top_3[['lat', 'lon']].copy()
                peta_rs['color'] = '#FF0000' 
                peta_rs['size'] = 100        
                
                
                peta_user = pd.DataFrame({
                    'lat': [user_lat],
                    'lon': [user_long],
                    'color': ['#0000FF'],    
                    'size': [100]
                })
                
                
                map_combined = pd.concat([peta_rs, peta_user], ignore_index=True)
                
                
                st.map(map_combined, latitude='lat', longitude='lon', color='color', size='size', zoom=10)
                
                
                st.caption("🔴 Merah: Rumah Sakit | 🔵 Biru: Lokasi Anda")
                
        else:
            st.error("MAAF: Tidak ditemukan RS yang sesuai kriteria di radius 100 KM.")