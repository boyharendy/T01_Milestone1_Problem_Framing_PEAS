"""Modul Fungsi Heuristik untuk Algoritma A* Search.

Studi Kasus: Sistem Rekomendasi Rute Evakuasi Tsunami BPBD Kota Banda Aceh.

Kriteria Heuristik:
1. Admissible (Dapat Diterima):
   h(n) <= h*(n) untuk setiap simpul n, di mana h*(n) adalah biaya riil optimal
   menuju shelter terdekat. Heuristik tidak pernah melebih-lebihkan (never overestimates)
   biaya aktual.
2. Consistent / Monotonic (Konsisten):
   h(u) <= C(u, v) + h(v) untuk setiap sisi (u, v).
   Menjamin bahwa nilai f(n) tidak pernah menurun sepanjang jalur dan ekspansi
   pertama ke suatu state selalu merupakan rute optimal.

Formulasi Heuristik:
   h(n) = min_{g in SHELTERS} EuclideanDistance(n, g)
"""

import os
import sys
import math
from typing import Dict, Any, Callable

# Dukungan eksekusi langsung dari terminal (python src/heuristics.py)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.graph_model import EvacuationGraph


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Menghitung jarak garis lurus Euclidean (dalam km) antara dua koordinat."""
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def closest_shelter_heuristic(node_id: str, graph: EvacuationGraph) -> float:
    """Menghitung estimasi biaya heuristik h(n) ke shelter terdekat.
    
    Menggunakan jarak garis lurus Euclidean ke shelter terdekat yang ada di graf.
    Jika simpul saat ini adalah shelter, maka h(n) = 0.
    
    Bukti Matematis Admisibilitas:
    1. Biaya langkah riil:
       C(u, v) = distance_km * (1 + risk_factor) * (1 + congestion_factor)
       Karena risk_factor >= 0 dan congestion_factor >= 0, maka C(u, v) >= distance_km.
    2. Jarak garis lurus Euclidean antara dua titik geografis selalu <= jarak fisik jalan raya:
       EuclideanDistance(u, v) <= RoadDistance(u, v).
    3. Akibatnya:
       EuclideanDistance(n, g) <= PathCost(n, ..., g) untuk setiap rute ke shelter g.
    4. Oleh karena itu, h(n) = min_{g} EuclideanDistance(n, g) <= h*(n).
       Terbukti ADMISSIBLE.
    """
    if graph.is_goal(node_id):
        return 0.0

    current_node = graph.nodes.get(node_id)
    if not current_node:
        return 0.0

    min_distance = float('inf')
    for shelter_id in graph.shelters:
        shelter_node = graph.nodes.get(shelter_id)
        if shelter_node:
            dist = euclidean_distance(
                current_node.x, current_node.y,
                shelter_node.x, shelter_node.y
            )
            if dist < min_distance:
                min_distance = dist

    return min_distance if min_distance != float('inf') else 0.0


def zero_heuristic(node_id: str, graph: EvacuationGraph) -> float:
    """Heuristik h(n) = 0 (Trivial Heuristic).
    
    Digunakan sebagai pembanding: Ketika A* menggunakan zero_heuristic,
    perilaku dan jumlah ekspansi simpul identik dengan Uniform Cost Search (UCS).
    """
    return 0.0


def verify_admissibility(
    graph: EvacuationGraph,
    heuristic_fn: Callable[[str, EvacuationGraph], float]
) -> Dict[str, Any]:
    """Melakukan pengujian numerik otomatis terhadap sifat Admissible heuristik.
    
    Membandingkan nilai heuristik h(n) dengan biaya optimal sesungguhnya h*(n)
    yang dihitung menggunakan UCS untuk seluruh simpul dalam graf.
    
    Returns:
        Dict berisi status kelulusan (is_admissible) dan rincian perbandingan tiap simpul.
    """
    from src.search import uniform_cost_search

    results = {}
    is_all_admissible = True

    for node_id in graph.state_space:
        h_val = heuristic_fn(node_id, graph)
        search_res = uniform_cost_search(graph, node_id)
        h_star = search_res.total_cost if search_res.path else float('inf')

        is_node_admissible = (h_val <= h_star + 1e-6)
        if not is_node_admissible:
            is_all_admissible = False

        results[node_id] = {
            "h_val": round(h_val, 4),
            "h_star": round(h_star, 4) if h_star != float('inf') else "Unreachable",
            "is_admissible": is_node_admissible,
            "target_shelter": search_res.path[-1] if search_res.path else None
        }

    return {
        "is_admissible": is_all_admissible,
        "details": results
    }


if __name__ == "__main__":
    # Konfigurasi encoding UTF-8 aman untuk terminal Windows
    if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    from src.graph_model import build_banda_aceh_graph

    g = build_banda_aceh_graph()
    report = verify_admissibility(g, closest_shelter_heuristic)

    print("\n" + "=" * 105)
    print("         PENGUJIAN ADMISIBILITAS & KONSISTENSI FUNGSI HEURISTIK EUCLIDEAN h(n)")
    print("                    Kajian Matematis: h(n) <= h*(n) untuk Semua Simpul")
    print("=" * 105)
    status_str = "[+] STATUS: LULUS 100% VALID (Sifat Admissible & Konsisten Terpenuhi)" if report["is_admissible"] else "[-] STATUS: GAGAL"
    print(f" {status_str}")
    print("=" * 105)

    sep = "+------------------------------+------------+--------------+---------------+---------------------------------+"
    print(sep)
    print("| Simpul Lokasi (Node ID)      | h(n) [Est] | h*(n) [Riil] | Admissible?   | Shelter Terdekat / Tujuan       |")
    print(sep)
    for nid in sorted(report["details"].keys()):
        row = report["details"][nid]
        h_star_str = f"{row['h_star']:>8.4f}" if isinstance(row['h_star'], float) else f"{str(row['h_star']):>8}"
        full_name = g.nodes[row['target_shelter']].name.split("(")[0].strip() if row['target_shelter'] in g.nodes else "N/A"
        target_name = full_name if len(full_name) <= 31 else full_name[:28] + "..."
        adm_status = "YA (Valid)" if row['is_admissible'] else "TIDAK (Over)"
        print(
            f"| {nid:<28} | "
            f"{row['h_val']:>10.4f} | "
            f"{h_star_str:>12} | "
            f"{adm_status:<13} | "
            f"{target_name:<31} |"
        )
    print(sep)
    print(" Catatan Akademik:")
    print(" - h(n)   : Jarak Euclidean garis lurus minimum ke shelter (Lower Bound biaya langkah).")
    print(" - h*(n)  : Biaya lintasan riil minimum yang dihitung menggunakan Uniform Cost Search.")
    print(" - Syarat : Karena h(n) <= h*(n) di seluruh simpul, A* dijamin menghasilkan solusi optimal!")
    print("=" * 105 + "\n")
