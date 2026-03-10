"""
Comparaison complète et détaillée des différentes méthodes d'optimisation
"""
import sys
import os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import time
from typing import Dict, List, Any

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod
from src.data.data_models import Trajectory

# Charger données
kml_file = Path(__file__).parent.parent / "data" / "sample" / "4B1804-track-EGM96.kml"
parser = KMLParser(str(kml_file))
traj = parser.parse()

print("=" * 80)
print("  COMPARAISON COMPLÈTE DES MÉTHODES D'OPTIMISATION DE TRAJECTOIRES  ")
print("=" * 80)
print(f"\n📊 Trajectoire originale: {len(traj)} points")
print(f"   Durée du vol: {traj.duration:.1f} secondes ({traj.duration/60:.1f} minutes)")
print(f"   Flight ID: {traj.flight_id}")

# Nombre de points cibles pour les optimisations
TARGET_POINTS = 200

# Dictionnaire pour stocker tous les résultats
results = {}
timings = {}

print(f"\n🔄 Optimisation en cours (cible: {TARGET_POINTS} points)...\n")

# 1. Optimisation KALMAN uniquement
print("   1/5 - Filtre de Kalman...")
start_time = time.time()
opt_kalman = TrajectoryOptimizer(method=OptimizationMethod.KALMAN)
result_kalman = opt_kalman.optimize(traj, target_points=TARGET_POINTS)
traj_kalman = result_kalman.get_optimized_trajectory()
timings['Kalman'] = time.time() - start_time
results['Kalman'] = result_kalman
print(f"        ✓ Kalman seul: {len(traj_kalman)} points ({timings['Kalman']:.3f}s)")

# 2. Optimisation B-SPLINE uniquement
print("   2/5 - B-spline...")
start_time = time.time()
opt_bspline = TrajectoryOptimizer(method=OptimizationMethod.BSPLINE)
result_bspline = opt_bspline.optimize(traj, target_points=TARGET_POINTS)
traj_bspline = result_bspline.get_optimized_trajectory()
timings['B-spline'] = time.time() - start_time
results['B-spline'] = result_bspline
print(f"        ✓ B-spline seul: {len(traj_bspline)} points ({timings['B-spline']:.3f}s)")

# 3. Optimisation HYBRIDE (Kalman + B-spline)
print("   3/5 - Hybride (Kalman + B-spline)...")
start_time = time.time()
opt_hybrid = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
result_hybrid = opt_hybrid.optimize(traj, target_points=TARGET_POINTS)
traj_hybrid = result_hybrid.get_optimized_trajectory()
timings['Hybride'] = time.time() - start_time
results['Hybride'] = result_hybrid
print(f"        ✓ Hybride: {len(traj_hybrid)} points ({timings['Hybride']:.3f}s)")

# 4. Optimisation WEATHER (avec données météo)
print("   4/5 - Météo (avec optimisation vent)...")
start_time = time.time()
opt_weather = TrajectoryOptimizer(method=OptimizationMethod.WEATHER)
result_weather = opt_weather.optimize(traj, use_weather=True, target_points=TARGET_POINTS)
traj_weather = result_weather.get_optimized_trajectory()
timings['Météo'] = time.time() - start_time
results['Météo'] = result_weather
print(f"        ✓ Météo optimisée: {len(traj_weather)} points ({timings['Météo']:.3f}s)")

# 5. Optimisation DIRECT COLLOCATION (NLP)
print("   5/5 - NLP Direct Collocation...")
start_time = time.time()
opt_nlp = TrajectoryOptimizer(method=OptimizationMethod.DIRECT_COLLOCATION)
result_nlp = opt_nlp.optimize(traj, use_weather=True, target_points=TARGET_POINTS)
traj_nlp = result_nlp.get_optimized_trajectory()
timings['NLP'] = time.time() - start_time
results['NLP'] = result_nlp
print(f"        ✓ NLP Direct Collocation: {len(traj_nlp)} points ({timings['NLP']:.3f}s)")

