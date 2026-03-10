"""
Injecteur de spoofing pour tester le système de détection
Permet d'ajouter différents types d'anomalies dans les trajectoires
"""
from __future__ import annotations
import numpy as np
from typing import List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import random

from ..data.data_models import Trajectory, Position


class SpoofingType(Enum):
    """Types de spoofing injectable"""
    TELEPORTATION = "teleportation"
    SPEED_MANIPULATION = "vitesse_manipulation"
    ALTITUDE_JUMP = "saut_altitude"
    TIME_WARP = "distorsion_temps"
    GHOST_AIRCRAFT = "avion_fantome"
    POSITION_DRIFT = "derive_position"
    ALTITUDE_INVERSION = "inversion_altitude"
    IMPOSSIBLE_MANEUVER = "manoeuvre_impossible"


@dataclass
class SpoofingConfig:
    """Configuration pour l'injection de spoofing"""
    spoofing_type: SpoofingType
    num_points: int = 1  # Nombre de points à affecter
    start_index: Optional[int] = None  # Index de départ (None = aléatoire)
    intensity: float = 1.0  # Intensité de l'anomalie (1.0 = normale, >1.0 = plus forte)
    description: str = ""
    
    def __repr__(self):
        return f"Spoofing({self.spoofing_type.value}, points={self.num_points}, intensité={self.intensity})"


