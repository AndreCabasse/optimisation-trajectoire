# Optimisation Partielle de Trajectoire

## 🎯 Nouvelle Fonctionnalité

Le programme permet maintenant de choisir **à partir de quel point** commencer l'optimisation de trajectoire. 

Cette fonctionnalité est particulièrement utile pour :
- 🛫 Conserver la phase de décollage et montée intacte
- ✈️ Optimiser uniquement la phase de croisière
- 🛬 Préserver la descente et l'approche finale
- 📊 Analyser l'impact de l'optimisation sur différentes phases de vol

## 📝 Utilisation

### Option 1 : Départ basé sur le TEMPS

Optimiser la trajectoire après un certain temps écoulé depuis le départ :

```python
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod

optimizer = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)

# Optimiser après 10 minutes (600 secondes)
result = optimizer.optimize(
    trajectory,
    target_points=100,
    start_time=600  # secondes
)
```

**Cas d'usage typiques :**
- `start_time=300` (5 min) : Après la montée initiale
- `start_time=600` (10 min) : Début de la phase de croisière
- `start_time=1800` (30 min) : Milieu d'un vol moyen-courrier

### Option 2 : Départ basé sur la DISTANCE

Optimiser la trajectoire après une certaine distance parcourue :

```python
# Optimiser après 50 km parcourus (50000 mètres)
result = optimizer.optimize(
    trajectory,
    target_points=100,
    start_distance=50000  # mètres
)
```

**Cas d'usage typiques :**
- `start_distance=20000` (20 km) : Court rayon autour de l'aéroport
- `start_distance=50000` (50 km) : Zone de contrôle terminal
- `start_distance=100000` (100 km) : Entrée en espace aérien en route

### Option 3 : Optimisation complète (par défaut)

Si aucun paramètre n'est spécifié, toute la trajectoire est optimisée :

```python
# Comportement par défaut - optimise tout
result = optimizer.optimize(
    trajectory,
    target_points=100
)
```

## 🎨 Visualisation dans le Dashboard

Le dashboard Streamlit inclut maintenant :

1. **Sélecteur radio** dans la barre latérale :
   - Début de la trajectoire (optimisation complète)
   - Temps écoulé
   - Distance parcourue

2. **Curseurs dynamiques** pour choisir la valeur :
   - Temps en minutes (0 - durée du vol)
   - Distance en kilomètres (0 - distance totale)

3. **Indicateur visuel** sur le graphique d'altitude :
   - Zone verte = partie préservée
   - Ligne verticale = point de départ de l'optimisation
   - Annotation avec le temps/distance exact

## 📊 Exemple avec Code Complet

```python
"""Exemple d'optimisation de la phase de croisière uniquement"""
from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod

# Charger la trajectoire
parser = KMLParser('data/sample/vol.kml')
trajectory = parser.parse()

print(f"Durée totale : {trajectory.duration/60:.1f} minutes")
print(f"Distance totale : {trajectory.get_cumulative_distances()[-1]/1000:.1f} km")

# Configuration
optimizer = TrajectoryOptimizer(
    method=OptimizationMethod.HYBRID,
    kalman_config={'process_noise': 1.0, 'measurement_noise': 10.0},
    bspline_config={'degree': 3}
)

# Optimiser seulement après 10 minutes (phase de croisière)
result = optimizer.optimize(
    trajectory,
    target_points=80,
    start_time=600  # 10 minutes en secondes
)

# Afficher les résultats
print(f"\nPoints originaux : {len(trajectory)}")
print(f"Points finaux : {len(result.optimized_positions)}")
print(f"Compression : {result.metrics['compression_ratio']:.2%}")

# Calculer combien de points ont été préservés
start_idx = trajectory.find_index_by_time(600)
print(f"\nPoints préservés : {start_idx}")
print(f"Points optimisés : {len(trajectory) - start_idx}")
```

## 🔧 Fonctionnement Interne

### Méthodes ajoutées à la classe `Trajectory`

1. **`get_cumulative_distances()`**
   - Calcule la distance cumulative le long de la trajectoire en mètres
   - Retourne un array NumPy avec la distance totale parcourue à chaque point

2. **`find_index_by_time(elapsed_seconds)`**
   - Trouve l'index du point le plus proche d'un temps donné
   - Utilise `np.argmin` pour la recherche efficace

3. **`find_index_by_distance(distance_meters)`**
   - Trouve l'index du point le plus proche d'une distance donnée
   - Utilise les distances cumulatives calculées

### Modifications dans `TrajectoryOptimizer.optimize()`