# Dictionnaire des trajectoires pour faciliter l'accès
trajectories = {
    'Original': traj,
    'Kalman': traj_kalman,
    'B-spline': traj_bspline,
    'Hybride': traj_hybrid,
    'Météo': traj_weather,
    'NLP': traj_nlp
}

# ============================================================================
# ANALYSE DÉTAILLÉE DES MÉTHODES
# ============================================================================

def compute_total_distance(trajectory: Trajectory) -> float:
    """Calcule la distance totale parcourue"""
    cart = trajectory.get_cartesian_array()
    return np.sum(np.sqrt(np.sum(np.diff(cart, axis=0)**2, axis=1)))

def compute_smoothness(trajectory: Trajectory) -> float:
    """Calcule la smoothness (lissage) - somme des variations d'accélération"""
    cart = trajectory.get_cartesian_array()
    if len(cart) < 3:
        return 0.0
    # Deuxième dérivée (accélération)
    acc = np.diff(cart, n=2, axis=0)
    # Somme des normes
    return np.sum(np.sqrt(np.sum(acc**2, axis=1)))

def compute_curvature_stats(trajectory: Trajectory) -> Dict:
    """Calcule les statistiques de courbure"""
    cart = trajectory.get_cartesian_array()
    if len(cart) < 3:
        return {'mean': 0, 'max': 0, 'std': 0}
    
    # Première et deuxième dérivées
    v = np.diff(cart, axis=0)
    a = np.diff(v, axis=0)
    
    # Courbure = ||v × a|| / ||v||^3
    curvatures = []
    for i in range(len(a)):
        cross = np.cross(v[i+1], a[i])
        v_norm = np.linalg.norm(v[i+1])
        if v_norm > 1e-6:
            curv = np.linalg.norm(cross) / (v_norm**3)
            curvatures.append(curv)
    
    if curvatures:
        return {
            'mean': np.mean(curvatures),
            'max': np.max(curvatures),
            'std': np.std(curvatures)
        }
    return {'mean': 0, 'max': 0, 'std': 0}

print("\n" + "=" * 80)
print("  📊 TABLEAU COMPARATIF DES MÉTHODES  ")
print("=" * 80)

# Calcul des métriques pour chaque méthode
metrics_table: Dict[str, Any] = {}
for name, trajectory in trajectories.items():
    if name == 'Original':
        metrics_table[name] = {
            'points': len(trajectory),
            'distance_km': compute_total_distance(trajectory) / 1000,
            'smoothness': compute_smoothness(trajectory),
            'curvature': compute_curvature_stats(trajectory),
            'time_s': 0.0
        }
    else:
        metrics_table[name] = {
            'points': len(trajectory),
            'distance_km': compute_total_distance(trajectory) / 1000,
            'smoothness': compute_smoothness(trajectory),
            'curvature': compute_curvature_stats(trajectory),
            'time_s': timings.get(name, 0.0),
            'compression': len(trajectory) / len(traj) * 100
        }

