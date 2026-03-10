"""
Exemple d'utilisation du détecteur de spoofing AVANCÉ
Montre comment utiliser toutes les fonctionnalités avancées

Usage:
    python example_advanced_spoofing.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.security.advanced_spoofing_detector import AdvancedSpoofingDetector
from src.security.spoofing_injector import SpoofingInjector, SpoofingConfig, SpoofingType
import numpy as np


def test_clean_trajectory():
    """Test sur une trajectoire propre (sans spoofing)"""
    print("\n" + "="*80)
    print("TEST 1: Trajectoire authentique (sans spoofing)")
    print("="*80)
    
    # Charger une trajectoire réelle
    kml_files = list(Path('../data/sample').glob('*.kml'))
    if not kml_files:
        print("⚠️  Aucun fichier KML dans ../data/sample/")
        return
    
    parser = KMLParser(str(kml_files[0]))
    trajectory = parser.parse()
    
    print(f"Vol: {trajectory.flight_id}")
    print(f"Points: {len(trajectory)}")
    
    # Analyse avec détecteur avancé
    detector = AdvancedSpoofingDetector(
        commercial_aircraft=True,
        enable_ml_scoring=True,
        enable_pattern_detection=True
    )
    
    report = detector.analyze_comprehensive(trajectory, verbose=True)
    
    return report


def test_injected_spoofing():
    """Test sur une trajectoire avec spoofing injecté"""
    print("\n" + "="*80)
    print("TEST 2: Trajectoire avec spoofing injecté")
    print("="*80)
    
    # Charger une trajectoire réelle
    kml_files = list(Path('../data/sample').glob('*.kml'))
    if not kml_files:
        print("⚠️  Aucun fichier KML dans ../data/sample/")
        return
    
    parser = KMLParser(str(kml_files[0]))
    trajectory = parser.parse()
    
    # Injecter différents types de spoofing
    injector = SpoofingInjector(seed=42)
    
    # Scénario mixte : plusieurs types d'anomalies
    print("\n🎭 Injection de spoofing...")
    
    # 1. Quelques sauts de position
    config1 = SpoofingConfig(
        spoofing_type=SpoofingType.TELEPORTATION,
        num_points=3,
        intensity=5.0
    )
    spoofed_trajectory = injector.inject(trajectory, config1)
    
    # 2. Vitesses excessives
    config2 = SpoofingConfig(
        spoofing_type=SpoofingType.SPEED_MANIPULATION,
        num_points=2,
        intensity=2.0
    )
    spoofed_trajectory = injector.inject(spoofed_trajectory, config2)
    
    # 3. Saut d'altitude
    config3 = SpoofingConfig(
        spoofing_type=SpoofingType.ALTITUDE_JUMP,
        num_points=1,
        intensity=2.0
    )
    spoofed_trajectory = injector.inject(spoofed_trajectory, config3)
    
    print(f"✓ Spoofing injecté: 3 types d'anomalies")
    
    # Détection avec le système avancé
    detector = AdvancedSpoofingDetector(
        commercial_aircraft=True,
        strict_mode=True,
        enable_ml_scoring=True,
        enable_pattern_detection=True
    )
    
    report = detector.analyze_comprehensive(spoofed_trajectory, verbose=True)
    
    # Vérifier si le spoofing a été détecté
    print("\n" + "="*80)
    print("RÉSULTAT DE DÉTECTION")
    print("="*80)
    print(f"Anomalies détectées    : {len(report.anomalies)}")
    print(f"Score de risque global : {report.global_risk_score*100:.1f}%")
    
    if report.global_risk_score > 0.5:
        print("✅ SUCCÈS - Spoofing détecté avec succès!")
    else:
        print("⚠️  Spoofing partiellement détecté")
    
    return report


def test_pattern_detection():
    """Test spécifique de la détection de patterns"""
    print("\n" + "="*80)
    print("TEST 3: Détection de patterns spécifiques")
    print("="*80)
    
    # Charger une trajectoire
    kml_files = list(Path('../data/sample').glob('*.kml'))
    if not kml_files:
        print("⚠️  Aucun fichier KML dans ../data/sample/")
        return
    
    parser = KMLParser(str(kml_files[0]))
    trajectory = parser.parse()
    
    # Test de chaque pattern individuellement
    detector = AdvancedSpoofingDetector()
    
    patterns_to_test = [
        ("Altitude constante", detector._detect_constant_altitude_drift),
        ("Cercle parfait", detector._detect_perfect_circle),
        ("Répétition position", detector._detect_position_repetition),
        ("Offset soudain", detector._detect_sudden_offset),
        ("Quantification", detector._detect_quantization),
        ("Virage impossible", detector._detect_impossible_turn),
        ("Discontinuité vitesse", detector._detect_velocity_discontinuity)
    ]
    
    print("\n🎯 Test des patterns de spoofing:")
    for name, func in patterns_to_test:
        try:
            detected, anomalies = func(trajectory)
            status = "✅ DÉTECTÉ" if detected else "❌ Non détecté"
            print(f"   {name:25s}: {status} ({len(anomalies)} anomalies)")
        except Exception as e:
            print(f"   {name:25s}: ⚠️  Erreur - {str(e)[:40]}")


def compare_basic_vs_advanced():
    """Compare le détecteur basique vs avancé"""
    print("\n" + "="*80)
    print("TEST 4: Comparaison détecteur basique vs avancé")
    print("="*80)
    
    # Charger et injecter du spoofing
    kml_files = list(Path('../data/sample').glob('*.kml'))
    if not kml_files:
        print("⚠️  Aucun fichier KML dans ../data/sample/")
        return
    
    parser = KMLParser(str(kml_files[0]))
    trajectory = parser.parse()
    
    # Injecter spoofing subtil
    injector = SpoofingInjector(seed=42)
    
    config1 = SpoofingConfig(
        spoofing_type=SpoofingType.TELEPORTATION,
        num_points=2,
        intensity=3.0
    )
    spoofed = injector.inject(trajectory, config1)
    
    config2 = SpoofingConfig(
        spoofing_type=SpoofingType.SPEED_MANIPULATION,
        num_points=2,
        intensity=1.5
    )
    spoofed = injector.inject(spoofed, config2)
    
    # Détecteur basique
    from src.security.spoofing_detector import SpoofingDetector
    basic_detector = SpoofingDetector()
    basic_anomalies = basic_detector.detect_anomalies(spoofed)
    basic_summary = basic_detector.get_summary(basic_anomalies)
    
    # Détecteur avancé
    advanced_detector = AdvancedSpoofingDetector(
        enable_ml_scoring=True,
        enable_pattern_detection=True
    )
    advanced_report = advanced_detector.analyze_comprehensive(spoofed, verbose=False)
    
    # Comparaison
    print("\n📊 COMPARAISON DES RÉSULTATS")
    print("-" * 80)
    print(f"{'Métrique':<35s} {'Basique':>15s} {'Avancé':>15s}")
    print("-" * 80)
    print(f"{'Anomalies détectées':<35s} {len(basic_anomalies):>15d} {len(advanced_report.anomalies):>15d}")
    print(f"{'Score de risque':<35s} {'-':>15s} {advanced_report.global_risk_score*100:>14.1f}%")
    print(f"{'Outliers statistiques':<35s} {'-':>15s} {advanced_report.statistical_outliers:>15d}")
    print(f"{'Patterns détectés':<35s} {'-':>15s} {len(advanced_report.detected_patterns):>15d}")
    print(f"{'Replay attack détecté':<35s} {'-':>15s} {'Oui' if advanced_report.replay_attack_detected else 'Non':>15s}")
    print(f"{'Continuité trajectoire':<35s} {'-':>15s} {advanced_report.trajectory_continuity_score*100:>14.1f}%")
    print(f"{'Plausibilité physique':<35s} {'-':>15s} {advanced_report.physical_plausibility*100:>14.1f}%")
    print("-" * 80)
    
    print(f"\n💡 Le détecteur avancé a trouvé {len(advanced_report.anomalies) - len(basic_anomalies)} anomalies supplémentaires")
    print(f"   grâce aux techniques ML et analyse de patterns.")


def test_replay_attack_detection():
    """Test spécifique de détection de replay attack"""
    print("\n" + "="*80)
    print("TEST 5: Détection de replay attack")
    print("="*80)
    
    # Charger une trajectoire
    kml_files = list(Path('../data/sample').glob('*.kml'))
    if not kml_files:
        print("⚠️  Aucun fichier KML dans ../data/sample/")
        return
    
    parser = KMLParser(str(kml_files[0]))
    trajectory = parser.parse()
    
    print(f"\n📡 Trajectoire originale: {len(trajectory)} points")
    
    # Simuler un replay attack en dupliquant un segment
    from src.data.data_models import Trajectory, Position
    from datetime import timedelta
    
    positions = []
    
    # Prendre la première moitié
    first_half = trajectory.positions[:len(trajectory) // 2]
    positions.extend(first_half)
    
    # Dupliquer un segment du début (replay)
    segment_to_replay = trajectory.positions[50:60]
    
    # Créer nouvelles positions avec timestamps ajustés
    last_time = positions[-1].timestamp
    time_delta = timedelta(seconds=1)
    
    for i, pos in enumerate(segment_to_replay):
        new_time = last_time + time_delta * (i + 1)
        new_pos = Position(
            latitude=pos.latitude,
            longitude=pos.longitude,
            altitude=pos.altitude,
            timestamp=new_time,
            ground_speed=pos.ground_speed,
            vertical_rate=pos.vertical_rate,
            heading=pos.heading
        )
        positions.append(new_pos)
    
    # Ajouter le reste avec timestamps ajustés
    last_time = positions[-1].timestamp
    remaining = trajectory.positions[len(trajectory) // 2:]
    for i, pos in enumerate(remaining):
        new_time = last_time + time_delta * (i + 1)
        new_pos = Position(
            latitude=pos.latitude,
            longitude=pos.longitude,
            altitude=pos.altitude,
            timestamp=new_time,
            ground_speed=pos.ground_speed,
            vertical_rate=pos.vertical_rate,
            heading=pos.heading
        )
        positions.append(new_pos)
    
    replay_trajectory = Trajectory(positions, flight_id="replay_test")
    
    print(f"🔄 Trajectoire avec replay: {len(replay_trajectory)} points (segment de 10 points rejoué)")
    
    # Détection
    detector = AdvancedSpoofingDetector()
    report = detector.analyze_comprehensive(replay_trajectory, verbose=True)
    
    if report.replay_attack_detected:
        print("\n✅ REPLAY ATTACK DÉTECTÉ AVEC SUCCÈS!")
    else:
        print("\n⚠️  Replay attack non détecté")


def main():
    """Exécute tous les tests"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 18 + "TESTS DU DÉTECTEUR ANTI-SPOOFING AVANCÉ" + " " * 20 + "║")
    print("║" + " " * 25 + "Février 2026 - ENAC" + " " * 33 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        # Test 1: Trajectoire propre
        report1 = test_clean_trajectory()
        
        # Test 2: Spoofing injecté
        report2 = test_injected_spoofing()
        
        # Test 3: Patterns spécifiques
        test_pattern_detection()
        
        # Test 4: Comparaison basique vs avancé
        compare_basic_vs_advanced()
        
        # Test 5: Replay attack
        test_replay_attack_detection()
        
        print("\n" + "="*80)
        print("✅ TOUS LES TESTS TERMINÉS")
        print("="*80)
        print("\n📖 Le détecteur avancé offre:")
        print("   • Détection statistique d'outliers multivariés")
        print("   • Reconnaissance de 7 patterns de spoofing connus")
        print("   • Analyse de cohérence globale de trajectoire")
        print("   • Détection de replay attacks")
        print("   • Scoring ML-like pour évaluation du risque")
        print("   • Recommandations automatiques")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
