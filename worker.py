import os
import psycopg2
import joblib # Untuk memuat model .pkl (ganti jika pakai tensorflow/keras)
import numpy as np
import requests # Untuk mengirim POST request ke API web
import time
from datetime import datetime

# --- 1. KONFIGURASI ---

# URL API Web kamu (endpoint yang baru kita buat di app.py)
WEB_ENDPOINT_URL = "https://hackathon-purwokerto-production.up.railway.app/api/update_status"

# Nama file model dan scaler
# Pastikan file-file ini ada di folder yang sama dengan worker.py
MODEL_FILE = 'model_banjir.pkl' # GANTI JIKA NAMA FILE BEDA
SCALER_FILE = 'scaler_banjir.pkl' # GANTI JIKA NAMA FILE BEDA

# Mapping hasil prediksi (angka) ke status (teks)
# SESUAIKAN INI dengan modelmu (Contoh: 0=Aman, 1=Siaga, 2=Bahaya)
STATUS_MAP = {
    0: "Aman",
    1: "Siaga",
    2: "Bahaya"
}

# --- 2. FUNGSI KONEKSI DATABASE (Sama seperti di app.py) ---
def get_db_connection():
    conn_params = {
        'host': os.environ.get('POSTGRES_HOST'), 
        'dbname': os.environ.get('POSTGRES_DB'),
        'user': os.environ.get('POSTGRES_USER'),
        'password': os.environ.get('POSTGRES_PASSWORD'),
        'port': os.environ.get('POSTGRES_PORT', '5432'), 
    }
    if not all(conn_params.values()):
        print("FATAL: Database environment variables are not fully set.")
        return None
    try:
        conn = psycopg2.connect(**conn_params)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

# --- 3. MUAT MODEL ML (Hanya sekali saat worker dimulai) ---
try:
    print(f"Memuat model dari {MODEL_FILE}...")
    model = joblib.load(MODEL_FILE)
    print(f"Memuat scaler dari {SCALER_FILE}...")
    scaler = joblib.load(SCALER_FILE)
    print("Model dan scaler berhasil dimuat.")
except FileNotFoundError:
    print(f"FATAL ERROR: File model/scaler tidak ditemukan.")
    print(f"Pastikan '{MODEL_FILE}' dan '{SCALER_FILE}' ada.")
    exit()
except Exception as e:
    print(f"FATAL ERROR: Gagal memuat model/scaler: {e}")
    exit()


# --- 4. FUNGSI UTAMA (Siklus Prediksi) ---
def jalankan_siklus_prediksi():
    print(f"\n[{datetime.now()}] Memulai siklus prediksi baru...")
    conn = None
    try:
        # (A) Hubungkan ke Database
        conn = get_db_connection()
        if not conn:
            print("Gagal terhubung ke database. Melewatkan siklus ini.")
            return

        cur = conn.cursor()

        # (B) Ambil Data Sensor Terbaru
        # Query ini mengambil 1 data paling baru dari sensor manapun.
        # SESUAIKAN query ini jika perlu (misal: data rata-rata 5 menit, atau data per sensor_id)
        query = """
        SELECT level, rainfall, soil_saturation 
        FROM sensor_readings
        ORDER BY timestamp DESC
        LIMIT 1;
        """
        cur.execute(query)
        data_terbaru = cur.fetchone() # Hasilnya: (150.5, 10.2, 0.8)

        if not data_terbaru:
            print("Tidak ada data sensor baru ditemukan di database.")
            return

        print(f"Data mentah dari DB: {data_terbaru}")
        
        # (C) Pra-pemrosesan Data
        # Ubah data (tuple) ke format yang diterima scaler/model (numpy array 2D)
        # Contoh: (150.5, 10.2, 0.8) -> [[150.5, 10.2, 0.8]]
        # PASTIKAN URUTAN FITUR INI SAMA SEPERTI SAAT TRAINING
        fitur_mentah = np.array([data_terbaru]) 
        fitur_diproses = scaler.transform(fitur_mentah)

        # (D) Lakukan Prediksi
        prediksi_angka = model.predict(fitur_diproses)[0] # Ambil hasil pertama
        status_string = STATUS_MAP.get(int(prediksi_angka), "Error") # Ubah angka ke teks

        print(f"Hasil Prediksi: {prediksi_angka} -> {status_string}")

        # (E) Kirim (POST) Hasil ke Web Server (app.py)
        payload = {
            "status": status_string,
            "ketinggian_air_terakhir": float(fitur_mentah[0][0]), # Kirim data mentah juga
            "curah_hujan_terakhir": float(fitur_mentah[0][1]), # Kirim data mentah juga
            # Tambahkan data lain jika perlu
        }

        response = requests.post(WEB_ENDPOINT_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"Sukses POST ke web server: {response.json().get('message')}")
        else:
            print(f"Gagal POST ke web server. Status: {response.status_code}, Respon: {response.text}")

    except psycopg2.Error as e:
        print(f"Error Database selama siklus: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error koneksi ke web server (requests): {e}")
    except Exception as e:
        print(f"Terjadi error tidak terduga dalam siklus: {e}")
    finally:
        if conn:
            conn.close()

# --- 5. LOOP UTAMA (Menjalankan worker terus-menerus) ---
if __name__ == "__main__":
    print("Worker prediksi ML dimulai...")
    print(f"Akan mengirim data ke: {WEB_ENDPOINT_URL}")
    while True:
        jalankan_siklus_prediksi()
        
        # Jeda waktu antar siklus (misal: setiap 60 detik)
        jeda_detik = 60 
        print(f"Siklus selesai. Menunggu {jeda_detik} detik...")
        time.sleep(jeda_detik)