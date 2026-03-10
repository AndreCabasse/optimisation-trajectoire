"""
Module de visualisation pour les trajectoires
"""
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # type: ignore
from typing import List, Optional
from pathlib import Path

from ..data.data_models import Trajectory, OptimizedTrajectory


class TrajectoryVisualizer:
    """Outils de visualisation pour les trajectoires"""
    
    @staticmethod
    def plot_trajectory_3d(
        trajectories: List[Trajectory],
        labels: Optional[List[str]] = None,
        output_file: Optional[str] = None
    ):
        """
        Affiche une ou plusieurs trajectoires en 3D
        
        Args:
            trajectories: Liste de trajectoires à afficher
            labels: Labels pour chaque trajectoire
            output_file: Fichier de sortie (None = affichage)
        """
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        colors = ['b', 'r', 'g', 'orange', 'purple']
        
        for i, traj in enumerate(trajectories):
            cart = traj.get_cartesian_array()
            label = labels[i] if labels and i < len(labels) else f'Trajectoire {i+1}'
            color = colors[i % len(colors)]
            
            ax.plot(cart[:, 0], cart[:, 1], cart[:, 2],
                   color=color, label=label, linewidth=2, alpha=0.8)
            
            # Marquer le début et la fin
            ax.scatter([cart[0, 0]], [cart[0, 1]], [cart[0, 2]],  # type: ignore
                      color=color, marker='o', s=100, label=f'{label} (début)')
            ax.scatter([cart[-1, 0]], [cart[-1, 1]], [cart[-1, 2]],  # type: ignore
                      color=color, marker='s', s=100, label=f'{label} (fin)')
        
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Altitude (m)')
        ax.legend()
        ax.set_title('Trajectoires 3D')
        
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Sauvegardé : {output_file}")
        else:
            plt.show()
    
    @staticmethod
    def plot_comparison(
        original: Trajectory,
        optimized: Trajectory,
        output_file: Optional[str] = None
    ):
        """
        Compare deux trajectoires (original vs optimisé)
        
        Args:
            original: Trajectoire originale
            optimized: Trajectoire optimisée
            output_file: Fichier de sortie
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        orig_cart = original.get_cartesian_array()
        opt_cart = optimized.get_cartesian_array()
        orig_ts = original.get_timestamps()
        opt_ts = optimized.get_timestamps()
        
        # Trajectoire 2D (vue du dessus)
        ax = axes[0, 0]
        ax.plot(orig_cart[:, 0], orig_cart[:, 1], 'b.-', label='Original', alpha=0.6)
        ax.plot(opt_cart[:, 0], opt_cart[:, 1], 'r-', label='Optimisé', linewidth=2)
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.legend()
        ax.set_title('Vue du dessus')
        ax.grid(True)
        
        # Profil d'altitude
        ax = axes[0, 1]
        ax.plot(orig_ts, orig_cart[:, 2], 'b.-', label='Original', alpha=0.6)
        ax.plot(opt_ts, opt_cart[:, 2], 'r-', label='Optimisé', linewidth=2)
        ax.set_xlabel('Temps (s)')
        ax.set_ylabel('Altitude (m)')
        ax.legend()
        ax.set_title('Profil d\'altitude')
        ax.grid(True)
        
        # Vitesse au sol
        ax = axes[1, 0]
        orig_speeds = [p.ground_speed for p in original.positions if p.ground_speed]
        opt_speeds = [p.ground_speed for p in optimized.positions if p.ground_speed]
        
        if orig_speeds:
            ax.plot(orig_ts[1:len(orig_speeds)+1], orig_speeds, 'b.-',
                   label='Original', alpha=0.6)
        if opt_speeds:
            ax.plot(opt_ts[1:len(opt_speeds)+1], opt_speeds, 'r-',
                   label='Optimisé', linewidth=2)
        ax.set_xlabel('Temps (s)')
        ax.set_ylabel('Vitesse sol (m/s)')
        ax.legend()
        ax.set_title('Vitesse au sol')
        ax.grid(True)
        
        # Taux de montée
        ax = axes[1, 1]
        orig_vr = [p.vertical_rate for p in original.positions if p.vertical_rate]
        opt_vr = [p.vertical_rate for p in optimized.positions if p.vertical_rate]
        
        if orig_vr:
            ax.plot(orig_ts[1:len(orig_vr)+1], orig_vr, 'b.-',
                   label='Original', alpha=0.6)
        if opt_vr:
            ax.plot(opt_ts[1:len(opt_vr)+1], opt_vr, 'r-',
                   label='Optimisé', linewidth=2)
        ax.set_xlabel('Temps (s)')
        ax.set_ylabel('Taux de montée (m/s)')
        ax.legend()
        ax.set_title('Taux de montée/descente')
        ax.grid(True)
        ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Sauvegardé : {output_file}")
        else:
            plt.show()
    
    @staticmethod
    def plot_interactive_map(
        trajectories: List[Trajectory],
        labels: Optional[List[str]] = None,
        output_file: str = "trajectory_map.html"
    ):
        """
        Crée une carte interactive avec Folium
        
        Args:
            trajectories: Trajectoire(s) à afficher (liste ou trajectoire unique)
            labels: Labels pour chaque trajectoire
            output_file: Fichier HTML de sortie
        """
        try:
            import folium
            from folium import plugins
            
            # Accepter une seule trajectoire ou une liste
            if isinstance(trajectories, Trajectory):
                trajectories = [trajectories]
            
            if not trajectories:
                print("Aucune trajectoire à afficher")
                return
            
            # Centre de la carte (basé sur la première trajectoire)
            coords = trajectories[0].get_coordinates_array()
            center_lat = np.mean(coords[:, 0])
            center_lon = np.mean(coords[:, 1])
            
            # Créer la carte
            m = folium.Map(
                location=[float(center_lat), float(center_lon)],
                zoom_start=10,
                tiles='OpenStreetMap'
            )
            
            # Couleurs pour différentes trajectoires
            colors = ['blue', 'red', 'green', 'orange', 'purple']
            
            # Ajouter chaque trajectoire
            for idx, traj in enumerate(trajectories):
                color = colors[idx % len(colors)]
                label = labels[idx] if labels and idx < len(labels) else f"Trajectoire {idx+1}"
                
                # Filtrer les points avec NaN
                points = [
                    [p.latitude, p.longitude] 
                    for p in traj.positions 
                    if not (np.isnan(p.latitude) or np.isnan(p.longitude))
                ]
                
                if not points:
                    print(f"   ⚠ Aucun point valide pour {label}")
                    continue
                
                # Ajouter la trajectoire
                folium.PolyLine(
                    points,
                    color=color,
                    weight=3 if idx == 0 else 2,
                    opacity=0.8 if idx == 0 else 0.7,
                    tooltip=f"{label} - {traj.flight_id}"
                ).add_to(m)
                
                # Ajouter des marqueurs pour la première trajectoire uniquement
                if idx == 0:
                    # Marquer le début et la fin
                    folium.Marker(
                        [traj.positions[0].latitude, traj.positions[0].longitude],
                        popup=f"Départ - {traj.positions[0].timestamp}",
                        icon=folium.Icon(color='green', icon='play')
                    ).add_to(m)
                    
                    folium.Marker(
                        [traj.positions[-1].latitude, traj.positions[-1].longitude],
                        popup=f"Arrivée - {traj.positions[-1].timestamp}",
                        icon=folium.Icon(color='red', icon='stop')
                    ).add_to(m)
                
                # Ajouter quelques marqueurs le long de la trajectoire
                step = max(1, len(traj.positions) // 10)
                for i in range(0, len(traj.positions), step):
                    pos = traj.positions[i]
                    # Ignorer les positions avec NaN
                    if np.isnan(pos.latitude) or np.isnan(pos.longitude):
                        continue
                    folium.CircleMarker(
                        [pos.latitude, pos.longitude],
                        radius=2 if idx > 0 else 3,
                        color=color,
                        fill=True,
                        opacity=0.6,
                        popup=f"{label}<br>Alt: {pos.altitude:.0f}m<br>Time: {pos.timestamp}"
                    ).add_to(m)
            
            # Ajouter une légende
            legend_html = '''
            <div style="position: fixed; 
                        top: 10px; right: 10px; width: 200px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:14px; padding: 10px">
            <b>Légende</b><br>
            '''
            for idx, traj in enumerate(trajectories):
                color = colors[idx % len(colors)]
                label = labels[idx] if labels and idx < len(labels) else f"Trajectoire {idx+1}"
                legend_html += f'<i style="background:{color};width:15px;height:3px;display:inline-block;"></i> {label} ({len(traj.positions)} pts)<br>'
            legend_html += '</div>'
            
            # m.get_root().html.add_child(folium.Element(legend_html))  # Commenté pour éviter erreur de type
            
            # Sauvegarder
            m.save(output_file)
            print(f"Carte interactive sauvegardée : {output_file}")
            
        except ImportError:
            print("Folium non installé. Utilisez : pip install folium")
