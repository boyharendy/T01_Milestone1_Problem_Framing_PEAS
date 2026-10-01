"""Data Engineer & Spatial Integrator - Milestone 2.

Menjembatani dunia nyata (jaringan jalan OpenStreetMap Banda Aceh) dengan
Algoritma Genetika. Fungsi utama untuk Lead AI Programmer:

    data = get_distance_matrix()
    data.time_min      # np.ndarray [n_bahaya x n_shelter], menit (inf = tidak terjangkau)
    data.distance_m    # np.ndarray [n_bahaya x n_shelter], meter
    data.danger_ids    # urutan baris
    data.shelter_ids   # urutan kolom

Catatan penting:
- Koordinat & angka demand/kapasitas di bawah adalah PLACEHOLDER. Verifikasi
  di Google Maps / data BPS-BPBD sebelum dipakai di laporan.
- ID lokasi sudah disamakan dengan ID node di src/graph_model.py (Milestone 1);
  Gampong_Pande adalah titik bahaya ke-5 baru (M2 mensyaratkan minimal 5).
"""
from __future__ import annotations

import itertools
import json
import logging
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import networkx as nx
import numpy as np

# Dukungan eksekusi langsung dari terminal (python src/data_loader.py)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
GRAPH_CACHE = DATA_DIR / "banda_aceh_drive.graphml"
MATRIX_CACHE = DATA_DIR / "distance_matrix.json"

# Pusat area unduhan graf (sekitar Masjid Raya Baiturrahman) dan radius (meter).
GRAPH_META = DATA_DIR / "banda_aceh_drive.meta.json"

# Area unduhan bawaan. get_distance_matrix() menghitung area sendiri dari semua titik.
MAP_CENTER = (5.5550, 95.3200)
MAP_RADIUS_M = 13000
MAP_PADDING_M = 3000      # jarak tambahan di luar titik terjauh
MIN_SEPARATION_M = 100    # titik lebih dekat dari ini dianggap mencurigakan

# Batas aman waktu tempuh (menit) - golden time tsunami, dipakai sebagai constraint GA.
TSUNAMI_LIMIT_MIN = 20.0

# Fallback bila graf OSM tidak tersedia (offline / CI): jarak garis lurus x faktor
# liku jalan, dibagi kecepatan rata-rata perkotaan.
FALLBACK_CIRCUITY = 1.35
FALLBACK_SPEED_KMH = 30.0
# Jarak maksimum titik ke node jalan terdekat sebelum diberi peringatan.
SNAP_WARN_M = 500


@dataclass(frozen=True)
class Location:
    """Titik bahaya (kelurahan/gampong) atau shelter."""

    id: str
    name: str
    lat: float
    lon: float
    kind: str  # "danger" | "shelter"
    quantity: int  # danger: jumlah pengungsi (demand); shelter: kapasitas


