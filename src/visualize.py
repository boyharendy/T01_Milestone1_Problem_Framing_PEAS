"""Modul Visualisasi Graf, Rute Evakuasi, dan Perbandingan Kinerja Algoritma.

Studi Kasus: Sistem Rekomendasi Rute Evakuasi Tsunami BPBD Kota Banda Aceh.
Menghasilkan output visual beresolusi tinggi (PNG) untuk laporan dan presentasi:
1. output/peta_jaringan_evakuasi.png      : Peta graf 2D koordinat riil Kota Banda Aceh.
2. output/skenario_rute_evakuasi.png      : Visualisasi rute 4 skenario titik bahaya pesisir.
3. output/perbandingan_kinerja.png        : Grafik batang perbandingan ekspansi simpul & waktu.
"""

import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Dukungan eksekusi langsung dari terminal
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.graph_model import build_banda_aceh_graph, EvacuationGraph
from src.search import uniform_cost_search, a_star_search
from src.heuristics import closest_shelter_heuristic

# Direktori output gambar
OUTPUT_DIR = project_root / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Palet warna visual estetis & profesional
COLOR_PALETTE = {
    "hazard": "#E63946",        # Merah bahaya (Pesisir)
    "intersection": "#457B9D",  # Biru persimpangan
    "shelter": "#2A9D8F",       # Hijau toska aman (Gedung Evakuasi)
    "edge": "#CBD5E1",          # Abu-abu jalan biasa
    "route": "#D90429",         # Merah tegas rute evakuasi
    "route_glow": "#FFB703",    # Oranye kontras
    "text_dark": "#1E293B",
    "bg": "#F8FAFC"
}


def draw_base_network(ax, graph: EvacuationGraph, title: str = "Peta Jaringan Evakuasi Kota Banda Aceh"):
    """Menggambar latar belakang jaringan jalan dan simpul graf."""
    ax.set_facecolor(COLOR_PALETTE["bg"])
    
    # 1. Gambar Ruas Jalan (Edges)
    drawn_edges = set()
    for u, edges in graph.adjacency.items():
        node_u = graph.nodes[u]
        for edge in edges:
            pair = tuple(sorted([edge.origin, edge.destination]))
            if pair in drawn_edges:
                continue
            drawn_edges.add(pair)
            node_v = graph.nodes[edge.destination]
            
            # Ketebalan berdasarkan tingkat risiko jalan
            alpha_val = 0.45 + (edge.risk_factor * 0.35)
            lw = 1.8 + (edge.risk_factor * 1.5)
            line_color = "#94A3B8" if edge.risk_factor < 0.3 else "#F87171"
            
            ax.plot(
                [node_u.x, node_v.x], [node_u.y, node_v.y],
                color=line_color, linewidth=lw, alpha=alpha_val, zorder=1
            )
            
            # Label jarak di tengah ruas jalan
            mid_x = (node_u.x + node_v.x) / 2
            mid_y = (node_u.y + node_v.y) / 2
            ax.text(
                mid_x, mid_y, f"{edge.distance_km}km",
                fontsize=7.5, color="#64748B", ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7),
                zorder=2
            )

    # 2. Gambar Simpul (Nodes) Berdasarkan Tipe
    LABEL_CONFIG = {
        "Ulee_Lheue": (0.0, 0.36, "Pelabuhan Ulee Lheue"),
        "Lampulo": (0.0, 0.38, "Pelabuhan Lampulo"),
        "Peunayong": (0.0, 0.35, "Kawasan Peunayong"),
        "Cut_Mutia": (-0.4, -0.38, "Kawasan Cut Mutia"),
        "Alue_Deah_Junction": (-0.3, 0.36, "Sp. Alue Deah"),
        "Escape_Building_Alue_Deah": (0.3, -0.38, "TES Alue Deah"),
        "Lambung_Junction": (-0.3, -0.38, "Sp. Lambung"),
        "Escape_Building_Lambung": (0.3, 0.36, "TES Lambung"),
        "Simpang_Lima": (0.0, -0.38, "Simpang Lima"),
        "Simpang_Jam": (0.0, 0.35, "Simpang Jam"),
        "Taman_Putroe_Phang": (-0.4, 0.35, "Putroe Phang"),
        "Museum_Tsunami": (0.0, -0.38, "Museum Tsunami"),
        "Kantor_Camat_Baiturrahman": (0.3, -0.38, "Camat Baiturrahman"),
        "Keutapang": (0.0, 0.35, "Simpang Keutapang"),
        "Dataran_Tinggi_Mata_Ie": (0.0, -0.40, "Bukit Mata Ie"),
    }

    for node_id, node in graph.nodes.items():
        if node.node_type == "hazard":
            color = COLOR_PALETTE["hazard"]
            marker = "s"  # Square
            size = 180
            edge_color = "#991B1B"
        elif node.node_type == "shelter":
            color = COLOR_PALETTE["shelter"]
            marker = "^"  # Triangle up
            size = 280
            edge_color = "#134E4A"
        else:
            color = COLOR_PALETTE["intersection"]
            marker = "o"  # Circle
            size = 130
            edge_color = "#1E3A8A"

        ax.scatter(
            node.x, node.y, s=size, c=color, marker=marker,
            edgecolors=edge_color, linewidth=1.5, zorder=5
        )

        # Label Teks Nama Simpul dengan offset kustom
        dx, dy, label_name = LABEL_CONFIG.get(node_id, (0.0, 0.3, node.name))
        weight_font = "bold" if node.node_type in ["hazard", "shelter"] else "normal"
        ax.text(
            node.x + dx, node.y + dy, label_name,
            fontsize=8.5, fontweight=weight_font, color=COLOR_PALETTE["text_dark"],
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#E2E8F0", alpha=0.9),
            zorder=6
        )

    # Dekorasi batas & keterangan
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12, color=COLOR_PALETTE["text_dark"])
    ax.set_xlabel("Koordinat Barat - Timur (km)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Koordinat Selatan - Utara (km)", fontsize=10, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4, color="#CBD5E1")
    ax.set_xlim(-0.5, 7.8)
    ax.set_ylim(-1.0, 10.8)


