// Koordinat Pusat Kabupaten Bandung (Placeholder)
const BANDUNG_CENTER = [-6.9219, 107.6105];
const API_READINGS_URL = "http://192.168.1.58:8000/api/readings"; // Endpoint GET API Anda

// 1. Inisialisasi Peta
const map = L.map('mapid').setView(BANDUNG_CENTER, 11);

// Muat Basemap (OpenStreetMap)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// 2. Logika Peta (Untuk Layer WMS Radith)
// Fungsi ini akan dipanggil setelah Radith selesai setup GeoServer
function loadWMSLayer(map) {
    // URL ini akan diganti oleh Radith
    L.tileLayer.wms('http://[RADITH_GEOSERVER_IP]:[PORT]/geoserver/wms', {
        layers: 'workspace:area_rawan_dummy', 
        format: 'image/png',
        transparent: true,
        attribution: 'EWS Project'
    }).addTo(map);
}

let sensorMarkers = {}; // Untuk menyimpan marker yang sudah ada

// 3. Fungsi Pemanggilan API ke Backend Anda (Port 8000)
async function fetchSensorData() {
    try {
        const response = await fetch(API_READINGS_URL);
        if (!response.ok) {
            // Jika API Flask crash (error 500)
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

// 4. Fungsi untuk Memperbarui Panel Dashboard dan Peta
function updateDashboard(readings, riskLevel) {
    document.getElementById('status-text').textContent = `Status: ${riskLevel}`;
    document.getElementById('status-text').className = riskLevel === 'WASPADA' ? 'text-red-600 font-bold' : 'text-green-600';

    const list = document.getElementById('sensor-data-list');
    list.innerHTML = ''; 

    // Loop data terbaru
    readings.forEach(reading => {
        // Update list
        const listItem = document.createElement('li');
        listItem.textContent = `Sensor ${reading.sensor_id}: Level ${reading.water_level}m (${reading.timestamp.substring(11, 16)})`;
        list.appendChild(listItem);
        
        // Update Peta
        const sensorKey = reading.sensor_id;
        
        if (reading.latitude && reading.longitude) {
            const latLng = [reading.latitude, reading.longitude];
            
            // Hapus marker lama jika sudah ada
            if (sensorMarkers[sensorKey]) {
                map.removeLayer(sensorMarkers[sensorKey]);
            }
            
            // Buat marker baru
            const marker = L.marker(latLng)
             .addTo(map)
             .bindPopup(`
                <b>Sensor ID: ${reading.sensor_id}</b><br>
                Level Air: ${reading.water_level} m<br>
                Curah Hujan: ${reading.rainfall} mm/h<br>
                Waktu: ${reading.timestamp.substring(11, 19)}
             `);
            
            sensorMarkers[sensorKey] = marker; // Simpan marker baru
        }
    });
}

// Panggil fungsi pengambilan data setiap 5 detik
setInterval(fetchSensorData, 5000); 

// Jalankan pemanggilan data pertama kali
fetchSensorData();

// loadWMSLayer(map); // Nonaktifkan, tunggu setup GeoServer Radith