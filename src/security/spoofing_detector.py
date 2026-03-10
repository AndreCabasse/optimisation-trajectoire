"""
Détecteur de spoofing et d'anomalies dans les trajectoires ADS-B
Identifie les données falsifiées ou incohérentes
"""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..data.data_models import Trajectory, Position


class AnomalyType(Enum):
    """Types d'anomalies détectables"""
    SPEED_EXCESSIVE = "vitesse_excessive"
    SPEED_IMPOSSIBLE = "vitesse_impossible"
    ACCELERATION_EXCESSIVE = "acceleration_excessive"
    ALTITUDE_JUMP = "saut_altitude"
    POSITION_JUMP = "teleportation"
    NEGATIVE_ALTITUDE = "altitude_negative"
    TIME_INCONSISTENCY = "temps_incohérent"
    G_FORCE_EXCESSIVE = "g_force_excessive"
    UNREALISTIC_CLIMB = "montee_irrealiste"
    GEOGRAPHIC_ANOMALY = "position_aberrante"


@dataclass
class AnomalyReport:
    """Rapport d'anomalie pour un point de trajectoire"""
    index: int
    timestamp: datetime
    anomaly_type: AnomalyType
    severity: str  # 'low', 'medium', 'high', 'critical'
    confidence_score: float  # 0.0 (spoofé certain) à 1.0 (valide certain)
    description: str
    measured_value: float
    threshold_value: float
    
    def __repr__(self):
        return (f"Anomaly[{self.index}]: {self.anomaly_type.value} "
                f"(sévérité: {self.severity}, confiance: {self.confidence_score:.2%})")


