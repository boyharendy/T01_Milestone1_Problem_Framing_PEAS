"""Offline tests for the genetic-algorithm evacuation solver."""

import json

import pytest

from src import ga_solver
from src.ga_solver import GASettings, TsunamiVRPGeneticAlgorithm


@pytest.fixture
def matrix_path(tmp_path):
    """Create a small deterministic matrix without requiring OSM or a network."""
    matrix = {
        "danger_ids": ["Danger_A", "Danger_B"],
        "shelter_ids": ["Shelter_A", "Shelter_B"],
        "time_min": [[5.0, 12.0], [14.0, 9.0]],
        "distance_m": [[1000.0, 2400.0], [2800.0, 1800.0]],
        "demands": [70, 60],
        "capacities": [200, 200],
    }
    path = tmp_path / "distance_matrix.json"
    path.write_text(json.dumps(matrix), encoding="utf-8")
    return path


def make_solver(matrix_path, **overrides):
    settings_values = {
        "num_trucks": 2,
        "truck_capacity": 200,
        "pop_size": 4,
        "generations": 4,
        "mutation_rate": 0.5,
        "tournament_size": 2,
        "elitism_count": 1,
    }
    settings_values.update(overrides)
    settings = GASettings(**settings_values)
    return TsunamiVRPGeneticAlgorithm(str(matrix_path), settings)


def test_init_population_encodes_valid_gene_ranges(matrix_path):
    solver = make_solver(matrix_path)

    population = solver.init_population()

    assert len(population) == solver.settings.pop_size
    assert all(len(chromosome) == solver.chrom_len for chromosome in population)
    for chromosome in population:
        truck_shelters = chromosome[:solver.num_trucks]
        danger_trucks = chromosome[solver.num_trucks:]
        assert all(0 <= shelter < solver.num_shelters for shelter in truck_shelters)
        assert all(0 <= truck < solver.num_trucks for truck in danger_trucks)


def test_fitness_for_feasible_plan_has_no_penalty(matrix_path):
    solver = make_solver(matrix_path)
    chromosome = [0, 1, 0, 1]

    fitness, total_time, penalty = solver.evaluate_fitness(chromosome)

    assert total_time == pytest.approx(14.0)
    assert penalty == pytest.approx(0.0)
    assert fitness == pytest.approx(1 / (23.0 + 1e-6))


def test_fitness_penalizes_truck_capacity_violation(matrix_path):
    solver = make_solver(matrix_path, truck_capacity=100)
    chromosome = [0, 1, 0, 0]

    fitness, total_time, penalty = solver.evaluate_fitness(chromosome)

    assert total_time == pytest.approx(19.0)
    assert penalty == pytest.approx(30 * ga_solver.PENALTY_CAPACITY_WEIGHT)
    assert fitness == pytest.approx(1 / (38.0 + 3000.0 + 1e-6))


def test_fitness_penalizes_tsunami_time_limit_violation(matrix_path):
    solver = make_solver(matrix_path, truck_capacity=200)
    chromosome = [1, 0, 0, 0]

    fitness, total_time, penalty = solver.evaluate_fitness(chromosome)

    assert total_time == pytest.approx(21.0)
    assert penalty == pytest.approx(ga_solver.PENALTY_TIME_WEIGHT)
    assert fitness == pytest.approx(1 / (42.0 + 1000.0 + 1e-6))


def test_unreachable_assignment_returns_minimum_fitness(matrix_path):
    solver = make_solver(matrix_path)
    solver.time_min[0][0] = float("inf")

    fitness, total_time, penalty = solver.evaluate_fitness([0, 1, 0, 1])

    assert fitness == pytest.approx(1e-9)
    assert total_time == float("inf")
    assert penalty == float("inf")


def test_tournament_selection_returns_best_sampled_individual(matrix_path, monkeypatch):
    solver = make_solver(matrix_path, pop_size=3, tournament_size=3)
    population = [[0, 0, 0, 0], [1, 1, 1, 1], [0, 1, 1, 0]]
    sampled_indices = iter([0, 1, 2])
    monkeypatch.setattr(ga_solver.random, "randint", lambda _low, _high: next(sampled_indices))

    selected = solver.tournament_selection(population, [0.1, 0.9, 0.5])

    assert selected == population[1]
    assert selected is not population[1]


def test_crossover_combines_parent_segments(matrix_path, monkeypatch):
    solver = make_solver(matrix_path)
    monkeypatch.setattr(ga_solver.random, "random", lambda: 0.0)
    monkeypatch.setattr(ga_solver.random, "randint", lambda _low, _high: 2)
    parent1 = [0, 1, 0, 1]
    parent2 = [1, 0, 1, 0]

    child1, child2 = solver.crossover(parent1, parent2)

    assert child1 == [0, 1, 1, 0]
    assert child2 == [1, 0, 0, 1]
    assert parent1 == [0, 1, 0, 1]
    assert parent2 == [1, 0, 1, 0]


def test_mutation_keeps_gene_values_in_valid_ranges(matrix_path, monkeypatch):
    solver = make_solver(matrix_path, mutation_rate=1.0)
    monkeypatch.setattr(ga_solver.random, "random", lambda: 0.0)
    monkeypatch.setattr(ga_solver.random, "randint", lambda _low, high: high)
    chromosome = [0, 0, 0, 0]

    solver.mutate(chromosome)

    assert chromosome == [1, 1, 1, 1]


def test_evolve_returns_valid_best_plan_and_monotonic_elite_history(matrix_path):
    solver = make_solver(matrix_path, pop_size=8, generations=6, elitism_count=2)

    result = solver.evolve()
    plan = solver.decode_chromosome(result["best_chromosome"])
    best_fitness_by_generation = [entry["best_fitness"] for entry in result["history"]]

    assert len(result["history"]) == solver.settings.generations
    assert len(result["best_chromosome"]) == solver.chrom_len
    assert result["best_fitness"] == pytest.approx(max(best_fitness_by_generation))
    assert all(
        earlier <= later
        for earlier, later in zip(best_fitness_by_generation, best_fitness_by_generation[1:])
    )
    assert plan
    for truck_plan in plan.values():
        assert set(truck_plan) == {"danger_zones", "shelter", "total_demand", "total_time_min"}
        assert truck_plan["shelter"] in solver.shelter_ids
        assert all(danger in solver.danger_ids for danger in truck_plan["danger_zones"])


def test_missing_distance_matrix_raises_clear_error(tmp_path):
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError, match="Distance matrix file not found"):
        TsunamiVRPGeneticAlgorithm(str(missing_path), GASettings())