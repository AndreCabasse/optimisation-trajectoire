"""
Script pour visualiser les résultats de comparaison avec matplotlib
Évite le problème de cache de Windows Photo Viewer
"""
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pathlib import Path
import sys

# Chemin vers les images
output_dir = Path(__file__).parent / 'output' / 'comparaison_complete'

images = {
    'Comparaison complète (8 graphiques)': 'methods_comparison.png',
    'Graphique radar (5 critères)': 'radar_comparison.png',
    'Infographie résumée': 'infographie_comparison.png'
}

print("="*80)
print("  📊 VISUALISATION DES RÉSULTATS DE COMPARAISON  ")
print("="*80)
print()

for title, filename in images.items():
    filepath = output_dir / filename
    
    if not filepath.exists():
        print(f"❌ Fichier non trouvé: {filepath}")
        continue
    
    # Obtenir les informations du fichier
    import os
    mod_time = os.path.getmtime(filepath)
    from datetime import datetime
    mod_datetime = datetime.fromtimestamp(mod_time)
    file_size = os.path.getsize(filepath) / 1024  # Ko
    
    print(f"\n📄 {title}")
    print(f"   Fichier: {filename}")
    print(f"   Dernière modification: {mod_datetime.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"   Taille: {file_size:.1f} Ko")
    print(f"   Ouverture...")
    
    # Charger et afficher l'image
    try:
        img = mpimg.imread(str(filepath))
        
        fig = plt.figure(figsize=(16, 10))
        plt.imshow(img)
        plt.axis('off')
        plt.title(f"{title}\n(Mis à jour: {mod_datetime.strftime('%H:%M:%S')})", 
                 fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        
        # Maximiser la fenêtre si possible
        manager = plt.get_current_fig_manager()
        try:
            manager.window.state('zoomed')  # Windows
        except:
            try:
                manager.full_screen_toggle()  # Autre
            except:
                pass
        
        plt.show()
        
        print(f"   ✅ Image affichée")
        
    except Exception as e:
        print(f"   ❌ Erreur lors de l'ouverture: {e}")

print("\n" + "="*80)
print("  ✅ VISUALISATION TERMINÉE  ")
print("="*80)
print()
print("💡 Conseil: Utilisez ce script au lieu de Windows Photo Viewer")
print("   pour éviter les problèmes de cache d'images.")
print()
print("📂 Vous pouvez aussi ouvrir le dossier:")
print(f"   {output_dir}")
print()
