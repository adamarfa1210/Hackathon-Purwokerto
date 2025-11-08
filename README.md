Tentu. Saya akan membuatkan ulang *file* `README.md` yang berisi semua informasi penting mengenai konfigurasi *deployment* Docker dan pembagian tugas tim Anda.

Berikut adalah *content* `README.md` yang dapat Anda gunakan. Setelah ini, Anda bisa langsung membuat dan *push* *file* ini ke GitHub.

-----

## 📄 `README.md` - Panduan Proyek EWS

# Sistem Peringatan Dini Banjir (EWS) Geospatial

Dokumen ini berisi informasi penting mengenai konfigurasi *backend* (Docker), akses *database*, dan pembagian tugas tim untuk memastikan kolaborasi berjalan lancar.

-----

## 🌐 Informasi Akses dan Konfigurasi Jaringan

Semua layanan berjalan di Virtual Machine (VM) Ubuntu, yang dapat diakses dari host Windows (komputer utama) Anda.

| Komponen | Akses dari Host (Windows) | Port Internal Container | Keterangan |
| :--- | :--- | :--- | :--- |
| **IP VM Ubuntu** | `192.168.1.14` | N/A | IP Statis untuk komunikasi Host \<-\> VM. |
| **API Ingestion** | `http://192.168.1.14:8000/api/ingest` | `8000` | *Endpoint* untuk mengirim data sensor (`POST` Request). |
| **Database PostGIS** | `192.168.1.14:5432` | `5432` | Koneksi untuk QGIS, DBeaver, atau *tools* DB lainnya. |

### Kredensial Database (Service `database`)

| Parameter | Nilai |
| :--- | :--- |
| Host | `database` (Hanya dari *container* lain) |
| Host | `192.168.1.14` (Dari **Host / QGIS**) |
| Port | `5432` |
| User | `user` |
| Password | `password` |
| Database | `mydb` |

-----

## 👥 Pembagian Tugas dan Software Kerja

Proyek ini dibagi menjadi tiga *stream* utama. Semua anggota tim diharapkan selalu melakukan `git pull origin main` sebelum memulai sesi kerja dan `git push origin main` setelah menyelesaikan tugas.

| Anggota Tim | Peran | Tugas Utama | Software/Akses | Port Terkait |
| :--- | :--- | :--- | :--- | :--- |
| **[Nama Anda]** | Backend & Frontend Integrator | Membangun dan menjaga stabilitas Docker dan API Ingestion. Mengembangkan *Frontend* (UI) untuk visualisasi. | Terminal (Docker, Git), Code Editor (Frontend) | **8000** (API) |
| **Radith** | Geospatial Analyst | Mengkoneksikan DB PostGIS ke QGIS. Membuat peta dasar, melakukan geoprocessing, dan visualisasi spasial. | **QGIS**, Koneksi DB (`192.168.1.14:5432`) | **5432** |
| **Jodi** | Machine Learning Engineer | Mengembangkan model **Early Warning System (EWS)** dan logika peringatan berbasis *threshold* atau ML. | Python Environment, Database Client (Opsional) | **5432** |

-----

## ⚙️ Cara Menjalankan Layanan (VM Ubuntu)

Pastikan Anda berada di direktori `docker-project` dan *file* `docker-compose.yml` sudah menggunakan *image* **`postgis/postgis:14-master`** untuk layanan *database*.

1.  **Pull Kode Terbaru:**
    ```bash
    git pull origin main
    ```
2.  **Jalankan Docker Compose (Build dan Deploy):**
    ```bash
    sudo docker compose up -d --build
    ```
3.  **Hentikan Layanan:**
    ```bash
    sudo docker compose down
    ```
