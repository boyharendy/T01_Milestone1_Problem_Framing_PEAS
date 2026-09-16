"""Unit Test Suite untuk Pemodelan Graf dan Algoritma Penelusuran (UCS & A*).

Memvalidasi:
1. Integritas struktur data graf dan 5-tupel (X, A, T, G, C).
2. Perhitungan bobot step cost C(u, v) = d * (1 + r) * (1 + c) >= d.
3. Keberhasilan penemuan rute optimal oleh Uniform Cost Search (UCS).
4. Keberhasilan penemuan rute optimal oleh A* Search.
5. Kesetaraan optimalitas biaya (Total Cost UCS == Total Cost A*).
6. Pembuktian numerik sifat Admissible & Consistent heuristik Euclidean h(n) <= h*(n).
7. Efisiensi ekspansi simpul A* dibandingkan UCS (nodes_expanded A* <= nodes_expanded UCS).
8. Penanganan Edge Cases (Start Node adalah Shelter, dan Node Terisolasi).
"""

import os
import sys

# Dukungan eksekusi langsung via tombol Run VS Code atau python tests/test_search.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from src.graph_model import (
    Node,
    Edge,
    EvacuationGraph,
    build_banda_aceh_graph,
)
from src.heuristics import (
    closest_shelter_heuristic,
    zero_heuristic,
    verify_admissibility,
)
from src.search import (
    uniform_cost_search,
    a_star_search,
    compare_algorithms,
)


@pytest.fixture
def graph():
    """Fixture untuk memuat pemodelan graf evakuasi Banda Aceh."""
    return build_banda_aceh_graph()


class TestGraphModel:
    """Pengujian terhadap model graf dan antarmuka 5-tupel (X, A, T, G, C)."""

    def test_state_space_and_shelters(self, graph):
        """Memastikan State Space (X) dan Goal Space (G) terdefinisi dengan benar."""
        assert len(graph.state_space) == 15
        assert len(graph.shelters) == 4
        # Pastikan seluruh shelter terdaftar
        expected_shelters = {
            "Escape_Building_Lambung",
            "Escape_Building_Alue_Deah",
            "Museum_Tsunami",
            "Dataran_Tinggi_Mata_Ie"
        }
        assert graph.shelters == expected_shelters

    def test_formal_tuples_interface(self, graph):
        """Memvalidasi pemanggilan antarmuka 5-tupel: X, A, T, G, C."""
        # Tupel X
        assert "Ulee_Lheue" in graph.state_space
        
        # Tupel A
        actions = graph.get_actions("Ulee_Lheue")
        assert len(actions) > 0
        assert "Alue_Deah_Junction" in actions

        # Tupel T
        next_state = graph.transition("Ulee_Lheue", "Alue_Deah_Junction")
        assert next_state == "Alue_Deah_Junction"

        # Tupel G
        assert not graph.is_goal("Ulee_Lheue")
        assert graph.is_goal("Escape_Building_Lambung")

        # Tupel C
        cost = graph.get_step_cost("Ulee_Lheue", "Alue_Deah_Junction")
        assert cost > 0
        assert cost != float('inf')

    def test_cost_formula_integrity(self, graph):
        """Memvalidasi formula biaya C(u, v) = d * (1 + r) * (1 + c) >= d."""
        edge = graph.get_edge("Ulee_Lheue", "Alue_Deah_Junction")
        assert edge is not None
        expected_cost = edge.distance_km * (1.0 + edge.risk_factor) * (1.0 + edge.congestion_factor)
        assert pytest.approx(edge.cost, rel=1e-5) == expected_cost
        assert edge.cost >= edge.distance_km


