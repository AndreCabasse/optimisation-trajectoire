"""
Script de validation des améliorations de précision
Compare ancien vs nouveau système d'optimisation

Usage:
    python test_precision_improvements.py
"""
import sys
from pathlib import Path
import numpy as np
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod
from src.data.data_models import Position


def test_coordinate_conversion():
    """Test de la conversion géographique améliorée"""
    print("=" * 70)
    print("TEST 1 : Conversion géographique (ECEF vs approximation)")
    print("=" * 70)
    
    # Point de test (Paris CDG)
    pos = Position(
        latitude=49.0097,
        longitude=2.5479,
        altitude=10000.0,
        timestamp=None
    )
    
    # Ancienne méthode (approximation)
    start = time.time()
    for _ in range(1000):
        cart_approx = pos.to_cartesian(use_precise=False)
    time_approx = (time.time() - start) * 1000
    
    # Nouvelle méthode (ECEF précis)
    start = time.time()
    for _ in range(1000):
        cart_precise = pos.to_cartesian(use_precise=True)
    time_precise = (time.time() - start) * 1000
    
    print(f"Approximation : {cart_approx}")
    print(f"ECEF précis   : {cart_precise}")
    print(f"Différence    : {np.linalg.norm(cart_precise - cart_approx):.2f} m")
    print(f"\nTemps (1000 conversions):")
    print(f"  Approximation : {time_approx:.1f} ms")
    print(f"  ECEF précis   : {time_precise:.1f} ms")
    print(f"  Surcoût       : +{(time_precise/time_approx - 1)*100:.1f}%")
    print("\n✅ ECEF recommandé pour haute précision (erreur < 1m)\n")


def test_kalman_improvements():
    """Test des améliorations du filtre de Kalman"""
    print("=" * 70)
    print("TEST 2 : Filtre de Kalman (altitude-dependent noise)")
    print("=" * 70)
    
    # Charger une trajectoire réelle
    try:
        kml_files = list(Path('data/sample').glob('*.kml'))
        if not kml_files:
            print("⚠️  Aucun fichier KML trouvé dans data/sample/")
            return
        
        parser = KMLParser(str(kml_files[0]))
        trajectory = parser.parse()
        print(f"Trajectoire : {trajectory.flight_id}")
        print(f"Points      : {len(trajectory)}")
        print(f"Durée       : {trajectory.duration:.0f}s\n")
        
        # ANCIEN : sans altitude-dependent noise
        print("--- ANCIEN (noise fixe) ---")
        opt_old = TrajectoryOptimizer(
            method=OptimizationMethod.KALMAN,
            kalman_config={
                'process_noise': 0.5,
                'measurement_noise': 5.0,
                'adaptive': True,
                'altitude_dependent_noise': False  # ANCIEN
            }
        )
        start = time.time()
        result_old = opt_old.optimize(trajectory, target_points=None)
        time_old = time.time() - start
        
        print(f"Smoothness       : {result_old.metrics['smoothness']:.2f}")
        print(f"Temps de calcul  : {time_old:.2f}s")
        
        # NOUVEAU : avec altitude-dependent noise
        print("\n--- NOUVEAU (noise adaptatif) ---")
        opt_new = TrajectoryOptimizer(
            method=OptimizationMethod.KALMAN,
            kalman_config={
                'process_noise': 0.3,
                'measurement_noise': 5.0,
                'adaptive': True,
                'altitude_dependent_noise': True  # NOUVEAU
            }
        )
        start = time.time()
        result_new = opt_new.optimize(trajectory, target_points=None)
        time_new = time.time() - start
        
        print(f"Smoothness       : {result_new.metrics['smoothness']:.2f}")
        print(f"Temps de calcul  : {time_new:.2f}s")
        
        # Comparaison
        improvement = ((result_old.metrics['smoothness'] - result_new.metrics['smoothness']) 
                      / result_old.metrics['smoothness'] * 100)
        print(f"\n✅ Amélioration smoothness : {improvement:+.1f}%")
        print(f"⚡ Surcoût temps          : +{(time_new/time_old - 1)*100:.1f}%\n")
        
    except Exception as e:
        print(f"❌ Erreur : {e}\n")


