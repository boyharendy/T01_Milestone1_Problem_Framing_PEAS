# Perancangan Sistem Rekomendasi Rute Evakuasi Tsunami Berbasis Agen Cerdas di BPBD Kota Banda Aceh

Proyek ini memodelkan jaringan evakuasi tsunami Kota Banda Aceh sebagai graf berbobot dan menghasilkan rekomendasi rute menuju shelter terdekat berdasarkan biaya operasional. Sistem menyediakan implementasi Uniform Cost Search (UCS), A* Search, pengujian otomatis, serta visualisasi jaringan dan perbandingan kinerja algoritma.

## Latar Belakang (Background)

Banda Aceh memiliki wilayah pesisir yang berisiko terhadap tsunami. Dalam situasi darurat, keputusan rute evakuasi perlu mempertimbangkan jarak, risiko jalur, kemacetan, kondisi jalan, serta ketersediaan shelter. Rute terpendek secara geografis belum tentu menjadi rute dengan biaya operasional dan risiko paling rendah.

Proyek ini dibuat sebagai prototipe agen cerdas untuk membantu proses rekomendasi rute evakuasi. Ruang masalah direpresentasikan sebagai graf yang berisi titik bahaya, persimpangan, dan shelter evakuasi. Setiap ruas jalan memiliki bobot biaya yang menggabungkan jarak fisik, faktor risiko, dan faktor kemacetan.

Tujuan utama sistem:

- Menemukan rute dengan biaya total minimum dari titik bahaya menuju shelter.
- Membandingkan UCS dan A* berdasarkan optimalitas dan jumlah simpul yang diekspansi.
- Memvalidasi bahwa heuristik A* bersifat admissible dan konsisten pada model graf.
- Menghasilkan visualisasi jaringan, skenario rute, dan benchmark untuk dokumentasi akademik.

Manfaat prototipe ini adalah menyediakan dasar teknis yang dapat dikembangkan menjadi sistem pendukung keputusan BPBD. Sistem belum menggantikan keputusan petugas lapangan dan belum terhubung ke sensor atau data operasional real-time.

## Arsitektur dan Penjelasan Kode (Code Explanation)

### Struktur Proyek

```text
T01_Milestone1_Problem_Framing_PEAS/
├── docs/
│   ├── peas_specification.md       # Matriks PEAS dan karakteristik lingkungan
│   └── problem_framing.md          # Konteks bisnis dan analisis masalah
├── output/                         # PNG hasil visualisasi
├── src/
│   ├── graph_model.py              # Model node, edge, dan graf evakuasi
│   ├── heuristics.py               # Heuristik Euclidean untuk A*
│   ├── search.py                   # UCS, A*, dan benchmark rute
│   └── visualize.py                # Pembuatan peta dan grafik kinerja
├── tests/
│   └── test_search.py              # Pengujian model, heuristik, dan algoritma
├── pyproject.toml                  # Metadata proyek dan dependensi
├── uv.lock                         # Versi dependensi yang terkunci
├── run_ai.py                       # Demo layanan AI opsional
└── README.md
```

### Model Ruang Keadaan

`EvacuationGraph` menyediakan antarmuka formal lima komponen ruang keadaan:

| Komponen | Implementasi | Keterangan |
| --- | --- | --- |
| `X` | `state_space` | Seluruh ID node yang terdaftar pada graf |
| `A` | `get_actions(state)` | Node tetangga yang dapat dicapai dari state saat ini |
| `T` | `transition(state, action)` | Transisi deterministik menuju node tujuan |
| `G` | `is_goal(state)` | True apabila state merupakan shelter |
| `C` | `get_step_cost(origin, destination)` | Biaya perpindahan pada satu ruas jalan |

Node menyimpan koordinat lokal, tipe lokasi, kapasitas shelter, dan deskripsi. Edge menyimpan jarak, faktor risiko, faktor kemacetan, dan status dapat dilalui. Biaya satu langkah dihitung dengan rumus:

```text
C(u, v) = distance_km * (1 + risk_factor) * (1 + congestion_factor)
```

Edge yang tidak dapat dilalui memiliki biaya tak hingga dan tidak dikembalikan sebagai aksi valid.

### Algoritma Pencarian

`src/search.py` menggunakan `heapq` sebagai priority queue.

