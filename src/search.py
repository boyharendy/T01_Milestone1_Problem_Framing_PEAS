"""Implementasi Algoritma Penelusuran Ruang Keadaan (UCS & A* Search).

Studi Kasus: Sistem Rekomendasi Rute Evakuasi Tsunami BPBD Kota Banda Aceh.

Kepatuhan Spesifikasi:
1. Menggunakan modul antrean prioritas bawaan Python: `heapq` (Wajib).
2. Algoritma 1: Uniform Cost Search (UCS) -> Ekspansi berdasarkan g(n) terkecil.
3. Algoritma 2: A* Search -> Ekspansi berdasarkan f(n) = g(n) + h(n) terkecil.
4. Menghasilkan rute optimal (minimum path cost), urutan ekspansi simpul,
   dan metrik efisiensi komputasi.
"""

import os
import sys
import heapq
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable

# Dukungan eksekusi langsung dari terminal (python src/search.py)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.graph_model import EvacuationGraph, build_banda_aceh_graph
from src.heuristics import closest_shelter_heuristic, zero_heuristic


@dataclass
class SearchResult:
    """Struktur data hasil penelusuran algoritma pencarian."""
    algorithm_name: str
    start_node: str
    target_shelter: Optional[str]
    path: List[str]
    total_cost: float
    nodes_expanded: int
    expansion_order: List[str]
    visited_costs: Dict[str, float]
    execution_time_ms: float

    def summary(self) -> str:
        """Menghasilkan ringkasan hasil rute dalam format teks informatif."""
        path_str = " -> ".join(self.path) if self.path else "Tidak Ditemukan Jalur"
        return (
            f"[{self.algorithm_name}] {self.start_node} -> {self.target_shelter or 'N/A'}\n"
            f"  - Rute Evakuasi      : {path_str}\n"
            f"  - Total Biaya Riil   : {self.total_cost:.4f}\n"
            f"  - Simpul Diekspansi  : {self.nodes_expanded} simpul\n"
            f"  - Waktu Eksekusi     : {self.execution_time_ms:.3f} ms"
        )


def uniform_cost_search(graph: EvacuationGraph, start_node: str) -> SearchResult:
    """Implementasi Uniform Cost Search (UCS) menggunakan antrean prioritas heapq.
    
    Karakteristik:
    - Mengekspansi simpul dengan akumulasi biaya lintasan g(n) terendah.
    - Menjamin optimalitas pada graf berbobot positif C(u, v) > 0.
    
    Struktur Heap Entry:
        (g_cost, counter, current_node, path)
    """
    start_time = time.perf_counter()

    if start_node not in graph.state_space:
        raise ValueError(f"Simpul awal '{start_node}' tidak ada dalam graf.")

    # Edge Case: Titik awal sudah merupakan shelter aman
    if graph.is_goal(start_node):
        elapsed = (time.perf_counter() - start_time) * 1000.0
        return SearchResult(
            algorithm_name="Uniform Cost Search (UCS)",
            start_node=start_node,
            target_shelter=start_node,
            path=[start_node],
            total_cost=0.0,
            nodes_expanded=0,
            expansion_order=[],
            visited_costs={start_node: 0.0},
            execution_time_ms=elapsed
        )

    # Inisialisasi Priority Queue (Frontier)
    # Counter digunakan sebagai tie-breaker penentu urutan FIFO jika biaya g identik
    counter = 0
    frontier: List[Tuple[float, int, str, List[str]]] = []
    heapq.heappush(frontier, (0.0, counter, start_node, [start_node]))

    # Menyimpan biaya terbaik (terendah) yang pernah ditemukan untuk tiap simpul
    best_costs: Dict[str, float] = {start_node: 0.0}
    expansion_order: List[str] = []
    nodes_expanded = 0

    while frontier:
        g_cost, _, current_node, path = heapq.heappop(frontier)

        # Jika sudah pernah menemukan rute yang lebih murah ke current_node, lewati
        if g_cost > best_costs.get(current_node, float('inf')):
            continue

        # Catat ekspansi simpul
        nodes_expanded += 1
        expansion_order.append(current_node)

        # GOAL TEST: Dijalankan saat simpul dikeluarkan (popped) dari priority queue
        if graph.is_goal(current_node):
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return SearchResult(
                algorithm_name="Uniform Cost Search (UCS)",
                start_node=start_node,
                target_shelter=current_node,
                path=path,
                total_cost=g_cost,
                nodes_expanded=nodes_expanded,
                expansion_order=expansion_order,
                visited_costs=best_costs,
                execution_time_ms=elapsed
            )

        # Ekspansi tetangga (Aksi yang tersedia dari current_node)
        for next_node in graph.get_actions(current_node):
            step_cost = graph.get_step_cost(current_node, next_node)
            new_g = g_cost + step_cost

            if new_g < best_costs.get(next_node, float('inf')):
                best_costs[next_node] = new_g
                counter += 1
                new_path = path + [next_node]
                heapq.heappush(frontier, (new_g, counter, next_node, new_path))

    # Jika tidak ada shelter yang dapat dicapai
    elapsed = (time.perf_counter() - start_time) * 1000.0
    return SearchResult(
        algorithm_name="Uniform Cost Search (UCS)",
        start_node=start_node,
        target_shelter=None,
        path=[],
        total_cost=float('inf'),
        nodes_expanded=nodes_expanded,
        expansion_order=expansion_order,
        visited_costs=best_costs,
        execution_time_ms=elapsed
    )


