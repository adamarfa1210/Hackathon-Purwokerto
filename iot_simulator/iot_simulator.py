import requests
import time
import random
import argparse
import sys

# --- REVISI KONFIGURASI API ---
# Ganti dengan URL publik Railway Anda yang sudah teruji.
# Protokol diubah ke HTTPS, dan Port 8000 (lokal) dihapus.

API_URL = "https://hackathon-purwokerto-production.up.railway.app/api/ingest"

# --- PARAMETER DASAR SIMULASI (Tidak Diubah) ---
MIN_LEVEL_BASE = 0.1
MAX_LEVEL_BASE = 3.0
MIN_RAIN = 0.1
MAX_RAIN = 200.0
MIN_SOIL = 10.0
MAX_SOIL = 99.0
SEND_INTERVAL_SEC = 10 

# Variabel yang akan diisi dari command line
DEVICE_ID = None
LATITUDE = None
LONGITUDE = None
LEVEL_OFFSET = 0.0 # Nilai offset khusus untuk ketinggian air

def generate_data():
    """Menghasilkan data sensor acak (simulasi) dengan offset level dan variasi ekstrem."""
    global LEVEL_OFFSET, MIN_LEVEL_BASE, MAX_LEVEL_BASE, MAX_RAIN, MIN_SOIL, MAX_SOIL

    # 1. Ketinggian Air (Level)
    base_level = random.uniform(MIN_LEVEL_BASE, MAX_LEVEL_BASE)
    level = round(base_level + LEVEL_OFFSET, 3)

    # 2. Curah Hujan (Rainfall) - Lebih sering dan lebih ekstrem
    if random.random() < 0.30: 
        rainfall = round(random.uniform(50.0, MAX_RAIN), 2)
    else:
        rainfall = round(random.uniform(MIN_RAIN, 30.0), 2)

    # 3. Kelembaban Tanah (Soil Saturation) - Rentang yang lebih lebar
    saturation = round(random.uniform(MIN_SOIL, MAX_SOIL), 1)

    return {
        "sensor_id": DEVICE_ID,
        "level": level,
        "rainfall": rainfall,
        "soil_saturation": saturation, 
        "latitude": LATITUDE,
        "longitude": LONGITUDE
    }

def send_reading():
    """Mengirim data yang dihasilkan ke API Ingestion."""
    payload = generate_data()

    try:
        # METHOD HARUS POST
        response = requests.post(API_URL, json=payload)
        response.raise_for_status() 
        
        status_message = "SUCCESS" if response.status_code in [200, 201] else f"HTTP {response.status_code}"
        
        print(f"[{time.strftime('%H:%M:%S')}] {DEVICE_ID} | {status_message} | Level: {payload['level']}m (Offset: +{LEVEL_OFFSET}m) | Rain: {payload['rainfall']}mm/h | Soil: {payload['soil_saturation']}%")

    except requests.exceptions.ConnectionError:
        print(f"[{time.strftime('%H:%M:%S')}] {DEVICE_ID} | ERROR: Koneksi ditolak. Pastikan URL API sudah benar (HTTPS).")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] {DEVICE_ID} | FAILED: {e}")

if __name__ == '__main__':
    
    # --- PROSES ARGUMEN COMMAND LINE (Tidak Diubah) ---
    parser = argparse.ArgumentParser(description="IoT Sensor Data Simulator Sungai Citarum.")
    parser.add_argument('--id', type=str, required=True, help='ID unik untuk sensor (misal: Citarum-01).')
    parser.add_argument('--lat', type=float, required=True, help='Latitude (lintang) lokasi sensor.')
    parser.add_argument('--lon', type=float, required=True, help='Longitude (bujur) lokasi sensor.')
    parser.add_argument('--offset', type=float, default=0.0, help='Offset ketinggian air (m) untuk mensimulasikan lokasi hilir/hulu.')
    
    try:
        args = parser.parse_args()
    except SystemExit:
        sys.exit(1)
        
    # Tetapkan variabel global dari argumen
    DEVICE_ID = args.id
    LATITUDE = args.lat
    LONGITUDE = args.lon
    LEVEL_OFFSET = args.offset 

    print(f"==================================================")
    print(f"Memulai simulasi IoT untuk Device ID: {DEVICE_ID}")
    print(f"Lokasi: ({LATITUDE}, {LONGITUDE}). Offset Level: +{LEVEL_OFFSET}m")
    print(f"Target API: {API_URL}. Interval: {SEND_INTERVAL_SEC} detik.")
    print(f"==================================================")

    random.seed(time.time()) 
    
    while True:
        send_reading()
        time.sleep(SEND_INTERVAL_SEC)