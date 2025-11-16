import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, WMSTileLayer } from 'react-leaflet'; 
import L from 'leaflet'; // Import Leaflet untuk ikon kustom dan marker
import 'leaflet/dist/leaflet.css'; 

// --- 1. Konfigurasi Global ---
const API_BASE_URL = process.env.REACT_APP_RAILWAY_API; 
// PERINGATAN: Ganti endpoint IP lokal ini dengan endpoint publik Anda di Railway!
const API_READINGS_URL = `${API_BASE_URL}/api/readings`;

// Konfigurasi GeoServer (HARAP DIISI SECARA MANUAL)
const GEOSERVER_WMS_URL = '[URL_GEOSERVER_ANDA]/wms'; 
const GEOSERVER_LAYER_NAME = '[WORKSPACE:LAYER_NAME_ANDA]'; 

const CENTER_COORDS = [-6.9219, 107.6105]; // Koordinat Pusat (Bandung, placeholder)


// --- 2. Fungsi Pembantu: Ikon Marker Dinamis ---
const getMarkerIcon = (riskLevel) => {
    let color = 'blue'; 
    const normalizedRisk = riskLevel ? riskLevel.toUpperCase() : 'AMAN';

    if (normalizedRisk === 'AMAN') {
        color = 'green';
    } else if (normalizedRisk === 'WASPADA' || normalizedRisk === 'SIAGA') {
        color = 'orange';
    } else if (normalizedRisk === 'BAHAYA') {
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


// --- 3. Komponen Utama Dashboard ---
const Dashboard = () => {
  // State Data Status Utama (ML)
  const [data, setData] = useState(null); // Data ML utama (ketinggian, curah hujan, debit)
  const [error, setError] = useState(null);
  
  // State Data Readings Sensor (Untuk Marker Peta)
  const [sensorReadings, setSensorReadings] = useState([]);
  const [overallRisk, setOverallRisk] = useState("LOADING");

  // Logika Fetching Data Sensor (Polling)
  const fetchSensorData = async () => {
    try {
      const response = await fetch(API_READINGS_URL); 
      
      if (!response.ok) {
        throw new Error(`HTTP error! status ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.status === 'success') {
          // --- ASUMSI PEMISAHAN DATA ---
          // Kita asumsikan data ML utama adalah yang terbaru dari readings[0]
          // dan status keseluruhan dari current_risk
          
          if (result.readings && result.readings.length > 0) {
              const latestReading = result.readings[0];
              // Map data readings ke format data ML (asumsi fieldnya sama)
              setData({
                  curah_hujan_mm_per_jam: latestReading.rainfall,
                  ketinggian_muka_air_meter: latestReading.water_level,
                  debit_air_m3_per_detik: latestReading.debit_air || 0, // Tambahkan debit_air jika ada
                  status: result.current_risk, // Status hasil ML/Logika
                  timestamp: latestReading.timestamp
              });
          }
          
          setSensorReadings(result.readings || []);
          setOverallRisk(result.current_risk || "AMAN");

      } else {
        setError(`Kesalahan Data: ${result.message}`);
      }

    } catch (err) {
      setError("Kesalahan Koneksi ke API Readings. Periksa IP/URL.");
      console.error("Error fetching data:", err);
    }
  };

  // Polling Data Sensor (Berjalan setiap 5 detik)
  useEffect(() => {
    fetchSensorData(); 
    
    const intervalId = setInterval(() => {
      fetchSensorData();
    }, 5000); 

    return () => clearInterval(intervalId); 
  }, []);

  
  // --- Tampilan Peta dan Dashboard ---
  if (error) {
    return <div className="min-h-screen p-8 flex items-center justify-center bg-red-100 text-red-700 text-center font-bold text-lg">{error}</div>;
  }
  if (!data) { 
    return <div className="min-h-screen p-8 flex items-center justify-center text-center text-gray-500 text-xl">Memuat data real-time...</div>;
  }
  
  const timeFormatted = new Date(data.timestamp).toLocaleString('id-ID');
  
  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-8">
      
      {/* --- Komponen StatusDisplay (Menggunakan data ML utama) --- */}
      <StatusDisplay data={data} timeFormatted={timeFormatted} overallRisk={overallRisk} />
      
      
      {/* --- Peta dengan GeoServer WMS dan Sensor Markers --- */}
      <div className="bg-white p-6 rounded-2xl shadow-xl">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">📍 Peta Sebaran Sensor IoT</h2>
          <div className="w-full h-96 rounded-xl overflow-hidden">
              <MapContainer center={CENTER_COORDS} zoom={11} className="w-full h-full">
                  <TileLayer
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
                  />
                  
                  {/* WMS Layer (GeoServer) */}
                  {GEOSERVER_WMS_URL && GEOSERVER_LAYER_NAME && GEOSERVER_WMS_URL.includes('/wms') && (
                      <WMSTileLayer
                          url={GEOSERVER_WMS_URL} 
                          layers={GEOSERVER_LAYER_NAME} 
                          format="image/png"
                          transparent={true}
                          version="1.1.0"
                          opacity={0.8}
                          zIndex={100}
                      />
                  )}

                  {/* Menampilkan Markers Sensor berdasarkan state sensorReadings */}
                  {sensorReadings.map((reading, index) => (
                      <Marker 
                          key={reading.sensor_id || index} 
                          position={[reading.latitude, reading.longitude]}
                          icon={getMarkerIcon(reading.risk_level || overallRisk)}
                      >
                          <Popup>
                              <b>Sensor ID: {reading.sensor_id}</b><br/>
                              Level Air: {reading.water_level} m<br/>
                              Curah Hujan: {reading.rainfall} mm/h<br/>
                              Status Sensor: {(reading.risk_level || overallRisk).toUpperCase()}
                          </Popup>
                      </Marker>
                  ))}

              </MapContainer>
          </div>
      </div>
    </div>
  );
};


// --- Komponen Pembantu StatusDisplay (Menggunakan data ML utama) ---
const StatusDisplay = ({ data, timeFormatted, overallRisk }) => {
    
    const getStatusClasses = (status) => {
        switch (status ? status.toUpperCase() : 'AMAN') {
            case 'BAHAYA':
                return 'bg-red-600 text-white animate-pulse border-red-800'; 
            case 'SIAGA':
            case 'WASPADA':
                return 'bg-yellow-500 text-gray-900 border-yellow-700';
            case 'AMAN':
            default:
                return 'bg-green-500 text-white border-green-700';
        }
    };
    
    const alertClasses = getStatusClasses(overallRisk);

    return (
        <>
            {/* --- Alert Banner Interaktif --- */}
            <div className={`p-6 rounded-2xl shadow-2xl transition-all duration-500 ${alertClasses} border-b-8 mb-10`}>
                <h2 className="text-3xl font-extrabold flex items-center">
                    🚨 STATUS HASIL PREDIKSI: {overallRisk.toUpperCase()}
                </h2>
                <p className="mt-2 text-md opacity-90">Data terakhir diperbarui: {timeFormatted}</p>
            </div>
            
            {/* --- Kartu Data Dinamis (Sesuai 3 Fitur Model) --- */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
                
                <DataCard 
                    title="Ketinggian Air" 
                    value={data.ketinggian_muka_air_meter} 
                    unit="meter" 
                    color="text-teal-600"
                    statusAlert={overallRisk}
                />

                <DataCard 
                    title="Curah Hujan" 
                    value={data.curah_hujan_mm_per_jam} 
                    unit="mm/jam" 
                    color="text-blue-600"
                    statusAlert={overallRisk}
                />

                <DataCard 
                    title="Debit Air" 
                    value={data.debit_air_m3_per_detik} 
                    unit="m³/detik" 
                    color="text-purple-600"
                    statusAlert={overallRisk}
                />
            </div>
        </>
    );
};

// --- Komponen Pembantu DataCard ---
const DataCard = ({ title, value, unit, color, statusAlert }) => {
    const isCritical = statusAlert === 'BAHAYA' || statusAlert === 'SIAGA' || statusAlert === 'WASPADA';
    const dynamicBorder = statusAlert === 'BAHAYA' ? 'border-red-500' : isCritical ? 'border-yellow-500' : 'border-gray-200';
    
    return (
        <div className={`bg-white p-6 rounded-2xl shadow-xl transition-all duration-300 border-b-4 ${dynamicBorder} hover:shadow-2xl`}>
            <p className="text-lg font-semibold text-gray-500">{title}</p>
            <p className={`text-6xl font-extrabold mt-1 ${color}`}>{parseFloat(value).toFixed(2)}</p>
            <p className="text-xl text-gray-600 mt-2">{unit}</p>
        </div>
    );
};


export default Dashboard;