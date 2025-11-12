import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS 
import json
from datetime import datetime # Ditambahkan

# --- KONFIGURASI FLASK DAN CORS ---
app = Flask(__name__)
CORS(app) 

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
# === BAGIAN BARU UNTUK MODEL ML (YANG KAMU TANYAKAN) ===
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
        "ketinggian_air": data.get('ketinggian_air_terakhir'), # Sesuaikan dengan payload worker
        "curah_hujan": data.get('curah_hujan_terakhir'),   # Sesuaikan dengan payload worker
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"Menerima status baru: {status_prediksi_terkini['status']}")
    return jsonify({"message": "Status updated successfully"}), 200

# --- ENDPOINT [GET] UNTUK DIBACA OLEH WEBSITE/FRONTEND ---
@app.route('/api/get_status', methods=['GET'])
def get_current_status_for_web():
    # Cukup kembalikan status terakhir yang disimpan
    return jsonify(status_prediksi_terkini)

# ===================================================================
# === ENDPOINT LAMA KAMU (UNTUK IoT & QGIS) ===
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

# --- ENDPOINT API (SIMPLE DEBUG READ) ---
@app.route('/api/simple_data', methods=['GET'])
def get_simple_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = "SELECT sensor_id, level, rainfall FROM sensor_readings LIMIT 10;"
        cur.execute(query)
        data = cur.fetchall() 
        return jsonify(data)
        
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return jsonify({"error": "An unexpected server error occurred.", "detail": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()

# --- ENDPOINT API (QGIS READ) ---
@app.route('/api/sensor_data', methods=['GET'])
def get_sensor_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
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