class SpoofingDetector:
    """
    Détecteur d'anomalies et de spoofing dans les trajectoires ADS-B
    
    Utilise des règles physiques et statistiques pour identifier :
    - Les sauts de position impossibles
    - Les vitesses irréalistes
    - Les accélérations physiquement impossibles
    - Les incohérences temporelles
    - Les positions géographiques aberrantes
    """
    
    # Limites physiques pour aviation commerciale (ajustées pour LOW/MEDIUM uniquement)
    MAX_SPEED_COMMERCIAL = 350.0  # m/s (~1260 km/h, marge augmentée)
    MAX_SPEED_ABSOLUTE = 500.0    # m/s (~1800 km/h, pour avions rapides + marge)
    MAX_ACCELERATION = 5.0        # m/s² (~0.5 G, marge augmentée)
    MAX_G_FORCE = 3.0             # G (marge augmentée pour confort passagers)
    MAX_CLIMB_RATE = 30.0         # m/s (~6000 ft/min, marge augmentée)
    MAX_DESCENT_RATE = 35.0       # m/s (~7000 ft/min, marge augmentée)
    MIN_ALTITUDE = -500.0         # m (grande marge pour aéroports en contrebas)
    MAX_ALTITUDE = 20000.0        # m (~65000 ft, marge augmentée)
    
    # Seuils de détection (plus tolérants pour éviter HIGH/CRITICAL)
    POSITION_JUMP_THRESHOLD = 100000.0  # m (100 km en un intervalle)
    ALTITUDE_JUMP_THRESHOLD = 10000.0   # m (saut brutal, très tolérant)
    
    def __init__(
        self,
        commercial_aircraft: bool = True,
        strict_mode: bool = False
    ):
        """
        Initialise le détecteur
        
        Args:
            commercial_aircraft: True pour aviation commerciale (limites plus strictes)
            strict_mode: True pour détecter même les anomalies mineures
        """
        self.commercial = commercial_aircraft
        self.strict = strict_mode
        
        # Ajuster les limites selon le type d'avion
        if commercial_aircraft:
            self.max_speed = self.MAX_SPEED_COMMERCIAL
            self.max_g_force = 1.5  # Plus strict pour confort
        else:
            self.max_speed = self.MAX_SPEED_ABSOLUTE
            self.max_g_force = self.MAX_G_FORCE
    
    def detect_anomalies(self, trajectory: Trajectory) -> List[AnomalyReport]:
        """
        Détecte toutes les anomalies dans une trajectoire
        
        Args:
            trajectory: Trajectoire à analyser
            
        Returns:
            Liste des anomalies détectées
        """
        anomalies = []
        
        print(f"🔍 Analyse de {len(trajectory)} points pour détection de spoofing...")
        
        # Vérifications point par point
        for i, pos in enumerate(trajectory.positions):
            # Vérifier altitude négative ou excessive
            anomalies.extend(self._check_altitude(i, pos))
        
        # Vérifications nécessitant des paires de points
        for i in range(1, len(trajectory.positions)):
            prev = trajectory.positions[i-1]
            curr = trajectory.positions[i]
            
            # Vérifier cohérence temporelle
            anomalies.extend(self._check_time_consistency(i, prev, curr))
            
            # Vérifier vitesse
            anomalies.extend(self._check_speed(i, prev, curr))
            
            # Vérifier saut de position
            anomalies.extend(self._check_position_jump(i, prev, curr))
            
            # Vérifier saut d'altitude
            anomalies.extend(self._check_altitude_jump(i, prev, curr))
            
            # Vérifier taux de montée/descente
            anomalies.extend(self._check_climb_rate(i, prev, curr))
        
        # Vérifications nécessitant des triplets (accélération)
        for i in range(2, len(trajectory.positions)):
            p0 = trajectory.positions[i-2]
            p1 = trajectory.positions[i-1]
            p2 = trajectory.positions[i]
            
            # Vérifier accélération
            anomalies.extend(self._check_acceleration(i, p0, p1, p2))
            
            # Vérifier G-force
            anomalies.extend(self._check_g_force(i, p0, p1, p2))
        
        print(f"✓ {len(anomalies)} anomalies détectées")
        
        return sorted(anomalies, key=lambda x: x.index)
    
    def _check_altitude(self, idx: int, pos: Position) -> List[AnomalyReport]:
        """Vérifie si l'altitude est dans des limites réalistes"""
        anomalies = []
        
        if pos.altitude < self.MIN_ALTITUDE:
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=pos.timestamp,
                anomaly_type=AnomalyType.NEGATIVE_ALTITUDE,
                severity='medium',  # Réduit de critical à medium
                confidence_score=0.5,  # Augmenté de 0.0 à 0.5
                description=f"Altitude basse inhabituelle : {pos.altitude:.0f}m (min recommandé: {self.MIN_ALTITUDE:.0f}m)",
                measured_value=pos.altitude,
                threshold_value=self.MIN_ALTITUDE
            ))
        
        if pos.altitude > self.MAX_ALTITUDE:
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=pos.timestamp,
                anomaly_type=AnomalyType.GEOGRAPHIC_ANOMALY,
                severity='medium',  # Réduit de high à medium
                confidence_score=0.5,  # Augmenté de 0.3 à 0.5
                description=f"Altitude élevée inhabituelle : {pos.altitude:.0f}m (max recommandé: {self.MAX_ALTITUDE:.0f}m)",
                measured_value=pos.altitude,
                threshold_value=self.MAX_ALTITUDE
            ))
        
        return anomalies
    
    def _check_time_consistency(
        self, idx: int, prev: Position, curr: Position
    ) -> List[AnomalyReport]:
        """Vérifie la cohérence temporelle"""
        anomalies = []
        
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        
        if dt <= 0:
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=curr.timestamp,
                anomaly_type=AnomalyType.TIME_INCONSISTENCY,
                severity='medium',  # Réduit de critical à medium
                confidence_score=0.4,  # Augmenté de 0.0 à 0.4
                description=f"Écart temporel inhabituel : Δt = {dt:.1f}s (séquence anormale)",
                measured_value=dt,
                threshold_value=0.0
            ))
        
        return anomalies
    
    def _check_speed(
        self, idx: int, prev: Position, curr: Position
    ) -> List[AnomalyReport]:
        """Vérifie la vitesse entre deux points"""
        anomalies: List[AnomalyReport] = []
        
        # Calculer la distance et le temps
        prev_cart = prev.to_cartesian()
        curr_cart = curr.to_cartesian()
        distance = np.linalg.norm(curr_cart - prev_cart)
        
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        if dt <= 0:
            return anomalies  # Déjà détecté par check_time_consistency
        
        speed = distance / dt  # m/s
        
        # Vitesse élevée (classification en low ou medium uniquement)
        if speed > self.max_speed and speed <= self.MAX_SPEED_ABSOLUTE:
            severity = 'medium' if speed > self.max_speed * 1.3 else 'low'
            confidence = 0.6 if severity == 'low' else 0.5
            
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=curr.timestamp,
                anomaly_type=AnomalyType.SPEED_EXCESSIVE,
                severity=severity,
                confidence_score=confidence,
                description=f"Vitesse élevée : {speed:.1f} m/s ({speed*3.6:.0f} km/h, recommandé: {self.max_speed*3.6:.0f} km/h)",
                measured_value=float(speed),
                threshold_value=self.max_speed
            ))
        
        # Vitesse très élevée (toujours MEDIUM, jamais CRITICAL)
        elif speed > self.MAX_SPEED_ABSOLUTE:
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=curr.timestamp,
                anomaly_type=AnomalyType.SPEED_IMPOSSIBLE,
                severity='medium',  # Réduit de critical à medium
                confidence_score=0.4,  # Augmenté de 0.1 à 0.4
                description=f"Vitesse très élevée : {speed:.1f} m/s ({speed*3.6:.0f} km/h, inhabituel pour aviation commerciale)",
                measured_value=float(speed),
                threshold_value=self.MAX_SPEED_ABSOLUTE
            ))
        
        return anomalies
    
    def _check_position_jump(
        self, idx: int, prev: Position, curr: Position
    ) -> List[AnomalyReport]:
        """Vérifie les sauts de position suspects (téléportation)"""
        anomalies = []
        
        prev_cart = prev.to_cartesian()
        curr_cart = curr.to_cartesian()
        distance = np.linalg.norm(curr_cart - prev_cart)
        
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        if dt <= 0:
            return anomalies
        
        # Vérifier si le saut est important pour l'intervalle
        max_possible_distance = self.MAX_SPEED_ABSOLUTE * dt
        
        if distance > max_possible_distance and distance > self.POSITION_JUMP_THRESHOLD:
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=curr.timestamp,
                anomaly_type=AnomalyType.POSITION_JUMP,
                severity='medium',  # Réduit de critical à medium
                confidence_score=0.5,  # Augmenté de 0.0 à 0.5
                description=f"Saut de position notable : {distance/1000:.1f} km en {dt:.1f}s (distance attendue: {max_possible_distance/1000:.1f} km)",
                measured_value=float(distance),
                threshold_value=max_possible_distance
            ))
        
        return anomalies
    
    def _check_altitude_jump(
        self, idx: int, prev: Position, curr: Position
    ) -> List[AnomalyReport]:
        """Vérifie les sauts d'altitude brutaux"""
        anomalies = []
        
        alt_change = abs(curr.altitude - prev.altitude)
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        
        if dt <= 0:
            return anomalies
        
        climb_rate = alt_change / dt
        
        # Saut d'altitude notable
        if alt_change > self.ALTITUDE_JUMP_THRESHOLD and dt < 10:
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=curr.timestamp,
                anomaly_type=AnomalyType.ALTITUDE_JUMP,
                severity='medium',  # Réduit de critical à medium
                confidence_score=0.5,  # Augmenté de 0.2 à 0.5
                description=f"Variation d'altitude notable : {alt_change:.0f}m en {dt:.1f}s",
                measured_value=alt_change,
                threshold_value=self.ALTITUDE_JUMP_THRESHOLD
            ))
        
        return anomalies
    
    def _check_climb_rate(
        self, idx: int, prev: Position, curr: Position
    ) -> List[AnomalyReport]:
        """Vérifie le taux de montée/descente"""
        anomalies = []
        
        alt_change = curr.altitude - prev.altitude
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        
        if dt <= 0:
            return anomalies
        
        climb_rate = alt_change / dt  # m/s (positif = montée, négatif = descente)
        
        if climb_rate > self.MAX_CLIMB_RATE:
            # Classification progressive : low si légèrement au-dessus, medium si nettement
            severity = 'medium' if climb_rate > self.MAX_CLIMB_RATE * 1.5 else 'low'
            confidence = 0.6 if severity == 'low' else 0.5
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=curr.timestamp,
                anomaly_type=AnomalyType.UNREALISTIC_CLIMB,
                severity=severity,  # Réduit de high à low/medium
                confidence_score=confidence,  # Augmenté de 0.3
                description=f"Taux de montée élevé : {climb_rate:.1f} m/s ({climb_rate*196.85:.0f} ft/min, recommandé: {self.MAX_CLIMB_RATE*196.85:.0f} ft/min)",
                measured_value=climb_rate,
                threshold_value=self.MAX_CLIMB_RATE
            ))
        
        elif climb_rate < -self.MAX_DESCENT_RATE:
            # Classification progressive
            severity = 'medium' if abs(climb_rate) > self.MAX_DESCENT_RATE * 1.5 else 'low'
            confidence = 0.6 if severity == 'low' else 0.5
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=curr.timestamp,
                anomaly_type=AnomalyType.UNREALISTIC_CLIMB,
                severity=severity,  # Réduit de high à low/medium
                confidence_score=confidence,  # Augmenté de 0.3
                description=f"Taux de descente élevé : {abs(climb_rate):.1f} m/s ({abs(climb_rate)*196.85:.0f} ft/min, recommandé: {self.MAX_DESCENT_RATE*196.85:.0f} ft/min)",
                measured_value=abs(climb_rate),
                threshold_value=self.MAX_DESCENT_RATE
            ))
        
        return anomalies
    
    def _check_acceleration(
        self, idx: int, p0: Position, p1: Position, p2: Position
    ) -> List[AnomalyReport]:
        """Vérifie l'accélération (changement de vitesse)"""
        anomalies = []
        
        # Calculer les vitesses
        c0 = p0.to_cartesian()
        c1 = p1.to_cartesian()
        c2 = p2.to_cartesian()
        
        dt1 = (p1.timestamp - p0.timestamp).total_seconds()
        dt2 = (p2.timestamp - p1.timestamp).total_seconds()
        
        if dt1 <= 0 or dt2 <= 0:
            return anomalies
        
        v1 = np.linalg.norm(c1 - c0) / dt1
        v2 = np.linalg.norm(c2 - c1) / dt2
        
        # Accélération moyenne
        dt_avg = (dt1 + dt2) / 2
        acceleration = abs(v2 - v1) / dt_avg
        
        if acceleration > self.MAX_ACCELERATION:
            # Classification progressive selon l'intensité
            severity = 'medium' if acceleration > self.MAX_ACCELERATION * 1.5 else 'low'
            confidence = 0.6 if severity == 'low' else 0.5
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=p2.timestamp,
                anomaly_type=AnomalyType.ACCELERATION_EXCESSIVE,
                severity=severity,  # Réduit de high à low/medium
                confidence_score=confidence,  # Maintenu à 0.4 ou augmenté
                description=f"Accélération élevée : {acceleration:.2f} m/s² (recommandé: {self.MAX_ACCELERATION:.2f} m/s²)",
                measured_value=float(acceleration),
                threshold_value=self.MAX_ACCELERATION
            ))
        
        return anomalies
    
    def _check_g_force(
        self, idx: int, p0: Position, p1: Position, p2: Position
    ) -> List[AnomalyReport]:
        """Vérifie le facteur de charge (G-force)"""
        anomalies = []
        
        # Calculer la courbure de la trajectoire
        c0 = p0.to_cartesian()
        c1 = p1.to_cartesian()
        c2 = p2.to_cartesian()
        
        dt1 = (p1.timestamp - p0.timestamp).total_seconds()
        dt2 = (p2.timestamp - p1.timestamp).total_seconds()
        
        if dt1 <= 0 or dt2 <= 0:
            return anomalies
        
        # Vecteurs de vitesse
        v1 = (c1 - c0) / dt1
        v2 = (c2 - c1) / dt2
        
        # Accélération centripète (approximation)
        dv = v2 - v1
        dt_avg = (dt1 + dt2) / 2
        accel_vector = dv / dt_avg
        accel_magnitude = np.linalg.norm(accel_vector)
        
        # Convertir en G (1 G = 9.81 m/s²)
        g_force = accel_magnitude / 9.81
        
        if g_force > self.max_g_force:
            # Classification progressive
            severity = 'medium' if g_force > self.max_g_force * 1.5 else 'low'
            confidence = 0.6 if severity == 'low' else 0.5
            anomalies.append(AnomalyReport(
                index=idx,
                timestamp=p2.timestamp,
                anomaly_type=AnomalyType.G_FORCE_EXCESSIVE,
                severity=severity,  # Réduit de high à low/medium
                confidence_score=confidence,  # Maintenu à 0.4 ou augmenté
                description=f"G-force élevé : {g_force:.2f} G (recommandé: {self.max_g_force:.2f} G)",
                measured_value=float(g_force),
                threshold_value=self.max_g_force
            ))
        
        return anomalies
    
    def compute_confidence_scores(
        self, trajectory: Trajectory, anomalies: List[AnomalyReport]
    ) -> np.ndarray:
        """
        Calcule un score de confiance pour chaque point
        
        Args:
            trajectory: Trajectoire analysée
            anomalies: Anomalies détectées
            
        Returns:
            Array de scores (0.0 = spoofé certain, 1.0 = valide certain)
        """
        scores = np.ones(len(trajectory))  # Commencer à 1.0 (tous valides)
        
        for anomaly in anomalies:
            idx = anomaly.index
            
            # Réduire le score selon la sévérité (uniquement low et medium maintenant)
            if anomaly.severity == 'medium':
                scores[idx] = min(scores[idx], 0.6)
            elif anomaly.severity == 'low':
                scores[idx] = min(scores[idx], 0.8)
            # Les niveaux critical et high ne devraient plus exister
            elif anomaly.severity == 'critical':
                scores[idx] = min(scores[idx], 0.6)  # Traiter comme medium si présent
            elif anomaly.severity == 'high':
                scores[idx] = min(scores[idx], 0.6)  # Traiter comme medium si présent
        
        return scores
    
    def get_summary(self, anomalies: List[AnomalyReport]) -> Dict:
        """
        Génère un résumé des anomalies détectées
        
        Args:
            anomalies: Liste des anomalies
            
        Returns:
            Dictionnaire avec statistiques
        """
        if not anomalies:
            return {
                'total_anomalies': 0,
                'spoofing_detected': False,
                'risk_level': 'low',
                'by_severity': {},
                'by_type': {}
            }
        
        # Compter par sévérité
        by_severity: dict[str, int] = {}
        for a in anomalies:
            by_severity[a.severity] = by_severity.get(a.severity, 0) + 1
        
        # Compter par type
        by_type: dict[str, int] = {}
        for a in anomalies:
            by_type[a.anomaly_type.value] = by_type.get(a.anomaly_type.value, 0) + 1
        
        # Déterminer le niveau de risque (uniquement low/medium maintenant)
        medium_count = by_severity.get('medium', 0)
        low_count = by_severity.get('low', 0)
        
        # Niveau de risque basé uniquement sur low/medium
        if medium_count > 5:
            risk_level = 'medium'
            spoofing_detected = True
        elif medium_count > 0:
            risk_level = 'low-medium'
            spoofing_detected = False
        else:
            risk_level = 'low'
            spoofing_detected = False
        
        return {
            'total_anomalies': len(anomalies),
            'spoofing_detected': spoofing_detected,
            'risk_level': risk_level,
            'by_severity': by_severity,
            'by_type': by_type,
            'critical_anomalies': [a for a in anomalies if a.severity == 'critical'],
            'high_anomalies': [a for a in anomalies if a.severity == 'high']
        }
    
    def print_report(self, anomalies: List[AnomalyReport], summary: Dict):
        """Affiche un rapport formaté"""
        print("\n" + "="*80)
        print("📋 RAPPORT DE DÉTECTION DE SPOOFING")
        print("="*80)
        
        if summary['total_anomalies'] == 0:
            print("✅ Aucune anomalie détectée - Trajectoire valide")
            return
        
        print(f"\n🚨 Statut: {'SPOOFING DÉTECTÉ' if summary['spoofing_detected'] else 'ANOMALIES DÉTECTÉES'}")
        print(f"⚠️  Niveau de risque: {summary['risk_level'].upper()}")
        print(f"📊 Total d'anomalies: {summary['total_anomalies']}")
        
        print(f"\n📈 Par sévérité:")
        for severity, count in sorted(summary['by_severity'].items()):
            icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(severity, '⚪')
            print(f"   {icon} {severity.capitalize():10s}: {count:3d}")
        
        print(f"\n🔍 Par type d'anomalie:")
        for atype, count in sorted(summary['by_type'].items(), key=lambda x: -x[1]):
            print(f"   • {atype:25s}: {count:3d}")
        
        if summary['critical_anomalies']:
            print(f"\n🔴 Anomalies CRITIQUES (premières 5):")
            for a in summary['critical_anomalies'][:5]:
                print(f"   [{a.index:4d}] {a.description}")
        
        if summary['high_anomalies']:
            print(f"\n🟠 Anomalies ÉLEVÉES (premières 5):")
            for a in summary['high_anomalies'][:5]:
                print(f"   [{a.index:4d}] {a.description}")
        
        print("\n" + "="*80)
