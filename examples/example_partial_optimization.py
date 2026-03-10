"""
Exemple d'optimisation partielle de trajectoire
Démontre comment optimiser seulement une partie de la trajectoire
à partir d'un temps ou d'une distance donnée
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.data.data_models import Trajectory
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod
from src.utils.visualization import TrajectoryVisualizer
from examples.optimize_trajectory import create_sample_trajectory


def main():
    """Exemple d'optimisation partielle"""
    
    print("=" * 70)
    print("OPTIMISATION PARTIELLE DE TRAJECTOIRE")
    print("=" * 70)
    print()
    
    # ===== 1. CHARGEMENT DES DONNÉES =====
    print("1. Chargement de la trajectoire...")
    
    # Vous pouvez utiliser un fichier KML ou une trajectoire d'exemple
    kml_file = Path(__file__).parent.parent / "data" / "sample" / "4B1804-track-EGM96.kml"
    
    try:
        parser = KMLParser(str(kml_file))
        trajectory = parser.parse()
        print(f"   ✓ Trajectoire KML chargée : {trajectory}")
    except FileNotFoundError:
        trajectory = create_sample_trajectory()
        print(f"   ✓ Trajectoire d'exemple créée : {trajectory}")
    
    # Informations sur la trajectoire
    distances = trajectory.get_cumulative_distances()
    timestamps = trajectory.get_timestamps()
    
    print(f"\n   Informations de la trajectoire :")
    print(f"   - Durée totale : {trajectory.duration:.0f} secondes ({trajectory.duration/60:.1f} minutes)")
    print(f"   - Distance totale : {distances[-1]/1000:.1f} km")
    print(f"   - Nombre de points : {len(trajectory)}")
    print()
    
    # ===== 2. EXEMPLES D'OPTIMISATION =====
    
    # Configuration de l'optimiseur
    optimizer = TrajectoryOptimizer(
        method=OptimizationMethod.HYBRID,
        kalman_config={'process_noise': 1.0, 'measurement_noise': 10.0},
        bspline_config={'degree': 3, 'smoothing_factor': None}
    )
    
    # --- Exemple A : Optimisation complète (comportement par défaut) ---
    print("2a. Optimisation COMPLÈTE (toute la trajectoire)")
    print("-" * 70)
    
    result_full = optimizer.optimize(
        trajectory,
        target_points=100
    )
    
    print(f"   ✓ Résultat : {len(result_full.optimized_positions)} points")
    print(f"   - Compression : {result_full.metrics['compression_ratio']:.2%}")
    print()
    
    # --- Exemple B : Optimisation à partir d'un TEMPS donné ---
    print("2b. Optimisation à partir d'un TEMPS (après 5 minutes)")
    print("-" * 70)
    
    start_time = 300  # 5 minutes = 300 secondes
    
    result_time = optimizer.optimize(
        trajectory,
        target_points=100,
        start_time=start_time
    )
    
    print(f"   ✓ Résultat : {len(result_time.optimized_positions)} points")
    print(f"   - Compression : {result_time.metrics['compression_ratio']:.2%}")
    print()
    
    # --- Exemple C : Optimisation à partir d'une DISTANCE donnée ---
    print("2c. Optimisation à partir d'une DISTANCE (après 50 km)")
    print("-" * 70)
    
    start_distance = 50000  # 50 km = 50000 mètres
    
    result_distance = optimizer.optimize(
        trajectory,
        target_points=100,
        start_distance=start_distance
    )
    
    print(f"   ✓ Résultat : {len(result_distance.optimized_positions)} points")
    print(f"   - Compression : {result_distance.metrics['compression_ratio']:.2%}")
    print()
    
    # --- Exemple D : Optimisation de la phase de croisière seulement ---
    print("2d. Optimisation de la PHASE DE CROISIÈRE uniquement")
    print("-" * 70)
    print("   (Conserve le décollage et la montée intacts)")
    
    # Typiquement, la montée dure environ 10-15 minutes
    cruise_start_time = 600  # 10 minutes
    
    result_cruise = optimizer.optimize(
        trajectory,
        target_points=80,
        start_time=cruise_start_time
    )
    
    print(f"   ✓ Résultat : {len(result_cruise.optimized_positions)} points")
    print(f"   - Compression : {result_cruise.metrics['compression_ratio']:.2%}")
    print()
    
    # ===== 3. VISUALISATION DES RÉSULTATS =====
    print("3. Génération des visualisations...")
    print()
    
    try:
        # Créer le dossier de sortie
        output_dir = Path("output/partial_optimization")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Comparaison des différentes approches
        trajectories = [
            trajectory,
            result_full.get_optimized_trajectory(),
            result_time.get_optimized_trajectory(),
            result_distance.get_optimized_trajectory(),
            result_cruise.get_optimized_trajectory()
        ]
        
        labels = [
            "Originale",
            "Optimisation complète",
            f"Optimisation après {start_time/60:.0f} min",
            f"Optimisation après {start_distance/1000:.0f} km",
            f"Optimisation croisière ({cruise_start_time/60:.0f} min)"
        ]
        
        # Carte interactive
        TrajectoryVisualizer.plot_interactive_map(
            trajectories,
            labels=labels,
            output_file=str(output_dir / "partial_optimization_map.html")
        )
        print(f"   ✓ Carte interactive : {output_dir / 'partial_optimization_map.html'}")
        
        # Graphique de comparaison
        TrajectoryVisualizer.plot_comparison(
            trajectory,
            result_cruise.get_optimized_trajectory(),
            output_file=str(output_dir / "cruise_optimization.png")
        )
        print(f"   ✓ Comparaison : {output_dir / 'cruise_optimization.png'}")
        
    except Exception as e:
        print(f"   ⚠ Erreur de visualisation : {e}")
    
    # ===== 4. AFFICHAGE DES MÉTRIQUES =====
    print()
    print("4. Comparaison des métriques")
    print("=" * 70)
    
    print("\n{:<30} | {:>10} | {:>12} | {:>12}".format(
        "Méthode", "Points", "Compression", "Smoothness"
    ))
    print("-" * 70)
    
    metrics_list = [
        ("Originale", len(trajectory), "0%", "N/A"),
        ("Optimisation complète", len(result_full.optimized_positions), 
         f"{result_full.metrics['compression_ratio']:.1%}", 
         f"{result_full.metrics.get('smoothness', 0):.0f}"),
        (f"Après {start_time/60:.0f} min", len(result_time.optimized_positions), 
         f"{result_time.metrics['compression_ratio']:.1%}", 
         f"{result_time.metrics.get('smoothness', 0):.0f}"),
        (f"Après {start_distance/1000:.0f} km", len(result_distance.optimized_positions), 
         f"{result_distance.metrics['compression_ratio']:.1%}", 
         f"{result_distance.metrics.get('smoothness', 0):.0f}"),
        (f"Croisière ({cruise_start_time/60:.0f} min)", len(result_cruise.optimized_positions), 
         f"{result_cruise.metrics['compression_ratio']:.1%}", 
         f"{result_cruise.metrics.get('smoothness', 0):.0f}")
    ]
    
    for method, points, compression, smoothness in metrics_list:
        print("{:<30} | {:>10} | {:>12} | {:>12}".format(
            method, points, compression, smoothness
        ))
    
    print()
    print("=" * 70)
    print("✈️ Optimisation partielle terminée !")
    print("=" * 70)
    print()
    print("💡 Cas d'usage recommandés :")
    print("   - start_time : Conserver le décollage et la montée, optimiser la croisière")
    print("   - start_distance : Optimiser après une certaine distance parcourue")
    print("   - Sans paramètre : Optimiser toute la trajectoire")
    print()


