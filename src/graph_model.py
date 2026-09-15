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


if __name__ == "__main__":
    graph = build_banda_aceh_graph()
    print("=== MODEL GRAF EVAKUASI BPBD KOTA BANDA ACEH ===")
    print(f"Total Simpul (X): {len(graph.state_space)} titik")
    print(f"Total Shelter (G): {len(graph.shelters)} titik aman")
    print("\nDaftar Shelter:")
    for s in graph.shelters:
        node = graph.nodes[s]
        print(f" - [{node.id}] {node.name} (Kapasitas: {node.capacity} orang)")
    
    print("\nContoh Formulasi Transisi:")
    start = "Ulee_Lheue"
    actions = graph.get_actions(start)
    print(f"Dari State: {start}")
    print(f"Aksi Tersedia (A): {actions}")
    for act in actions:
        cost = graph.get_step_cost(start, act)
        print(f" -> MoveTo({act}) => Biaya Transisi C({start}, {act}) = {cost:.3f}")
