import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS 
import json
from datetime import datetime

# --- KONFIGURASI FLASK DAN CORS ---
app = Flask(__name__)
# Solusi CORS: Mengizinkan akses dari semua origin (*) untuk semua endpoint di bawah /api/
# Ini mengatasi masalah di Vercel/IP lokal Anda.
CORS(app, resources={r"/api/*": {"origins": "*"}})

# --- PENYIMPANAN STATUS PREDIKSI (DI MEMORI) ---
# Variabel global untuk menyimpan status prediksi terakhir dari worker.py
status_prediksi_terkini = {
    "status": "Inisialisasi",
    "ketinggian_air": None,
    "curah_hujan": None,
    "timestamp": datetime.now().isoformat()
}

# --- FUNGSI KONEKSI DATABASE ---
def get_db_connection():
    # Ambil detail koneksi dari Environment Variables Railway
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
    
# --- ENDPOINT UTAMA ---
@app.route('/')
def index():
    conn = get_db_connection()
    if conn:
        conn.close()
        return "API Service is running and connected to database."
    else:
        return "API Service is running but **FAILED** to connect to database.", 500


# ===================================================================
# === BAGIAN BARU UNTUK MODEL ML ===
# ===================================================================

# --- ENDPOINT [POST] UNTUK MENERIMA PREDIKSI DARI WORKER ---
@app.route('/api/update_status', methods=['POST'])
def update_status_from_worker():
    global status_prediksi_terkini
    data = request.get_json()

    # Validasi data yang masuk
    if 'status' not in data:
        return jsonify({"message": "Error: 'status' field is missing"}), 400

    # Perbarui status global
    status_prediksi_terkini = {
        "status": data.get('status'),
        "ketinggian_air": data.get('ketinggian_air_terakhir'),
        "curah_hujan": data.get('curah_hujan_terakhir'),
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"Menerima status baru: {status_prediksi_terkini['status']}")
    return jsonify({"message": "Status updated successfully"}), 200

# --- ENDPOINT [GET] UNTUK DIBACA OLEH WEBSITE/FRONTEND (Status ML) ---
@app.route('/api/get_status', methods=['GET'])
def get_current_status_for_web():
    # Cukup kembalikan status terakhir yang disimpan
    return jsonify(status_prediksi_terkini)

# --- ENDPOINT API (READINGS UNTUK FRONTEND - MENGGANTIKAN IP LOKAL) ---
# HANYA MENGGUNAKAN /readings UNTUK MENGHINDARI KONFLIK ROUTING DENGAN /api/
@app.route('/readings', methods=['GET'])
def get_readings_for_web():
    # Mengambil data terbaru dari database untuk markers peta
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "failed", "message": "Database connection failed"}), 500

    cur = None
    try:
        # PENTING: Gunakan kursor untuk SELECT (seperti di endpoint lain)
        cur = conn.cursor(cursor_factory=RealDictCursor) 
        
        # Karena kita hanya menguji koneksi, ambil data dummy (sensor_readings) 
        # dan kembalikan dalam format yang diharapkan frontend
        query = """
        SELECT sensor_id, level AS water_level, rainfall, latitude, longitude, timestamp, 
               CASE 
                   WHEN level > 3.5 THEN 'BAHAYA'
                   WHEN level > 2.5 THEN 'WASPADA'
                   ELSE 'AMAN'
               END AS risk_level
        FROM sensor_readings
        ORDER BY timestamp DESC
        LIMIT 5;
        """
        cur.execute(query)
        readings = cur.fetchall() 
        
        current_risk = status_prediksi_terkini['status']

        return jsonify({
            "status": "success",
            "readings": readings,
            "current_risk": current_risk.upper()
        })
        
    except Exception as e:
        print(f"Readings Error: {e}")
        return jsonify({"status": "failed", "message": "An error occurred while fetching readings."}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()
        

# ===================================================================
# === ENDPOINT LAMA (IoT & QGIS) ===
# ===================================================================

# --- ENDPOINT API (IoT WRITE) ---
@app.route('/api/ingest', methods=['POST'])
def ingest_data():
    data = request.get_json()
    conn = get_db_connection()
    
    if not conn:
        return jsonify({"status": "failed", "message": "Database connection failed"}), 500
        
    try:
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
            data['sensor_id'], 
            float(data['level']), 
            float(data['rainfall']), 
            float(data['soil_saturation']),
            float(data['latitude']),
            float(data['longitude']),
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
        print(f"Database insertion error: {e}") 
        return jsonify({"status": "failed", "message": "Database insertion error."}), 500

# --- ENDPOINT API (QGIS READ - GeoJSON) ---
@app.route('/api/sensor_data', methods=['GET'])
def get_sensor_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Mengambil data GeoJSON dari data sensor terbaru (sudah ada di kode Anda)
        query = """
        WITH latest_readings AS (
            SELECT DISTINCT ON (sensor_id) *
            FROM sensor_readings
            ORDER BY sensor_id, timestamp DESC
        )
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(
                json_agg(
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
                ), 
                '[]'::json 
            )
        ) AS geojson_output
        FROM latest_readings t;
        """
        
        cur.execute(query)
        row = cur.fetchone()
        
        geojson_data = row.get('geojson_output') if row else None
        
        if geojson_data is None:
             geojson_data = {'type': 'FeatureCollection', 'features': []}
             
        return jsonify(geojson_data)
        
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return jsonify({"error": "An unexpected server error occurred.", "detail": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


# --- BLOK UNTUK MENJALANKAN SERVER ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)