import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, WMSTileLayer } from 'react-leaflet'; 
import 'leaflet/dist/leaflet.css'; 
// Asumsi: Backend API Anda sekarang mengembalikan semua 3 fitur yang dibutuhkan model.

// --- Konfigurasi URL API ---
const API_BASE_URL = process.env.REACT_APP_RAILWAY_API; 
const API_STATUS_URL = `${API_BASE_URL}/api/get_status`;

// --- Konfigurasi GeoServer (Silahkan diisi) ---
const GEOSERVER_WMS_URL = '[URL_GEOSERVER_ANDA]/wms'; 
const GEOSERVER_LAYER_NAME = '[WORKSPACE:LAYER_NAME_ANDA]'; 


// --- Komponen Utama Dashboard ---
const Dashboard = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  // Logika Fetching Data Status (Polling)
  const fetchDataStatus = async () => {
    try {
      const response = await fetch(API_STATUS_URL);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      
      // Catatan: Asumsi hasil API memiliki 3 fitur + status + timestamp
      // Contoh hasil: 
      // {
      //   "curah_hujan_mm_per_jam": 28.35, 
      //   "ketinggian_muka_air_meter": 4.616, 
      //   "debit_air_m3_per_detik": 55.2,
      //   "status": "Bahaya", 
      //   "timestamp": "2025-11-16T11:47:00.000000"
      // }
      
      setData(result);
      setError(null);
    } catch (err) {
      console.error("Gagal mengambil data status:", err);
      setError("Koneksi ke API Status Gagal. Pastikan REACT_APP_RAILWAY_API sudah benar."); 
    }
  };

  // Polling Status (Berjalan setiap 5 detik)
  useEffect(() => {
    fetchDataStatus(); 
    
    const intervalId = setInterval(() => {
      fetchDataStatus();
    }, 5000); 

    return () => clearInterval(intervalId); 
  }, []);

  if (error) {
    return <div className="min-h-screen p-8 flex items-center justify-center bg-red-100 text-red-700 text-center font-bold text-lg">{error}</div>;
  }
  if (!data) {
    return <div className="min-h-screen p-8 flex items-center justify-center text-center text-gray-500 text-xl">Memuat data real-time...</div>;
  }
  
  const timeFormatted = new Date(data.timestamp).toLocaleString('id-ID');
  
  return (
    <StatusDisplay data={data} timeFormatted={timeFormatted} />
  );
};

// --- Komponen Pembantu StatusDisplay ---
const StatusDisplay = ({ data, timeFormatted }) => {
    
    const getStatusClasses = (status) => {
        switch (status) {
            case 'Bahaya':
                return 'bg-red-600 text-white animate-pulse border-red-800'; 
            case 'Siaga':
                return 'bg-yellow-500 text-gray-900 border-yellow-700';
            case 'Aman':
            default:
                return 'bg-green-500 text-white border-green-700';
        }
    };
    
    const alertClasses = getStatusClasses(data.status);

    return (
        <div className="min-h-screen bg-gray-50 p-4 sm:p-8">
            <h1 className="text-4xl font-extrabold text-gray-800 mb-6">🔴 Dashboard Pemantauan Bencana Purwokerto</h1>

            {/* --- Alert Banner Interaktif --- */}
            <div className={`p-6 rounded-2xl shadow-2xl transition-all duration-500 ${alertClasses} border-b-8 mb-10`}>
                <h2 className="text-3xl font-extrabold flex items-center">
                    🚨 STATUS HASIL PREDIKSI: {data.status ? data.status.toUpperCase() : "N/A"}
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
                    statusAlert={data.status}
                />

                <DataCard 
                    title="Curah Hujan" 
                    value={data.curah_hujan_mm_per_jam} 
                    unit="mm/jam" 
                    color="text-blue-600"
                    statusAlert={data.status}
                />

                {/* Fitur Baru Sesuai Model ML */}
                <DataCard 
                    title="Debit Air" 
                    value={data.debit_air_m3_per_detik} 
                    unit="m³/detik" 
                    color="text-purple-600"
                    statusAlert={data.status}
                />
            </div>
            
            {/* --- Peta dengan GeoServer WMS --- */}
            <div className="bg-white p-6 rounded-2xl shadow-xl">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">📍 Peta Sebaran Sensor IoT</h2>
                <div className="w-full h-96 rounded-xl overflow-hidden">
                    <MapContainer center={[-7.420, 109.225]} zoom={12} className="w-full h-full">
                        <TileLayer
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                            attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
                        />
                        
                        {/* Layer GeoServer (WMS) */}
                        {GEOSERVER_WMS_URL !== '[URL_GEOSERVER_ANDA]/wms' && GEOSERVER_LAYER_NAME !== '[WORKSPACE:LAYER_NAME_ANDA]' && (
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

                        <Marker position={[-7.420, 109.225]}>
                            <Popup>
                                Titik Pusat Purwokerto. <br/> Layer GeoServer akan muncul di sini.
                            </Popup>
                        </Marker>

                    </MapContainer>
                </div>
            </div>

        </div>
    );
};

// --- Komponen Pembantu DataCard ---
const DataCard = ({ title, value, unit, color, statusAlert }) => {
    // Logika untuk highlight kartu saat Bahaya/Siaga
    const isCritical = statusAlert === 'Bahaya' || statusAlert === 'Siaga';
    const dynamicBorder = statusAlert === 'Bahaya' ? 'border-red-500' : isCritical ? 'border-yellow-500' : 'border-gray-200';
    
    return (
        <div className={`bg-white p-6 rounded-2xl shadow-xl transition-all duration-300 border-b-4 ${dynamicBorder} hover:shadow-2xl`}>
            <p className="text-lg font-semibold text-gray-500">{title}</p>
            {/* Menggunakan toFixed(2) untuk membulatkan tampilan nilai */}
            <p className={`text-6xl font-extrabold mt-1 ${color}`}>{parseFloat(value).toFixed(2)}</p>
            <p className="text-xl text-gray-600 mt-2">{unit}</p>
        </div>
    );
};


export default Dashboard;