def a_star_search(
    graph: EvacuationGraph,
    start_node: str,
    heuristic_fn: Optional[Callable[[str, EvacuationGraph], float]] = None
) -> SearchResult:
    """Implementasi Algoritma A* Search menggunakan antrean prioritas heapq.
    
    Karakteristik:
    - Evaluasi fungsi f(n) = g(n) + h(n).
    - g(n): Akumulasi biaya riil dari titik awal ke simpul n.
    - h(n): Estimasi biaya terarah ke shelter terdekat (Euclidean Admissible).
    - Menjamin optimalitas dan memangkas jumlah ekspansi simpul dibanding UCS.
    
    Struktur Heap Entry:
        (f_score, g_cost, counter, current_node, path)
    """
    start_time = time.perf_counter()
    h_fn = heuristic_fn or closest_shelter_heuristic

    if start_node not in graph.state_space:
        raise ValueError(f"Simpul awal '{start_node}' tidak ada dalam graf.")

    # Edge Case: Titik awal sudah merupakan shelter aman
    if graph.is_goal(start_node):
        elapsed = (time.perf_counter() - start_time) * 1000.0
        return SearchResult(
            algorithm_name="A* Search (A-Star)",
            start_node=start_node,
            target_shelter=start_node,
            path=[start_node],
            total_cost=0.0,
            nodes_expanded=0,
            expansion_order=[],
            visited_costs={start_node: 0.0},
            execution_time_ms=elapsed
        )

    # Inisialisasi Priority Queue
    counter = 0
    start_h = h_fn(start_node, graph)
    frontier: List[Tuple[float, float, int, str, List[str]]] = []
    heapq.heappush(frontier, (start_h, 0.0, counter, start_node, [start_node]))

    # Menyimpan biaya g terbaik (terendah) untuk tiap simpul
    best_g_costs: Dict[str, float] = {start_node: 0.0}
    expansion_order: List[str] = []
    nodes_expanded = 0

    while frontier:
        f_score, g_cost, _, current_node, path = heapq.heappop(frontier)

        # Jika sudah pernah menemukan nilai g yang lebih baik untuk simpul ini, lewati
        if g_cost > best_g_costs.get(current_node, float('inf')):
            continue

        # Catat ekspansi simpul
        nodes_expanded += 1
        expansion_order.append(current_node)

        # GOAL TEST: Dijalankan saat simpul dikeluarkan (popped) dari priority queue
        if graph.is_goal(current_node):
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return SearchResult(
                algorithm_name="A* Search (A-Star)",
                start_node=start_node,
                target_shelter=current_node,
                path=path,
                total_cost=g_cost,
                nodes_expanded=nodes_expanded,
                expansion_order=expansion_order,
                visited_costs=best_g_costs,
                execution_time_ms=elapsed
            )

        # Ekspansi tetangga
        for next_node in graph.get_actions(current_node):
            step_cost = graph.get_step_cost(current_node, next_node)
            new_g = g_cost + step_cost

            if new_g < best_g_costs.get(next_node, float('inf')):
                best_g_costs[next_node] = new_g
                h_val = h_fn(next_node, graph)
                new_f = new_g + h_val
                counter += 1
                new_path = path + [next_node]
                heapq.heappush(frontier, (new_f, new_g, counter, next_node, new_path))

    # Jika tidak ada shelter yang dapat dicapai
    elapsed = (time.perf_counter() - start_time) * 1000.0
    return SearchResult(
        algorithm_name="A* Search (A-Star)",
        start_node=start_node,
        target_shelter=None,
        path=[],
        total_cost=float('inf'),
        nodes_expanded=nodes_expanded,
        expansion_order=expansion_order,
        visited_costs=best_g_costs,
        execution_time_ms=elapsed
    )


