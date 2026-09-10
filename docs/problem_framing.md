# Problem Framing

## 1. Profil Domain Bisnis

BPBD Kota Banda Aceh adalah instansi pemerintah daerah yang bertanggung jawab atas mitigasi
dan penanggulangan bencana di Kota Banda Aceh, wilayah pesisir dengan risiko gempa dan
tsunami tinggi mengingat sejarah bencana tsunami 2004. Instansi ini mengoperasikan sistem
peringatan dini berupa sirene yang tersebar di beberapa titik kota, seperti kawasan Jalan Cut
Mutia, Taman Putroe Phang, Kantor Camat Baiturrahman, Indrapuri, Keutapang, hingga Kilometer
Nol, serta menyediakan peta jalur evakuasi tsunami yang dibagi ke dalam beberapa sektor
wilayah kota (Sektor A hingga E).

> **Catatan akademik:** profil dan fakta EWS/peta evakuasi sektor di atas merujuk pada sumber
> publik BPBD/BNPB/JICA. Detail proses internal spesifik dan data numerik (jumlah penduduk
> per sektor, kapasitas shelter, dll.) yang belum tersedia di sumber publik diasumsikan secara
> wajar untuk keperluan pemodelan PEAS dan graf pada milestone berikutnya.

## 2. Alur Proses Saat Ini (As-Is)

1. Sensor gempa/BMKG mendeteksi potensi tsunami → BPBD Kota Banda Aceh menerima peringatan dini.
2. Petugas mengaktifkan sirene EWS di titik-titik yang tersebar di kota.
3. Warga merujuk pada peta evakuasi statis per sektor untuk menentukan arah evakuasi ke
   shelter/dataran tinggi terdekat.
4. Peta bersifat statis dan sama untuk semua kondisi — tidak ada mekanisme yang menyesuaikan
   rekomendasi rute secara real-time berdasarkan kondisi terkini (jalur rusak, kepadatan massa,
   dsb.).
5. Petugas lapangan berkoordinasi secara manual/reaktif saat muncul kendala di lapangan
   (kemacetan, jalur terputus). BPBD juga secara rutin menguji sirene EWS dan kesiapan jalur
   evakuasi melalui simulasi tahunan Hari Kesiapsiagaan Bencana (HKB), namun ini bersifat
   latihan berkala, bukan sistem rekomendasi rute adaptif yang berjalan real-time.

## 3. Pain Points

1. **Rekomendasi rute bersifat statis, bukan real-time** — peta jalur evakuasi per sektor
   memberi panduan umum, tapi tidak menyesuaikan dengan kondisi aktual saat bencana terjadi.
2. **Tidak ada personalisasi rute berdasarkan lokasi individu** — warga dalam satu sektor bisa
   punya rute optimal berbeda tergantung kepadatan real-time, namun peta statis seragam.
3. **Potensi penumpukan massa di jalur populer** — tanpa distribusi rute berbasis kepadatan,
   banyak warga memilih jalur yang sama, menyebabkan bottleneck saat evakuasi massal.
4. **Risiko jalur dinamis tidak terdeteksi otomatis** — jalur rusak pascagempa (retak, longsor,
   runtuh) tidak ter-update di peta/rekomendasi, berisiko mengarahkan warga ke jalur berbahaya.
5. **Ketergantungan pada kesiapsiagaan manual** — begitu bencana nyata terjadi, keputusan rute
   tetap diambil manual oleh tiap individu tanpa bantuan rekomendasi cerdas, padahal waktu
   evakuasi tsunami hanya terhitung belasan menit.

## 4. Justifikasi AI (Search-based Agent)

Proses manual saat ini (sirene + peta statis) tidak mampu memproses secara simultan tiga
variabel kritis — jarak, risiko jalur, dan kepadatan — untuk merekomendasikan rute yang
dipersonalisasi per lokasi warga dalam hitungan detik. Agen cerdas berbasis algoritma
pencarian (search-based agent) dapat memodelkan jaringan jalur evakuasi sebagai graf berbobot
dan secara otomatis menghitung rute teraman-tercepat dari titik bahaya ke shelter terdekat,
memperbarui rekomendasi begitu ada perubahan kondisi jalur — sesuatu yang mustahil dilakukan
secara manual oleh petugas dalam skala kota dan dalam waktu yang sangat terbatas.