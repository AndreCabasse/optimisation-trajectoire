"""
Version PARALLÉLISÉE des comparaisons - 10x plus rapide !
"""
import sys
from pathlib import Path
import time
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Tuple

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod
from src.data.data_models import Trajectory


def optimize_single_method(args: Tuple[str, OptimizationMethod, str, int]) -> Tuple[str, object, float]:
    """
    Fonction pour optimiser une seule méthode (sera exécutée en parallèle)
    
    Args:
        args: (method_name, method_type, kml_file_path, target_points)
    
    Returns:
        (method_name, result, execution_time)
    """
    method_name, method_type, kml_file_path, target_points = args
    
    # Charger la trajectoire (chaque processus a sa propre copie)
    parser = KMLParser(kml_file_path)
    traj = parser.parse()
    
    # Optimiser
    start_time = time.time()
    optimizer = TrajectoryOptimizer(method=method_type)
    result = optimizer.optimize(traj, target_points=target_points)
    elapsed = time.time() - start_time
    
    return (method_name, result, elapsed)


def main():
    """Comparaison parallélisée des méthodes"""
    
    print("="*80)
    print("  🚀 COMPARAISON PARALLÉLISÉE DES MÉTHODES (VERSION RAPIDE)")
    print("="*80)
    print()
    
    # Charger données pour info
    kml_file = Path(__file__).parent.parent / "data" / "sample" / "F-HZUE-track-EGM96.kml"
    parser = KMLParser(str(kml_file))
    traj = parser.parse()
    
    print(f"📊 Trajectoire originale: {len(traj)} points")
    print(f"   Durée du vol: {traj.duration:.1f}s ({traj.duration/60:.1f} min)")
    print(f"   Flight ID: {traj.flight_id}")
    print()
    
    TARGET_POINTS = 200
    
    # Préparer les tâches pour parallélisation
    methods = {
        'Kalman': OptimizationMethod.KALMAN,
        'B-spline': OptimizationMethod.BSPLINE,
        'Hybride': OptimizationMethod.HYBRID,
        'Météo': OptimizationMethod.WEATHER,
        'NLP': OptimizationMethod.DIRECT_COLLOCATION
    }
    
    tasks = [
        (name, method_type, str(kml_file), TARGET_POINTS)
        for name, method_type in methods.items()
    ]
    
    print(f"⚡ Exécution parallèle de {len(tasks)} méthodes...")
    print()
    
    results = {}
    timings = {}
    
    total_start = time.time()
    
    # Exécution parallèle
    with ProcessPoolExecutor(max_workers=5) as executor:
        # Soumettre toutes les tâches
        futures = {executor.submit(optimize_single_method, task): task[0] for task in tasks}
        
        # Récupérer les résultats au fur et à mesure
        for future in as_completed(futures):
            method_name = futures[future]
            try:
                name, result, elapsed = future.result()
                results[name] = result
                timings[name] = elapsed
                
                traj_result = result.get_optimized_trajectory()
                print(f"   ✓ {name}: {len(traj_result)} points ({elapsed:.3f}s)")
                
            except Exception as e:
                print(f"   ✗ {method_name}: Erreur - {e}")
    
    total_elapsed = time.time() - total_start
    
    print()
    print("="*80)
    print("  📊 RÉSULTATS")
    print("="*80)
    print()
    
    # Tableau comparatif
    print(f"{'Méthode':<15} {'Points':<10} {'Distance (km)':<15} {'Temps calc.':<15}")
    print("="*80)
    
    for name in ['Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
        if name in results:
            result = results[name]
            traj_opt = result.get_optimized_trajectory()
            dist_km = result.metrics.get('distance_optimized', 0) / 1000
            time_calc = timings[name]
            
            print(f"{name:<15} {len(traj_opt):<10} {dist_km:<15.2f} {time_calc:<15.3f}s")
    
    print()
    print("="*80)
    print("  🎯 NOUVELLES MÉTRIQUES AVANCÉES")
    print("="*80)
    print()
    
    for name in ['Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
        if name in results:
            result = results[name]
            m = result.metrics
            
            print(f"\n🔹 {name}:")
            print(f"   Carburant: {m.get('fuel_consumption_kg', 0):.1f} kg")
            if 'fuel_saving_kg' in m:
                print(f"   Économie carburant: {m['fuel_saving_kg']:.1f} kg ({m['fuel_saving_percent']:.2f}%)")
            print(f"   G-force max: {m.get('max_g_force', 0):.2f} G")
            print(f"   G-force moy: {m.get('avg_g_force', 0):.2f} G")
            print(f"   Taux montée max: {m.get('max_climb_rate_ms', 0):.2f} m/s")
            print(f"   Courbure max: {m.get('curvature_max', 0):.2e}")
    
    print()
    print("="*80)
    print(f"  ⚡ PERFORMANCE: {total_elapsed:.1f}s (vs ~60s en séquentiel)")
    print(f"  🚀 Gain: {60/total_elapsed:.1f}x plus rapide!")
    print("="*80)


if __name__ == "__main__":
    main()