- **UCS** memilih node dengan akumulasi biaya `g(n)` paling kecil. Pada graf dengan bobot positif, algoritma ini menjamin rute optimal.
- **A*** memilih node berdasarkan `f(n) = g(n) + h(n)`, dengan `g(n)` sebagai biaya aktual dan `h(n)` sebagai estimasi menuju shelter.
- `closest_shelter_heuristic` menggunakan jarak Euclidean minimum dari node ke shelter terdekat. Karena biaya ruas tidak lebih kecil daripada jarak fisik, heuristik ini digunakan sebagai lower bound.
- `SearchResult` mengembalikan rute, shelter tujuan, biaya total, jumlah node yang diekspansi, urutan ekspansi, dan waktu eksekusi.

Implementasi menggunakan pemeriksaan biaya terbaik (`best_costs` atau `best_g_costs`) untuk melewati entri priority queue yang sudah tidak optimal. Counter tambahan digunakan sebagai tie-breaker agar entri dengan prioritas sama tetap dapat diurutkan secara deterministik.

### Alur Eksekusi

1. `build_banda_aceh_graph()` membuat node, shelter, dan edge jaringan evakuasi.
2. Algoritma menerima ID titik awal, misalnya `Ulee_Lheue`.
3. Priority queue diinisialisasi dengan titik awal dan biaya nol.
4. Node dengan prioritas terbaik dikeluarkan dan diuji sebagai goal.
5. Tetangga yang dapat dilalui diekspansi, lalu biaya dan path terbaik diperbarui.
6. Proses berhenti saat shelter pertama dikeluarkan dari queue atau queue kosong.
7. Hasil dikemas sebagai `SearchResult` dan ditampilkan dalam format ringkasan.
8. Modul visualisasi menggunakan hasil UCS dan A* untuk menghasilkan tiga file PNG.

Tidak terdapat threading, IPC, atau sinkronisasi antarproses. Eksekusi bersifat sinkron dan deterministik terhadap data graf yang digunakan, sedangkan waktu eksekusi dapat berubah antar-run karena dipengaruhi kondisi mesin.

## Prasyarat dan Cara Menjalankan (Getting Started)

### Prasyarat Sistem

- Windows, Linux, atau macOS.
- Python 3.11 atau lebih baru.
- Git.
- `uv` untuk membuat environment dan memasang dependensi.
- Ruang disk yang cukup untuk environment Python dan dependensi Matplotlib.

Instalasi `uv` pada Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Instalasi Proyek

```powershell
git clone https://github.com/boyharendy/T01_Milestone1_Problem_Framing_PEAS.git
cd T01_Milestone1_Problem_Framing_PEAS
uv sync
```

`uv sync` membuat atau memperbarui `.venv` dan memasang dependensi berdasarkan `pyproject.toml` serta `uv.lock`.

### Menjalankan Rekomendasi Rute

```powershell
uv run python -m src.search
```

Perintah tersebut menjalankan empat skenario titik bahaya: `Ulee_Lheue`, `Lampulo`, `Peunayong`, dan `Cut_Mutia`, kemudian membandingkan UCS dengan A*.

Alternatif untuk menjalankan file secara langsung:

```powershell
uv run python src/search.py
```

### Menghasilkan Visualisasi

```powershell
uv run python -m src.visualize
```

Perintah tersebut membuat atau memperbarui:

- `output/peta_jaringan_evakuasi.png`
- `output/skenario_rute_evakuasi.png`
- `output/perbandingan_kinerja_ucs_vs_astar.png`

### Menjalankan Pengujian

```powershell
uv run pytest -v
```

Pengujian mencakup model graf, rumus biaya, goal test, admissibility dan konsistensi heuristik, optimalitas UCS dan A*, kasus titik awal yang sudah menjadi shelter, serta node terisolasi.

### Menjalankan Demo Layanan AI Opsional

```powershell
uv run python run_ai.py
```

Demo dapat berjalan dalam mode tanpa API key. Untuk mode Gemini, buat file `.env` berdasarkan `.env.example` dan isi API key sesuai konfigurasi layanan yang digunakan. API key tidak boleh di-commit ke repository.

## Hasil Eksekusi (Results)

Contoh hasil pengujian:

