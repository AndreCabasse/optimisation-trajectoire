# Guide de démarrage rapide

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation de base

### 1. Avec vos propres données KML

```python
from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod

# Charger la trajectoire
parser = KMLParser('chemin/vers/votre_vol.kml')
trajectory = parser.parse()

# Optimiser
optimizer = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
result = optimizer.optimize(trajectory, target_points=100)

print(f"Compression: {result.metrics['compression_ratio']:.2%}")
print(f"Smoothness: {result.metrics['smoothness']:.2f}")
```

### 2. Avec l'exemple fourni

```bash
cd examples
python optimize_trajectory.py
```

Cela générera :
- `output/comparison.png` - Comparaison des trajectoires
- `output/trajectory_map.html` - Carte interactive

## Méthodes disponibles

### Filtre de Kalman
Idéal pour éliminer le bruit des données ADS-B :

```python
from src.filters.kalman_filter import KalmanFilter

kalman = KalmanFilter(
    process_noise=1.0,
    measurement_noise=10.0
)
smoothed = kalman.smooth_trajectory(trajectory)
```

### B-spline
Pour l'interpolation et la réduction du nombre de points :

```python
from src.optimization.bspline import BSplineOptimizer

bspline = BSplineOptimizer(degree=3)
optimized = bspline.optimize(trajectory, target_points=50)
```

### Hybride (Recommandé)
Combine Kalman et B-spline :

```python
optimizer = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
result = optimizer.optimize(trajectory, target_points=100)
```

### Avec météo
Intègre les données de vent :

```python
optimizer = TrajectoryOptimizer(
    method=OptimizationMethod.WEATHER,
    weather_api_key="YOUR_API_KEY"  # ou None pour simulation
)
result = optimizer.optimize(trajectory, use_weather=True)
```

## Obtenir des données KML

### OpenSky Network
1. Visitez https://opensky-network.org/
2. Recherchez un vol
3. Exportez en format KML

### FlightRadar24
1. Recherchez un vol sur https://www.flightradar24.com/
2. Téléchargez les données (compte premium requis)

## Structure des fichiers

```
votre_projet/
├── data/
│   └── sample/
│       └── votre_vol.kml
├── examples/
│   └── optimize_trajectory.py
├── output/
│   ├── comparison.png
│   └── trajectory_map.html
└── src/
    ├── data/           # Parsing KML
    ├── filters/        # Filtre de Kalman
    ├── optimization/   # B-spline et optimiseur
    ├── weather/        # API météo
    └── utils/          # Visualisation
```

## Prochaines étapes

1. **Récupérer des données réelles** depuis OpenSky Network
2. **Tester différentes méthodes** d'optimisation
3. **Ajuster les paramètres** selon vos besoins
4. **Intégrer l'API météo** pour des optimisations réalistes
5. **Étendre le modèle** avec vos propres algorithmes

## Ressources

- [OpenSky Network](https://opensky-network.org/)
- [Documentation Kalman Filter](https://en.wikipedia.org/wiki/Kalman_filter)
- [B-splines](https://docs.scipy.org/doc/scipy/reference/interpolate.html)
- [OpenWeatherMap API](https://openweathermap.org/api)
