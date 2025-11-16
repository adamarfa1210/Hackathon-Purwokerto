import React from 'react';
import ReactDOM from 'react-dom/client';
import Dashboard from './Dashboard.jsx'; // Mengimpor komponen utama

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {/* Menggunakan Dashboard.jsx sebagai aplikasi utama */}
    <Dashboard /> 
  </React.StrictMode>
);