# PLACEHOLDER - ganti dengan koordinat presisi dari Google Maps + data resmi.
DANGER_POINTS: tuple[Location, ...] = (
    Location("Ulee_Lheue", "Ulee Lheue", 5.55596, 95.28432, "danger", 400), 
    Location("Peunayong", "Peunayong", 5.56050, 95.31893, "danger", 500),
    Location("Cut_Mutia", "Cut Mutia", 5.55830, 95.31801, "danger", 300),
    Location("Gampong_Pande", "Gampong Pande", 5.58136, 95.31491, "danger", 250),
)
SHELTERS: tuple[Location, ...] = (
    # ID & kapasitas mengikuti build_banda_aceh_graph() Milestone 1; koordinat = PLACEHOLDER.
    Location("Escape_Building_Lambung", "Gedung Evakuasi Tsunami (TES) Lambung", 5.53519, 95.28252, "shelter", 1200),
    Location("Escape_Building_Alue_Deah", "Gedung Evakuasi Tsunami Alue Deah Teungoh", 5.57000, 95.29500, "shelter", 1000),
    Location("Museum_Tsunami", "Museum Tsunami Banda Aceh", 5.54802, 95.31528, "shelter", 3500),
    Location("Dataran_Tinggi_Mata_Ie", "Gampong Mata Ie (Montasik)", 5.4725702, 95.3925207, "shelter", 20000),
)
@dataclass
class DistanceData:
    """Hasil perhitungan matriks jarak/waktu tempuh riil."""

    danger_ids: list[str]
    shelter_ids: list[str]
    distance_m: np.ndarray
    time_min: np.ndarray
    source: str  # "osm" | "haversine_fallback"
    danger_nodes: list[int | None] = field(default_factory=list, repr=False)
    shelter_nodes: list[int | None] = field(default_factory=list, repr=False)
    routes: dict[tuple[str, str], list[int] | None] = field(default_factory=dict, repr=False)
    graph: nx.MultiDiGraph | None = field(default=None, repr=False)
    dangers: tuple[Location, ...] = field(default=DANGER_POINTS, repr=False)
    shelters: tuple[Location, ...] = field(default=SHELTERS, repr=False)

    def time(self, danger_id: str, shelter_id: str) -> float:
        return float(self.time_min[self.danger_ids.index(danger_id), self.shelter_ids.index(shelter_id)])

    def distance(self, danger_id: str, shelter_id: str) -> float:
        return float(self.distance_m[self.danger_ids.index(danger_id), self.shelter_ids.index(shelter_id)])

    def demands(self) -> list[int]:
        return [loc.quantity for loc in self.dangers]

    def capacities(self) -> list[int]:
        return [loc.quantity for loc in self.shelters]

    def to_json(self, path: Path = MATRIX_CACHE) -> Path:
        """Simpan matriks (tanpa graf) agar GA bisa jalan tanpa osmnx/internet."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": self.source,
            "danger_ids": self.danger_ids,
            "shelter_ids": self.shelter_ids,
            # inf -> None agar valid JSON
            "distance_m": [[None if math.isinf(v) else v for v in row] for row in self.distance_m.tolist()],
            "time_min": [[None if math.isinf(v) else v for v in row] for row in self.time_min.tolist()],
            "demands": self.demands(),
            "capacities": self.capacities(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @classmethod
    def from_json(cls, path: Path = MATRIX_CACHE) -> "DistanceData":
        raw = json.loads(path.read_text(encoding="utf-8"))
        to_arr = lambda m: np.array([[math.inf if v is None else v for v in r] for r in m], dtype=float)
        return cls(
            danger_ids=raw["danger_ids"],
            shelter_ids=raw["shelter_ids"],
            distance_m=to_arr(raw["distance_m"]),
            time_min=to_arr(raw["time_min"]),
            source=raw["source"],
        )


# --------------------------------------------------------------------------- #
# Geometri & graf
# --------------------------------------------------------------------------- #
def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Jarak lingkaran-besar dua koordinat (meter)."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def compute_map_area(locations: Sequence[Location], padding_m: float = MAP_PADDING_M) -> tuple[tuple[float, float], int]:
    """Pusat & radius (meter, dibulatkan ke atas per 500) yang mencakup semua titik + padding."""
    lats = [loc.lat for loc in locations]
    lons = [loc.lon for loc in locations]
    center = ((min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2)
    farthest = max(haversine_m(center[0], center[1], loc.lat, loc.lon) for loc in locations)
    return center, int(math.ceil((farthest + padding_m) / 500.0) * 500)


def validate_locations(dangers: Sequence[Location], shelters: Sequence[Location]) -> None:
    """Tolak ID ganda; beri peringatan bila dua titik nyaris di koordinat yang sama."""
    everything = [*dangers, *shelters]
    ids = [loc.id for loc in everything]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"ID lokasi ganda: {duplicates}")
    for a, b in itertools.combinations(everything, 2):
        gap = haversine_m(a.lat, a.lon, b.lat, b.lon)
        if gap < MIN_SEPARATION_M:
            logger.warning("%s dan %s hanya berjarak %.0f m - kemungkinan salah koordinat!", a.id, b.id, gap)


def _cache_covers(center: tuple[float, float], radius_m: float) -> bool:
    """True bila graf di cache mencakup area (center, radius_m) yang diminta."""
    if not (GRAPH_CACHE.exists() and GRAPH_META.exists()):
        return False
    try:
        meta = json.loads(GRAPH_META.read_text(encoding="utf-8"))
        shift = haversine_m(center[0], center[1], meta["center"][0], meta["center"][1])
        return shift + radius_m <= float(meta["radius_m"])
    except (OSError, ValueError, KeyError, TypeError):
        return False


def load_road_graph(use_cache: bool = True, center: tuple[float, float] = MAP_CENTER,
                    radius_m: int = MAP_RADIUS_M) -> nx.MultiDiGraph:
    """Unduh (atau muat dari cache) graf jalan Banda Aceh via OSMnx.

    Cache dipakai hanya jika areanya mencakup area yang diminta; jika tidak, peta diunduh ulang.
    Setiap edge diberi atribut `speed_kph` dan `travel_time` (detik).
    """
    import osmnx as ox  # import lokal: modul tetap bisa diimpor tanpa osmnx

    if use_cache and _cache_covers(center, radius_m):
        logger.info("Memuat graf dari cache %s", GRAPH_CACHE)
        return ox.load_graphml(GRAPH_CACHE)

    logger.info("Mengunduh graf jalan dari OpenStreetMap (pusat=%s, radius=%d m) ...", center, radius_m)
    graph = ox.graph_from_point(center, dist=radius_m, network_type="drive", simplify=True)
    graph = ox.routing.add_edge_speeds(graph)
    graph = ox.routing.add_edge_travel_times(graph)
    GRAPH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, GRAPH_CACHE)
    GRAPH_META.write_text(json.dumps({"center": list(center), "radius_m": radius_m}), encoding="utf-8")
    return graph


def nearest_node(graph: nx.MultiDiGraph, lat: float, lon: float) -> tuple[int, float]:
    """Node jalan terdekat + jarak snap (meter). Brute-force numpy, tanpa scikit-learn."""
    ids = np.fromiter(graph.nodes, dtype=object)
    ys = np.array([graph.nodes[n]["y"] for n in ids], dtype=float)
    xs = np.array([graph.nodes[n]["x"] for n in ids], dtype=float)
    dy = np.radians(ys - lat) * 6_371_000.0
    dx = np.radians(xs - lon) * 6_371_000.0 * math.cos(math.radians(lat))
    idx = int(np.argmin(dx * dx + dy * dy))
    return ids[idx], float(math.hypot(dx[idx], dy[idx]))


def apply_closures(graph: nx.MultiDiGraph, closures: Iterable[tuple[float, float, float]]) -> nx.MultiDiGraph:
    """Simulasi jalan terputus: hapus semua node dalam radius (lat, lon, radius_m).

    Dipakai untuk edge case "jalan utama terputus" -> waktu tempuh = inf.
    """
    g = graph.copy()
    for lat, lon, radius in closures:
        doomed = [n for n, d in g.nodes(data=True) if haversine_m(lat, lon, d["y"], d["x"]) <= radius]
        g.remove_nodes_from(doomed)
        logger.warning("Closure (%.4f, %.4f, r=%sm): %d node dihapus", lat, lon, radius, len(doomed))
    return g


def _best_edge(graph: nx.MultiDiGraph, u: int, v: int) -> dict:
    return min(graph[u][v].values(), key=lambda d: d.get("travel_time", math.inf))


def _path_length_m(graph: nx.MultiDiGraph, path: Sequence[int]) -> float:
    return float(sum(_best_edge(graph, u, v).get("length", 0.0) for u, v in zip(path[:-1], path[1:])))


# --------------------------------------------------------------------------- #
# API utama
# --------------------------------------------------------------------------- #
def _fallback_matrices(dangers: Sequence[Location], shelters: Sequence[Location], congestion_factor: float):
    dist = np.array([[haversine_m(d.lat, d.lon, s.lat, s.lon) * FALLBACK_CIRCUITY for s in shelters]
                     for d in dangers])
    minutes = dist / (FALLBACK_SPEED_KMH * 1000 / 60) * congestion_factor
    return dist, minutes


def get_distance_matrix(
    dangers: Sequence[Location] = DANGER_POINTS,
    shelters: Sequence[Location] = SHELTERS,
    *,
    graph: nx.MultiDiGraph | None = None,
    use_cache: bool = True,
    allow_fallback: bool = True,
    congestion_factor: float = 1.0,
    closures: Iterable[tuple[float, float, float]] = (),
) -> DistanceData:
    """Hitung matriks jarak (m) & waktu tempuh (menit) jalan riil bahaya -> shelter.

    Args:
        graph: graf siap pakai (untuk testing). Jika None -> unduh/muat cache.
        allow_fallback: bila graf gagal diunduh, pakai estimasi haversine
            (source="haversine_fallback") alih-alih error. Set False untuk data final laporan.
        congestion_factor: pengali waktu tempuh (>=1). 1.0 = lancar, 1.5 = padat.
        closures: daftar (lat, lon, radius_m) titik jalan terputus.

    Pasangan yang tidak terhubung bernilai np.inf (bukan error), sesuai edge case.
    """
    if congestion_factor < 1.0:
        raise ValueError("congestion_factor harus >= 1.0")
    closures = list(closures)
    validate_locations(dangers, shelters)
    danger_ids = [d.id for d in dangers]
    shelter_ids = [s.id for s in shelters]

    if graph is None:
        try:
            center, radius_m = compute_map_area([*dangers, *shelters])
            graph = load_road_graph(use_cache=use_cache, center=center, radius_m=radius_m)
        except Exception as exc:  # jaringan/Overpass/osmnx belum terpasang
            if not allow_fallback:
                raise
            logger.warning("Graf OSM tidak tersedia (%s). Memakai fallback haversine.", exc)
            dist, minutes = _fallback_matrices(dangers, shelters, congestion_factor)
            if closures:
                logger.warning("closures diabaikan pada mode fallback (tidak ada graf).")
            return DistanceData(danger_ids, shelter_ids, dist, minutes, "haversine_fallback",
                                dangers=tuple(dangers), shelters=tuple(shelters))

    def snap(loc: Location) -> int | None:
        node, gap = nearest_node(graph, loc.lat, loc.lon)
        if gap > SNAP_WARN_M:
            logger.warning("%s berjarak %.0f m dari jalan terdekat - cek koordinat!", loc.id, gap)
        return node

    # Snap ke graf UTUH dulu; jika node-nya lalu terhapus oleh closure, titik itu
    # dianggap terisolasi (inf) dan tidak "melompat" ke jalan tetangga.
    d_nodes = [snap(d) for d in dangers]
    s_nodes = [snap(s) for s in shelters]
    if closures:
        graph = apply_closures(graph, closures)
    d_nodes = [n if n in graph else None for n in d_nodes]
    s_nodes = [n if n in graph else None for n in s_nodes]

    dist = np.full((len(dangers), len(shelters)), np.inf)
    minutes = np.full_like(dist, np.inf)
    routes: dict[tuple[str, str], list[int] | None] = {}

    for i, src in enumerate(d_nodes):
        seconds, paths = ({}, {}) if src is None else nx.single_source_dijkstra(graph, src, weight="travel_time")
        for j, dst in enumerate(s_nodes):
            if dst is None or dst not in seconds:
                routes[(danger_ids[i], shelter_ids[j])] = None
                continue
            path = paths[dst]
            minutes[i, j] = seconds[dst] / 60.0 * congestion_factor
            dist[i, j] = _path_length_m(graph, path)
            routes[(danger_ids[i], shelter_ids[j])] = path

    return DistanceData(danger_ids, shelter_ids, dist, minutes, "osm", d_nodes, s_nodes, routes, graph,
                        tuple(dangers), tuple(shelters))


def get_matrices_for_ga(**kwargs) -> tuple[list[list[float]], list[list[float]]]:
    """Kemudahan untuk GA: (time_min, distance_m) sebagai list-of-list biasa."""
    data = get_distance_matrix(**kwargs)
    return data.time_min.tolist(), data.distance_m.tolist()


if __name__ == "__main__":
    # Konfigurasi encoding UTF-8 aman untuk terminal Windows
    if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = get_distance_matrix()
    print(f"\nSumber data: {result.source}")
    print(f"Sel bertanda * melebihi batas aman {TSUNAMI_LIMIT_MIN:.0f} menit\n")
    print(f"{'Menit (jarak km)':<18}" + "".join(f"{s[:24]:>27}" for s in result.shelter_ids))
    for i, d in enumerate(result.danger_ids):
        row = ""
        for j in range(len(result.shelter_ids)):
            t, km = result.time_min[i, j], result.distance_m[i, j] / 1000
            flag = "*" if t > TSUNAMI_LIMIT_MIN else " "
            row += f"{t:>15.1f}{flag} ({km:>5.1f} km)"
        print(f"{d:<18}{row}")
    print("\nDisimpan ke:", result.to_json())