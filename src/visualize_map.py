"""Visualisasi peta riil Banda Aceh - Milestone 2.

Menggambar rute yang menelusuri geometri jalan OSM (melengkung), bukan garis lurus
seperti Milestone 1. Latar belakang digambar langsung dari edge graf (matplotlib),
sehingga tidak bergantung pada versi API plotting osmnx.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Mapping, Sequence

import matplotlib

matplotlib.use("Agg")  # aman di server/CI; ganti ke backend interaktif bila ingin plt.show()
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.collections import LineCollection

# Dukungan eksekusi langsung dari terminal (python src/visualize_map.py)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data_loader import ROOT, DistanceData, _best_edge

OUTPUT_DIR = ROOT / "output"
PALETTE = plt.get_cmap("tab10").colors


def _edge_coords(graph: nx.MultiDiGraph, u: int, v: int) -> list[tuple[float, float]]:
    """Koordinat (x=lon, y=lat) satu edge; memakai geometri asli jika tersedia."""
    data = _best_edge(graph, u, v)
    geom = data.get("geometry")
    if geom is not None:
        return list(geom.coords)
    return [(graph.nodes[u]["x"], graph.nodes[u]["y"]), (graph.nodes[v]["x"], graph.nodes[v]["y"])]


def _route_lines(graph: nx.MultiDiGraph, path: Sequence[int]) -> list[list[tuple[float, float]]]:
    return [_edge_coords(graph, u, v) for u, v in zip(path[:-1], path[1:])]


def _base_map(data: DistanceData, title: str):
    fig, ax = plt.subplots(figsize=(11, 11))
    graph = data.graph
    if graph is not None:
        segments = [_edge_coords(graph, u, v) for u, v, _ in graph.edges(keys=True)]
        ax.add_collection(LineCollection(segments, colors="#c8c8c8", linewidths=0.4, zorder=1))
        xs = [d["x"] for _, d in graph.nodes(data=True)]
        ys = [d["y"] for _, d in graph.nodes(data=True)]
        ax.set_xlim(min(xs), max(xs))
        ax.set_ylim(min(ys), max(ys))
    else:
        title += "\n(mode fallback: garis lurus, graf jalan OSM tidak tersedia)"
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    return fig, ax


def _mark_locations(ax, data: DistanceData) -> None:
    for d in data.dangers:
        ax.scatter(d.lon, d.lat, marker="^", s=110, c="#d62728", edgecolors="black", zorder=5)
        ax.annotate(d.name, (d.lon, d.lat), xytext=(5, 6), textcoords="offset points", fontsize=8, zorder=6)
    for s in data.shelters:
        ax.scatter(s.lon, s.lat, marker="s", s=110, c="#2ca02c", edgecolors="black", zorder=5)
        ax.annotate(s.name, (s.lon, s.lat), xytext=(5, -12), textcoords="offset points", fontsize=8, zorder=6)
    ax.scatter([], [], marker="^", c="#d62728", edgecolors="black", label="Titik bahaya")
    ax.scatter([], [], marker="s", c="#2ca02c", edgecolors="black", label="Shelter BPBD")


def _finish(fig, ax, data: DistanceData, save_path: Path | None, show: bool) -> Path | None:
    ax.set_aspect(1.0 / math.cos(math.radians(data.dangers[0].lat)))
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    saved = None
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=200)
        saved = save_path
    if show:
        plt.show()
    plt.close(fig)
    return saved


def _draw_path(ax, data: DistanceData, path: list[int] | None, a, b, color, label: str) -> None:
    """Gambar rute riil; jika graf/rute tidak ada, garis lurus putus-putus."""
    if data.graph is not None and path:
        ax.add_collection(LineCollection(_route_lines(data.graph, path), colors=[color], linewidths=2.6,
                                         zorder=3, label=label))
    else:
        ax.plot([a.lon, b.lon], [a.lat, b.lat], "--", color=color, linewidth=1.8, zorder=3, label=label)


def plot_assignments(data: DistanceData, assignments: Sequence[tuple[str, str]] | None = None,
                     save_path: Path | None = OUTPUT_DIR / "peta_rute_riil.png", show: bool = False):
    """Gambar rute tiap titik bahaya -> shelter.

    Args:
        assignments: pasangan (danger_id, shelter_id). None -> shelter tercepat per titik bahaya.
    """
    by_id_d = {d.id: d for d in data.dangers}
    by_id_s = {s.id: s for s in data.shelters}
    if assignments is None:
        assignments = []
        for i, d_id in enumerate(data.danger_ids):
            j = int(data.time_min[i].argmin())
            if math.isfinite(data.time_min[i, j]):
                assignments.append((d_id, data.shelter_ids[j]))

    fig, ax = _base_map(data, "Rute Evakuasi Riil - Banda Aceh")
    for k, (d_id, s_id) in enumerate(assignments):
        t = data.time(d_id, s_id)
        label = f"{d_id} -> {s_id} ({t:.1f} mnt)" if math.isfinite(t) else f"{d_id} -> {s_id} (TERPUTUS)"
        _draw_path(ax, data, data.routes.get((d_id, s_id)), by_id_d[d_id], by_id_s[s_id],
                   PALETTE[k % len(PALETTE)], label)
    _mark_locations(ax, data)
    return _finish(fig, ax, data, save_path, show)


def plot_truck_routes(data: DistanceData, plan: Mapping[str, tuple[Sequence[str], str]],
                      save_path: Path | None = OUTPUT_DIR / "peta_rute_armada_ga.png", show: bool = False):
    """Gambar rute armada hasil GA: Truk -> urutan titik bahaya -> shelter.

    Args:
        plan: {"Truk_1": (["Ulee_Lheue", "Gampong_Pande"], "Escape_Building_Lambung"), ...}
    """
    by_id = {loc.id: loc for loc in (*data.dangers, *data.shelters)}
    fig, ax = _base_map(data, "Rute Armada Evakuasi Hasil Algoritma Genetika")
    for k, (truck, (stops, shelter)) in enumerate(plan.items()):
        color = PALETTE[k % len(PALETTE)]
        waypoints = [*stops, shelter]
        for n, (a_id, b_id) in enumerate(zip(waypoints[:-1], waypoints[1:])):
            path = None
            if data.graph is not None:
                src = data.danger_nodes[data.danger_ids.index(a_id)]
                dst = (data.danger_nodes[data.danger_ids.index(b_id)] if b_id in data.danger_ids
                       else data.shelter_nodes[data.shelter_ids.index(b_id)])
                try:
                    path = nx.shortest_path(data.graph, src, dst, weight="travel_time")
                except (nx.NetworkXNoPath, nx.NodeNotFound, TypeError):
                    path = None
            label = f"{truck}: {' > '.join(waypoints)}" if n == 0 else "_nolegend_"
            _draw_path(ax, data, path, by_id[a_id], by_id[b_id], color, label)
    _mark_locations(ax, data)
    return _finish(fig, ax, data, save_path, show)


if __name__ == "__main__":
    from src.data_loader import get_distance_matrix

    result = get_distance_matrix()
    print("Tersimpan:", plot_assignments(result))