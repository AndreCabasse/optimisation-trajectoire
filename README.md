# Optimisation de Trajectoires d'Avions

Projet d'optimisation de trajectoires aériennes basé sur des données ADS-B (OpenSky Network) avec prise en compte des conditions météorologiques réelles.

## 📋 Description

Ce projet permet de :
- Récupérer et parser des données de trajectoires au format KML (OpenSky Network)
- Appliquer un filtre de Kalman pour le lissage et la prédiction
- Utiliser des B-splines pour l'interpolation et l'optimisation
- Intégrer des données météorologiques (vent, température, pression)
- Générer des trajectoires optimisées

## 🏗️ Structure du Projet

```
.
├── src/
│   ├── data/
│   │   ├── kml_parser.py          # Parser de fichiers KML
│   │   └── data_models.py         # Modèles de données
│   ├── filters/
│   │   └── kalman_filter.py       # Implémentation du filtre de Kalman
│   ├── optimization/
│   │   ├── bspline.py             # Interpolation B-spline
│   │   └── trajectory_optimizer.py # Optimiseur principal
│   ├── weather/
│   │   └── weather_api.py         # Intégration API météo
│   └── utils/
│       └── visualization.py       # Outils de visualisation
├── examples/
│   └── optimize_trajectory.py     # Exemple d'utilisation
├── data/
│   └── sample/                    # Données d'exemple
├── tests/
│   └── ...                        # Tests unitaires
├── requirements.txt               # Dépendances Python
└── README.md
```

## 🚀 Installation

```bash
pip install -r requirements.txt
```

## 📦 Dépendances Principales

- `numpy` - Calculs numériques
- `scipy` - Optimisation et B-splines
- `lxml` - Parsing XML/KML
- `matplotlib` - Visualisation
- `requests` - Requêtes API météo
- `pyproj` - Conversions de coordonnées

## 💻 Utilisation

### Interface Graphique (Recommandé)

**Dashboard Streamlit Amélioré** - Interface professionnelle et intuitive :
```bash
cd examples
streamlit run dashboard_improved.py
```

**Fonctionnalités du Dashboard :**
- 🎨 Design moderne avec CSS personnalisé
- 📊 4 graphiques de comparaison (altitude, vitesse, montée, courbure)
- 🎯 Sélection point de départ d'optimisation
- 💾 Export des résultats en CSV
- 📖 Guide d'utilisation intégré
- ⚡ Feedback visuel en temps réel

Voir [DASHBOARD_IMPROVEMENTS.md](DASHBOARD_IMPROVEMENTS.md) pour tous les détails.

### Utilisation Programmatique

```python
from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod

# Charger les données
parser = KMLParser('data/flight_trajectory.kml')
trajectory = parser.parse()

# Optimiser avec point de départ personnalisé
optimizer = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
optimized = optimizer.optimize(
    trajectory, 
    target_points=100,
    start_time=600  # Optimiser après 10 minutes
)

# Afficher les métriques
print(f"Compression: {optimized.metrics['compression_ratio']:.2%}")
```

## 📊 Méthodes d'Optimisation

Le projet propose **5 méthodes d'optimisation** différentes :

### 1. Filtre de Kalman
- ✅ Lissage des données bruitées ADS-B
- ✅ Estimation de la vitesse et de l'accélération
- ⚡ Ultra-rapide (0.04s)
- ⚠️ Ne réduit pas le nombre de points

### 2. B-spline
- ✅ Interpolation lisse par courbes cubiques
- ✅ Compression des données (60% de réduction)
- ⚡ Très rapide (0.002s)
- ✅ Contrôle de la courbure et continuité

### 3. Hybride (Kalman + B-spline)
- 🏆 **RECOMMANDÉ** - Meilleur compromis qualité/performance
- ✅ Combine le lissage et la compression
- ✅ Smoothness optimale (25,029 vs 147,624 original)
- ✅ 60% de compression avec excellente qualité

### 4. Météo (Weather-based)
- ✅ Optimisation tenant compte du vent
- ✅ Réduction de la consommation de carburant
- 🌤️ Utilise des données météo réelles ou simulées

### 5. NLP Direct Collocation
- ✅ Optimisation mathématique non-linéaire
- ✅ Meilleure compression (80% de réduction)
- ✅ Respect strict des contraintes
- ⚠️ Plus lent (28s vs 0.04s)

### 📈 Comparaison des Performances

| Méthode | Points | Temps | Smoothness | Usage recommandé |
|---------|--------|-------|------------|------------------|
| Kalman | 501 | 0.04s | ⭐⭐⭐ | Lissage simple |
| B-spline | 200 | 0.002s | ⭐⭐⭐⭐ | Compression rapide |
| **Hybride** | 200 | 0.04s | ⭐⭐⭐⭐⭐ | **Usage général** 🏆 |
| Météo | 200 | 0.04s | ⭐⭐⭐⭐ | Optimisation réaliste |
| NLP | 99 | 28s | ⭐⭐⭐ | Compression max |

Pour comparer toutes les méthodes visuellement :
```bash
python examples/compare_methods.py  # Comparaison complète
python examples/radar_comparison.py  # Graphique radar
```

📖 Voir [COMPARAISON_METHODES.md](COMPARAISON_METHODES.md) pour l'analyse détaillée

## 🌤️ Intégration Météo

Le projet peut intégrer des données météorologiques pour optimiser les trajectoires :
- Données de vent (direction, intensité)
- Température
- Pression atmosphérique

API supportées :
- OpenWeatherMap
- NOAA
- Données personnalisées

## 📝 License

MIT

## 👤 Auteur

Projet technique ENAC - 2A