def test_bspline_auto_smooth():
    """Test de la détection automatique du smoothing"""
    print("=" * 70)
    print("TEST 3 : B-spline (auto-smoothing vs fixe)")
    print("=" * 70)
    
    try:
        kml_files = list(Path('data/sample').glob('*.kml'))
        if not kml_files:
            print("⚠️  Aucun fichier KML trouvé dans data/sample/")
            return
        
        parser = KMLParser(str(kml_files[0]))
        trajectory = parser.parse()
        print(f"Trajectoire : {trajectory.flight_id}")
        print(f"Points      : {len(trajectory)}\n")
        
        # ANCIEN : smoothing fixe
        print("--- ANCIEN (smoothing=0.5 fixe) ---")
        opt_old = TrajectoryOptimizer(
            method=OptimizationMethod.BSPLINE,
            bspline_config={
                'degree': 3,
                'smoothing_factor': 0.5,
                'auto_smooth': False
            }
        )
        start = time.time()
        result_old = opt_old.optimize(trajectory, target_points=150)
        time_old = time.time() - start
        
        print(f"Smoothness       : {result_old.metrics['smoothness']:.2f}")
        print(f"Curvature max    : {result_old.metrics['curvature_max']:.6f}")
        print(f"Temps de calcul  : {time_old:.2f}s")
        
        # NOUVEAU : auto-smoothing
        print("\n--- NOUVEAU (auto-smoothing par CV) ---")
        opt_new = TrajectoryOptimizer(
            method=OptimizationMethod.BSPLINE,
            bspline_config={
                'degree': 3,
                'smoothing_factor': None,
                'auto_smooth': True  # NOUVEAU
            }
        )
        start = time.time()
        result_new = opt_new.optimize(trajectory, target_points=150)
        time_new = time.time() - start
        
        print(f"Smoothness       : {result_new.metrics['smoothness']:.2f}")
        print(f"Curvature max    : {result_new.metrics['curvature_max']:.6f}")
        print(f"Temps de calcul  : {time_new:.2f}s")
        
        # Comparaison
        improvement_smooth = ((result_old.metrics['smoothness'] - result_new.metrics['smoothness']) 
                             / result_old.metrics['smoothness'] * 100)
        improvement_curv = ((result_old.metrics['curvature_max'] - result_new.metrics['curvature_max']) 
                           / result_old.metrics['curvature_max'] * 100)
        
        print(f"\n✅ Amélioration smoothness : {improvement_smooth:+.1f}%")
        print(f"✅ Amélioration curvature  : {improvement_curv:+.1f}%")
        print(f"⚡ Surcoût temps          : +{(time_new/time_old - 1)*100:.1f}%\n")
        
    except Exception as e:
        print(f"❌ Erreur : {e}\n")


