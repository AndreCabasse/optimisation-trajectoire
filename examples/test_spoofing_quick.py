"""
Test rapide du système de détection de spoofing
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.security.spoofing_detector import SpoofingDetector
from src.security.spoofing_injector import SpoofingInjector, SpoofingConfig, SpoofingType


def main():
    """Fonction principale"""
    print("\n" + "="*80)
    print("SYSTÈME DE DÉTECTION DE SPOOFING ADS-B - TEST RAPIDE")
    print("="*80)
    
    # 1. Charger une trajectoire réelle
    print("\n[1/4] Chargement de la trajectoire...")
    kml_file = Path(__file__).parent.parent / "data" / "sample" / "F-HZUE-track-EGM96.kml"
    parser = KMLParser(str(kml_file))
    trajectory = parser.parse()
    print(f"   OK - {len(trajectory.positions)} points charges")
    
    # 2. Créer le détecteur
    print("\n[2/4] Initialisation du detecteur...")
    detector = SpoofingDetector()
    print("   OK")
    
    # 3. Injecter du spoofing
    print("\n[3/4] Injection de spoofing (scenario 'medium')...")
    injector = SpoofingInjector(seed=42)
    spoofed = injector.create_spoofing_scenario(trajectory, scenario="medium")
    print("   OK")
    print(injector.get_injection_report())
    
    # 4. Détecter les anomalies
    print("\n[4/4] Detection des anomalies...")
    anomalies = detector.detect_anomalies(spoofed)
    print(f"   OK - {len(anomalies)} anomalies detectees")
    
    # Afficher le résumé
    summary = detector.get_summary(anomalies)
    print(f"\n{'='*80}")
    print("RESULTATS")
    print(f"{'='*80}")
    print(f"Niveau de risque : {summary['risk_level']}")
    print(f"Total anomalies  : {summary['total_anomalies']}")
    print(f"Spoofing detecte : {'OUI' if summary['spoofing_detected'] else 'NON'}")
    print(f"Critical         : {summary['by_severity'].get('critical', 0)}")
    print(f"High             : {summary['by_severity'].get('high', 0)}")
    print(f"Medium           : {summary['by_severity'].get('medium', 0)}")
    print(f"Low              : {summary['by_severity'].get('low', 0)}")
    
    # Scores de confiance
    confidence = detector.compute_confidence_scores(spoofed, anomalies)
    print(f"\nScore de confiance moyen : {confidence.mean():.3f}")
    print(f"Points suspects (<0.8)   : {(confidence < 0.8).sum()}")
    print(f"Points critiques (<0.5)  : {(confidence < 0.5).sum()}")
    
    print(f"\n{'='*80}")
    print("TEST TERMINE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
