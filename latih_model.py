import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

# --- 1. Muat Data (Data yang kamu buat tadi) ---
try:
    df = pd.read_csv('dummy_data_banjir.csv')
except FileNotFoundError:
    print("Error: File 'dummy_data_banjir.csv' tidak ditemukan.")
    print("Pastikan kamu sudah menjalankan skrip pembuat data terlebih dahulu.")
    exit()

print("Data dummy_data_banjir.csv berhasil dimuat.")

# --- 2. Feature Engineering (Membuat Target 'status') ---
# Kita perlu target untuk diprediksi.
# Kita buat 'status' berdasarkan 'ketinggian_muka_air_meter'
# Ini harus SAMA dengan STATUS_MAP di worker.py (0=Aman, 1=Siaga, 2=Bahaya)

def tentukan_status(level):
    if level > 3.5:  # Di atas 3.5m = Bahaya
        return 2
    if level > 2.5:  # Di atas 2.5m = Siaga
        return 1
    return 0         # Di bawah 2.5m = Aman

df['status'] = df['ketinggian_muka_air_meter'].apply(tentukan_status)

print(f"Distribusi Status:\n{df['status'].value_counts(normalize=True)}")

# --- 3. Tentukan Fitur (X) dan Target (y) ---
# Fitur (X) adalah data sensor yang akan dipakai worker.py untuk memprediksi.
# Kita pakai fitur yang sama dengan yang ada di dummy data.
# PENTING: Pastikan urutan ini SAMA dengan di worker.py
fitur = ['curah_hujan_mm_per_jam', 'ketinggian_muka_air_meter', 'debit_air_m3_per_detik']
target = 'status'

X = df[fitur]
y = df[target]

# --- 4. Bagi Data (Data Latih & Data Tes) ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"Data dibagi: {len(X_train)} data latih, {len(X_test)} data tes.")

# --- 5. Buat, Latih, dan Simpan SCALER ---
# (Ini jawaban untuk pertanyaanmu)
print("\nMembuat dan melatih scaler...")
scaler = StandardScaler()

# Penting: 'fit_transform' hanya pada X_train
# Ini "mengajari" scaler rata-rata dan standar deviasi dari data latih
X_train_scaled = scaler.fit_transform(X_train)

# Simpan scaler yang sudah "belajar"
joblib.dump(scaler, 'scaler_banjir.pkl')
print("✅ File 'scaler_banjir.pkl' berhasil disimpan.")

# Gunakan scaler yang sama untuk 'transform' data tes
X_test_scaled = scaler.transform(X_test)


# --- 6. Buat, Latih, dan Simpan MODEL ---
print("\nMembuat dan melatih model...")

# Kita gunakan RandomForest sebagai contoh
model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')

# Latih model menggunakan data yang sudah di-scale
model.fit(X_train_scaled, y_train)

# Simpan model yang sudah "belajar"
joblib.dump(model, 'model_banjir.pkl')
print("✅ File 'model_banjir.pkl' berhasil disimpan.")


# --- 7. (Opsional) Evaluasi Model ---
print("\n--- Hasil Evaluasi Model (Akurasi) ---")
y_pred = model.predict(X_test_scaled)
print(classification_report(y_test, y_pred, target_names=['Aman (0)', 'Siaga (1)', 'Bahaya (2)']))
print("="*40)
print("Selesai! File model.pkl dan scaler.pkl sudah siap.")