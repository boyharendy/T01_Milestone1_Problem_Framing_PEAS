import random
import numpy as np
import logging
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import json
import math
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants
TSUNAMI_LIMIT_MIN = 20.0
PENALTY_CAPACITY_WEIGHT = 100.0
PENALTY_TIME_WEIGHT = 1000.0
PENALTY_SHELTER_CAP_WEIGHT = 50.0

@dataclass
class GASettings:
    num_trucks: int = 15
    truck_capacity: int = 100
    pop_size: int = 100
    generations: int = 200
    mutation_rate: float = 0.1
    tournament_size: int = 5
    elitism_count: int = 2

class TsunamiVRPGeneticAlgorithm:
    def __init__(self, distance_matrix_path: str, settings: GASettings):
        self.settings = settings
        
        # Load Data from JSON
        path = Path(distance_matrix_path)
        if not path.exists():
            raise FileNotFoundError(f"Distance matrix file not found: {path}")
            
        data = json.loads(path.read_text(encoding="utf-8"))
        self.danger_ids = data["danger_ids"]
        self.shelter_ids = data["shelter_ids"]
        
        # Replace null/None with infinity
        to_inf = lambda x: float('inf') if x is None else float(x)
        self.time_min = [[to_inf(v) for v in row] for row in data["time_min"]]
        self.distance_m = [[to_inf(v) for v in row] for row in data["distance_m"]]
        
        self.demands = data["demands"]
        self.capacities = data["capacities"]
        
        self.num_dangers = len(self.danger_ids)
        self.num_shelters = len(self.shelter_ids)
        self.num_trucks = settings.num_trucks
        
        # Chromosome length = num_trucks (shelter for each truck) + num_dangers (truck for each danger zone)
        self.chrom_len = self.num_trucks + self.num_dangers

    def init_population(self) -> List[List[int]]:
        """Generate initial random population"""
        population = []
        for _ in range(self.settings.pop_size):
            # Shelter assignment for each truck
            truck_shelters = [random.randint(0, self.num_shelters - 1) for _ in range(self.num_trucks)]
            # Truck assignment for each danger zone
            danger_trucks = [random.randint(0, self.num_trucks - 1) for _ in range(self.num_dangers)]
            population.append(truck_shelters + danger_trucks)
        return population

    def evaluate_fitness(self, chromosome: List[int]) -> Tuple[float, float, float]:
        """
        Evaluate chromosome.
        Returns: (fitness, total_time, total_penalty)
        """
        truck_shelters = chromosome[:self.num_trucks]
        danger_trucks = chromosome[self.num_trucks:]
        
        total_time = 0.0
        max_time = 0.0
        penalty = 0.0
        
        shelter_loads = [0] * self.num_shelters
        
        for t in range(self.num_trucks):
            s = truck_shelters[t]
            assigned_dangers = [d for d in range(self.num_dangers) if danger_trucks[d] == t]
            
            if not assigned_dangers:
                continue
                
            truck_time = 0.0
            truck_load = 0
            
            for d in assigned_dangers:
                truck_load += self.demands[d]
                # Assuming truck visits danger zone and drops at shelter.
                # If multiple zones, it accumulates time.
                truck_time += self.time_min[d][s]
                
            total_time += truck_time
            max_time = max(max_time, truck_time)
            shelter_loads[s] += truck_load
            
            # Constraint 1: Truck Capacity (Penalti Berat)
            if truck_load > self.settings.truck_capacity:
                penalty += (truck_load - self.settings.truck_capacity) * PENALTY_CAPACITY_WEIGHT
                
            # Constraint 2: Time Limit (Penalti Kritis)
            if truck_time > TSUNAMI_LIMIT_MIN:
                penalty += (truck_time - TSUNAMI_LIMIT_MIN) * PENALTY_TIME_WEIGHT
                
        # Shelter Capacity Constraint
        for s in range(self.num_shelters):
            if shelter_loads[s] > self.capacities[s]:
                penalty += (shelter_loads[s] - self.capacities[s]) * PENALTY_SHELTER_CAP_WEIGHT
                
        # Handle unreachable paths (inf)
        if math.isinf(total_time) or math.isinf(penalty):
            return 1e-9, float('inf'), float('inf')
            
        # Fitness formula: 1 / (Waktu Tempuh + Penalti)
        # Using max_time (makespan) or total_time as objective. Let's minimize total_time + max_time
        objective = total_time + max_time + penalty
        fitness = 1.0 / (objective + 1e-6)
        
        return fitness, total_time, penalty

    def tournament_selection(self, population: List[List[int]], fitness_scores: List[float]) -> List[int]:
        """Tournament selection operator"""
        best_idx = -1
        best_fitness = -1.0
        for _ in range(self.settings.tournament_size):
            idx = random.randint(0, self.settings.pop_size - 1)
            if fitness_scores[idx] > best_fitness:
                best_fitness = fitness_scores[idx]
                best_idx = idx
        return population[best_idx].copy()

    def crossover(self, parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
        """Single-point crossover"""
        if random.random() < 0.8: # Crossover probability
            pt = random.randint(1, self.chrom_len - 1)
            child1 = parent1[:pt] + parent2[pt:]
            child2 = parent2[:pt] + parent1[pt:]
            return child1, child2
        return parent1.copy(), parent2.copy()

    def mutate(self, chromosome: List[int]):
        """Mutation operator"""
        for i in range(self.num_trucks):
            if random.random() < self.settings.mutation_rate:
                chromosome[i] = random.randint(0, self.num_shelters - 1)
                
        for i in range(self.num_trucks, self.chrom_len):
            if random.random() < self.settings.mutation_rate:
                chromosome[i] = random.randint(0, self.num_trucks - 1)

    def evolve(self) -> Dict:
        """Main Evolution Loop"""
        population = self.init_population()
        
        best_overall_chromosome = None
        best_overall_fitness = -1.0
        best_overall_time = float('inf')
        
        history = []
        
        for gen in range(self.settings.generations):
            # Evaluate
            evaluations = [self.evaluate_fitness(ind) for ind in population]
            fitness_scores = [e[0] for e in evaluations]
            
            # Find best in generation
            best_idx = int(np.argmax(fitness_scores))
            gen_best_fitness = fitness_scores[best_idx]
            gen_best_time = evaluations[best_idx][1]
            gen_best_penalty = evaluations[best_idx][2]
            
            if gen_best_fitness > best_overall_fitness:
                best_overall_fitness = gen_best_fitness
                best_overall_chromosome = population[best_idx].copy()
                best_overall_time = gen_best_time
                
            history.append({
                "generation": gen,
                "best_fitness": gen_best_fitness,
                "total_time": gen_best_time,
                "penalty": gen_best_penalty
            })
            
            logger.info(f"Gen {gen}: Fitness={gen_best_fitness:.6f}, Time={gen_best_time:.2f}m, Penalty={gen_best_penalty:.2f}")
            
            # Next generation
            new_population = []
            
            # Elitism
            sorted_indices = np.argsort(fitness_scores)[::-1]
            for i in range(self.settings.elitism_count):
                new_population.append(population[sorted_indices[i]].copy())
                
            # Crossover and Mutation
            while len(new_population) < self.settings.pop_size:
                p1 = self.tournament_selection(population, fitness_scores)
                p2 = self.tournament_selection(population, fitness_scores)
                
                c1, c2 = self.crossover(p1, p2)
                self.mutate(c1)
                self.mutate(c2)
                
                new_population.append(c1)
                if len(new_population) < self.settings.pop_size:
                    new_population.append(c2)
                    
            population = new_population
            
        return {
            "best_chromosome": best_overall_chromosome,
            "best_fitness": best_overall_fitness,
            "best_time": best_overall_time,
            "history": history
        }

    def decode_chromosome(self, chromosome: List[int]) -> Dict:
        """Decode chromosome into a readable plan"""
        truck_shelters = chromosome[:self.num_trucks]
        danger_trucks = chromosome[self.num_trucks:]
        
        plan = {}
        for t in range(self.num_trucks):
            assigned = [d for d in range(self.num_dangers) if danger_trucks[d] == t]
            if not assigned:
                continue
            plan[f"Truck_{t}"] = {
                "danger_zones": [self.danger_ids[d] for d in assigned],
                "shelter": self.shelter_ids[truck_shelters[t]],
                "total_demand": sum(self.demands[d] for d in assigned),
                "total_time_min": sum(self.time_min[d][truck_shelters[t]] for d in assigned)
            }
        return plan

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Skala Kecil Benchmark
    settings = GASettings(
        num_trucks=3,
        truck_capacity=200, # Large capacity for small scale test
        pop_size=50,
        generations=50
    )
    
    # Adjust path assuming this runs from src directory or root directory
    import os
    base_dir = os.path.dirname(os.path.dirname(__file__))
    matrix_path = os.path.join(base_dir, "data", "distance_matrix.json")
    
    print("Mulai Evolusi Skala Kecil...")
    solver = TsunamiVRPGeneticAlgorithm(matrix_path, settings)
    result = solver.evolve()
    
    print("\n--- Solusi Terbaik ---")
    plan = solver.decode_chromosome(result["best_chromosome"])
    print(json.dumps(plan, indent=2))
