# Gunakan base image Python yang stabil dan ramping
FROM python:3.11-slim

# Tetapkan variabel lingkungan PORT ke 8080 (standar Railway jika tidak disetel)
ENV PORT 8080

# Tetapkan direktori kerja di dalam container
WORKDIR /app

# Salin dan instal dependensi
COPY requirements.txt .

# Instal Gunicorn dan semua dependensi
# Gunakan --no-cache-dir untuk mengurangi ukuran image
RUN pip install --no-cache-dir gunicorn -r requirements.txt

# Salin kode aplikasi (app.py dan file lain yang mungkin ada)
COPY . .

# Perintah untuk menjalankan server menggunakan Gunicorn
# Gunakan port 8000 secara eksplisit, sesuai dengan docker-compose.yml
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]