# Affichage du tableau
print(f"\n{'Méthode':<15} {'Points':<10} {'Distance':<12} {'Compression':<12} {'Temps calc.':<12}")
print("=" * 80)
for name in ['Original', 'Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    m = metrics_table[name]
    if name == 'Original':
        print(f"{name:<15} {m['points']:<10} {m['distance_km']:>8.2f} km  {'-':<12} {'-':<12}")
    else:
        print(f"{name:<15} {m['points']:<10} {m['distance_km']:>8.2f} km  "
              f"{m['compression']:>8.1f}%    {m['time_s']:>8.3f}s")

print("\n" + "=" * 80)
print("  📈 MÉTRIQUES QUALITATIVES  ")
print("=" * 80)

print(f"\n{'Méthode':<15} {'Smoothness':<15} {'Courbure moy.':<15} {'Courbure max':<15}")
print("=" * 80)
for name in ['Original', 'Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    m = metrics_table[name]
    print(f"{name:<15} {m['smoothness']:>12.1f}   "
          f"{m['curvature']['mean']:>12.2e}   {m['curvature']['max']:>12.2e}")  # type: ignore

# Analyse des différences par rapport à l'original
print("\n" + "=" * 80)
print("  🎯 ÉCARTS PAR RAPPORT À LA TRAJECTOIRE ORIGINALE  ")
print("=" * 80)

coords_orig = traj.get_coordinates_array()
orig_cart = traj.get_cartesian_array()

for name in ['Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    trajectory = trajectories[name]
    coords = trajectory.get_coordinates_array()
    cart = trajectory.get_cartesian_array()
    
    # Prendre le minimum commun
    n_compare = min(len(coords_orig), len(coords))
    
    # Différences en coordonnées géographiques
    diff_lat = np.abs(coords_orig[:n_compare, 0] - coords[:n_compare, 0])
    diff_lon = np.abs(coords_orig[:n_compare, 1] - coords[:n_compare, 1])
    diff_alt = np.abs(coords_orig[:n_compare, 2] - coords[:n_compare, 2])
    
    # Écart horizontal en mètres
    dist_horiz = np.sqrt((orig_cart[:n_compare, 0] - cart[:n_compare, 0])**2 + 
                         (orig_cart[:n_compare, 1] - cart[:n_compare, 1])**2)
    
    print(f"\n{name}:")
    print(f"  Latitude  - moy: {np.mean(diff_lat)*111320:>8.1f}m, max: {np.max(diff_lat)*111320:>8.1f}m")
    print(f"  Longitude - moy: {np.mean(diff_lon)*111320:>8.1f}m, max: {np.max(diff_lon)*111320:>8.1f}m")
    print(f"  Altitude  - moy: {np.mean(diff_alt):>8.1f}m, max: {np.max(diff_alt):>8.1f}m")
    print(f"  Écart 2D  - moy: {np.mean(dist_horiz):>8.1f}m, max: {np.max(dist_horiz):>8.1f}m")

# Comparaison des métriques d'optimisation
print("\n" + "=" * 80)
print("  🔬 MÉTRIQUES D'OPTIMISATION (du TrajectoryOptimizer)  ")
print("=" * 80)

for name in ['Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    result = results[name]
    print(f"\n{name}:")
    for key, value in result.metrics.items():
        if isinstance(value, float):
            print(f"  {key:<25}: {value:>12.4f}")
        else:
            print(f"  {key:<25}: {value}")

# ============================================================================
# VISUALISATIONS GRAPHIQUES AVANCÉES
# ============================================================================

print("\n" + "=" * 80)
print("  📉 GÉNÉRATION DES VISUALISATIONS  ")
print("=" * 80)

# Créer figure avec grille de sous-graphiques
fig = plt.figure(figsize=(20, 14))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

# Couleurs pour chaque méthode
colors = {
    'Original': '#2E86AB',  # Bleu
    'Kalman': '#06A77D',    # Vert
    'B-spline': '#F18F01', # Orange
    'Hybride': '#C73E1D',   # Rouge
    'Météo': '#8B4C9B',     # Violet
    'NLP': '#E63946'        # Rouge foncé
}

# 1. VUE DU DESSUS - Trajectoires 2D
print("   ➤ Vue du dessus...")
ax1 = fig.add_subplot(gs[0, :2])
for name in ['Original', 'Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    cart = trajectories[name].get_cartesian_array()
    lw = 1 if name == 'Original' else 2
    alpha = 0.4 if name == 'Original' else 0.8
    ls = '-' if name != 'NLP' else '--'
    ax1.plot(cart[:, 0]/1000, cart[:, 1]/1000, color=colors[name], 
             label=f"{name} ({len(cart)} pts)", linewidth=lw, alpha=alpha, linestyle=ls)

# Marqueurs départ/arrivée
orig_cart = trajectories['Original'].get_cartesian_array()
ax1.scatter([orig_cart[0, 0]/1000], [orig_cart[0, 1]/1000], 
           c='green', s=150, marker='o', label='Départ', zorder=10, edgecolors='white', linewidths=2)
ax1.scatter([orig_cart[-1, 0]/1000], [orig_cart[-1, 1]/1000], 
           c='red', s=150, marker='s', label='Arrivée', zorder=10, edgecolors='white', linewidths=2)
ax1.set_xlabel('X (km)', fontsize=11)
ax1.set_ylabel('Y (km)', fontsize=11)
ax1.legend(loc='best', fontsize=9)
ax1.set_title('Vue du dessus - Comparaison des trajectoires', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3)

# 2. PROFIL D'ALTITUDE
print("   ➤ Profil d'altitude...")
ax2 = fig.add_subplot(gs[0, 2])
for name in ['Original', 'Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    cart = trajectories[name].get_cartesian_array()
    ts = trajectories[name].get_timestamps()
    lw = 1 if name == 'Original' else 2
    alpha = 0.4 if name == 'Original' else 0.8
    ls = '-' if name != 'NLP' else '--'
    ax2.plot(ts/60, cart[:, 2], color=colors[name], label=name, 
             linewidth=lw, alpha=alpha, linestyle=ls)
ax2.set_xlabel('Temps (min)', fontsize=11)
ax2.set_ylabel('Altitude (m)', fontsize=11)
ax2.legend(loc='best', fontsize=8)
ax2.set_title('Profil d\'altitude', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3)

# 3. ZOOM SUR UN SEGMENT
print("   ➤ Zoom sur segment...")
ax3 = fig.add_subplot(gs[1, 0])
zoom_start = 0
zoom_end = min(50, len(orig_cart))
for name in ['Original', 'Kalman', 'B-spline', 'Hybride']:
    cart = trajectories[name].get_cartesian_array()
    n = min(zoom_end, len(cart))
    lw = 1 if name == 'Original' else 2
    alpha = 0.5 if name == 'Original' else 0.9
    ax3.plot(cart[:n, 0], cart[:n, 1], '.-', color=colors[name], 
             label=name, linewidth=lw, alpha=alpha, markersize=4)
ax3.set_xlabel('X (m)', fontsize=11)
ax3.set_ylabel('Y (m)', fontsize=11)
ax3.legend(loc='best', fontsize=9)
ax3.set_title(f'Zoom: premiers {zoom_end} points', fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3)

# 4. ÉCART HORIZONTAL PAR RAPPORT À L'ORIGINAL
print("   ➤ Écarts horizontaux...")
ax4 = fig.add_subplot(gs[1, 1])
for name in ['Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    cart = trajectories[name].get_cartesian_array()
    n_compare = min(len(orig_cart), len(cart))
    dist = np.sqrt((orig_cart[:n_compare, 0] - cart[:n_compare, 0])**2 + 
                   (orig_cart[:n_compare, 1] - cart[:n_compare, 1])**2)
    ls = '-' if name != 'NLP' else '--'
    ax4.plot(dist, color=colors[name], label=f"{name} (moy: {np.mean(dist):.1f}m)", 
             linewidth=2, linestyle=ls)
ax4.set_xlabel('Point', fontsize=11)
ax4.set_ylabel('Écart horizontal (m)', fontsize=11)
ax4.legend(loc='best', fontsize=9)
ax4.set_title('Écart par rapport à la trajectoire originale', fontsize=12, fontweight='bold')
ax4.grid(True, alpha=0.3)

# 5. ÉCART EN ALTITUDE
print("   ➤ Écarts en altitude...")
ax5 = fig.add_subplot(gs[1, 2])
for name in ['Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    cart = trajectories[name].get_cartesian_array()
    n_compare = min(len(orig_cart), len(cart))
    diff_alt = np.abs(orig_cart[:n_compare, 2] - cart[:n_compare, 2])
    ls = '-' if name != 'NLP' else '--'
    ax5.plot(diff_alt, color=colors[name], label=f"{name} (moy: {np.mean(diff_alt):.1f}m)", 
             linewidth=2, linestyle=ls)
ax5.set_xlabel('Point', fontsize=11)
ax5.set_ylabel('Écart altitude (m)', fontsize=11)
ax5.legend(loc='best', fontsize=9)
ax5.set_title('Écart en altitude par rapport à l\'original', fontsize=12, fontweight='bold')
ax5.grid(True, alpha=0.3)

# 6. GRAPHIQUE EN BARRES - NOMBRE DE POINTS
print("   ➤ Comparaison nombre de points...")
ax6 = fig.add_subplot(gs[2, 0])
methods = ['Original', 'Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']
points = [int(metrics_table[m]['points']) for m in methods]  # type: ignore
bars = ax6.bar(range(len(methods)), points, color=[colors[m] for m in methods], alpha=0.7, edgecolor='black')
ax6.set_xticks(range(len(methods)))
ax6.set_xticklabels(methods, rotation=45, ha='right')
ax6.set_ylabel('Nombre de points', fontsize=11)
ax6.set_title('Compression des données', fontsize=12, fontweight='bold')
ax6.grid(True, alpha=0.3, axis='y')
# Ajouter valeurs sur les barres
for i, v in enumerate(points):
    ax6.text(i, v + 10, str(v), ha='center', va='bottom', fontsize=9, fontweight='bold')

# 7. GRAPHIQUE EN BARRES - DISTANCE TOTALE
print("   ➤ Comparaison distances...")
ax7 = fig.add_subplot(gs[2, 1])
distances_list = [float(metrics_table[m]['distance_km']) for m in methods]  # type: ignore
bars = ax7.bar(range(len(methods)), distances_list, color=[colors[m] for m in methods], alpha=0.7, edgecolor='black')
ax7.set_xticks(range(len(methods)))
ax7.set_xticklabels(methods, rotation=45, ha='right')
ax7.set_ylabel('Distance (km)', fontsize=11)
ax7.set_title('Distance totale parcourue', fontsize=12, fontweight='bold')
ax7.grid(True, alpha=0.3, axis='y')
for i, v in enumerate(distances_list):  # type: ignore
    ax7.text(i, v + 0.5, f"{v:.1f}", ha='center', va='bottom', fontsize=9, fontweight='bold')

# 8. GRAPHIQUE EN BARRES - TEMPS DE CALCUL
print("   ➤ Temps de calcul...")
ax8 = fig.add_subplot(gs[2, 2])
methods_opt = ['Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']
times = [timings[m] for m in methods_opt]
bars = ax8.bar(range(len(methods_opt)), times, color=[colors[m] for m in methods_opt], alpha=0.7, edgecolor='black')
ax8.set_xticks(range(len(methods_opt)))
ax8.set_xticklabels(methods_opt, rotation=45, ha='right')
ax8.set_ylabel('Temps (secondes)', fontsize=11)
ax8.set_title('Temps de calcul', fontsize=12, fontweight='bold')
ax8.grid(True, alpha=0.3, axis='y')
for i, v in enumerate(times):  # type: ignore
    ax8.text(i, v + 0.02, f"{v:.3f}s", ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.suptitle('🔬 ANALYSE COMPARATIVE DES MÉTHODES D\'OPTIMISATION DE TRAJECTOIRES', 
             fontsize=16, fontweight='bold', y=0.995)

# Créer le dossier de sortie s'il n'existe pas
output_dir = Path('output') / 'comparaison_complete'
output_dir.mkdir(parents=True, exist_ok=True)

plt.savefig(output_dir / 'methods_comparison.png', dpi=300, bbox_inches='tight')
print(f"\n✅ Graphique principal sauvegardé: {output_dir / 'methods_comparison.png'}")

# ============================================================================
# CARTE INTERACTIVE FOLIUM
# ============================================================================

print("\n   ➤ Carte interactive HTML...")
import folium

# Obtenir les coordonnées géographiques pour toutes les trajectoires
coords_data = {}
for name in ['Original', 'Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    coords_data[name] = trajectories[name].get_coordinates_array()

# Centre de la carte
center_lat = float(np.mean(coords_data['Original'][:, 0]))
center_lon = float(np.mean(coords_data['Original'][:, 1]))

# Créer la carte
m = folium.Map(  # type: ignore
    location=[center_lat, center_lon],
    zoom_start=8,
    tiles='OpenStreetMap'
)

# Définir les couleurs et styles pour chaque méthode
map_styles = {
    'Original': {'color': 'blue', 'weight': 2, 'opacity': 0.5, 'dash': None},
    'Kalman': {'color': 'green', 'weight': 3, 'opacity': 0.7, 'dash': None},
    'B-spline': {'color': 'orange', 'weight': 3, 'opacity': 0.7, 'dash': None},
    'Hybride': {'color': 'red', 'weight': 3, 'opacity': 0.8, 'dash': None},
    'Météo': {'color': 'purple', 'weight': 3, 'opacity': 0.8, 'dash': None},
    'NLP': {'color': 'darkred', 'weight': 3, 'opacity': 0.8, 'dash': '10, 5'}
}

# Ajouter les trajectoires
for name in ['Original', 'Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    coords = coords_data[name]
    style = map_styles[name]
    
    polyline = folium.PolyLine(
        locations=[[pos[0], pos[1]] for pos in coords],
        color=style['color'],
        weight=style['weight'],
        opacity=style['opacity'],
        popup=f"{name} ({len(coords)} points)"
    )
    
    if style['dash']:
        polyline.options['dashArray'] = style['dash']  # type: ignore
    
    polyline.add_to(m)  # type: ignore

# Marqueurs départ et arrivée
folium.Marker(
    location=[coords_data['Original'][0, 0], coords_data['Original'][0, 1]],
    popup='🛫 Départ',
    icon=folium.Icon(color='green', icon='play', prefix='fa')  # type: ignore
).add_to(m)  # type: ignore

folium.Marker(
    location=[coords_data['Original'][-1, 0], coords_data['Original'][-1, 1]],
    popup='🛬 Arrivée',
    icon=folium.Icon(color='red', icon='stop', prefix='fa')  # type: ignore
).add_to(m)  # type: ignore

# Calculer les distances totales pour la légende
distances_map: Dict[str, float] = {}
for name in ['Original', 'Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']:
    cart = trajectories[name].get_cartesian_array()
    dist_m = np.sum(np.sqrt(np.sum(np.diff(cart, axis=0)**2, axis=1)))
    distances_map[name] = float(dist_m / 1000)  # en km

# Créer la légende HTML
legend_html = f'''
<div style="position: fixed; 
            top: 10px; right: 10px; width: 400px; 
            background-color: white; border:4px solid #2E86AB; z-index:9999; 
            font-size:14px; padding: 18px; border-radius: 10px; 
            box-shadow: 0 6px 12px rgba(0,0,0,0.4);">
<h3 style="margin: 0 0 15px 0; color: #2E86AB; border-bottom: 3px solid #2E86AB; 
           padding-bottom: 8px; text-align: center;">
🛩️ Comparaison des Méthodes d'Optimisation
</h3>

<div style="margin: 10px 0; padding: 8px; background-color: #f0f8ff; border-radius: 5px;">
<span style="color: blue; font-weight: bold; font-size: 20px;">━━━</span> 
<strong>Original</strong><br/>
<span style="margin-left: 30px; color: #555; font-size: 12px;">
• {len(coords_data['Original'])} points (données brutes ADS-B)<br/>
• Distance: {distances_map['Original']:.2f} km
</span>
</div>

<div style="margin: 10px 0; padding: 8px; background-color: #f0fff0; border-radius: 5px;">
<span style="color: green; font-weight: bold; font-size: 20px;">━━━</span> 
<strong>Kalman</strong><br/>
<span style="margin-left: 30px; color: #555; font-size: 12px;">
• {len(coords_data['Kalman'])} points (filtre de Kalman seul)<br/>
• Distance: {distances_map['Kalman']:.2f} km ({(distances_map['Kalman']-distances_map['Original'])/distances_map['Original']*100:+.2f}%)<br/>
• Temps: {timings['Kalman']:.3f}s
</span>
</div>

<div style="margin: 10px 0; padding: 8px; background-color: #fff8f0; border-radius: 5px;">
<span style="color: orange; font-weight: bold; font-size: 20px;">━━━</span> 
<strong>B-spline</strong><br/>
<span style="margin-left: 30px; color: #555; font-size: 12px;">
• {len(coords_data['B-spline'])} points (B-spline seul)<br/>
• Distance: {distances_map['B-spline']:.2f} km ({(distances_map['B-spline']-distances_map['Original'])/distances_map['Original']*100:+.2f}%)<br/>
• Temps: {timings['B-spline']:.3f}s
</span>
</div>

<div style="margin: 10px 0; padding: 8px; background-color: #fff0f0; border-radius: 5px;">
<span style="color: red; font-weight: bold; font-size: 20px;">━━━</span> 
<strong>Hybride</strong><br/>
<span style="margin-left: 30px; color: #555; font-size: 12px;">
• {len(coords_data['Hybride'])} points (Kalman + B-spline)<br/>
• Distance: {distances_map['Hybride']:.2f} km ({(distances_map['Hybride']-distances_map['Original'])/distances_map['Original']*100:+.2f}%)<br/>
• Temps: {timings['Hybride']:.3f}s
</span>
</div>

<div style="margin: 10px 0; padding: 8px; background-color: #f8f0ff; border-radius: 5px;">
<span style="color: purple; font-weight: bold; font-size: 20px;">━━━</span> 
<strong>Météo</strong><br/>
<span style="margin-left: 30px; color: #555; font-size: 12px;">
• {len(coords_data['Météo'])} points (optimisation avec vent)<br/>
• Distance: {distances_map['Météo']:.2f} km ({(distances_map['Météo']-distances_map['Original'])/distances_map['Original']*100:+.2f}%)<br/>
• Temps: {timings['Météo']:.3f}s
</span>
</div>

<div style="margin: 10px 0; padding: 8px; background-color: #fff0f5; border-radius: 5px;">
<span style="color: darkred; font-weight: bold; font-size: 20px;">╍╍╍</span> 
<strong>NLP Direct Collocation</strong><br/>
<span style="margin-left: 30px; color: #555; font-size: 12px;">
• {len(coords_data['NLP'])} points (optimisation non-linéaire)<br/>
• Distance: {distances_map['NLP']:.2f} km ({(distances_map['NLP']-distances_map['Original'])/distances_map['Original']*100:+.2f}%)<br/>
• Temps: {timings['NLP']:.3f}s
</span>
</div>

<div style="margin-top: 15px; padding-top: 10px; border-top: 2px solid #ddd; 
            font-size: 11px; color: #666; text-align: center;">
📌 Cliquez sur les lignes pour voir les détails<br/>
🎯 Target: {TARGET_POINTS} points pour toutes les optimisations
</div>
</div>
'''

m.get_root().html.add_child(folium.Element(legend_html))  # type: ignore

# Sauvegarder la carte
map_file = output_dir / 'methods_comparison_map.html'
m.save(str(map_file))  # type: ignore
print(f"✅ Carte interactive sauvegardée: {map_file}")

print("\n" + "=" * 80)
print("  🎉 ANALYSE COMPLÈTE TERMINÉE  ")
print("=" * 80)
print(f"\n📁 Fichiers générés dans {output_dir}/:")
print(f"   • methods_comparison.png (graphiques)")
print(f"   • methods_comparison_map.html (carte interactive)")
print(f"\n💡 Recommandations:")

# Trouver la meilleure méthode selon différents critères
best_compression = min([(m, metrics_table[m]['points']) for m in ['Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']], key=lambda x: x[1])  # type: ignore
best_time = min([(m, timings[m]) for m in timings.keys()], key=lambda x: x[1])
best_smoothness = min([(m, metrics_table[m]['smoothness']) for m in ['Kalman', 'B-spline', 'Hybride', 'Météo', 'NLP']], key=lambda x: x[1])  # type: ignore

print(f"   🏆 Meilleure compression: {best_compression[0]} ({best_compression[1]} points)")
print(f"   ⚡ Plus rapide: {best_time[0]} ({best_time[1]:.3f}s)")
print(f"   📐 Plus lisse: {best_smoothness[0]} (smoothness: {best_smoothness[1]:.1f})")
print(f"\n   ✅ Pour la plupart des cas: méthode HYBRIDE (bon équilibre)")
print(f"   ✅ Pour optimisation réelle avec météo: méthode MÉTÉO ou NLP")
print(f"   ✅ Pour simple lissage rapide: méthode KALMAN")

print("\n" + "=" * 80)
