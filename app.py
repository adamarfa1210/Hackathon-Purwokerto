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
        'port': os.environ.get('POSTGRES_PORT', '5432'), # DIKOREKSI: POSTGRES_PORT
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


# --- ENDPOINT API (SIMPLE DEBUG READ - Berdasarkan instruksi sebelumnya) ---
@app.route('/api/simple_data', methods=['GET'])
def get_simple_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Implementasi query dan fetchall() sesuai instruksi sebelumnya
        query = "SELECT sensor_id, level, rainfall FROM sensor_readings LIMIT 10;"
        
        cur.execute(query)
        # Menggunakan fetchall() untuk mengambil semua 10 baris data sebagai list of dictionaries
        data = cur.fetchall() 
        
        return jsonify(data)
        
    except psycopg2.Error as e:
        print(f"SQL Error: {e}")
        return jsonify({"error": "Failed to execute database query", "detail": str(e)}), 500
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return jsonify({"error": "An unexpected server error occurred.", "detail": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


# --- ENDPOINT API (QGIS READ - FIX UNTUK KESTABILAN DAN DEBUG) ---
@app.route('/api/sensor_data', methods=['GET'])
def get_sensor_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cur = None
    try:
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
                '[]'::json -- Jika tidak ada data, kembalikan array kosong
            )
        ) AS geojson_output -- Tambahkan alias yang jelas
        FROM latest_readings t;
        """
        
        cur.execute(query)
        row = cur.fetchone()
        
        column_key = 'geojson_output'
        
        # Perhatikan: Di sini sudah menggunakan row.get(column_key) untuk menghindari KeyError
        geojson_data = row.get(column_key) if row else None
        
        # Jika hasil query null, kembalikan GeoJSON kosong yang valid
        if geojson_data is None:
             geojson_data = {'type': 'FeatureCollection', 'features': []}
             
        return jsonify(geojson_data)
        
    except psycopg2.Error as e:
        # Perubahan: Menyertakan pesan error SQL secara detail di respons JSON
        error_detail = str(e).split('\n')[0] # Ambil baris pertama error
        print(f"SQL Error: {e}")
        return jsonify({"error": "Failed to execute database query or GeoJSON error", "detail": error_detail}), 500
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return jsonify({"error": "An unexpected server error occurred.", "detail": str(e)}), 500
    finally:
        # Menjamin kursor dan koneksi ditutup, bahkan jika ada error
        if cur: cur.close()
        if conn: conn.close()


if __name__ == '__main__':
    # Blok ini hanya berjalan saat running lokal atau langsung (bukan via Gunicorn/Railway)
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)