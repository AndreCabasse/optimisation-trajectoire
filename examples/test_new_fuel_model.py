"""
Script de test pour valider les améliorations du modèle de carburant et des calculs physiques
Version Mars 2026
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod

def test_fuel_model():
    """Test du nouveau modèle de consommation de carburant"""
    print("\n" + "="*80)
    print("🧪 TEST DU MODÈLE DE CONSOMMATION DE CARBURANT AMÉLIORÉ")
    print("="*80)
    
    # Charger une trajectoire d'exemple
    kml_path = Path(__file__).parent.parent / "data" / "sample" / "4B1804-track-EGM96.kml"
    
    if not kml_path.exists():
        print(f"❌ Fichier non trouvé: {kml_path}")
        return
    
    print(f"\n📂 Chargement: {kml_path.name}")
    parser = KMLParser(str(kml_path))
    trajectory = parser.parse()
    
    print(f"✅ Trajectoire chargée: {len(trajectory)} points")
    print(f"   Durée: {trajectory.duration:.0f}s ({trajectory.duration/3600:.2f}h)")
    
    # Tester différentes méthodes
    methods = [
        ("Kalman", OptimizationMethod.KALMAN),
        ("B-spline", OptimizationMethod.BSPLINE),
        ("Hybride", OptimizationMethod.HYBRID),
        ("Météo", OptimizationMethod.WEATHER),
        ("Collocation Directe", OptimizationMethod.DIRECT_COLLOCATION)
    ]
    
    print("\n" + "-"*80)
    print("📊 COMPARAISON DES MÉTHODES")
    print("-"*80)
    print(f"{'Méthode':<20} {'Points':<8} {'Distance':<12} {'Carburant':<15} {'Variation':<15} {'G-max':<8}")
    print("-"*80)
    
    results = []
    
    for name, method in methods:
        try:
            optimizer = TrajectoryOptimizer(method=method)
            result = optimizer.optimize(trajectory, target_points=200)
            
            metrics = result.metrics
            opt_traj = result.optimized_trajectory
            points = len(opt_traj.positions)
            dist_km = metrics['distance_optimized'] / 1000
            fuel_kg = metrics.get('fuel_consumption_kg', 0)
            fuel_var = metrics.get('fuel_saving_kg', 0)
            fuel_pct = metrics.get('fuel_saving_percent', 0)
            g_max = metrics.get('max_g_force', 0)
            
            # Déterminer si économie ou surconsommation
            if fuel_var >= 0:
                fuel_status = f"✅ -{fuel_var:.1f}kg ({fuel_pct:+.2f}%)"
            else:
                fuel_status = f"⚠️ +{abs(fuel_var):.1f}kg ({fuel_pct:+.2f}%)"
            
            print(f"{name:<20} {points:<8} {dist_km:<12.2f} {fuel_kg:<15.1f} {fuel_status:<15} {g_max:<8.3f}")
            
            results.append({
                'name': name,
                'metrics': metrics,
                'result': result
            })
            
        except Exception as e:
            print(f"{name:<20} ❌ ERREUR: {str(e)[:40]}")
    
    print("-"*80)
    
    # Analyse détaillée de la méthode Hybride
    print("\n" + "="*80)
    print("🔍 ANALYSE DÉTAILLÉE - MÉTHODE HYBRIDE")
    print("="*80)
    
    hybrid_result = [r for r in results if r['name'] == "Hybride"]
    if hybrid_result:
        metrics = hybrid_result[0]['metrics']
        
        print(f"\n📏 DISTANCE")
        print(f"   Originale:    {metrics['distance_original']/1000:.2f} km")
        print(f"   Optimisée:    {metrics['distance_optimized']/1000:.2f} km")
        print(f"   Variation:    {metrics['distance_change_percent']:+.2f}%")
        
        print(f"\n⛽ CARBURANT (Modèle Amélioré)")
        fuel_orig = metrics.get('fuel_consumption_original_kg', 0)
        fuel_opt = metrics.get('fuel_consumption_kg', 0)
        fuel_saving = metrics.get('fuel_saving_kg', 0)
        fuel_pct = metrics.get('fuel_saving_percent', 0)
        
        print(f"   Consommation originale:  {fuel_orig:.1f} kg")
        print(f"   Consommation optimisée:  {fuel_opt:.1f} kg")
        
        if fuel_saving >= 0:
            print(f"   ✅ ÉCONOMIE:             {fuel_saving:.1f} kg ({fuel_pct:.2f}%)")
        else:
            print(f"   ⚠️ SURCONSOMMATION:      {abs(fuel_saving):.1f} kg ({abs(fuel_pct):.2f}%)")
            print(f"\n   💡 Explication:")
            if metrics['distance_change_percent'] > 0:
                print(f"      - Distance augmentée de {metrics['distance_change_percent']:.2f}%")
            g_avg = metrics.get('avg_g_force', 1.0)
            if g_avg > 1.01:
                print(f"      - Facteur de charge moyen: {g_avg:.3f} G (virages)")
            print(f"      - Optimisation privilégie le confort et la sécurité")
        
        print(f"\n⚡ DYNAMIQUE DE VOL")
        print(f"   G-force moyen:        {metrics.get('avg_g_force', 0):.3f} G")
        print(f"   G-force maximal:      {metrics.get('max_g_force', 0):.3f} G")
        print(f"   Courbure moyenne:     {metrics.get('curvature_avg', 0):.2e}")
        print(f"   Courbure maximale:    {metrics.get('curvature_max', 0):.2e}")
        
        vr_max = metrics.get('max_climb_rate_ms', 0)
        vr_avg = metrics.get('avg_climb_rate_ms', 0)
        print(f"\n✈️ TAUX DE MONTÉE/DESCENTE")
        print(f"   Moyen:    {vr_avg:.2f} m/s ({vr_avg*60/0.3048:.0f} ft/min)")
        print(f"   Maximal:  {vr_max:.2f} m/s ({vr_max*60/0.3048:.0f} ft/min)")
        
        if vr_max > 15:
            print(f"   ⚠️ Attention: taux de montée élevé (limite recommandée: 15 m/s)")
        elif vr_max > 10:
            print(f"   ℹ️ Taux de montée standard pour aviation commerciale")
        else:
            print(f"   ✅ Taux de montée confortable")
        
        print(f"\n📊 COMPRESSION")
        opt_traj = hybrid_result[0]['result'].optimized_trajectory
        print(f"   Points optimisés:     {len(opt_traj
        print(f"   Points optimisés:     {len(hybrid_result[0]['result'].optimized_trajectory.positions)} pts")
        print(f"   Taux de compression:  {metrics['compression_ratio']*100:.1f}%")
        print(f"   Smoothness:           {metrics['smoothness']:.0f}")
        print(f"   Smoothness originale: {metrics['original_smoothness']:.0f}")
    
    print("\n" + "="*80)
    print("✅ TESTS TERMINÉS")
    print("="*80)
    
    print("\n💡 RÉSUMÉ:")
    print("   - Le nouveau modèle de carburant prend en compte:")
    print("     ✓ Distance réelle parcourue (kg/km)")
    print("     ✓ Virages et manœuvres (traînée induite)")
    print("     ✓ Accélérations/décélérations")
    print("     ✓ Altitude de croisière (efficacité aérodynamique)")
    print("     ✓ Changements d'altitude (énergie potentielle)")
    print("\n   - L'affichage est maintenant honnête:")
    print("     ✓ Économie = réduction réelle de carburant")
    print("     ✓ Surconsommation = augmentation (avec explication)")
    print("\n   - Les calculs physiques sont améliorés:")
    print("     ✓ G-forces calculées avec décomposition vectorielle")
    print("     ✓ Contraintes réalistes (taux de montée, altitude, etc.)")
    print("     ✓ Validation automatique de la trajectoire")
    
    print("\n🚀 Lancer le dashboard pour voir les résultats:")
    print("   streamlit run examples/dashboard_improved.py")
    print()


if __name__ == "__main__":
    test_fuel_model()
