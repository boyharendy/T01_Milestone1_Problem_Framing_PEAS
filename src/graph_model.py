"""Pemodelan Graf Masalah Bisnis & Formulasi Ruang Keadaan Formal (5-Tupel).

Studi Kasus: Sistem Rekomendasi Rute Evakuasi Tsunami BPBD Kota Banda Aceh.
Berdasarkan Analisis Problem Framing & Matriks PEAS (Bab 1 & Bab 2).

Formulasi Formal 5-Tupel:
1. X (State Space):
   Himpunan diskrit seluruh titik lokasi geografis di Kota Banda Aceh
   (zona bahaya pesisir, persimpangan jalan utama, dan gedung shelter evakuasi).
2. A (Action Space):
   Himpunan aksi transisi berpindah dari state saat ini (u) ke titik tetangga (v)
   yang terhubung langsung oleh segmen jalan valid: A(u) = {MoveTo(v) | (u,v) in E}.
3. T (Transition Model):
   Fungsi transisi deterministik snapshot: T(u, MoveTo(v)) = v.
4. G (Goal Test):
   Predikat logis penentu keselamatan evakuasi: G(u) = True jika u in SHELTERS.
5. C (Path Cost / Step Cost):
   Biaya transisi berbasis metrik operasional riil yang mengintegrasikan jarak fisik,
   skor risiko jalur bencana, dan faktor kemacetan/kepadatan:
   C(u, v) = distance_km * (1 + risk_factor) * (1 + congestion_factor).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional


@dataclass
class Node:
    """Representasi sebuah simpul (node) pada jaringan evakuasi Banda Aceh."""
    id: str
    name: str
    x: float  # Koordinat lokal X (dalam km)
    y: float  # Koordinat lokal Y (dalam km)
    node_type: str  # 'hazard', 'intersection', atau 'shelter'
    capacity: Optional[int] = None  # Kapasitas penampungan orang (jika shelter)
    description: str = ""


@dataclass
class Edge:
    """Representasi sisi berbobot (weighted edge) antar simpul jalur evakuasi."""
    origin: str
    destination: str
    distance_km: float
    risk_factor: float = 0.0        # Bobot risiko (0.0 = aman, 1.0 = risiko tsunami/reruntuhan sangat tinggi)
    congestion_factor: float = 0.0  # Bobot kemacetan (0.0 = lancar, 1.0 = padat merayap)
    is_passable: bool = True        # Status keterbukaan jalur (False jika jembatan runtuh/tertutup)

    @property
    def cost(self) -> float:
        """Menghitung biaya transisi riil (Step Cost C) sesuai rumusan PEAS.
        
        Formula:
            C(u, v) = distance_km * (1 + risk_factor) * (1 + congestion_factor)
        
        Catatan Matematis:
            Karena risk_factor >= 0 dan congestion_factor >= 0, maka:
            C(u, v) >= distance_km (tidak pernah lebih kecil dari jarak fisik jalan).
        """
        if not self.is_passable:
            return float('inf')
        return self.distance_km * (1.0 + self.risk_factor) * (1.0 + self.congestion_factor)


class EvacuationGraph:
    """Struktur data graf jaringan evakuasi berbasis adjacency list.
    
    Menyediakan antarmuka formal 5-tupel (X, A, T, G, C) untuk algoritma penelusuran.
    """

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.adjacency: Dict[str, List[Edge]] = {}
        self.shelters: Set[str] = set()

    def add_node(self, node: Node) -> None:
        """Menambahkan simpul baru ke dalam graf."""
        self.nodes[node.id] = node
        if node.id not in self.adjacency:
            self.adjacency[node.id] = []
        if node.node_type == 'shelter':
            self.shelters.add(node.id)

    def add_edge(
        self,
        origin: str,
        destination: str,
        distance_km: float,
        risk_factor: float = 0.0,
        congestion_factor: float = 0.0,
        bidirectional: bool = True,
        is_passable: bool = True
    ) -> None:
        """Menambahkan sisi berbobot ke dalam graf."""
        if origin not in self.nodes or destination not in self.nodes:
            raise ValueError(f"Simpul {origin} atau {destination} belum terdaftar pada graf.")

        edge = Edge(
            origin=origin,
            destination=destination,
            distance_km=distance_km,
            risk_factor=risk_factor,
            congestion_factor=congestion_factor,
            is_passable=is_passable
        )
        self.adjacency[origin].append(edge)

        if bidirectional:
            reverse_edge = Edge(
                origin=destination,
                destination=origin,
                distance_km=distance_km,
                risk_factor=risk_factor,
                congestion_factor=congestion_factor,
                is_passable=is_passable
            )
            self.adjacency[destination].append(reverse_edge)

    # -------------------------------------------------------------------------
    # ANTARMUKA FORMAL 5-TUPEL (X, A, T, G, C)
    # -------------------------------------------------------------------------

    @property
    def state_space(self) -> Set[str]:
        """Tupel 1 - X (State Space): Himpunan seluruh simpul/titik lokasi yang valid."""
        return set(self.nodes.keys())

    def get_actions(self, state: str) -> List[str]:
        """Tupel 2 - A (Action Space): Himpunan aksi transisi yang dapat dieksekusi dari state u."""
        if state not in self.adjacency:
            return []
        # Aksi yang valid adalah menuju simpul tetangga yang jalurnya dapat dilalui (passable)
        return [edge.destination for edge in self.adjacency[state] if edge.is_passable]

    def transition(self, state: str, action: str) -> str:
        """Tupel 3 - T (Transition Model): Hasil deterministik dari aksi MoveTo(action)."""
        valid_actions = self.get_actions(state)
        if action not in valid_actions:
            raise ValueError(f"Aksi MoveTo({action}) tidak valid dari state {state}")
        return action

    def is_goal(self, state: str) -> bool:
        """Tupel 4 - G (Goal Test): Menguji apakah state saat ini merupakan shelter aman."""
        return state in self.shelters

    def get_step_cost(self, origin: str, destination: str) -> float:
        """Tupel 5 - C (Path Cost / Step Cost): Biaya riil transisi dari u ke v."""
        if origin not in self.adjacency:
            return float('inf')
        for edge in self.adjacency[origin]:
            if edge.destination == destination:
                return edge.cost
        return float('inf')

    def get_edge(self, origin: str, destination: str) -> Optional[Edge]:
        """Mengambil objek Edge antara dua simpul jika ada."""
        if origin not in self.adjacency:
            return None
        for edge in self.adjacency[origin]:
            if edge.destination == destination:
                return edge
        return None


def build_banda_aceh_graph() -> EvacuationGraph:
    """Membangun pemodelan graf jaringan evakuasi Kota Banda Aceh.
    
    Data diturunkan dari dokumen Problem Framing & PEAS BPBD Kota Banda Aceh:
    - Zona Bahaya Pesisir: Ulee Lheue, Lampulo, Peunayong, Cut Mutia.
    - Persimpangan / Waypoint: Simpang Lima, Simpang Jam, Taman Putroe Phang, 
      Kantor Camat Baiturrahman, Keutapang.
    - Gedung Evakuasi (Shelters): Escape Building Lambung, Escape Building Alue Deah,
      Museum Tsunami, Dataran Tinggi Mata Ie.
    """
    g = EvacuationGraph()

    # 1. Inisialisasi Simpul (Nodes) dengan koordinat lokal km (X, Y)
    nodes_data = [
        # --- Zona Pesisir / Titik Bahaya (Hazard Points) ---
        Node(
            id="Ulee_Lheue",
            name="Pelabuhan Ulee Lheue (Pesisir Pantai)",
            x=0.5, y=8.0,
            node_type="hazard",
            description="Zona merah pesisir pantai barat daya, paparan gelombang tsunami langsung."
        ),
        Node(
            id="Lampulo",
            name="Pelabuhan Perikanan Lampulo",
            x=6.5, y=9.5,
            node_type="hazard",
            description="Zona pesisir timur laut, rawan hempasan gelombang muara sungai."
        ),
        Node(
            id="Peunayong",
            name="Kawasan Komersial Peunayong",
            x=5.5, y=7.5,
            node_type="hazard",
            description="Kawasan padat pertokoan dekat aliran Krueng Aceh."
        ),
        Node(
            id="Cut_Mutia",
            name="Kawasan Jalan Cut Mutia",
            x=4.8, y=7.0,
            node_type="hazard",
            description="Pusat kota lama pesisir dengan sirene EWS aktif."
        ),

        # --- Persimpangan / Titik Transit Evakuasi (Intersections) ---
        Node(
            id="Alue_Deah_Junction",
            name="Simpang Alue Deah Teungoh",
            x=1.5, y=8.5,
            node_type="intersection",
            description="Persimpangan pesisir barat menuju shelter Alue Deah."
        ),
        Node(
            id="Lambung_Junction",
            name="Simpang Gampong Lambung",
            x=1.5, y=7.2,
            node_type="intersection",
            description="Persimpangan evakuasi menuju Escape Building Lambung."
        ),
        Node(
            id="Simpang_Lima",
            name="Simpang Lima Banda Aceh",
            x=5.8, y=6.2,
            node_type="intersection",
            description="Titik simpul protokol utama penghubung timur dan barat kota."
        ),
        Node(
            id="Simpang_Jam",
            name="Simpang Jam Banda Aceh",
            x=4.5, y=5.2,
            node_type="intersection",
            description="Persimpangan cagar budaya sentral dekat Taman Putroe Phang."
        ),
        Node(
            id="Taman_Putroe_Phang",
            name="Kawasan Taman Putroe Phang",
            x=3.8, y=4.8,
            node_type="intersection",
            description="Ruang terbuka hijau perantara dan lokasi sirene EWS."
        ),
        Node(
            id="Kantor_Camat_Baiturrahman",
            name="Kantor Camat Baiturrahman",
            x=4.8, y=4.2,
            node_type="intersection",
            description="Pusat administrasi kecamatan dengan pemancar sirene EWS."
        ),
        Node(
            id="Keutapang",
            name="Simpang Keutapang Dua",
            x=4.0, y=2.0,
            node_type="intersection",
            description="Persimpangan selatan pembagi arus menuju perbukitan Mata Ie."
        ),

        # --- Gedung Evakuasi / Titik Aman (Designated Shelters - Goal States) ---
        Node(
            id="Escape_Building_Lambung",
            name="Gedung Evakuasi Tsunami (TES) Lambung",
            x=1.8, y=7.5,
            node_type="shelter",
            capacity=1200,
            description="Shelter vertikal 4 lantai konstruksi tahan gempa & tsunami JICA."
        ),
        Node(
            id="Escape_Building_Alue_Deah",
            name="Gedung Evakuasi Tsunami Alue Deah Teungoh",
            x=2.2, y=8.8,
            node_type="shelter",
            capacity=1000,
            description="Shelter evakuasi vertikal zona pesisir barat laut."
        ),
        Node(
            id="Museum_Tsunami",
            name="Museum Tsunami Banda Aceh (Escape Hill)",
            x=4.3, y=5.0,
            node_type="shelter",
            capacity=3500,
            description="Gedung monumen mitigasi bencana dengan atap evakuasi darurat."
        ),
        Node(
            id="Dataran_Tinggi_Mata_Ie",
            name="Dataran Tinggi Perbukitan Mata Ie",
            x=3.5, y=0.0,
            node_type="shelter",
            capacity=20000,
            description="Zona topografi tinggi alami di selatan kota, aman permanen dari hempasan tsunami."
        )
    ]

    for node in nodes_data:
        g.add_node(node)

    # 2. Inisialisasi Sisi Berbobot (Edges)
    # Param: (origin, destination, distance_km, risk_factor, congestion_factor)
    # risk_factor: 0.0 (aman) s/d 1.0 (sangat rawan genangan/reruntuhan)
    # congestion_factor: 0.0 (lancar) s/d 1.0 (arus massa padat)
    
    # Koridor Evakuasi Barat (Ulee Lheue & Sekitarnya)
    g.add_edge("Ulee_Lheue", "Alue_Deah_Junction", distance_km=1.2, risk_factor=0.7, congestion_factor=0.4)
    g.add_edge("Alue_Deah_Junction", "Escape_Building_Alue_Deah", distance_km=0.8, risk_factor=0.3, congestion_factor=0.2)
    g.add_edge("Alue_Deah_Junction", "Lambung_Junction", distance_km=1.4, risk_factor=0.5, congestion_factor=0.3)
    g.add_edge("Ulee_Lheue", "Lambung_Junction", distance_km=1.3, risk_factor=0.6, congestion_factor=0.5)
    g.add_edge("Lambung_Junction", "Escape_Building_Lambung", distance_km=0.5, risk_factor=0.2, congestion_factor=0.2)
    g.add_edge("Lambung_Junction", "Taman_Putroe_Phang", distance_km=3.4, risk_factor=0.3, congestion_factor=0.4)

    # Koridor Evakuasi Timur & Pusat Kota (Lampulo, Peunayong, Cut Mutia)
    g.add_edge("Lampulo", "Peunayong", distance_km=2.2, risk_factor=0.6, congestion_factor=0.5)
    g.add_edge("Lampulo", "Simpang_Lima", distance_km=3.4, risk_factor=0.4, congestion_factor=0.4)
    g.add_edge("Peunayong", "Cut_Mutia", distance_km=0.9, risk_factor=0.4, congestion_factor=0.6)
    g.add_edge("Peunayong", "Simpang_Lima", distance_km=1.4, risk_factor=0.2, congestion_factor=0.7)
    g.add_edge("Cut_Mutia", "Simpang_Jam", distance_km=1.9, risk_factor=0.3, congestion_factor=0.5)
    g.add_edge("Simpang_Lima", "Simpang_Jam", distance_km=1.6, risk_factor=0.2, congestion_factor=0.6)

    # Koridor Menuju Shelter Sentral (Museum Tsunami & Baiturrahman)
    g.add_edge("Simpang_Jam", "Museum_Tsunami", distance_km=0.4, risk_factor=0.1, congestion_factor=0.3)
    g.add_edge("Taman_Putroe_Phang", "Museum_Tsunami", distance_km=0.6, risk_factor=0.1, congestion_factor=0.2)
    g.add_edge("Taman_Putroe_Phang", "Simpang_Jam", distance_km=0.8, risk_factor=0.1, congestion_factor=0.3)
    g.add_edge("Simpang_Jam", "Kantor_Camat_Baiturrahman", distance_km=1.1, risk_factor=0.1, congestion_factor=0.4)
    g.add_edge("Museum_Tsunami", "Kantor_Camat_Baiturrahman", distance_km=1.0, risk_factor=0.1, congestion_factor=0.3)

    # Koridor Menuju Evakuasi Selatan (Keutapang & Perbukitan Mata Ie)
    g.add_edge("Kantor_Camat_Baiturrahman", "Keutapang", distance_km=2.4, risk_factor=0.1, congestion_factor=0.5)
    g.add_edge("Taman_Putroe_Phang", "Keutapang", distance_km=2.9, risk_factor=0.1, congestion_factor=0.3)
    g.add_edge("Keutapang", "Dataran_Tinggi_Mata_Ie", distance_km=2.1, risk_factor=0.0, congestion_factor=0.2)

    return g


def print_full_graph_data(graph: EvacuationGraph) -> None:
    """Mencetak katalog lengkap seluruh data dummy graf evakuasi Banda Aceh.
    
    Menampilkan:
    1. Tabel seluruh Simpul (Nodes) dengan koordinat, tipe, dan kapasitas.
    2. Tabel seluruh Ruas Jalan (Edges) dengan jarak, risiko, kemacetan, dan biaya transisi.
    3. Ringkasan statistik formal 5-tupel.
    """
    print("=" * 105)
    print("       KATALOG LENGKAP DATA DUMMY GRAF JARINGAN EVAKUASI TSUNAMI BPBD KOTA BANDA ACEH")
    print("=" * 105)

    # 1. TABEL SIMPUL (NODES / STATE SPACE X)
    print("\n[1] DAFTAR LENGKAP SIMPUL / TITIK LOKASI (STATE SPACE X)")
    print("-" * 105)
    print(f"{'No':<3} | {'ID Simpul':<26} | {'Tipe':<13} | {'Koordinat (km)':<16} | {'Kapasitas':<11} | {'Keterangan'}")
    print("-" * 105)
    
    for idx, (node_id, node) in enumerate(graph.nodes.items(), start=1):
        coord_str = f"({node.x:.1f}, {node.y:.1f})"
        cap_str = f"{node.capacity:,} jiwa" if node.capacity else "-"
        print(f"{idx:<3} | {node.id:<26} | {node.node_type:<13} | {coord_str:<16} | {cap_str:<11} | {node.name}")
    print("-" * 105)

    # 2. TABEL RUAS JALAN (EDGES)
    print("\n[2] DAFTAR LENGKAP RUAS JALAN BERBOBOT (EDGES / TRANSITION & COST)")
    print("-" * 105)
    print(f"{'No':<3} | {'Asal (u)':<24} -> {'Tujuan (v)':<25} | {'Jarak':<7} | {'Risk':<5} | {'Cong':<5} | {'Biaya C(u,v)'}")
    print("-" * 105)

    seen_edges = set()
    edge_idx = 1
    for u, edges in graph.adjacency.items():
        for edge in edges:
            pair_key = tuple(sorted([edge.origin, edge.destination]))
            # Cetak semua edge searah yang ada di adjacency list
            print(
                f"{edge_idx:<3} | {edge.origin:<24} -> {edge.destination:<25} | "
                f"{edge.distance_km:>4.1f} km | {edge.risk_factor:>4.2f} | "
                f"{edge.congestion_factor:>4.2f} | {edge.cost:>8.3f}"
            )
            edge_idx += 1
    print("-" * 105)

    # 3. RINGKASAN FORMAL & STATISTIK JARINGAN
    total_shelter_cap = sum(n.capacity for n in graph.nodes.values() if n.capacity)
    unique_segments = len(graph.adjacency) # total edges / 2 if symmetric
    total_directed_edges = sum(len(edges) for edges in graph.adjacency.values())

    print("\n[3] RINGKASAN FORMULASI 5-TUPEL & STATISTIK GRAF")
    print(f" - Tupel 1 (State Space X)    : {len(graph.state_space)} titik lokasi geografis")
    print(f" - Tupel 2 (Action Space A)   : MoveTo(v) melalui {total_directed_edges} transisi terarah ({total_directed_edges // 2} ruas jalan 2 arah)")
    print(f" - Tupel 3 (Transition T)     : Deterministik T(u, MoveTo(v)) = v")
    print(f" - Tupel 4 (Goal Test G)      : {len(graph.shelters)} Designated Shelters (Total Daya Tampung: {total_shelter_cap:,} jiwa)")
    print(f" - Tupel 5 (Step Cost C)      : C(u, v) = Jarak x (1 + Risk) x (1 + Congestion)")
    print("=" * 105)


if __name__ == "__main__":
    graph = build_banda_aceh_graph()
    print_full_graph_data(graph)