```python
def optimize(
    self,
    trajectory: Trajectory,
    use_weather: bool = False,
    target_points: Optional[int] = None,
    start_time: Optional[float] = None,      # NOUVEAU
    start_distance: Optional[float] = None   # NOUVEAU
) -> OptimizedTrajectory:
    """
    Si start_time ou start_distance est spécifié :
    1. Trouve l'index correspondant dans la trajectoire
    2. Divise la trajectoire en deux parties :
       - Partie préservée (positions[:start_idx])
       - Partie à optimiser (positions[start_idx:])
    3. Applique l'optimisation uniquement sur la 2e partie
    4. Combine les deux parties pour obtenir le résultat final
    """
```

## 📈 Cas d'Usage Avancés

### 1. Optimiser uniquement la descente

```python
# Trouver où commence la descente (altitude max)
coords = trajectory.get_coordinates_array()
max_alt_idx = np.argmax(coords[:, 2])
descent_time = trajectory.get_timestamps()[max_alt_idx]

# Optimiser à partir de ce point
result = optimizer.optimize(trajectory, start_time=descent_time)
```

### 2. Optimisation multi-segments

Voir le fichier [example_partial_optimization.py](../examples/example_partial_optimization.py) pour un exemple complet.

```python
# Diviser manuellement en segments
t1, t2 = 600, 3000  # 10 min et 50 min
idx1 = trajectory.find_index_by_time(t1)
idx2 = trajectory.find_index_by_time(t2)

# Segment 1 : inchangé
seg1 = trajectory.positions[:idx1]

# Segment 2 : optimisation forte
traj2 = Trajectory(trajectory.positions[idx1:idx2])
opt2 = optimizer_cruise.optimize(traj2, target_points=30)

# Segment 3 : optimisation légère
traj3 = Trajectory(trajectory.positions[idx2:])
opt3 = optimizer_light.optimize(traj3)

# Combiner
final = seg1 + opt2.optimized_positions + opt3.optimized_positions
```

## 🚀 Lancer les Exemples

### Dashboard interactif
```bash
cd examples
streamlit run dashboard.py
```

Utilisez les contrôles dans la barre latérale pour tester différents points de départ.

### Script d'exemple
```bash
cd examples
python example_partial_optimization.py
```

Ce script génère :
- Comparaison de 5 approches différentes
- Graphiques et cartes interactives
- Métriques détaillées
- Visualisation dans `output/partial_optimization/`

## 💡 Recommandations

### Pour un vol commercial typique

1. **Décollage et montée** (0-10 min) : **Préserver**
   - Trajectoire dict
ée par le contrôle aérien
   - Contraintes strictes de séparation

2. **Croisière** (10-50 min) : **Optimiser agressivement**
   - Grande liberté de route
   - Potentiel maximum d'économie de carburant
   - Utiliser `start_time=600` (10 min)

3. **Descente et approche** (50-60 min) : **Optimiser légèrement**
   - Contraintes de l'approche finale
   - Considérer `start_time` pour fin de croisière

### Choix entre temps et distance

- **Utiliser `start_time`** quand :
  - Les phases de vol sont basées sur le temps
  - Vous connaissez la durée des manœuvres
  - Analyse temporelle importante

- **Utiliser `start_distance`** quand :
  - Les zones géographiques sont importantes
  - Espaces aériens définis par distance
  - Optimisation basée sur la géographie

## 📚 Fichiers Modifiés

- `src/data/data_models.py` : Méthodes de recherche dans Trajectory
- `src/optimization/trajectory_optimizer.py` : Paramètres start_time et start_distance
- `examples/dashboard.py` : Interface Streamlit avec sélecteurs
- `examples/example_partial_optimization.py` : Exemples d'utilisation

## ⚙️ Tests

Pour tester la fonctionnalité :

```bash
# Test avec trajectoire synthétique
cd examples
python example_partial_optimization.py

# Test avec vos données KML
python -c "
from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod

parser = KMLParser('votre_fichier.kml')
traj = parser.parse()

opt = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
result = opt.optimize(traj, target_points=100, start_time=300)

print(f'Compression: {result.metrics[\"compression_ratio\"]:.2%}')
"
```

## 🎓 En Résumé

Cette fonctionnalité vous permet de :
- ✅ Choisir précisément où commencer l'optimisation
- ✅ Préserver les phases critiques (décollage, approche)
- ✅ Optimiser intelligemment par phase de vol
- ✅ Visualiser clairement les zones préservées vs optimisées
- ✅ Adapter l'optimisation au contexte opérationnel

---

**Auteur :** Projet ENAC 2A - Optimisation de Trajectoires  
**Date :** Février 2026
