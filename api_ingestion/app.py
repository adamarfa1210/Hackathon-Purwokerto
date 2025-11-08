# Isi api_ingestion/app.py
import os
import psycopg2
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Konfigurasi Database ---
DB_HOST = 'database'  # Nama service PostGIS di docker-compose.yml
DB_NAME = os.getenv('POSTGRES_DB', 'mydb')
DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'password')
DB_PORT = '5432'

# Fungsi untuk koneksi database
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )

# Endpoint Ingestion Data (HTTP POST)
@app.route('/api/ingest', methods=['POST'])
def ingest_data():
    data = request.json
    
    if not all(k in data for k in ['sensor_id', 'level', 'latitude', 'longitude']):
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Contoh Query untuk menyimpan data dan lokasi (menggunakan ST_SetSRID untuk PostGIS)
        query = """
        INSERT INTO sensor_readings (sensor_id, water_level, timestamp, location)
        VALUES (%s, %s, NOW(), ST_SetSRID(ST_MakePoint(%s, %s), 4326));
        """
        cur.execute(query, (data['sensor_id'], data['level'], data['longitude'], data['latitude']))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Data ingested"}), 201

    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
