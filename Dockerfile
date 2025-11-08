# Isi Dockerfile (di direktori docker-project)
FROM python:3.9-slim

# Tetapkan direktori kerja
WORKDIR /app

# Salin dan instal dependencies
COPY api_ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin kode aplikasi
COPY api_ingestion/app.py .

# Jalankan server
CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]
