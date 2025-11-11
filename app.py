import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS 
import json

# --- KONFIGURASI FLASK DAN CORS ---
app = Flask(__name__)
# Izinkan CORS dari semua origin (*) untuk pengembangan
# Untuk production, ganti '*' dengan domain frontend Anda
CORS(app) 

# --- FUNGSI KONEKSI DATABASE ---
def get_db_connection():
    # Ambil detail koneksi dari Environment Variables Railway
    # Railway akan menyediakan ini secara otomatis jika Anda menautkan Service Postgres
    conn_params = {
        'host': os.environ.get('POSTGRES_HOST'), 
        'dbname': os.environ.get('POSTGRES_DB'),
        'user': os.environ.get('POSTGRES_USER'),
        'password': os.environ.get('POSTGRES_PASSWORD'),
        'port': os.environ.get('POSTGRES_PORT', '5432'), # Gunakan default 5432
    }
    
    # Cek apakah semua variabel kunci tersedia sebelum mencoba koneksi
    if not all(conn_params.values()):
        print("FATAL: Database environment variables are not fully set.")
        return None
        
    try:
        conn = psycopg2.connect(**conn_params)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None
    
# --- ENDPOINT UTAMA ---
@app.route('/')
def index():
    # Cek koneksi DB sederhana untuk diagnostic
    conn = get_db_connection()
    if conn:
        conn.close()
        return "API Service is running and connected to database."
    else:
        return "API Service is running but **FAILED** to connect to database.", 500


# --- ENDPOINT API (IoT WRITE) ---
@app.route('/api/ingest', methods=['POST'])
def ingest_data():
    data = request.get_json()
    conn = get_db_connection()
    
    if not conn:
        return jsonify({"status": "failed", "message": "Database connection failed"}), 500
        
    try:
        # Pengecekan data awal
        required_fields = ['sensor_id', 'level', 'rainfall', 'soil_saturation', 'latitude', 'longitude']
        for field in required_fields:
            if field not in data:
                 raise KeyError(field)

        query = """
        INSERT INTO sensor_readings 
            (sensor_id, level, rainfall, soil_saturation, latitude, longitude, geom, timestamp)
        VALUES
            (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), NOW())
        """
        
        cur = conn.cursor()
        cur.execute(query, (
            # 1. Pastikan nilai numerik dikonversi ke float di Python
            data['sensor_id'], 
            float(data['level']), 
            float(data['rainfall']), 
            float(data['soil_saturation']),
            float(data['latitude']),
            float(data['longitude']),
            # 2. Koordinat untuk ST_MakePoint juga harus float
            float(data['longitude']), 
            float(data['latitude']) 
        ))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Data ingested successfully"}), 201
        
    except KeyError as e:
        conn.close()
        return jsonify({"status": "failed", "message": f"Missing or invalid field in payload: {e}"}), 400
    except psycopg2.Error as e:
        conn.close()
        # Log error ke console untuk debugging
        print(f"Database insertion error: {e}") 
        return jsonify({"status": "failed", "message": "Database insertion error."}), 500


# --- ENDPOINT API (QGIS READ) ---
@app.route('/api/sensor_data', methods=['GET'])
def get_sensor_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Query untuk mengambil data terbaru (latest) per sensor_id dalam format GeoJSON
    query = """
    WITH latest_readings AS (
        SELECT DISTINCT ON (sensor_id) *
        FROM sensor_readings
        ORDER BY sensor_id, timestamp DESC
    )
    SELECT json_build_object(
        'type', 'FeatureCollection',
        'features', json_agg(
            json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(t.geom)::json,
                'properties', json_build_object(
                    'sensor_id', t.sensor_id, 
                    'level', t.level, 
                    'rainfall', t.rainfall, 
                    'soil_saturation', t.soil_saturation, 
                    'timestamp', t.timestamp
                )
            )
        )
    )
    FROM latest_readings t;
    """
    
    try:
        cur.execute(query)
        # Menggunakan COALESCE untuk memastikan selalu mengembalikan FeatureCollection kosong jika tidak ada data
        row = cur.fetchone()
        geojson_data = row[0] if row and row[0] else {'type': 'FeatureCollection', 'features': []}
        
        cur.close()
        conn.close()
        
        return jsonify(geojson_data)
        
    except psycopg2.Error as e:
        conn.close()
        print(f"SQL Error: {e}")
        return jsonify({"error": "Failed to execute database query"}), 500


if __name__ == '__main__':
    # Blok ini hanya berjalan saat running lokal atau langsung (bukan via Gunicorn/Railway)
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)