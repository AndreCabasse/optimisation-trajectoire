"""
Script simple pour visualiser la détection de spoofing
Crée une carte HTML interactive montrant :
- La trajectoire originale (bleue)
- La trajectoire avec spoofing (colorée selon confiance)
- Les anomalies détectées (marqueurs)
"""
import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import folium

from src.data.kml_parser import KMLParser
from src.security.spoofing_detector import SpoofingDetector
from src.security.spoofing_injector import SpoofingInjector, SpoofingConfig, SpoofingType


def creer_carte_spoofing(
    original,
    spoofed,
    anomalies,
    confidence,
    output_file="output/carte_spoofing.html"
):
    """
    Crée une carte interactive HTML avec visualisation complète
    
    Args:
        original: Trajectoire originale
        spoofed: Trajectoire avec spoofing injecté
        anomalies: Liste des anomalies détectées
        confidence: Scores de confiance pour chaque point
        output_file: Fichier HTML de sortie
    """
    print(f"\n🗺️  Création de la carte interactive...")
    
    # Créer la carte centrée sur la trajectoire
    center_lat = sum(p.latitude for p in original.positions) / len(original.positions)
    center_lon = sum(p.longitude for p in original.positions) / len(original.positions)
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # ========== TRAJECTOIRE ORIGINALE (BLEUE) ==========
    original_coords = [(p.latitude, p.longitude) for p in original.positions]
    folium.PolyLine(
        original_coords,
        color='blue',
        weight=3,
        opacity=0.5,
        popup='<b>Trajectoire originale</b><br>Données non modifiées',
        tooltip='Trajectoire originale'
    ).add_to(m)
    
    # Points de départ et fin (original)
    folium.Marker(
        location=[original.positions[0].latitude, original.positions[0].longitude],
        popup='<b>🛫 Départ</b>',
        icon=folium.Icon(color='blue', icon='plane', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        location=[original.positions[-1].latitude, original.positions[-1].longitude],
        popup='<b>🛬 Arrivée</b>',
        icon=folium.Icon(color='blue', icon='flag-checkered', prefix='fa')
    ).add_to(m)
    
    # ========== TRAJECTOIRE SPOOFÉE (COLORÉE PAR CONFIANCE) ==========
    for i, pos in enumerate(spoofed.positions):
        if i == 0:
            continue
        
        prev_pos = spoofed.positions[i-1]
        conf = confidence[i]
        
        # Couleur selon le score de confiance
        if conf >= 0.9:
            color = 'green'
            label = 'Excellent'
        elif conf >= 0.7:
            color = 'orange'
            label = 'Moyen'
        elif conf >= 0.5:
            color = 'red'
            label = 'Suspect'
        else:
            color = 'darkred'
            label = 'Très suspect'
        
        folium.PolyLine(
            [(prev_pos.latitude, prev_pos.longitude), (pos.latitude, pos.longitude)],
            color=color,
            weight=4,
            opacity=0.8,
            popup=f'<b>Segment {i}</b><br>Confiance: {conf:.1%}<br>État: {label}'
        ).add_to(m)
    
    # ========== ANOMALIES DÉTECTÉES (MARQUEURS COLORÉS) ==========
    anomaly_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
    
    for anomaly in anomalies:
        if anomaly.index < len(spoofed.positions):
            pos = spoofed.positions[anomaly.index]
            
            # Couleur et icône selon la sévérité
            severity_config = {
                'low': {'color': 'lightblue', 'icon': 'info-sign', 'size': 6},
                'medium': {'color': 'orange', 'icon': 'warning-sign', 'size': 8},
                'high': {'color': 'red', 'icon': 'exclamation-sign', 'size': 10},
                'critical': {'color': 'darkred', 'icon': 'remove-sign', 'size': 12}
            }
            
            config = severity_config.get(anomaly.severity, severity_config['low'])
            anomaly_counts[anomaly.severity] += 1
            
            # Marqueur pour l'anomalie
            folium.CircleMarker(
                location=[pos.latitude, pos.longitude],
                radius=config['size'],
                color=config['color'],
                fill=True,
                fillColor=config['color'],
                fillOpacity=0.8,
                popup=f"""
                    <div style='width: 250px'>
                        <h4>⚠️ Anomalie #{anomaly.index}</h4>
                        <p><b>Type:</b> {anomaly.anomaly_type.value}</p>
                        <p><b>Sévérité:</b> <span style='color:{config["color"]}'>{anomaly.severity.upper()}</span></p>
                        <p><b>Confiance:</b> {anomaly.confidence_score:.1%}</p>
                        <p><b>Description:</b> {anomaly.description}</p>
                        <p><b>Valeur mesurée:</b> {anomaly.measured_value:.2f}</p>
                        <p><b>Seuil:</b> {anomaly.threshold_value:.2f}</p>
                        <p><b>Timestamp:</b> {anomaly.timestamp.strftime('%H:%M:%S')}</p>
                    </div>
                """,
                tooltip=f'{anomaly.anomaly_type.value} ({anomaly.severity})'
            ).add_to(m)
    
    # ========== LÉGENDE ==========
    legend_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 280px; height: auto; 
                background-color: white; z-index:9999; font-size:13px;
                border:3px solid #333; border-radius: 8px; padding: 15px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        
        <h3 style="margin-top:0; color:#333;">🛡️ Détection de Spoofing</h3>
        
        <h4 style="margin-bottom:5px;">Trajectoires:</h4>
        <p style="margin:3px 0;"><span style="color: blue; font-weight:bold;">━━━</span> Trajectoire originale</p>
        <p style="margin:3px 0;"><span style="color: green; font-weight:bold;">━━━</span> Confiance élevée (&gt;90%)</p>
        <p style="margin:3px 0;"><span style="color: orange; font-weight:bold;">━━━</span> Confiance moyenne (70-90%)</p>
        <p style="margin:3px 0;"><span style="color: red; font-weight:bold;">━━━</span> Confiance faible (&lt;70%)</p>
        
        <h4 style="margin-bottom:5px; margin-top:10px;">Anomalies détectées:</h4>
        <p style="margin:3px 0;">🔵 <span style="color:lightblue;">Low</span> ({anomaly_counts['low']})</p>
        <p style="margin:3px 0;">🟠 <span style="color:orange;">Medium</span> ({anomaly_counts['medium']})</p>
        <p style="margin:3px 0;">🔴 <span style="color:red;">High</span> ({anomaly_counts['high']})</p>
        <p style="margin:3px 0;">⛔ <span style="color:darkred;">Critical</span> ({anomaly_counts['critical']})</p>
        
        <hr style="margin:10px 0;">
        <p style="margin:3px 0; font-size:11px;"><b>Total:</b> {len(anomalies)} anomalies</p>
        <p style="margin:3px 0; font-size:11px;"><b>Points:</b> {len(spoofed.positions)}</p>
        <p style="margin:3px 0; font-size:11px;"><b>Confiance moy.:</b> {confidence.mean():.1%}</p>
    </div>
    '''
    
    # Ajouter la légende à la carte
    m.get_root().html.add_child(folium.Element(legend_html))  # type: ignore
    
    # Sauvegarder la carte
    Path(output_file).parent.mkdir(exist_ok=True, parents=True)
    m.save(output_file)
    
    print(f"   ✓ Carte sauvegardée : {output_file}")
    print(f"   📊 {len(anomalies)} anomalies marquées sur la carte")
    print(f"   📍 Confiance moyenne : {confidence.mean():.1%}")
    
    return output_file


# ============================================================
# EXEMPLES D'UTILISATION
# ============================================================

def exemple_1_simple():
    """Exemple 1 : Visualisation simple avec injection légère"""
    print("\n" + "="*70)
    print("EXEMPLE 1 : Visualisation avec spoofing léger")
    print("="*70)
    
    # 1. Charger une trajectoire
    parser = KMLParser("data/sample/F-HZUE-track-EGM96.kml")
    trajectory = parser.parse()
    print(f"✓ Trajectoire chargée : {len(trajectory)} points")
    
    # 2. Injecter du spoofing léger
    injector = SpoofingInjector(seed=42)
    spoofed = injector.create_spoofing_scenario(trajectory, scenario="light")
    
    # 3. Détecter les anomalies
    detector = SpoofingDetector()
    anomalies = detector.detect_anomalies(spoofed)
    confidence = detector.compute_confidence_scores(spoofed, anomalies)
    
    # 4. Afficher le résumé
    summary = detector.get_summary(anomalies)
    detector.print_report(anomalies, summary)
    
    # 5. Créer la carte
    carte = creer_carte_spoofing(
        trajectory,
        spoofed,
        anomalies,
        confidence,
        output_file="output/exemple_1_leger.html"
    )
    
    print(f"\n✅ Ouvrez {carte} dans votre navigateur pour voir les résultats !")


def exemple_2_comparaison_scenarios():
    """Exemple 2 : Comparer plusieurs scénarios"""
    print("\n" + "="*70)
    print("EXEMPLE 2 : Comparaison de différents scénarios")
    print("="*70)
    
    # Charger la trajectoire
    parser = KMLParser("data/sample/F-HZUE-track-EGM96.kml")
    trajectory = parser.parse()
    
    injector = SpoofingInjector(seed=42)
    detector = SpoofingDetector()
    
    scenarios = ["light", "medium", "heavy"]
    
    for scenario in scenarios:
        print(f"\n--- Scénario : {scenario.upper()} ---")
        
        # Injecter + détecter
        spoofed = injector.create_spoofing_scenario(trajectory, scenario=scenario)
        anomalies = detector.detect_anomalies(spoofed)
        confidence = detector.compute_confidence_scores(spoofed, anomalies)
        
        # Résumé rapide
        summary = detector.get_summary(anomalies)
        print(f"   Anomalies : {summary['total_anomalies']}")
        print(f"   Risque : {summary['risk_level']}")
        
        # Créer la carte
        creer_carte_spoofing(
            trajectory,
            spoofed,
            anomalies,
            confidence,
            output_file=f"output/scenario_{scenario}.html"
        )
    
    print(f"\n✅ 3 cartes créées dans le dossier 'output/'")


def exemple_3_injection_personnalisee():
    """Exemple 3 : Injection personnalisée de types spécifiques"""
    print("\n" + "="*70)
    print("EXEMPLE 3 : Injection personnalisée")
    print("="*70)
    
    # Charger la trajectoire
    parser = KMLParser("data/sample/F-HZUE-track-EGM96.kml")
    trajectory = parser.parse()
    
    # Créer des injections personnalisées
    injector = SpoofingInjector(seed=42)
    
    configs = [
        SpoofingConfig(
            SpoofingType.TELEPORTATION,
            num_points=5,
            intensity=2.0,
            description="Téléportation massive"
        ),
        SpoofingConfig(
            SpoofingType.ALTITUDE_JUMP,
            num_points=3,
            intensity=1.5,
            description="Sauts d'altitude"
        ),
        SpoofingConfig(
            SpoofingType.IMPOSSIBLE_MANEUVER,
            num_points=7,
            intensity=1.0,
            description="Manœuvre impossible"
        )
    ]
    
    print("\nInjection de 3 types d'anomalies personnalisées...")
    spoofed = injector.inject_multiple(trajectory, configs)
    
    # Détecter
    detector = SpoofingDetector()
    anomalies = detector.detect_anomalies(spoofed)
    confidence = detector.compute_confidence_scores(spoofed, anomalies)
    
    # Rapport détaillé
    summary = detector.get_summary(anomalies)
    detector.print_report(anomalies, summary)
    
    # Carte
    creer_carte_spoofing(
        trajectory,
        spoofed,
        anomalies,
        confidence,
        output_file="output/injection_personnalisee.html"
    )
    
    print(f"\n✅ Carte créée : output/injection_personnalisee.html")


def menu_principal():
    """Menu interactif pour choisir un exemple"""
    print("\n" + "="*70)
    print(" "*15 + "🛡️  VISUALISATION DE SPOOFING ADS-B")
    print("="*70)
    print("\nChoisissez un exemple :\n")
    print("  1. Exemple simple (spoofing léger)")
    print("  2. Comparaison de scénarios (light, medium, heavy)")
    print("  3. Injection personnalisée")
    print("  4. Lancer tous les exemples")
    print("  0. Quitter")
    print()
    
    choix = input("Votre choix : ").strip()
    
    if choix == "1":
        exemple_1_simple()
    elif choix == "2":
        exemple_2_comparaison_scenarios()
    elif choix == "3":
        exemple_3_injection_personnalisee()
    elif choix == "4":
        exemple_1_simple()
        exemple_2_comparaison_scenarios()
        exemple_3_injection_personnalisee()
    elif choix == "0":
        print("Au revoir !")
        return
    else:
        print("Choix invalide !")
        return
    
    print("\n" + "="*70)
    print("✅ TERMINÉ !")
    print("="*70)
    print("\n💡 Ouvrez les fichiers HTML dans le dossier 'output/' avec votre navigateur")
    print("   Les cartes sont interactives : cliquez sur les points pour voir les détails !")


if __name__ == "__main__":
    menu_principal()