class SpoofingInjector:
    """
    Injecteur de spoofing dans les trajectoires
    
    Permet d'ajouter différents types d'anomalies pour tester la détection :
    - Téléportation : sauts de position impossibles
    - Vitesse manipulée : vitesses irréalistes
    - Sauts d'altitude : changements brutaux d'altitude
    - Distorsion temporelle : timestamps incohérents
    - Avion fantôme : création de positions fictives
    - Dérive de position : décalage progressif
    - Manœuvres impossibles : G-forces excessifs
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialise l'injecteur
        
        Args:
            seed: Graine aléatoire pour reproductibilité
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        self.injections: list[dict] = []  # Historique des injections
    
    def inject(
        self,
        trajectory: Trajectory,
        config: SpoofingConfig
    ) -> Trajectory:
        """
        Injecte du spoofing dans une trajectoire
        
        Args:
            trajectory: Trajectoire originale
            config: Configuration du spoofing
            
        Returns:
            Nouvelle trajectoire avec spoofing injecté
        """
        print(f"💉 Injection de {config.spoofing_type.value}...")
        
        # Copier les positions
        positions = [Position(
            latitude=p.latitude,
            longitude=p.longitude,
            altitude=p.altitude,
            timestamp=p.timestamp,
            ground_speed=p.ground_speed,
            vertical_rate=p.vertical_rate,
            heading=p.heading
        ) for p in trajectory.positions]
        
        # Déterminer les indices à affecter
        if config.start_index is None:
            # Éviter le début et la fin
            start = random.randint(
                len(positions) // 4,
                3 * len(positions) // 4
            )
        else:
            start = config.start_index
        
        end = min(start + config.num_points, len(positions))
        affected_indices = list(range(start, end))
        
        # Appliquer le spoofing selon le type
        if config.spoofing_type == SpoofingType.TELEPORTATION:
            self._inject_teleportation(positions, affected_indices, config.intensity)
        
        elif config.spoofing_type == SpoofingType.SPEED_MANIPULATION:
            self._inject_speed_manipulation(positions, affected_indices, config.intensity)
        
        elif config.spoofing_type == SpoofingType.ALTITUDE_JUMP:
            self._inject_altitude_jump(positions, affected_indices, config.intensity)
        
        elif config.spoofing_type == SpoofingType.TIME_WARP:
            self._inject_time_warp(positions, affected_indices, config.intensity)
        
        elif config.spoofing_type == SpoofingType.GHOST_AIRCRAFT:
            self._inject_ghost_aircraft(positions, affected_indices, config.intensity)
        
        elif config.spoofing_type == SpoofingType.POSITION_DRIFT:
            self._inject_position_drift(positions, affected_indices, config.intensity)
        
        elif config.spoofing_type == SpoofingType.ALTITUDE_INVERSION:
            self._inject_altitude_inversion(positions, affected_indices, config.intensity)
        
        elif config.spoofing_type == SpoofingType.IMPOSSIBLE_MANEUVER:
            self._inject_impossible_maneuver(positions, affected_indices, config.intensity)
        
        # Enregistrer l'injection
        self.injections.append({
            'type': config.spoofing_type,
            'indices': affected_indices,
            'intensity': config.intensity
        })
        
        print(f"   ✓ {len(affected_indices)} points affectés (indices {affected_indices[0]} à {affected_indices[-1]})")
        
        return Trajectory(
            positions=positions,
            flight_id=f"{trajectory.flight_id}_spoofed" if trajectory.flight_id else "spoofed"
        )
    
    def inject_multiple(
        self,
        trajectory: Trajectory,
        configs: List[SpoofingConfig]
    ) -> Trajectory:
        """
        Injecte plusieurs types de spoofing
        
        Args:
            trajectory: Trajectoire originale
            configs: Liste de configurations
            
        Returns:
            Trajectoire avec tous les spoofings injectés
        """
        current = trajectory
        for config in configs:
            current = self.inject(current, config)
        
        return current
    
    def _inject_teleportation(
        self, positions: List[Position], indices: List[int], intensity: float
    ):
        """Décalage de position réaliste (low/medium) : 500m à 5km"""
        for idx in indices:
            # Décalage réaliste : 500m à 5km selon l'intensité
            jump_distance = (500 + random.random() * 4500) * intensity  # 500m à 5km
            
            # Ajouter un décalage aléatoire en lat/lon
            lat_offset = (random.random() - 0.5) * jump_distance / 111320
            lon_offset = (random.random() - 0.5) * jump_distance / (111320 * np.cos(np.radians(positions[idx].latitude)))
            
            positions[idx].latitude += lat_offset
            positions[idx].longitude += lon_offset
    
    def _inject_speed_manipulation(
        self, positions: List[Position], indices: List[int], intensity: float
    ):
        """Vitesse manipulée réaliste : écart de 10-50 m/s (36-180 km/h)"""
        if len(indices) < 2:
            return
        
        # Créer des écarts de vitesse réalistes
        idx = indices[0]
        
        # Écart de vitesse modéré : 10-50 m/s selon l'intensité
        if idx > 0:
            prev = positions[idx - 1]
            dt = (positions[idx].timestamp - prev.timestamp).total_seconds()
            
            # Vitesse cible : 320-370 m/s * intensity (vitesse commerciale + écart)
            base_speed = 250  # Vitesse normale ~900 km/h
            speed_error = (10 + random.random() * 40) * intensity  # Erreur de 10-50 m/s
            target_speed = base_speed + speed_error
            target_distance = target_speed * max(dt, 1.0)
            
            # Déplacer le point
            bearing = random.random() * 2 * np.pi
            lat_offset = (target_distance * np.cos(bearing)) / 111320
            lon_offset = (target_distance * np.sin(bearing)) / (111320 * np.cos(np.radians(positions[idx].latitude)))
            
            positions[idx].latitude += lat_offset
            positions[idx].longitude += lon_offset
    
    def _inject_altitude_jump(
        self, positions: List[Position], indices: List[int], intensity: float
    ):
        """Saut d'altitude réaliste : 50-300m"""
        for idx in indices:
            # Saut d'altitude modéré : 50-300 m selon l'intensité
            jump = (50 + random.random() * 250) * intensity
            
            # Alterner montée et descente
            if random.random() > 0.5:
                jump = -jump
            
            positions[idx].altitude += jump
            
            # S'assurer que l'altitude reste > 0
            positions[idx].altitude = max(0, positions[idx].altitude)
    
    def _inject_time_warp(
        self, positions: List[Position], indices: List[int], intensity: float
    ):
        """Distorsion temporelle : timestamps incohérents MAIS en ordre croissant"""
        for idx in indices:
            if idx > 0 and idx < len(positions) - 1:
                # Calculer l'intervalle normal entre ce point et le suivant
                normal_interval = (positions[idx + 1].timestamp - positions[idx].timestamp).total_seconds()
                
                if normal_interval > 0:
                    if random.random() > 0.5:
                        # Réduire drastiquement l'intervalle (compression temporelle)
                        # Mais garder un minimum pour maintenir l'ordre
                        reduction = min(normal_interval * 0.9, 5 * intensity)
                        warp = timedelta(seconds=reduction)
                    else:
                        # Augmenter l'intervalle (dilatation temporelle)
                        warp = timedelta(seconds=100 * intensity)
                    
                    # Appliquer la distorsion en décalant tous les points suivants
                    for i in range(idx, len(positions)):
                        positions[i].timestamp += warp
    
    def _inject_ghost_aircraft(
        self, positions: List[Position], indices: List[int], intensity: float
    ):
        """Position déviée réaliste : décalage de 2-10km"""
        for idx in indices:
            # Décalage modéré par rapport à la position actuelle
            offset_distance = (2000 + random.random() * 8000) * intensity  # 2-10 km
            
            # Direction aléatoire
            bearing = random.random() * 2 * np.pi
            lat_offset = (offset_distance * np.cos(bearing)) / 111320
            lon_offset = (offset_distance * np.sin(bearing)) / (111320 * np.cos(np.radians(positions[idx].latitude)))
            
            positions[idx].latitude += lat_offset
            positions[idx].longitude += lon_offset
    
    def _inject_position_drift(
        self, positions: List[Position], indices: List[int], intensity: float
    ):
        """Dérive de position progressive réaliste : ~100-500m cumulés"""
        if not indices:
            return
        
        # Dérive cumulative réaliste
        drift_lat = 0.0
        drift_lon = 0.0
        
        # Taux de dérive par point : ~10-50m par point
        drift_rate_lat = (random.random() - 0.5) * 0.0005 * intensity  # ~50m max
        drift_rate_lon = (random.random() - 0.5) * 0.0005 * intensity
        
        for idx in indices:
            drift_lat += drift_rate_lat
            drift_lon += drift_rate_lon
            
            positions[idx].latitude += drift_lat
            positions[idx].longitude += drift_lon
    
    def _inject_altitude_inversion(
        self, positions: List[Position], indices: List[int], intensity: float
    ):
        """Erreur d'altitude réaliste : décalage de 20-100m"""
        for idx in indices:
            # Décalage d'altitude modéré : +/- 20-100m
            altitude_error = (20 + random.random() * 80) * intensity
            if random.random() > 0.5:
                altitude_error = -altitude_error
            positions[idx].altitude += altitude_error
            positions[idx].altitude = max(0, positions[idx].altitude)
    
    def _inject_impossible_maneuver(
        self, positions: List[Position], indices: List[int], intensity: float
    ):
        """Écart de cap réaliste : changement de 5-30 degrés"""
        if len(indices) < 3:
            return
        
        # Modifier le cap de façon modérée
        for idx in indices:
            if idx > 0 and idx < len(positions) - 1:
                # Écart de cap : 5-30 degrés selon l'intensité
                heading_error = (5 + random.random() * 25) * intensity
                
                # Convertir en décalage de position (virage progressif)
                if idx > 0:
                    prev = positions[idx - 1]
                    dt = (positions[idx].timestamp - prev.timestamp).total_seconds()
                    
                    # Calculer le décalage latéral pour créer l'écart de cap
                    # Distance parcourue normalement
                    speed = 250  # m/s (~900 km/h)
                    distance = speed * dt
                    
                    # Décalage latéral pour l'écart de cap
                    lateral_offset = distance * np.tan(np.radians(heading_error))
                    
                    # Appliquer le décalage perpendiculaire
                    bearing = random.random() * 2 * np.pi
                    lat_offset = (lateral_offset * np.cos(bearing)) / 111320
                    lon_offset = (lateral_offset * np.sin(bearing)) / (111320 * np.cos(np.radians(positions[idx].latitude)))
                    
                    positions[idx].latitude += lat_offset
                    positions[idx].longitude += lon_offset
    
    def create_spoofing_scenario(
        self,
        trajectory: Trajectory,
        scenario: str = "light"
    ) -> Trajectory:
        """
        Crée un scénario de spoofing prédéfini
        
        Args:
            trajectory: Trajectoire originale
            scenario: 'light', 'medium', 'heavy', 'mixed'
            
        Returns:
            Trajectoire avec spoofing injecté
        """
        configs = []
        
        if scenario == "light":
            # Spoofing léger : anomalies LOW réalistes (écarts mineurs)
            configs = [
                SpoofingConfig(SpoofingType.SPEED_MANIPULATION, num_points=2, intensity=0.5, 
                             description="Écart de vitesse mineur (~20 km/h)"),
                SpoofingConfig(SpoofingType.ALTITUDE_JUMP, num_points=1, intensity=0.4,
                             description="Écart d'altitude mineur (~50m)"),
                SpoofingConfig(SpoofingType.IMPOSSIBLE_MANEUVER, num_points=2, intensity=0.3,
                             description="Écart de cap mineur (~5-10°)")
            ]
        
        elif scenario == "medium":
            # Spoofing moyen : anomalies MEDIUM réalistes (écarts modérés)
            configs = [
                SpoofingConfig(SpoofingType.TELEPORTATION, num_points=3, intensity=0.8,
                             description="Décalage de position modéré (~2-4 km)"),
                SpoofingConfig(SpoofingType.ALTITUDE_JUMP, num_points=2, intensity=0.7,
                             description="Écart d'altitude modéré (~150m)"),
                SpoofingConfig(SpoofingType.POSITION_DRIFT, num_points=8, intensity=0.6,
                             description="Dérive progressive (~200-300m)"),
                SpoofingConfig(SpoofingType.IMPOSSIBLE_MANEUVER, num_points=3, intensity=0.7,
                             description="Écart de cap modéré (~15-20°)")
            ]
        
        elif scenario == "heavy":
            # Note: ce scénario n'est plus recommandé - utiliser 'realistic' à la place
            configs = [
                SpoofingConfig(SpoofingType.TELEPORTATION, num_points=4, intensity=1.0,
                             description="Décalage de position (~5 km)"),
                SpoofingConfig(SpoofingType.SPEED_MANIPULATION, num_points=3, intensity=0.9,
                             description="Écart de vitesse notable (~50 km/h)"),
                SpoofingConfig(SpoofingType.ALTITUDE_JUMP, num_points=3, intensity=0.9,
                             description="Écart d'altitude notable (~250m)"),
                SpoofingConfig(SpoofingType.IMPOSSIBLE_MANEUVER, num_points=3, intensity=0.8,
                             description="Écart de cap notable (~25°)")
            ]
        
        elif scenario == "mixed":
            # Scénario mixte réaliste : combinaison LOW + MEDIUM
            configs = [
                SpoofingConfig(SpoofingType.TELEPORTATION, num_points=2, intensity=0.6,
                             description="Décalage de position (~1-3 km)"),
                SpoofingConfig(SpoofingType.SPEED_MANIPULATION, num_points=3, intensity=0.7,
                             description="Écart de vitesse (~30-40 km/h)"),
                SpoofingConfig(SpoofingType.ALTITUDE_JUMP, num_points=2, intensity=0.6,
                             description="Écart d'altitude (~100m)"),
                SpoofingConfig(SpoofingType.POSITION_DRIFT, num_points=5, intensity=0.5,
                             description="Dérive progressive (~150m)"),
                SpoofingConfig(SpoofingType.IMPOSSIBLE_MANEUVER, num_points=2, intensity=0.6,
                             description="Écart de cap (~12-15°)")
            ]
        
        elif scenario == "realistic":
            # Scénario le plus réaliste : uniquement LOW et MEDIUM
            configs = [
                SpoofingConfig(SpoofingType.POSITION_DRIFT, num_points=6, intensity=0.5,
                             description="Dérive GPS progressive"),
                SpoofingConfig(SpoofingType.ALTITUDE_JUMP, num_points=2, intensity=0.5,
                             description="Erreur altimétrique"),
                SpoofingConfig(SpoofingType.SPEED_MANIPULATION, num_points=2, intensity=0.6,
                             description="Écart de vitesse modéré")
            ]
        
        else:
            raise ValueError(f"Scénario inconnu : {scenario}. Utilisez 'light', 'medium', 'mixed' ou 'realistic'")
        
        print(f"\n🎭 Création du scénario '{scenario}' avec {len(configs)} types de spoofing")
        return self.inject_multiple(trajectory, configs)
    
    def get_injection_report(self) -> str:
        """Retourne un rapport des injections effectuées"""
        if not self.injections:
            return "Aucune injection effectuée"
        
        report = f"\n📊 Rapport d'injection de spoofing\n"
        report += f"{'='*60}\n"
        report += f"Total d'injections : {len(self.injections)}\n\n"
        
        for i, inj in enumerate(self.injections, 1):
            report += f"{i}. {inj['type'].value}\n"
            report += f"   Indices : {min(inj['indices'])} à {max(inj['indices'])} ({len(inj['indices'])} points)\n"
            report += f"   Intensité : {inj['intensity']}\n\n"
        
        return report
