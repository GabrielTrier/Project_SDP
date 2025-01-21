import pandas as pd
import gurobipy 
from gurobipy import Model, GRB, quicksum

def load_data():
    """Charge les données à partir des fichiers CSV."""
    brick_index_value = pd.read_csv('./bricks_index_values.csv')
    brick_rp_distances = pd.read_csv('./brick_rp_distances.csv')
    bricks = brick_index_value['brick'].tolist()
    reps = list(range(1, 5))  # 4 représentants

    distances = {
        row['brick']: [row[f'rp{i}'] for i in reps]
        for _, row in brick_rp_distances.iterrows()
    }
    
    index_values = dict(zip(brick_index_value['brick'], brick_index_value['index_value']))

    return bricks, reps, distances, index_values

def setup_model_minimize_distance(bricks, reps, distances, index_values, L=0.8, U=1.2):
    """Crée et configure le modèle Gurobi pour minimiser la distance."""
    model = Model("Minimize_Distance")

    # Variables de décision
    x = model.addVars(bricks, reps, vtype=GRB.BINARY, name="x")

    # Fonction objectif : minimiser la distance totale
    model.setObjective(
        quicksum(distances[b][r - 1] * x[b, r] for b in bricks for r in reps), GRB.MINIMIZE
    )

    # Contraintes : chaque brique est assignée à un seul représentant
    model.addConstrs(
        (quicksum(x[b, r] for r in reps) == 1 for b in bricks), name="AssignEachBrick"
    )

    # Contraintes de charge de travail dans l'intervalle [L, U]
    model.addConstrs(
        (quicksum(index_values[b] * x[b, r] for b in bricks) >= L for r in reps), name="MinWorkload"
    )
    model.addConstrs(
        (quicksum(index_values[b] * x[b, r] for b in bricks) <= U for r in reps), name="MaxWorkload"
    )

    return model, x

def setup_model_minimize_disruption(bricks, reps, index_values, initial_assignment, L=0.8, U=1.2):
    """Crée et configure le modèle Gurobi pour minimiser la perturbation."""
    model = Model("Minimize_Disruption")

    # Variables de décision
    x = model.addVars(bricks, reps, vtype=GRB.BINARY, name="x")
    y = model.addVars(bricks, reps, vtype=GRB.BINARY, name="y")

    # Fonction objectif : minimiser la perturbation pondérée par l'index
    model.setObjective(
        quicksum(index_values[b] * y[b, r] for b in bricks for r in reps), GRB.MINIMIZE
    )

    # Contraintes : chaque brick doit être attribué à un seul représentant
    model.addConstrs(
        (quicksum(x[b, r] for r in reps) == 1 for b in bricks), name="AssignEachBrick"
    )

    # Contraintes de charge de travail dans l'intervalle [L, U]
    model.addConstrs(
        (quicksum(index_values[b] * x[b, r] for b in bricks) >= L for r in reps), name="MinWorkload"
    )
    model.addConstrs(
        (quicksum(index_values[b] * x[b, r] for b in bricks) <= U for r in reps), name="MaxWorkload"
    )

    # Mesurer la perturbation
    model.addConstrs(
        (y[b, r] >= x[b, r] - (1 if initial_assignment[b] == r else 0)
         for b in bricks for r in reps), name="Disruption"
    )

    return model, x, y

def solve_model(model):
    """Résout le modèle d'optimisation."""
    model.optimize()

    if model.Status == GRB.OPTIMAL:
        print("\nSolution optimale trouvée :", model.ObjVal)
        return True
    else:
        print("\nLe modèle n'a pas trouvé de solution optimale.")
        return False

def extract_results(bricks, reps, x):
    """Extrait les résultats du modèle et retourne un DataFrame."""
    results = []
    for b in bricks:
        for r in reps:
            if x[b, r].X > 0.5:
                results.append([b, r])

    results_df = pd.DataFrame(results, columns=['Brick', 'Représentant'])
    return results_df

def main():
    """Pipeline principal pour charger les données, configurer, résoudre et afficher les résultats."""
    bricks, reps, distances, index_values = load_data()

    # Modèle pour minimiser la distance
    model_distance, x_distance = setup_model_minimize_distance(bricks, reps, distances, index_values)
    if solve_model(model_distance):
        results_distance = extract_results(bricks, reps, x_distance)
        print("Résultats pour la minimisation de la distance:")
        print(results_distance)

    # Assignation initiale
    initial_assignment = {
        4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 15: 1,   # SR 1
        10: 2, 11: 2, 12: 2, 13: 2, 14: 2,     # SR 2
        9: 3, 16: 3, 17: 3, 18: 3,             # SR 3
        1: 4, 2: 4, 3: 4, 19: 4, 20: 4, 21: 4, 22: 4  # SR 4
    }

    # Modèle pour minimiser la perturbation
    model_disruption, x_disruption, y_disruption = setup_model_minimize_disruption(
        bricks, reps, index_values, initial_assignment
    )
    if solve_model(model_disruption):
        results_disruption = extract_results(bricks, reps, x_disruption)
        print("Résultats pour la minimisation de la perturbation:")
        print(results_disruption)

if __name__ == "__main__":
    main()


'''
Solution optimale trouvée : 154.62
Résultats pour la minimisation de la distance:
    Brick  Représentant
0       1             4
1       2             4
2       3             4
3       4             1
4       5             1
5       6             1
6       7             1
7       8             1
8       9             1
9      10             3
10     11             2
11     12             1
12     13             2
13     14             2
14     15             3
15     16             3
16     17             3
17     18             2
18     19             1
19     20             1
20     21             4
21     22             4

Solution optimale trouvée : 0.1696
Résultats pour la minimisation de la perturbation:
    Brick  Représentant
0       1             4
1       2             4
2       3             4
3       4             1
4       5             1
5       6             1
6       7             1
7       8             1
8       9             3
9      10             2
10     11             3
11     12             3
12     13             2
13     14             2
14     15             1
15     16             3
16     17             3
17     18             3
18     19             4
19     20             4
20     21             4
21     22             4
'''