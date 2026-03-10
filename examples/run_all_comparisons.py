"""
Script principal pour générer TOUTES les comparaisons en une seule commande
"""
import sys
from pathlib import Path
import subprocess
import time

print("="*80)
print("  🚀 GÉNÉRATION COMPLÈTE DE LA COMPARAISON DES MÉTHODES  ")
print("="*80)
print()

scripts = [
    ("compare_methods.py", "Comparaison détaillée avec 8 graphiques"),
    ("radar_comparison.py", "Graphique radar comparatif"),
    ("create_infographic.py", "Infographie résumée"),
]

total_start = time.time()

for i, (script, description) in enumerate(scripts, 1):
    print(f"\n[{i}/{len(scripts)}] 📊 {description}...")
    print("-" * 80)
    
    script_path = Path(__file__).parent / script
    start = time.time()
    
    try:
        # Exécuter le script avec encodage UTF-8 explicite
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Remplacer les caractères invalides au lieu de crasher
            cwd=script_path.parent
        )
        
        elapsed = time.time() - start
        
        if result.returncode == 0:
            print(f"✅ Succès ({elapsed:.1f}s)")
            # Afficher seulement les lignes importantes
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if '✅' in line or '🏆' in line or 'sauvegardé' in line.lower():
                        print(f"   {line}")
        else:
            print(f"❌ Erreur ({elapsed:.1f}s)")
            if result.stderr:
                print(result.stderr)
    
    except Exception as e:
        print(f"❌ Erreur: {e}")

total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("  ✅ GÉNÉRATION COMPLÈTE TERMINÉE  ")
print("="*80)
print(f"\n⏱️  Temps total: {total_elapsed:.1f} secondes")
print(f"\n📁 Fichiers générés dans output/comparaison_complete/:")
print(f"   1. methods_comparison.png - Graphiques détaillés (8 panneaux)")
print(f"   2. methods_comparison_map.html - Carte interactive Folium")
print(f"   3. radar_comparison.png - Graphique radar (5 critères)")
print(f"   4. infographie_comparison.png - Infographie résumée")
print(f"\n📖 Documentation:")
print(f"   • COMPARAISON_METHODES.md - Analyse détaillée complète")
print(f"   • README.md - Vue d'ensemble mise à jour")

print(f"\n💡 Pour ouvrir les résultats:")
print(f"   • Windows: explorer output\\comparaison_complete")
print(f"   • Mac/Linux: open output/comparaison_complete")

print("\n" + "="*80)
