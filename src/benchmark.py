"""Benchmark genetic-algorithm runtime and convergence at two problem scales.

The repository matrix currently contains four danger locations. The small
scenario uses two existing rows; the large scenario retains those source rows
and adds clearly labelled synthetic rows to reach the required ten locations.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from src.ga_solver import GASettings, TsunamiVRPGeneticAlgorithm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MATRIX_PATH = PROJECT_ROOT / "data" / "distance_matrix.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def _load_matrix(path: Path) -> dict[str, Any]:
    """Load and validate the JSON matrix expected by the GA solver."""
    if not path.is_file():
        raise FileNotFoundError(f"Distance matrix file not found: {path}")

    matrix = json.loads(path.read_text(encoding="utf-8"))
    required = {"danger_ids", "shelter_ids", "time_min", "distance_m", "demands", "capacities"}
    missing = required.difference(matrix)
    if missing:
        raise ValueError(f"Distance matrix is missing fields: {', '.join(sorted(missing))}")

    danger_count = len(matrix["danger_ids"])
    shelter_count = len(matrix["shelter_ids"])
    if danger_count == 0 or shelter_count == 0:
        raise ValueError("Distance matrix must contain at least one danger and one shelter")
    if len(matrix["demands"]) != danger_count or len(matrix["capacities"]) != shelter_count:
        raise ValueError("Demand/capacity lengths do not match the matrix IDs")
    for key in ("time_min", "distance_m"):
        values = matrix[key]
        if len(values) != danger_count or any(len(row) != shelter_count for row in values):
            raise ValueError(f"'{key}' dimensions do not match danger and shelter IDs")
    return matrix


def _make_scenario_matrix(
    source: dict[str, Any], danger_count: int
) -> tuple[dict[str, Any], int]:
    """Create a matrix with the requested danger count and report synthetic rows."""
    source_count = len(source["danger_ids"])
    if danger_count < 1:
        raise ValueError("danger_count must be positive")

    result = dict(source)
    result["danger_ids"] = list(source["danger_ids"][:danger_count])
    result["demands"] = list(source["demands"][:danger_count])
    result["time_min"] = [list(row) for row in source["time_min"][:danger_count]]
    result["distance_m"] = [list(row) for row in source["distance_m"][:danger_count]]
    synthetic_count = 0

    for index in range(source_count, danger_count):
        source_index = index % source_count
        synthetic_number = index + 1
        # Slight deterministic variation avoids making all generated rows identical.
        scale = 1.0 + 0.025 * (index - source_count + 1)
        result["danger_ids"].append(f"Synthetic_Danger_{synthetic_number:02d}")
        result["demands"].append(source["demands"][source_index])
        for key in ("time_min", "distance_m"):
            row = source[key][source_index]
            result[key].append([None if value is None else float(value) * scale for value in row])
        synthetic_count += 1

    return result, synthetic_count


def _run_scenario(
    matrix: dict[str, Any],
    *,
    scenario_name: str,
    num_trucks: int,
    synthetic_dangers: int,
    repeats: int,
    seed: int,
    population_size: int,
    generations: int,
    truck_capacity: int,
    working_dir: Path,
) -> dict[str, Any]:
    """Run repeated GA trials and aggregate runtime and generation fitness."""
    matrix_path = working_dir / f"{scenario_name}_matrix.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")

    trial_runtimes: list[float] = []
    trial_best_fitness: list[float] = []
    trial_histories: list[list[float]] = []

    for trial in range(repeats):
        random.seed(seed + trial)
        settings = GASettings(
            num_trucks=num_trucks,
            truck_capacity=truck_capacity,
            pop_size=population_size,
            generations=generations,
            mutation_rate=0.1,
            tournament_size=min(5, population_size),
            elitism_count=min(2, population_size - 1),
        )
        solver = TsunamiVRPGeneticAlgorithm(str(matrix_path), settings)

        started = time.perf_counter()
        result = solver.evolve()
        trial_runtimes.append(time.perf_counter() - started)
        trial_best_fitness.append(float(result["best_fitness"]))
        trial_histories.append([float(item["best_fitness"]) for item in result["history"]])

    mean_history = [
        statistics.fmean(history[generation] for history in trial_histories)
        for generation in range(generations)
    ]
    return {
        "scenario": scenario_name,
        "num_trucks": num_trucks,
        "num_dangers": len(matrix["danger_ids"]),
        "num_shelters": len(matrix["shelter_ids"]),
        "synthetic_dangers": synthetic_dangers,
        "repeats": repeats,
        "runtime_seconds": trial_runtimes,
        "mean_runtime_seconds": statistics.fmean(trial_runtimes),
        "stdev_runtime_seconds": statistics.stdev(trial_runtimes) if repeats > 1 else 0.0,
        "best_fitness_by_trial": trial_best_fitness,
        "mean_best_fitness": statistics.fmean(trial_best_fitness),
        "mean_fitness_by_generation": mean_history,
    }


def _save_runtime_plot(results: list[dict[str, Any]], path: Path) -> None:
    labels = [
        f"{item['scenario']}\n{item['num_trucks']} truk, {item['num_dangers']} titik"
        for item in results
    ]
    means = [item["mean_runtime_seconds"] for item in results]
    errors = [item["stdev_runtime_seconds"] for item in results]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, means, yerr=errors, capsize=5, color=["#2a9d8f", "#e76f51"])
    ax.bar_label(bars, labels=[f"{value:.4f} s" for value in means], padding=4)
    ax.set_title("Waktu Komputasi Genetic Algorithm")
    ax.set_ylabel("Waktu rata-rata per evolusi (detik)")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _save_convergence_plot(results: list[dict[str, Any]], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for item in results:
        generations = range(1, len(item["mean_fitness_by_generation"]) + 1)
        ax.plot(generations, item["mean_fitness_by_generation"], label=item["scenario"])
    ax.set_title("Konvergensi Fitness Genetic Algorithm")
    ax.set_xlabel("Generasi")
    ax.set_ylabel("Fitness terbaik rata-rata")
    ax.legend()
    ax.grid(linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_benchmarks(
    matrix_path: Path = DEFAULT_MATRIX_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    repeats: int = 3,
    seed: int = 42,
    population_size: int = 50,
    generations: int = 50,
    truck_capacity: int = 600,
) -> dict[str, Any]:
    """Run the rubric's small and large scenarios and save plots and JSON."""
    if repeats < 1 or population_size < 2 or generations < 1 or truck_capacity < 1:
        raise ValueError("repeats/generations/truck_capacity must be positive; population_size must be at least 2")

    source = _load_matrix(Path(matrix_path))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scenario_specs = (("Kecil", 3, 2), ("Besar", 15, 10))
    results = []
    # Store temporary scenario matrices outside the repository output directory.
    import tempfile

    with tempfile.TemporaryDirectory(prefix="evacuation-ga-benchmark-") as temp_dir:
        working_dir = Path(temp_dir)
        for name, truck_count, danger_count in scenario_specs:
            scenario_matrix, synthetic_count = _make_scenario_matrix(source, danger_count)
            results.append(
                _run_scenario(
                    scenario_matrix,
                    scenario_name=name,
                    num_trucks=truck_count,
                    synthetic_dangers=synthetic_count,
                    repeats=repeats,
                    seed=seed,
                    population_size=population_size,
                    generations=generations,
                    truck_capacity=truck_capacity,
                    working_dir=working_dir,
                )
            )

    summary = {
        "source_matrix": str(Path(matrix_path)),
        "source": source.get("source", "unspecified"),
        "seed": seed,
        "population_size": population_size,
        "generations": generations,
        "truck_capacity": truck_capacity,
        "note": (
            "The large scenario includes synthetic danger rows because the source matrix "
            "contains fewer than ten danger locations. Source coordinates and demand values "
            "also require verification before operational interpretation; synthetic results "
            "are for scale testing, not real-location route claims."
        ),
        "results": results,
    }
    (output_dir / "benchmark_results.json").write_text(
        json.dumps(summary, indent=2, allow_nan=True), encoding="utf-8"
    )
    _save_runtime_plot(results, output_dir / "benchmark_runtime.png")
    _save_convergence_plot(results, output_dir / "benchmark_convergence.png")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark GA runtime and convergence at two problem scales.")
    parser.add_argument("--matrix-path", type=Path, default=DEFAULT_MATRIX_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--population-size", type=int, default=50)
    parser.add_argument("--generations", type=int, default=50)
    parser.add_argument("--truck-capacity", type=int, default=600)
    args = parser.parse_args()

    summary = run_benchmarks(
        args.matrix_path,
        args.output_dir,
        repeats=args.repeats,
        seed=args.seed,
        population_size=args.population_size,
        generations=args.generations,
        truck_capacity=args.truck_capacity,
    )
    print("Skenario | Truk | Titik bahaya | Sintetis | Waktu rata-rata (s) | Fitness terbaik rata-rata")
    for result in summary["results"]:
        print(
            f"{result['scenario']:<8} | {result['num_trucks']:>4} | "
            f"{result['num_dangers']:>12} | {result['synthetic_dangers']:>8} | "
            f"{result['mean_runtime_seconds']:>19.6f} | {result['mean_best_fitness']:.8f}"
        )
    print(f"\nGrafik dan ringkasan disimpan di: {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()