```text
============================= test session starts =============================
collected 13 items

tests/test_search.py::TestGraphModel::test_state_space_and_shelters PASSED
tests/test_search.py::TestHeuristics::test_heuristic_admissibility_all_nodes PASSED
tests/test_search.py::TestSearchAlgorithms::test_search_optimality_and_equivalence[Ulee_Lheue] PASSED
...
tests/test_search.py::TestSearchAlgorithms::test_edge_case_isolated_node PASSED

============================= 13 passed in 0.23s ================================
```

Setiap `PASSED` menunjukkan satu skenario valid. Pengujian optimalitas memastikan biaya rute UCS dan A* setara, sedangkan pengujian heuristik memastikan nilai estimasi tidak melebihi biaya optimal pada graf uji.

Contoh ringkasan keluaran pencarian:

```text
[A* Search (A-Star)] Ulee_Lheue -> Escape_Building_Lambung
  - Rute Evakuasi      : Ulee_Lheue -> Lambung_Junction -> Escape_Building_Lambung
  - Total Biaya Riil   : 3.8400
  - Simpul Diekspansi  : 4 simpul
  - Waktu Eksekusi     : 0.0xx ms
```

Biaya total adalah akumulasi biaya operasional setiap edge, bukan jarak fisik semata. Jumlah simpul yang diekspansi digunakan untuk membandingkan efisiensi pencarian; waktu eksekusi bersifat informatif dan dapat berbeda pada setiap komputer.

Visualisasi menyajikan node bahaya, persimpangan, shelter, edge jaringan, rute A*, dan perbandingan jumlah ekspansi UCS terhadap A*. File PNG pada `output/` dapat digunakan dalam laporan atau presentasi.

## Analisis dan Evaluasi (Review and Future Improvements)

### Evaluasi Implementasi Saat Ini

- **Optimalitas:** UCS menghasilkan rute minimum berdasarkan biaya edge positif. A* menghasilkan biaya yang sama dengan UCS pada pengujian karena menggunakan heuristik admissible.
- **Efisiensi:** A* dapat mengurangi jumlah node yang diekspansi karena prioritasnya diarahkan oleh estimasi jarak ke shelter. Keuntungan aktual bergantung pada bentuk graf dan kualitas heuristik.
- **Kompleksitas:** Dengan priority queue, proses pencarian secara umum memiliki biaya sekitar `O((V + E) log V)` untuk graf berbobot, dengan `V` sebagai jumlah node dan `E` sebagai jumlah edge. Penyimpanan path pada setiap entri queue meningkatkan penggunaan memori dibandingkan menyimpan predecessor saja.
- **Keterbatasan data:** Graf dan bobot saat ini merupakan data pemodelan statis. Sistem belum menerima GPS warga, laporan kerusakan, kepadatan lalu lintas, peringatan BMKG, atau okupansi shelter secara real-time.
- **Keterbatasan model:** Faktor risiko dan kemacetan dirangkum dalam bobot sederhana. Kapasitas shelter belum menjadi constraint pencarian dan belum ada optimasi distribusi banyak kelompok warga.
- **Keterbatasan validasi:** Test suite memvalidasi algoritma dan model, tetapi belum menguji integrasi dengan API eksternal, ketahanan terhadap data sensor yang tidak lengkap, atau performa pada graf skala kota yang besar.

### Pengembangan Berikutnya

1. Integrasikan sumber data real-time untuk status jalan, kepadatan, peringatan tsunami, dan kapasitas shelter.
2. Tambahkan validasi skema input serta penanganan data sensor yang hilang, terlambat, atau tidak konsisten.
3. Gunakan predecessor map untuk mengurangi duplikasi penyimpanan path pada priority queue.
4. Tambahkan constraint kapasitas shelter dan model multi-agent untuk mencegah penumpukan warga pada satu rute.
5. Kembangkan API atau antarmuka peta untuk menampilkan rekomendasi berdasarkan lokasi GPS pengguna.
6. Tambahkan benchmark pada graf yang lebih besar serta continuous integration untuk menjalankan test otomatis pada setiap pull request.
7. Kalibrasikan bobot risiko dan kemacetan menggunakan data historis BPBD agar biaya rute lebih representatif.

## Lisensi

Proyek ini didistribusikan berdasarkan lisensi MIT. Lihat file [LICENSE](LICENSE) untuk detail selengkapnya.