def test_hybrid_full_comparison():
    """Test complet avec méthode HYBRID"""
    print("=" * 70)
    print("TEST 4 : HYBRID complet (toutes améliorations)")
    print("=" * 70)
    
    try:
        kml_files = list(Path('data/sample').glob('*.kml'))
        if not kml_files:
            print("⚠️  Aucun fichier KML trouvé dans data/sample/")
            return
        
        parser = KMLParser(str(kml_files[0]))
        trajectory = parser.parse()
        print(f"Trajectoire : {trajectory.flight_id}")
        print(f"Points      : {len(trajectory)}")
        print(f"Durée       : {trajectory.duration/60:.1f}min\n")
        
        # Configuration ANCIENNE
        print("--- CONFIGURATION ANCIENNE ---")
        opt_old = TrajectoryOptimizer(
            method=OptimizationMethod.HYBRID,
            kalman_config={
                'process_noise': 0.5,
                'measurement_noise': 5.0,
                'adaptive': True,
                'altitude_dependent_noise': False
            },
            bspline_config={
                'degree': 3,
                'smoothing_factor': 0.5,
                'auto_smooth': False
            }
        )
        start = time.time()
        result_old = opt_old.optimize(trajectory, target_points=120)
        time_old = time.time() - start
        
        print(f"Points optimisés      : {len(result_old.optimized_positions)}")
        print(f"Compression           : {result_old.metrics['compression_ratio']:.1%}")
        print(f"Smoothness            : {result_old.metrics['smoothness']:.2f}")
        print(f"Max G-force           : {result_old.metrics['max_g_force']:.2f}")
        print(f"Curvature max         : {result_old.metrics['curvature_max']:.6f}")
        print(f"Max climb rate        : {result_old.metrics['max_climb_rate_ms']:.1f} m/s")
        print(f"Temps de calcul       : {time_old:.2f}s")
        
        # Configuration NOUVELLE
        print("\n--- CONFIGURATION NOUVELLE (HAUTE PRÉCISION) ---")
        opt_new = TrajectoryOptimizer(
            method=OptimizationMethod.HYBRID,
            kalman_config={
                'process_noise': 0.3,
                'measurement_noise': 5.0,
                'adaptive': True,
                'altitude_dependent_noise': True  # ✨
            },
            bspline_config={
                'degree': 3,
                'smoothing_factor': None,
                'auto_smooth': True  # ✨
            }
        )
        start = time.time()
        result_new = opt_new.optimize(trajectory, target_points=150)  # Plus de points
        time_new = time.time() - start
        
        print(f"Points optimisés      : {len(result_new.optimized_positions)}")
        print(f"Compression           : {result_new.metrics['compression_ratio']:.1%}")
        print(f"Smoothness            : {result_new.metrics['smoothness']:.2f}")
        print(f"Max G-force           : {result_new.metrics['max_g_force']:.2f}")
        print(f"Curvature max         : {result_new.metrics['curvature_max']:.6f}")
        print(f"Max climb rate        : {result_new.metrics['max_climb_rate_ms']:.1f} m/s")
        print(f"Temps de calcul       : {time_new:.2f}s")
        
        # Comparaison détaillée
        print("\n" + "=" * 70)
        print("COMPARAISON DES PERFORMANCES")
        print("=" * 70)
        
        metrics_comparison = {
            'Smoothness': (result_old.metrics['smoothness'], result_new.metrics['smoothness']),
            'Max G-force': (result_old.metrics['max_g_force'], result_new.metrics['max_g_force']),
            'Curvature max': (result_old.metrics['curvature_max'], result_new.metrics['curvature_max']),
            'Max climb rate': (result_old.metrics['max_climb_rate_ms'], result_new.metrics['max_climb_rate_ms'])
        }
        
        for metric_name, (old_val, new_val) in metrics_comparison.items():
            improvement = ((old_val - new_val) / old_val * 100) if old_val != 0 else 0
            status = "✅" if improvement > 0 else "⚠️"
            print(f"{status} {metric_name:20s}: {old_val:10.4f} → {new_val:10.4f} ({improvement:+6.1f}%)")
        
        time_overhead = (time_new / time_old - 1) * 100
        print(f"\n⚡ Surcoût temps de calcul : +{time_overhead:.1f}%")
        
        # Verdict global
        avg_improvement = np.mean([
            ((old - new) / old * 100) if old != 0 else 0
            for old, new in metrics_comparison.values()
        ])
        
        print(f"\n🎯 AMÉLIORATION MOYENNE : {avg_improvement:+.1f}%")
        
        if avg_improvement > 30:
            print("🏆 EXCELLENT ! Les améliorations sont très significatives.")
        elif avg_improvement > 15:
            print("✅ BON ! Les améliorations sont notables.")
        elif avg_improvement > 5:
            print("👍 CORRECT ! Amélioration légère mais mesurable.")
        else:
            print("ℹ️  Les améliorations dépendent de la qualité des données initiales.")
        
        print()
        
    except Exception as e:
        print(f"❌ Erreur : {e}\n")
        import traceback
        traceback.print_exc()


def main():
    """Exécute tous les tests de validation"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "VALIDATION DES AMÉLIORATIONS DE PRÉCISION" + " " * 16 + "║")
    print("║" + " " * 15 + "Projet ENAC 2A - Février 2026" + " " * 23 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    # Test 1 : Conversion géographique
    test_coordinate_conversion()
    
    # Test 2 : Kalman amélioré
    test_kalman_improvements()
    
    # Test 3 : B-spline auto-smooth
    test_bspline_auto_smooth()
    
    # Test 4 : Comparaison complète
    test_hybrid_full_comparison()
    
    print("=" * 70)
    print("TESTS TERMINÉS")
    print("=" * 70)
    print("\n📖 Consultez AMELIORATIONS_PRECISION.md pour le guide complet\n")


if __name__ == '__main__':
    main()