def example_custom_segments():
    """
    Exemple avancé : Optimiser différemment plusieurs segments
    """
    print("\n" + "=" * 70)
    print("EXEMPLE AVANCÉ : Optimisation multi-segments")
    print("=" * 70)
    
    trajectory = create_sample_trajectory()
    
    # Définir les segments
    # Segment 1 : Décollage et montée (0-10 min) - pas d'optimisation
    # Segment 2 : Croisière (10-50 min) - optimisation forte
    # Segment 3 : Descente et approche (50-60 min) - optimisation légère
    
    duration = trajectory.duration
    
    # Points de division
    t1 = 600   # 10 minutes
    t2 = 3000  # 50 minutes
    
    idx1 = trajectory.find_index_by_time(t1)
    idx2 = trajectory.find_index_by_time(t2)
    
    print(f"\nSegmentation de la trajectoire :")
    print(f"  - Décollage/Montée : 0 - {t1/60:.0f} min ({idx1} points)")
    print(f"  - Croisière : {t1/60:.0f} - {t2/60:.0f} min ({idx2-idx1} points)")
    print(f"  - Descente/Approche : {t2/60:.0f} - {duration/60:.0f} min ({len(trajectory)-idx2} points)")
    
    # Segment 1 : Inchangé
    segment1 = trajectory.positions[:idx1]
    
    # Segment 2 : Optimisation forte
    traj2 = Trajectory(trajectory.positions[idx1:idx2], "cruise")
    optimizer_cruise = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
    opt2 = optimizer_cruise.optimize(traj2, target_points=30)
    segment2 = opt2.optimized_positions
    
    # Segment 3 : Optimisation légère
    traj3 = Trajectory(trajectory.positions[idx2:], "approach")
    optimizer_approach = TrajectoryOptimizer(method=OptimizationMethod.KALMAN)
    opt3 = optimizer_approach.optimize(traj3)
    segment3 = opt3.optimized_positions
    
    # Combiner
    final_positions = segment1 + segment2 + segment3
    final_trajectory = Trajectory(final_positions, "multi_segment_optimized")
    
    print(f"\nRésultat final :")
    print(f"  - Points originaux : {len(trajectory)}")
    print(f"  - Points finaux : {len(final_trajectory)}")
    print(f"  - Compression : {(1 - len(final_trajectory)/len(trajectory)):.1%}")
    print()


if __name__ == "__main__":
    main()
    
    # Décommenter pour l'exemple avancé :
    # example_custom_segments()
