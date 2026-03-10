"""
Exemple complet d'utilisation du système d'optimisation de trajectoires
"""
import sys
from pathlib import Path
import numpy as np

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.data.data_models import Trajectory
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod
from src.utils.visualization import TrajectoryVisualizer


def main():
    """Exemple d'optimisation de trajectoire"""
    
    print("=" * 70)
    print("OPTIMISATION DE TRAJECTOIRE D'AVION")
    print("=" * 70)
    print()
    
    # ===== 1. CHARGEMENT DES DONNÉES =====
    print("1. Chargement des données KML...")
    
    # Remplacer par le chemin de votre fichier KML
    kml_file = Path(__file__).parent.parent / "data" / "sample" / "4B1804-track-EGM96.kml"
    
    try:
        parser = KMLParser(str(kml_file))
        trajectory = parser.parse()
        
        print(f"   ✓ Trajectoire chargée : {trajectory}")
        print(f"   - Durée : {trajectory.duration:.0f} secondes")
        print(f"   - Points : {len(trajectory)}")
        print()
        
    except FileNotFoundError:
        print(f"   ✗ Fichier non trouvé : {kml_file}")
        print()
        print("Pour tester sans fichier KML, utilisez la fonction create_sample_trajectory()")
        print()
        
        # Créer une trajectoire de test
        trajectory = create_sample_trajectory()
        print(f"   ✓ Trajectoire d'exemple créée : {trajectory}")
        print()
    
    # ===== 2. OPTIMISATION =====
    print("2. Optimisation de la trajectoire...")
    print()
    
    # Configuration de l'optimiseur
    # Méthodes disponibles : KALMAN, BSPLINE, HYBRID, WEATHER
    
    # Option A : Méthode hybride (recommandée)
    print("   a) Optimisation hybride (Kalman + B-spline)...")
    optimizer_hybrid = TrajectoryOptimizer(
        method=OptimizationMethod.HYBRID,
        kalman_config={
            'process_noise': 1.0,
            'measurement_noise': 10.0
        },
        bspline_config={
            'degree': 3,
            'smoothing_factor': None  # Interpolation exacte
        }
    )
    
    optimized_hybrid = optimizer_hybrid.optimize(
        trajectory,
        use_weather=False,
        target_points=100  # Réduire à 100 points
    )
    
    print(f"   ✓ Optimisation terminée")
    print(f"   - Méthode : {optimized_hybrid.method}")
    print(f"   - Points optimisés : {len(optimized_hybrid.optimized_positions)}")
    print(f"   - Ratio de compression : {optimized_hybrid.metrics['compression_ratio']:.2%}")
    print()
    
    # Option B : Avec données météo
    print("   b) Optimisation avec météo (mode simulation)...")
    optimizer_weather = TrajectoryOptimizer(
        method=OptimizationMethod.WEATHER,
        weather_api_key=None  # None = mode simulation
    )
    
    optimized_weather = optimizer_weather.optimize(
        trajectory,
        use_weather=True,
        target_points=100
    )
    
    print(f"   ✓ Optimisation avec météo terminée")
    print()
    
    # ===== 3. AFFICHAGE DES MÉTRIQUES =====
    print("3. Métriques d'optimisation (Hybride):")
    print()
    for key, value in optimized_hybrid.metrics.items():
        if isinstance(value, float):
            print(f"   - {key:25s}: {value:10.2f}")
        else:
            print(f"   - {key:25s}: {value}")
    print()
    
    # ===== 4. VISUALISATION =====
    print("4. Génération des visualisations...")
    
    try:
        # Comparaison original vs optimisé
        TrajectoryVisualizer.plot_comparison(
            trajectory,
            optimized_hybrid.get_optimized_trajectory(),
            output_file="output/comparison.png"
        )
        print("   ✓ Comparaison sauvegardée : output/comparison.png")
        
        # Carte interactive avec comparaison
        TrajectoryVisualizer.plot_interactive_map(
            [trajectory, optimized_hybrid.get_optimized_trajectory()],
            labels=["Trajectoire originale", "Trajectoire optimisée"],
            output_file="output/trajectory_map.html"
        )
        print("   ✓ Carte interactive : output/trajectory_map.html")
        
    except Exception as e:
        print(f"   ⚠ Erreur de visualisation : {e}")
    
    print()
    print("=" * 70)
    print("Terminé !")
    print("=" * 70)