def plot_overview_map(graph: EvacuationGraph) -> Path:
    """Membuat peta ikhtisar jaringan lengkap Kota Banda Aceh."""
    fig, ax = plt.subplots(figsize=(12, 10), dpi=300)
    draw_base_network(ax, graph, title="PETA TOPOLOGI GRAF JARINGAN EVAKUASI TSUNAMI BANDA ACEH\nBPBD Kota Banda Aceh - Pemodelan Formal 5-Tupel (X, A, T, G, C)")

    # Legenda Kustom
    hazard_proxy = plt.Line2D([0], [0], marker="s", color="w", label="Zona Bahaya Pesisir (Titik Awal)", markerfacecolor=COLOR_PALETTE["hazard"], markersize=10, markeredgecolor="#991B1B")
    inter_proxy = plt.Line2D([0], [0], marker="o", color="w", label="Persimpangan / Titik Transit Evakuasi", markerfacecolor=COLOR_PALETTE["intersection"], markersize=9, markeredgecolor="#1E3A8A")
    shelter_proxy = plt.Line2D([0], [0], marker="^", color="w", label="Designated Shelter (Goal State)", markerfacecolor=COLOR_PALETTE["shelter"], markersize=12, markeredgecolor="#134E4A")
    edge_safe_proxy = plt.Line2D([0], [0], color="#94A3B8", lw=2, label="Ruas Jalan Evakuasi Aman / Sedang")
    edge_risk_proxy = plt.Line2D([0], [0], color="#F87171", lw=3, label="Ruas Jalan Rawan / Risiko Tinggi Tsunami")

    ax.legend(
        handles=[hazard_proxy, inter_proxy, shelter_proxy, edge_safe_proxy, edge_risk_proxy],
        loc="upper left", frameon=True, facecolor="white", edgecolor="#CBD5E1",
        fontsize=9, title="Keterangan Elemen Graf", title_fontsize=10
    )

    out_path = OUTPUT_DIR / "peta_jaringan_evakuasi.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def plot_four_scenarios(graph: EvacuationGraph) -> Path:
    """Membuat 4 subplot perbandingan rute evakuasi hasil pencarian optimal."""
    scenarios = [
        ("Ulee_Lheue", "Skenario 1: Pelabuhan Ulee Lheue (Pesisir Barat Daya)"),
        ("Lampulo", "Skenario 2: Pelabuhan Perikanan Lampulo (Pesisir Timur Laut)"),
        ("Peunayong", "Skenario 3: Kawasan Komersial Peunayong (Krueng Aceh)"),
        ("Cut_Mutia", "Skenario 4: Kawasan Jalan Cut Mutia (Kota Lama)")
    ]

    fig, axes = plt.subplots(2, 2, figsize=(18, 16), dpi=300)
    axes = axes.flatten()

    for idx, (start_id, title) in enumerate(scenarios):
        ax = axes[idx]
        draw_base_network(ax, graph, title=title)

        # Cari rute optimal menggunakan A* Search
        res_a_star = a_star_search(graph, start_id, closest_shelter_heuristic)
        res_ucs = uniform_cost_search(graph, start_id)
        path = res_a_star.path

        # Gambar garis rute evakuasi bercahaya (glow effect)
        for i in range(len(path) - 1):
            u = graph.nodes[path[i]]
            v = graph.nodes[path[i + 1]]
            
            # Glow luar
            ax.plot([u.x, v.x], [u.y, v.y], color=COLOR_PALETTE["route_glow"], lw=7, alpha=0.6, zorder=3)
            # Garis rute utama
            ax.plot([u.x, v.x], [u.y, v.y], color=COLOR_PALETTE["route"], lw=3.5, zorder=4)
            # Panah arah evakuasi
            ax.annotate(
                "", xy=(v.x, v.y), xytext=(u.x, u.y),
                arrowprops=dict(arrowstyle="-|>", color="#991B1B", lw=2, mutation_scale=16),
                zorder=4
            )

        # Hitung jarak fisik kumulatif
        path_distance = 0.0
        for i in range(len(path) - 1):
            e = graph.get_edge(path[i], path[i + 1])
            if e:
                path_distance += e.distance_km

        # Kotak Informasi Metrik Kinerja
        savings = ((res_ucs.nodes_expanded - res_a_star.nodes_expanded) / res_ucs.nodes_expanded * 100) if res_ucs.nodes_expanded > 0 else 0
        info_text = (
            f"Shelter Tujuan: {graph.nodes[path[-1]].name.split('(')[0].strip()}\n"
            f"Total Jarak Fisik: {path_distance:.2f} km\n"
            f"Total Biaya Riil (C*): {res_a_star.total_cost:.4f}\n"
            f"Simpul Diekspansi UCS : {res_ucs.nodes_expanded}\n"
            f"Simpul Diekspansi A*  : {res_a_star.nodes_expanded} (Hemat {savings:.1f}%)"
        )
        ax.text(
            0.03, 0.04, info_text, transform=ax.transAxes,
            fontsize=9, verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.5", fc="#EFF6FF", ec="#3B82F6", lw=1.2, alpha=0.95),
            zorder=10
        )

    out_path = OUTPUT_DIR / "skenario_rute_evakuasi.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def plot_performance_benchmark(graph: EvacuationGraph) -> Path:
    """Membuat grafik batang ilmiah komparasi efisiensi UCS vs A* Search."""
    hazard_nodes = ["Ulee_Lheue", "Lampulo", "Peunayong", "Cut_Mutia"]
    labels = ["Ulee Lheue", "Lampulo", "Peunayong", "Cut Mutia"]

    ucs_expansions = []
    astar_expansions = []
    ucs_runtimes = []
    astar_runtimes = []

    for node_id in hazard_nodes:
        res_ucs = uniform_cost_search(graph, node_id)
        res_astar = a_star_search(graph, node_id, closest_shelter_heuristic)
        ucs_expansions.append(res_ucs.nodes_expanded)
        astar_expansions.append(res_astar.nodes_expanded)
        ucs_runtimes.append(res_ucs.execution_time_ms)
        astar_runtimes.append(res_astar.execution_time_ms)

    x = np.arange(len(labels))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

    # 1. Grafik Jumlah Simpul Diekspansi
    rects1 = ax1.bar(x - width/2, ucs_expansions, width, label="Uniform Cost Search (UCS)", color="#3B82F6", edgecolor="#1D4ED8")
    rects2 = ax1.bar(x + width/2, astar_expansions, width, label="A* Search (Euclidean Heuristic)", color="#10B981", edgecolor="#047857")

    ax1.set_title("Efisiensi Pencarian: Jumlah Simpul yang Diekspansi\n(Lebih rendah = Lebih efisien)", fontsize=11, fontweight="bold", color=COLOR_PALETTE["text_dark"])
    ax1.set_ylabel("Jumlah Simpul Diekspansi", fontsize=10, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9.5)
    ax1.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#E2E8F0")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)
    ax1.set_ylim(0, max(ucs_expansions) + 2)

    # Nilai di atas bar
    for rect in rects1:
        height = rect.get_height()
        ax1.annotate(f"{height}", xy=(rect.get_x() + rect.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")
    for rect in rects2:
        height = rect.get_height()
        ax1.annotate(f"{height}", xy=(rect.get_x() + rect.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")

    # 2. Grafik Penghematan Persentase (%)
    savings = [((u - a) / u * 100) if u > 0 else 0 for u, a in zip(ucs_expansions, astar_expansions)]
    colors_bar = ["#64748B" if s == 0 else "#059669" for s in savings]
    rects3 = ax2.bar(labels, savings, width=0.45, color=colors_bar, edgecolor="#064E3B")

    ax2.set_title("Persentase Penghematan Ruang Pencarian oleh A*\nFormula: (Exp_UCS - Exp_A*) / Exp_UCS * 100%", fontsize=11, fontweight="bold", color=COLOR_PALETTE["text_dark"])
    ax2.set_ylabel("Penghematan Ekspansi Simpul (%)", fontsize=10, fontweight="bold")
    ax2.set_ylim(0, 35)
    ax2.grid(axis="y", linestyle="--", alpha=0.5)

    for rect in rects3:
        height = rect.get_height()
        ax2.annotate(f"{height:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9.5, fontweight="bold")

    plt.suptitle("EVALUASI KINERJA KOMPARATIF: UNIFORM COST SEARCH VS A* SEARCH\nStudi Kasus Evakuasi Tsunami BPBD Kota Banda Aceh", fontsize=12, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.92])
    out_path = OUTPUT_DIR / "perbandingan_kinerja_ucs_vs_astar.png"
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def generate_all_visualizations(show_gui: bool = False):
    """Menjalankan seluruh pipeline pembuatan gambar dan visualisasi."""
    print("=" * 80)
    print("         MEMPROSES PEMBUATAN VISUALISASI GRAF & HASIL PENCARIAN")
    print("=" * 80)
    
    graph = build_banda_aceh_graph()
    
    print("[1/3] Merender Peta Ikhtisar Graf Jaringan Evakuasi...")
    peta_path = plot_overview_map(graph)
    print(f"      -> Tersimpan: {peta_path}")
    
    print("[2/3] Merender 4 Skenario Rute Evakuasi Optimal...")
    skenario_path = plot_four_scenarios(graph)
    print(f"      -> Tersimpan: {skenario_path}")

    print("[3/3] Merender Grafik Batang Benchmark Kinerja UCS vs A*...")
    benchmark_path = plot_performance_benchmark(graph)
    print(f"      -> Tersimpan: {benchmark_path}")

    print("=" * 80)
    print(" [SELESAI] Seluruh gambar berhasil dibuat dengan resolusi tinggi (300 DPI)!")
    print(f" Folder output gambar: {OUTPUT_DIR.resolve()}")
    print("=" * 80)


if __name__ == "__main__":
    generate_all_visualizations()