class TestHeuristics:
    """Pengujian terhadap fungsi heuristik Euclidean dan sifat admissibility."""

    def test_heuristic_goal_is_zero(self, graph):
        """Nilai heuristik di titik goal (shelter) wajib bernilai 0.0."""
        for shelter in graph.shelters:
            assert closest_shelter_heuristic(shelter, graph) == 0.0

    def test_heuristic_admissibility_all_nodes(self, graph):
        """Memastikan h(n) <= h*(n) untuk setiap simpul di Kota Banda Aceh."""
        report = verify_admissibility(graph, closest_shelter_heuristic)
        assert report["is_admissible"] is True
        for node_id, data in report["details"].items():
            assert data["is_admissible"] is True, f"Simpul {node_id} melanggar admisibilitas!"

    def test_heuristic_consistency_monotonicity(self, graph):
        """Memastikan sifat konsisten h(u) <= C(u, v) + h(v) untuk setiap sisi."""
        for u in graph.state_space:
            h_u = closest_shelter_heuristic(u, graph)
            for v in graph.get_actions(u):
                h_v = closest_shelter_heuristic(v, graph)
                step_cost = graph.get_step_cost(u, v)
                assert h_u <= step_cost + h_v + 1e-6, (
                    f"Inkonsistensi terdeteksi pada transisi {u} -> {v}: "
                    f"h({u})={h_u} > C({u},{v})={step_cost} + h({v})={h_v}"
                )


class TestSearchAlgorithms:
    """Pengujian fungsionalitas dan kebenaran algoritma UCS dan A* Search."""

    @pytest.mark.parametrize("start_node", [
        "Ulee_Lheue",
        "Lampulo",
        "Peunayong",
        "Cut_Mutia"
    ])
    def test_search_optimality_and_equivalence(self, graph, start_node):
        """Memvalidasi bahwa UCS dan A* sama-sama menghasilkan rute dengan biaya minimum optimal."""
        res_ucs = uniform_cost_search(graph, start_node)
        res_astar = a_star_search(graph, start_node, closest_shelter_heuristic)

        # 1. Jalur harus ditemukan dan berakhir di salah satu shelter
        assert len(res_ucs.path) >= 2
        assert len(res_astar.path) >= 2
        assert res_ucs.path[-1] in graph.shelters
        assert res_astar.path[-1] in graph.shelters

        # 2. Total biaya optimal UCS dan A* harus sama persis
        assert pytest.approx(res_ucs.total_cost, rel=1e-5) == res_astar.total_cost

        # 3. A* harus efisien: jumlah ekspansi simpul A* <= UCS
        assert res_astar.nodes_expanded <= res_ucs.nodes_expanded

    def test_a_star_with_zero_heuristic_equals_ucs(self, graph):
        """A* dengan zero_heuristic harus identik jumlah ekspansinya dengan UCS."""
        res_ucs = uniform_cost_search(graph, "Ulee_Lheue")
        res_astar_zero = a_star_search(graph, "Ulee_Lheue", zero_heuristic)

        assert pytest.approx(res_ucs.total_cost, rel=1e-5) == res_astar_zero.total_cost
        assert res_ucs.nodes_expanded == res_astar_zero.nodes_expanded

    def test_edge_case_start_already_at_shelter(self, graph):
        """Titik awal yang sudah berada di shelter harus mengembalikan biaya 0 dan 0 ekspansi."""
        shelter_start = "Museum_Tsunami"
        res_ucs = uniform_cost_search(graph, shelter_start)
        res_astar = a_star_search(graph, shelter_start)

        assert res_ucs.total_cost == 0.0
        assert res_ucs.path == [shelter_start]
        assert res_ucs.nodes_expanded == 0

        assert res_astar.total_cost == 0.0
        assert res_astar.path == [shelter_start]
        assert res_astar.nodes_expanded == 0

    def test_edge_case_isolated_node(self):
        """Simpul yang terisolasi tanpa jalur keluar harus mengembalikan jalur kosong & biaya tak hingga."""
        g = EvacuationGraph()
        g.add_node(Node(id="Pulau_Terpencil", name="Pulau Terpencil", x=0.0, y=0.0, node_type="hazard"))
        g.add_node(Node(id="Shelter_Aman", name="Shelter Aman", x=10.0, y=10.0, node_type="shelter"))

        res = uniform_cost_search(g, "Pulau_Terpencil")
        assert res.path == []
        assert res.total_cost == float('inf')
        assert res.target_shelter is None


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))

