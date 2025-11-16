import React from 'react';
import ReactDOM from 'react-dom/client';
import Dashboard from './Dashboard.jsx';

// --- TAMBAHKAN KODE INI UNTUK MEMBATALKAN PENDAFTARAN SERVICE WORKER ---
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.ready.then(registration => {
    registration.unregister();
  });
}
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {/* Menggunakan Dashboard.jsx sebagai aplikasi utama */}
    <Dashboard /> 
  </React.StrictMode>
);