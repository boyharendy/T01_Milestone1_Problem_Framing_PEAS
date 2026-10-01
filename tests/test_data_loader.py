"""Tes offline untuk data_loader & visualize_map (graf sintetis, tanpa internet)."""
import os
import sys

# Dukungan eksekusi langsung dari terminal
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import networkx as nx
import numpy as np
import pytest

from src.data_loader import (DANGER_POINTS, MIN_SEPARATION_M, SHELTERS, DistanceData, Location,
                             compute_map_area, get_distance_matrix, haversine_m, validate_locations)
from src.visualize_map import plot_assignments, plot_truck_routes


def _grid_graph() -> nx.MultiDiGraph:
    """Grid 6x6 di sekitar Banda Aceh; tiap edge 500 m dan 60 detik."""
    g = nx.MultiDiGraph(crs="EPSG:4326")
    lat0, lon0, step = 5.545, 95.285, 0.01
    for r in range(6):
        for c in range(6):
            g.add_node(r * 6 + c, y=lat0 + r * step, x=lon0 + c * step)
    for r in range(6):
        for c in range(6):
            for dr, dc in ((0, 1), (1, 0)):
                rr, cc = r + dr, c + dc
                if rr < 6 and cc < 6:
                    u, v = r * 6 + c, rr * 6 + cc
                    for a, b in ((u, v), (v, u)):
                        g.add_edge(a, b, length=500.0, travel_time=60.0)
    return g


def test_fallback_shape_and_positive(monkeypatch):
    monkeypatch.setattr("src.data_loader.load_road_graph", lambda **_: (_ for _ in ()).throw(OSError("offline")))
    data = get_distance_matrix()
    assert data.source == "haversine_fallback"
    assert data.time_min.shape == (len(DANGER_POINTS), len(SHELTERS))
    assert (data.time_min > 0).all() and np.isfinite(data.time_min).all()


def test_fallback_disabled_raises(monkeypatch):
    monkeypatch.setattr("src.data_loader.load_road_graph", lambda **_: (_ for _ in ()).throw(OSError("offline")))
    with pytest.raises(OSError):
        get_distance_matrix(allow_fallback=False)


def test_graph_matrix_matches_hand_calculation():
    data = get_distance_matrix(graph=_grid_graph())
    assert data.source == "osm"
    assert np.isfinite(data.time_min).all()
    # satu edge = 60 s = 1 menit, 500 m -> jarak harus = 500 * waktu (menit)
    assert np.allclose(data.distance_m, data.time_min * 500.0)


def test_congestion_scales_time_not_distance():
    g = _grid_graph()
    base = get_distance_matrix(graph=g)
    jam = get_distance_matrix(graph=g, congestion_factor=1.5)
    assert np.allclose(jam.time_min, base.time_min * 1.5)
    assert np.allclose(jam.distance_m, base.distance_m)
    with pytest.raises(ValueError):
        get_distance_matrix(graph=g, congestion_factor=0.5)


def test_closure_isolating_shelter_gives_inf_not_error():
    g = _grid_graph()
    target = SHELTERS[0]
    data = get_distance_matrix(graph=g, closures=[(target.lat, target.lon, 1_500)])
    assert np.isinf(data.time_min[:, 0]).all()
    assert data.routes[(DANGER_POINTS[0].id, target.id)] is None


def test_json_roundtrip_preserves_inf(tmp_path):
    g = _grid_graph()
    data = get_distance_matrix(graph=g, closures=[(SHELTERS[0].lat, SHELTERS[0].lon, 1_500)])
    restored = DistanceData.from_json(data.to_json(tmp_path / "m.json"))
    assert restored.danger_ids == data.danger_ids
    assert np.array_equal(np.isinf(restored.time_min), np.isinf(data.time_min))


def test_haversine_known_distance():
    assert haversine_m(0, 0, 0, 1) == pytest.approx(111_195, rel=1e-3)
    assert haversine_m(5.5, 95.3, 5.5, 95.3) == 0


def test_plots_create_files(tmp_path):
    data = get_distance_matrix(graph=_grid_graph())
    out1 = plot_assignments(data, save_path=tmp_path / "a.png")
    plan = {"Truk_1": ([DANGER_POINTS[0].id, DANGER_POINTS[1].id], SHELTERS[1].id)}
    out2 = plot_truck_routes(data, plan, save_path=tmp_path / "b.png")
    assert out1.stat().st_size > 0 and out2.stat().st_size > 0

def test_map_area_covers_every_location():
    everything = [*DANGER_POINTS, *SHELTERS]
    center, radius = compute_map_area(everything)
    assert all(haversine_m(center[0], center[1], p.lat, p.lon) < radius for p in everything)


def test_default_locations_are_not_overlapping():
    everything = [*DANGER_POINTS, *SHELTERS]
    for i, a in enumerate(everything):
        for b in everything[i + 1:]:
            assert haversine_m(a.lat, a.lon, b.lat, b.lon) >= MIN_SEPARATION_M, (a.id, b.id)


def test_validate_rejects_duplicate_ids():
    with pytest.raises(ValueError):
        validate_locations(DANGER_POINTS, (*SHELTERS, SHELTERS[0]))


def test_validate_warns_when_points_overlap(caplog):
    twin_a = Location("A", "A", 5.5, 95.3, "shelter", 10)
    twin_b = Location("B", "B", 5.50001, 95.3, "shelter", 10)
    with caplog.at_level("WARNING"):
        validate_locations((), (twin_a, twin_b))
    assert "salah koordinat" in caplog.text