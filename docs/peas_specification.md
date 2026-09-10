# PEAS Specification

## 1. Performance Measure (P)

1. Total waktu evakuasi dari titik bahaya ke shelter (dalam menit).
2. Persentase warga yang berhasil mencapai shelter sebelum estimasi waktu tsunami tiba.
3. Minimisasi jarak tempuh rute (meter/km).
4. Minimisasi skor risiko kumulatif sepanjang rute (akumulasi bobot risiko jalur yang dilalui).
5. Tingkat distribusi beban jalur (menghindari satu jalur menampung terlalu banyak orang sekaligus).

## 2. Environment (E)

1. Jaringan jalan/jalur evakuasi Kota Banda Aceh (dimodelkan sebagai graf).
2. Sistem peringatan dini BMKG (waktu & estimasi kedatangan tsunami).
3. Data kondisi infrastruktur jalur secara real-time (rusak/aman).
4. Data kepadatan pejalan kaki/kendaraan per jalur.
5. Lokasi dan kapasitas shelter/titik kumpul evakuasi.

## 3. Actuators (A)

1. Menampilkan rekomendasi rute evakuasi ke warga (lewat aplikasi/notifikasi).
2. Melakukan reroute otomatis saat kondisi jalur berubah (rusak/padat).
3. Menandai/memperbarui status suatu jalur sebagai "tidak aman" di sistem.
4. Mengirim prioritas alert ke petugas lapangan di titik jalur kritis.

## 4. Sensors (S)

1. Lokasi awal/titik bahaya warga (GPS).
2. Status kondisi jalur real-time (dari laporan lapangan/sensor IoT/BPBD).
3. Data kepadatan lalu lintas per jalur.
4. Estimasi waktu kedatangan tsunami (dari BMKG).
5. Status okupansi/kapasitas shelter saat ini.

## 5. Analisis Sifat Lingkungan Tugas

### Partially Observable (bukan Fully Observable)
Agen tidak punya akses penuh ke seluruh kondisi kota secara real-time — status kerusakan
jalur, kepadatan warga di titik tertentu, atau posisi pasti setiap individu tidak selalu
tersedia secara instan/akurat. Agen bergantung pada sensor/laporan yang mungkin delay atau
tidak lengkap.

### Stochastic (bukan Deterministic)
Hasil dari suatu aksi tidak selalu pasti — misalnya rekomendasi rute yang diberikan bisa saja
tidak dipatuhi warga, atau kondisi jalur bisa berubah tiba-tiba (longsor susulan, kemacetan
mendadak) di luar prediksi model.

### Sequential (bukan Episodic)
Keputusan rute yang direkomendasikan di satu titik waktu memengaruhi kondisi (kepadatan,
ketersediaan shelter) untuk keputusan berikutnya — misalnya jika terlalu banyak warga
diarahkan ke satu jalur, itu memengaruhi rekomendasi untuk warga lain setelahnya. Keputusan
agen tidak berdiri sendiri per instance.

### Dynamic (bukan Static)
Lingkungan terus berubah selama agen "berpikir" — kondisi jalur, kepadatan, dan waktu tersisa
sebelum tsunami tiba terus bergerak, sehingga agen harus mempertimbangkan perubahan tersebut
secara berkelanjutan, bukan mengasumsikan dunia diam.

### Discrete (bukan Continuous)
Ruang state dimodelkan sebagai graf dengan node (titik/persimpangan/shelter) dan edge (segmen
jalur) yang terbatas jumlahnya — bukan ruang koordinat kontinu tak terhingga. Aksi agen
(memilih jalur berikutnya) juga berasal dari himpunan pilihan diskrit.

### Multi-agent
Terdapat banyak warga yang bergerak secara bersamaan dan saling memengaruhi (kepadatan jalur
dipengaruhi keputusan kolektif banyak individu), serta interaksi dengan petugas lapangan BPBD
yang juga mengambil tindakan di lingkungan yang sama.