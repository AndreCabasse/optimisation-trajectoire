"""
Test des corrections pour résultats réalistes
Valide que toutes les méthodes respectent les contraintes physiques
"""
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import (
    TrajectoryOptimizer,
    OptimizationMethod,
    OptimizationProfile
)


def test_method(trajectory, method, profile=None, target_points=100):
    """
    Test une méthode d'optimisation et affiche les résultats
    """
    print(f"\n{'='*80}")
    print(f"TEST: {method.value.upper()}")
    if profile:
        print(f"Profil: {profile.value}")
    print('='*80)
    
    # Créer l'optimiseur
    config = {'method': method}
    if profile:
        config['optimization_profile'] = profile
    
    optimizer = TrajectoryOptimizer(**config)
    
    # Optimiser
    result = optimizer.optimize(trajectory, target_points=target_points)
    
    # Afficher les métriques clés
    print("\n📊 MÉTRIQUES:")
    metrics = result.metrics
    
    print(f"   Points: {len(trajectory)} → {len(result.optimized_positions)} "
          f"({metrics.get('compression_ratio', 0)*100:.1f}%)")
    
    if 'distance_km' in metrics:
        dist_original = trajectory.get_cumulative_distances()[-1] / 1000.0
        dist_optimized = metrics['distance_km']
        variation = 100.0 * abs(dist_optimized - dist_original) / dist_original
        print(f"   Distance: {dist_original:.1f} km → {dist_optimized:.1f} km "
              f"({variation:+.2f}%)")
    
    if 'fuel_kg' in metrics:
        print(f"   Carburant: {metrics['fuel_kg']:.1f} kg")
        if 'fuel_diff_kg' in metrics:
            diff = metrics['fuel_diff_kg']
            print(f"   Variation: {diff:+.1f} kg")
    
    if 'max_g_force' in metrics:
        print(f"   G-force max: {metrics['max_g_force']:.2f}g")
    
    if 'avg_curvature' in metrics:
        print(f"   Courbure moy: {metrics['avg_curvature']:.6f}")
    
    return result


def main():
    """
    Lance les tests sur toutes les méthodes avec une trajectoire exemple
    """
    print("\n🧪 TESTS DE VALIDATION - CORRECTIONS RÉALISME 2026")
    print("="*80)
    
    # Charger une trajectoire exemple
    kml_file = Path(__file__).parent.parent / "data" / "sample" / "F-HZUE-track-EGM96.kml"
    
    if not kml_file.exists():
        print(f"❌ Fichier non trouvé: {kml_file}")
        print("   Veuillez spécifier un fichier KML valide")
        return
    
    print(f"\n📂 Chargement: {kml_file.name}")
    parser = KMLParser()
    trajectory = parser.parse(str(kml_file))
    
    dist_original = trajectory.get_cumulative_distances()[-1] / 1000.0
    print(f"   Points: {len(trajectory)}")
    print(f"   Distance: {dist_original:.1f} km")
    
    # TEST 1: Kalman (débruitage)
    test_method(trajectory, OptimizationMethod.KALMAN)
    
    # TEST 2: B-spline avec preserve_distance=True (défaut)
    print("\n💡 NOTE: B-spline utilise preserve_distance=True par défaut")
    test_method(trajectory, OptimizationMethod.BSPLINE, target_points=100)
    
    # TEST 3: Hybrid (Kalman + B-spline)
    test_method(trajectory, OptimizationMethod.HYBRID, target_points=100)
    
    # TEST 4: Weather (si disponible)
    print("\n💡 NOTE: Weather utilise des données météo simulées (mode mock)")
    test_method(trajectory, OptimizationMethod.WEATHER, target_points=100)
    
    # TEST 5: Direct Collocation - Profil BALANCED
    test_method(
        trajectory,
        OptimizationMethod.DIRECT_COLLOCATION,
        profile=OptimizationProfile.BALANCED,
        target_points=50
    )
    
    # TEST 6: Direct Collocation - Profil FUEL_SAVER
    test_method(
        trajectory,
        OptimizationMethod.DIRECT_COLLOCATION,
        profile=OptimizationProfile.FUEL_SAVER,
        target_points=50
    )
    
    # TEST 7: Direct Collocation - Profil COMFORT
    test_method(
        trajectory,
        OptimizationMethod.DIRECT_COLLOCATION,
        profile=OptimizationProfile.COMFORT,
        target_points=50
    )
    
    print("\n" + "="*80)
    print("✅ TESTS TERMINÉS")
    print("="*80)
    print("\n📋 VÉRIFICATIONS:")
    print("   - Toutes les méthodes ont émis '✓ Validation réussie' ?")
    print("   - Aucun avertissement de distance excessive ?")
    print("   - Aucune altitude négative ou > 15000m ?")
    print("   - Toutes les G-forces < 1.5g ?")
    print("\n   Si OUI → Les corrections sont EFFICACES")
    print("   Si NON → Vérifier les avertissements ci-dessus\n")


if __name__ == "__main__":
    main()