def compare_algorithms(graph: EvacuationGraph, start_node: str) -> Dict[str, SearchResult]:
    """Menjalankan dan membandingkan performa UCS dan A* untuk titik awal yang sama."""
    res_ucs = uniform_cost_search(graph, start_node)
    res_astar = a_star_search(graph, start_node, closest_shelter_heuristic)
    return {
        "UCS": res_ucs,
        "A*": res_astar
    }


if __name__ == "__main__":
    graph = build_banda_aceh_graph()
    test_locations = ["Ulee_Lheue", "Lampulo", "Peunayong", "Cut_Mutia"]

    print("=" * 88)
    print("SISTEM REKOMENDASI RUTE EVAKUASI TSUNAMI BPBD KOTA BANDA ACEH")
    print("KOMPARASI KINERJA ALGORITMA PENELUSURAN: UCS vs A* SEARCH (heapq)")
    print("=" * 88)

    for loc in test_locations:
        node_name = graph.nodes[loc].name
        comparison = compare_algorithms(graph, loc)
        ucs = comparison["UCS"]
        astar = comparison["A*"]

        print(f"\n[Titik Awal Bencana]: {loc} ({node_name})")
        print(f"  • UCS : Biaya = {ucs.total_cost:.4f} | Rute = {' -> '.join(ucs.path)}")
        print(f"          Ekspansi = {ucs.nodes_expanded} simpul | Waktu = {ucs.execution_time_ms:.3f} ms")
        print(f"  • A*  : Biaya = {astar.total_cost:.4f} | Rute = {' -> '.join(astar.path)}")
        print(f"          Ekspansi = {astar.nodes_expanded} simpul | Waktu = {astar.execution_time_ms:.3f} ms")

        # Validasi Konsistensi Optimasi
        cost_diff = abs(ucs.total_cost - astar.total_cost)
        is_identical = cost_diff < 1e-5
        reduction = (
            ((ucs.nodes_expanded - astar.nodes_expanded) / ucs.nodes_expanded) * 100
            if ucs.nodes_expanded > 0 else 0.0
        )

        print(f"  --> Status Hasil: {'Kedua Algoritma Menemukan Biaya Optimal yang SAMA' if is_identical else 'Beda Biaya'}")
        print(f"  --> Efisiensi A*: Menghemat {reduction:.1f}% ekspansi simpul berkat panduan heuristik h(n)")

    print("\n" + "=" * 88)
