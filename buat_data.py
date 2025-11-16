import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- Konfigurasi Data Dummy ---
JUMLAH_BARIS_DATA = 2000
WAKTU_MULAI = datetime(2025, 11, 1, 0, 0)
INTERVAL_WAKTU_MENIT = 10
NAMA_FILE_OUTPUT = 'dummy_data_banjir.csv'

# --- Level Dasar (Saat tidak banjir) ---
BASE_WATER_LEVEL = 1.5  # meter (level air normal)
BASE_DISCHARGE = 5.0    # m^3/detik (debit normal)

print(f"Membuat {JUMLAH_BARIS_DATA} baris data dummy...")

# 1. Membuat daftar timestamp
timestamps = [WAKTU_MULAI + timedelta(minutes=x * INTERVAL_WAKTU_MENIT) for x in range(JUMLAH_BARIS_DATA)]

# 2. Inisialisasi array untuk parameter
curah_hujan = np.zeros(JUMLAH_BARIS_DATA)
ketinggian_air = np.full(JUMLAH_BARIS_DATA, BASE_WATER_LEVEL)
debit_air = np.full(JUMLAH_BARIS_DATA, BASE_DISCHARGE)

# 3. Membuat simulasi "kejadian hujan"
for _ in range(np.random.randint(3, 7)):
    start_index = np.random.randint(0, JUMLAH_BARIS_DATA - 200)
    duration = np.random.randint(30, 120)
    end_index = start_index + duration
    intensity = np.random.uniform(10, 80)
    rain_pattern = np.sin(np.linspace(0, np.pi, duration)) * intensity
    curah_hujan[start_index:end_index] += rain_pattern

# 4. Simulasi Ketinggian Air dan Debit Air
for i in range(1, JUMLAH_BARIS_DATA):
    inflow = curah_hujan[i-1] * 0.01
    outflow = (ketinggian_air[i-1] - BASE_WATER_LEVEL) * 0.05
    noise = np.random.rand() * 0.01
    
    ketinggian_air[i] = ketinggian_air[i-1] + inflow - outflow + noise
    if ketinggian_air[i] < BASE_WATER_LEVEL:
        ketinggian_air[i] = BASE_WATER_LEVEL
        
    height_above_base = ketinggian_air[i] - BASE_WATER_LEVEL
    debit_air[i] = BASE_DISCHARGE + (height_above_base**2) * 2.5 + (np.random.rand() * 0.5)
    if debit_air[i] < BASE_DISCHARGE:
        debit_air[i] = BASE_DISCHARGE

# 5. Membuat DataFrame Pandas
df = pd.DataFrame({
    'timestamp': timestamps,
    'curah_hujan_mm_per_jam': np.round(curah_hujan, 2),
    'ketinggian_muka_air_meter': np.round(ketinggian_air, 2),
    'debit_air_m3_per_detik': np.round(debit_air, 2)
})

# 6. Menyimpan ke file CSV
df.to_csv(NAMA_FILE_OUTPUT, index=False)

print(f"\n✅ File dummy '{NAMA_FILE_OUTPUT}' berhasil dibuat.")

# --- 7. (BARU) OUTPUT KESIMPULAN DATA ---

print("\n" + "="*50)
print("📊 KESIMPULAN DATA HIDROLOGI (DUMMY)")
print("="*50)

# Menghitung durasi
waktu_awal = df['timestamp'].min()
waktu_akhir = df['timestamp'].max()
durasi_total_jam = (waktu_akhir - waktu_awal).total_seconds() / 3600
durasi_total_hari = durasi_total_jam / 24

print("\n--- 1. INFORMASI UMUM ---")
print(f"Rentang Waktu:\t\t{waktu_awal} s/d {waktu_akhir}")
print(f"Total Durasi Data:\t{durasi_total_jam:.1f} jam (atau {durasi_total_hari:.1f} hari)")
print(f"Jumlah Data Point:\t{len(df)}")
print(f"Interval Data:\t\t{INTERVAL_WAKTU_MENIT} menit")


print("\n--- 2. STATISTIK PUNCAK (PEAK) ---")
# Cari baris data dengan nilai tertinggi untuk setiap parameter
peak_hujan = df.loc[df['curah_hujan_mm_per_jam'].idxmax()]
peak_level = df.loc[df['ketinggian_muka_air_meter'].idxmax()]
peak_debit = df.loc[df['debit_air_m3_per_detik'].idxmax()]

print(f"Curah Hujan Tertinggi:\t{peak_hujan['curah_hujan_mm_per_jam']:.2f} mm/jam (pada {peak_hujan['timestamp']})")
print(f"Ketinggian Air Tertinggi:\t{peak_level['ketinggian_muka_air_meter']:.2f} m (pada {peak_level['timestamp']})")
print(f"Debit Air Tertinggi:\t{peak_debit['debit_air_m3_per_detik']:.2f} m³/detik (pada {peak_debit['timestamp']})")


print("\n--- 3. STATISTIK RATA-RATA ---")
# Hitung rata-rata yang relevan
avg_level = df['ketinggian_muka_air_meter'].mean()
avg_debit = df['debit_air_m3_per_detik'].mean()
# Rata-rata curah hujan (hanya saat sedang hujan) agar lebih informatif
avg_hujan_saat_hujan = df[df['curah_hujan_mm_per_jam'] > 1]['curah_hujan_mm_per_jam'].mean()

print(f"Rata-rata Ketinggian Air:\t{avg_level:.2f} m")
print(f"Rata-rata Debit Air:\t\t{avg_debit:.2f} m³/detik")
print(f"Rata-rata Curah Hujan (saat hujan > 1mm/jam):\t{avg_hujan_saat_hujan:.2f} mm/jam")


print("\n--- 4. ANALISIS AMBANG BATAS (CONTOH) ---")
# Tentukan ambang batas (dummy)
THRESHOLD_HUJAN_LEBAT = 30 # mm/jam
THRESHOLD_LEVEL_SIAGA = 3.5 # meter

# Hitung berapa kali (berapa interval) data melewati ambang batas
count_hujan_lebat = (df['curah_hujan_mm_per_jam'] > THRESHOLD_HUJAN_LEBAT).sum()
count_level_siaga = (df['ketinggian_muka_air_meter'] > THRESHOLD_LEVEL_SIAGA).sum()

total_jam_hujan_lebat = (count_hujan_lebat * INTERVAL_WAKTU_MENIT) / 60
total_jam_level_siaga = (count_level_siaga * INTERVAL_WAKTU_MENIT) / 60

print(f"Jumlah interval 'Hujan Lebat' (> {THRESHOLD_HUJAN_LEBAT} mm/jam):\t{count_hujan_lebat} kali (sekitar {total_jam_hujan_lebat:.1f} jam)")
print(f"Jumlah interval 'Level Siaga' (> {THRESHOLD_LEVEL_SIAGA} m):\t{count_level_siaga} kali (sekitar {total_jam_level_siaga:.1f} jam)")
print("\n" + "="*50)

