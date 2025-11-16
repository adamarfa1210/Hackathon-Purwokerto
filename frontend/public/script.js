// Konfigurasi Umum
const BANDUNG_CENTER = [-6.9219, 107.6105];
const API_READINGS_URL = "http://192.168.1.58:8000/api/readings"; // Endpoint GET API Anda

// Konfigurasi GeoServer Radith (Harap diisi saat siap)
const GEOSERVER_WMS_URL = 'http://[RADITH_GEOSERVER_IP]:[PORT]/geoserver/wms';
const GEOSERVER_LAYER_NAME = 'workspace:area_rawan_dummy'; 

// --- 1. Definisi Peta ---
const map = L.map('mapid').setView(BANDUNG_CENTER, 11);

// Muat Basemap (OpenStreetMap)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// --- 2. Ikon Marker Dinamis (Untuk Visualisasi Risiko) ---

/**
 * Mendapatkan ikon marker berwarna berdasarkan tingkat risiko.
 * Asumsi: Risk level dari backend adalah 'AMAN', 'SIAGA', 'BAHAYA', atau 'WASPADA'.
 */
const getMarkerIcon = (riskLevel) => {
    let color = 'blue'; // Default jika data tidak terdefinisi
    
    if (riskLevel === 'AMAN') {
        color = 'green';
    } else if (riskLevel === 'WASPADA' || riskLevel === 'SIAGA') {
        color = 'orange';
    } else if (riskLevel === 'BAHAYA') {
        color = 'red';
    }
    
    // Menggunakan ikon dari leaflet-color-markers
    return L.icon({
        iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });
};

let sensorMarkers = {}; // Untuk menyimpan marker yang sudah ada

// --- 3. Logika Peta (WMS Layer GeoServer) ---
/**
 * Fungsi untuk menambahkan WMS Layer dari GeoServer ke peta.
 * Akan dijalankan sekali setelah script dimuat.
 */
function loadWMSLayer() {
    // Hanya load jika URL GeoServer sudah diisi (bukan placeholder)
    if (GEOSERVER_WMS_URL.includes('[RADITH_GEOSERVER_IP]')) {
        console.warn("WMS Layer tidak dimuat: URL GeoServer masih placeholder.");
        return;
    }
    
    L.tileLayer.wms(GEOSERVER_WMS_URL, {
        layers: GEOSERVER_LAYER_NAME, 
        format: 'image/png',
        transparent: true,
        attribution: 'EWS Project',
        zIndex: 5, // Di atas basemap
    }).addTo(map);
    console.log("WMS Layer GeoServer dimuat.");
}


// --- 4. Fungsi Pemanggilan API dan Update Dashboard ---
async function fetchSensorData() {
    try {
        const response = await fetch(API_READINGS_URL);
        if (!response.ok) {
            throw new Error(`API Error: HTTP status ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            updateDashboard(data.readings, data.current_risk); 
        } else {
            document.getElementById('status-text').textContent = `Kesalahan Data: ${data.message}`;
        }

    } catch (error) {
        document.getElementById('status-text').textContent = `Kesalahan Koneksi: ${error.message}`;
        console.error("Error fetching data:", error);
    }
}

/**
 * Memperbarui panel dashboard dan menempatkan marker sensor di peta.
 * @param {Array} readings - Array data sensor terbaru.
 * @param {string} riskLevel - Tingkat risiko keseluruhan (dari backend).
 */
function updateDashboard(readings, riskLevel) {
    // Update Status Utama
    const statusElement = document.getElementById('status-text');
    statusElement.textContent = `Status: ${riskLevel.toUpperCase()}`;
    statusElement.className = riskLevel === 'BAHAYA' ? 'text-red-600 font-bold' : 
                              (riskLevel === 'WASPADA' || riskLevel === 'SIAGA' ? 'text-orange-600 font-bold' : 'text-green-600 font-bold');


    // Update List Data Sensor
    const list = document.getElementById('sensor-data-list');
    if (list) list.innerHTML = ''; 

    readings.forEach(reading => {
        // Asumsi data reading memiliki: sensor_id, water_level, rainfall, timestamp, latitude, longitude, dan risk_level (optional)

        // 1. Update list
        if (list) {
            const listItem = document.createElement('li');
            const levelText = reading.water_level !== undefined ? `${reading.water_level}m` : 'N/A';
            const timeText = reading.timestamp ? reading.timestamp.substring(11, 16) : 'N/A';
            
            // Asumsi risk_level per sensor ada di reading.risk_level, jika tidak, pakai status umum.
            const sensorRiskDisplay = reading.risk_level || riskLevel; 
            
            listItem.innerHTML = `Sensor ${reading.sensor_id}: Level **${levelText}** (${timeText}) [${sensorRiskDisplay.toUpperCase()}]`;
            list.appendChild(listItem);
        }
        
        // 2. Update Peta (Hanya jika koordinat tersedia)
        if (reading.latitude && reading.longitude) {
            const sensorKey = reading.sensor_id;
            const latLng = [reading.latitude, reading.longitude];
            
            // Gunakan risk level per sensor jika ada, jika tidak, pakai status umum
            const currentSensorRisk = reading.risk_level || riskLevel; 

            // Hapus marker lama jika sudah ada
            if (sensorMarkers[sensorKey]) {
                map.removeLayer(sensorMarkers[sensorKey]);
            }
            
            // Buat marker baru
            const marker = L.marker(latLng, { 
                 icon: getMarkerIcon(currentSensorRisk)
            })
             .addTo(map)
             .bindPopup(`
                <b>Sensor ID: ${reading.sensor_id}</b><br>
                Level Air: ${reading.water_level} m<br>
                Curah Hujan: ${reading.rainfall} mm/h<br>
                Status Sensor: ${currentSensorRisk.toUpperCase()}<br>
                Waktu: ${reading.timestamp.substring(11, 19)}
             `);
            
            sensorMarkers[sensorKey] = marker; // Simpan marker baru
        }
    });
}


// --- 5. Inisialisasi Script ---

// Panggil fungsi pengambilan data setiap 5 detik
setInterval(fetchSensorData, 5000); 

// Jalankan pemanggilan data pertama kali
fetchSensorData();

// Muat layer WMS dari GeoServer
loadWMSLayer();