def create_sample_trajectory():
    """
    Crée une trajectoire d'exemple pour les tests
    Simule un vol avec montée, palier et descente
    """
    from datetime import datetime, timedelta
    from src.data.data_models import Position, Trajectory
    import numpy as np
    
    # Paramètres du vol
    num_points = 200
    duration = 3600  # 1 heure
    
    # Position de départ (aéroport de Toulouse par exemple)
    lat_start = 43.629
    lon_start = 1.364
    alt_start = 150
    
    # Position d'arrivée (aéroport de Paris)
    lat_end = 48.725
    lon_end = 2.360
    alt_end = 100
    
    positions = []
    t0 = datetime.now()
    
    for i in range(num_points):
        progress = i / (num_points - 1)
        
        # Interpolation linéaire avec un peu de bruit
        noise = np.random.randn(3) * 0.01
        
        lat = lat_start + (lat_end - lat_start) * progress + noise[0]
        lon = lon_start + (lon_end - lon_start) * progress + noise[1]
        
        # Profil d'altitude : montée, palier, descente
        if progress < 0.2:
            # Montée
            alt = alt_start + (10000 - alt_start) * (progress / 0.2)
        elif progress < 0.8:
            # Palier
            alt = 10000 + np.sin(progress * 20) * 100  # Petites oscillations
        else:
            # Descente
            alt = 10000 - (10000 - alt_end) * ((progress - 0.8) / 0.2)
        
        alt += noise[2] * 50
        
        timestamp = t0 + timedelta(seconds=duration * progress)
        
        # Vitesse typique
        ground_speed = 200 + np.random.randn() * 10  # ~200 m/s
        
        positions.append(Position(
            latitude=lat,
            longitude=lon,
            altitude=alt,
            timestamp=timestamp,
            ground_speed=ground_speed
        ))
    
    return Trajectory(positions, flight_id="SAMPLE_FLIGHT")


def example_only_kalman():
    """Exemple avec seulement le filtre de Kalman"""
    from src.filters.kalman_filter import KalmanFilter
    
    print("Exemple : Filtre de Kalman seul")
    print("-" * 50)
    
    trajectory = create_sample_trajectory()
    
    kalman = KalmanFilter(
        process_noise=1.0,
        measurement_noise=15.0
    )
    
    # Filtrage
    filtered = kalman.filter_trajectory(trajectory)
    print(f"Filtrage terminé : {len(filtered)} points")
    
    # Lissage RTS
    smoothed = kalman.smooth_trajectory(trajectory)
    print(f"Lissage RTS terminé : {len(smoothed)} points")
    
    # Visualisation
    TrajectoryVisualizer.plot_trajectory_3d(
        [trajectory, filtered, smoothed],
        labels=['Original', 'Filtré', 'Lissé'],
        output_file="output/kalman_only.png"
    )


def example_only_bspline():
    """Exemple avec seulement B-spline"""
    from src.optimization.bspline import BSplineOptimizer
    
    print("Exemple : B-spline seul")
    print("-" * 50)
    
    trajectory = create_sample_trajectory()
    
    bspline = BSplineOptimizer(
        degree=3,
        smoothing_factor=100.0  # Lissage
    )
    
    # Optimisation
    optimized = bspline.optimize(trajectory, target_points=50)
    print(f"Optimisation terminée : {optimized}")
    
    # Calculer la courbure
    curvature = bspline.compute_curvature(trajectory)
    print(f"Courbure moyenne : {np.mean(curvature):.6f}")
    print(f"Courbure max : {np.max(curvature):.6f}")
    
    # Visualisation
    TrajectoryVisualizer.plot_comparison(
        trajectory,
        optimized,
        output_file="output/bspline_only.png"
    )


if __name__ == "__main__":
    # Créer le dossier de sortie
    Path("output").mkdir(exist_ok=True)
    Path("data/sample").mkdir(parents=True, exist_ok=True)
    
    # Lancer l'exemple principal
    main()
    
    # Décommenter pour tester les exemples individuels :
    # example_only_kalman()
    # example_only_bspline()
