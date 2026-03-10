"""
Détecteur de spoofing GPS/ADS-B AVANCÉ
Utilise des techniques statistiques, ML et analyse de patterns
"""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from scipy import stats  # type: ignore
from scipy.spatial.distance import cdist  # type: ignore

from ..data.data_models import Trajectory, Position
from .spoofing_detector import AnomalyType, AnomalyReport, SpoofingDetector


@dataclass
class SpoofingPattern:
    """Pattern de spoofing connu"""
    name: str
    description: str
    detection_function: callable
    severity_override: Optional[str] = None


@dataclass
class AdvancedSpoofingReport:
    """Rapport de détection avancé"""
    trajectory_id: str
    total_points: int
    anomalies: List[AnomalyReport]
    confidence_scores: np.ndarray
    global_risk_score: float  # 0.0 (sûr) à 1.0 (spoofing certain)
    detected_patterns: List[str] = field(default_factory=list)
    statistical_outliers: int = 0
    replay_attack_detected: bool = False
    trajectory_continuity_score: float = 1.0
    physical_plausibility: float = 1.0
    recommendations: List[str] = field(default_factory=list)


class AdvancedSpoofingDetector(SpoofingDetector):
    """
    Détecteur avancé combinant:
    - Détection classique basée sur règles physiques
    - Analyse statistique (outliers, distributions)
    - Détection de patterns de spoofing connus
    - Analyse de cohérence globale de trajectoire
    - Détection de replay attacks
    - Scoring ML-like basé sur features
    """
    
    def __init__(
        self,
        commercial_aircraft: bool = True,
        strict_mode: bool = False,
        enable_ml_scoring: bool = True,
        enable_pattern_detection: bool = True
    ):
        """
        Initialise le détecteur avancé
        
        Args:
            commercial_aircraft: True pour aviation commerciale
            strict_mode: Mode strict (plus sensible)
            enable_ml_scoring: Activer le scoring ML-like
            enable_pattern_detection: Activer la détection de patterns
        """
        super().__init__(commercial_aircraft, strict_mode)
        self.enable_ml = enable_ml_scoring
        self.enable_patterns = enable_pattern_detection
        
        # Enregistrer les patterns de spoofing connus
        self.known_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> List[SpoofingPattern]:
        """Initialise la base de patterns de spoofing connus"""
        return [
            SpoofingPattern(
                name="constant_altitude_drift",
                description="Position dérive mais altitude reste constante (spoofing simple)",
                detection_function=self._detect_constant_altitude_drift
            ),
            SpoofingPattern(
                name="perfect_circle",
                description="Trajectoire circulaire parfaite (GPS jammer)",
                detection_function=self._detect_perfect_circle
            ),
            SpoofingPattern(
                name="position_repetition",
                description="Positions identiques répétées (replay attack)",
                detection_function=self._detect_position_repetition
            ),
            SpoofingPattern(
                name="sudden_offset",
                description="Offset soudain appliqué à toute la trajectoire",
                detection_function=self._detect_sudden_offset
            ),
            SpoofingPattern(
                name="quantization_artifact",
                description="Valeurs trop régulières/quantifiées (spoofing algorithmique)",
                detection_function=self._detect_quantization
            ),
            SpoofingPattern(
                name="impossible_turn",
                description="Virage instantané physiquement impossible",
                detection_function=self._detect_impossible_turn
            ),
            SpoofingPattern(
                name="velocity_discontinuity",
                description="Discontinuité soudaine de vitesse sans raison",
                detection_function=self._detect_velocity_discontinuity
            )
        ]
    
    def analyze_comprehensive(
        self,
        trajectory: Trajectory,
        verbose: bool = True
    ) -> AdvancedSpoofingReport:
        """
        Analyse complète anti-spoofing multi-couches
        
        Args:
            trajectory: Trajectoire à analyser
            verbose: Afficher les informations de progression
            
        Returns:
            Rapport complet d'analyse
        """
        if verbose:
            print("\n" + "="*80)
            print("🔬 ANALYSE ANTI-SPOOFING AVANCÉE")
            print("="*80)
        
        # 1. Détection classique basée sur règles physiques
        if verbose:
            print("\n[1/6] 🔍 Détection classique (règles physiques)...")
        basic_anomalies = self.detect_anomalies(trajectory)
        
        # 2. Analyse statistique (outliers multivariés)
        if verbose:
            print("[2/6] 📊 Analyse statistique avancée...")
        statistical_anomalies, outlier_count = self._detect_statistical_outliers(trajectory)
        all_anomalies = basic_anomalies + statistical_anomalies
        
        # 3. Détection de patterns de spoofing connus
        detected_patterns = []
        if self.enable_patterns:
            if verbose:
                print("[3/6] 🎯 Détection de patterns de spoofing...")
            pattern_anomalies, detected_patterns = self._detect_known_patterns(trajectory)
            all_anomalies.extend(pattern_anomalies)
        
        # 4. Analyse de cohérence globale
        if verbose:
            print("[4/6] 🌍 Analyse de cohérence globale...")
        continuity_score = self._compute_trajectory_continuity(trajectory)
        physical_plausibility = self._compute_physical_plausibility(trajectory)
        
        # 5. Détection de replay attack
        if verbose:
            print("[5/6] 🔄 Détection de replay attack...")
        replay_detected, replay_anomalies = self._detect_replay_attack(trajectory)
        all_anomalies.extend(replay_anomalies)
        
        # 6. Scoring ML-like global
        if verbose:
            print("[6/6] 🤖 Calcul du score de risque ML...")
        confidence_scores = self.compute_confidence_scores(trajectory, all_anomalies)
        global_risk_score = self._compute_global_risk_score(
            trajectory, all_anomalies, confidence_scores,
            continuity_score, physical_plausibility
        )
        
        # Générer des recommandations
        recommendations = self._generate_recommendations(
            all_anomalies, global_risk_score, detected_patterns, replay_detected
        )
        
        report = AdvancedSpoofingReport(
            trajectory_id=trajectory.flight_id or "unknown",
            total_points=len(trajectory),
            anomalies=sorted(all_anomalies, key=lambda x: (x.index, x.severity)),
            confidence_scores=confidence_scores,
            global_risk_score=global_risk_score,
            detected_patterns=detected_patterns,
            statistical_outliers=outlier_count,
            replay_attack_detected=replay_detected,
            trajectory_continuity_score=continuity_score,
            physical_plausibility=physical_plausibility,
            recommendations=recommendations
        )
        
        if verbose:
            self._print_advanced_report(report)
        
        return report
    
    def _detect_statistical_outliers(
        self,
        trajectory: Trajectory
    ) -> Tuple[List[AnomalyReport], int]:
        """
        Détecte les outliers statistiques multivariés
        Utilise Isolation Forest concept simplifié
        """
        anomalies = []
        
        if len(trajectory) < 10:
            return anomalies, 0
        
        # Extraire features pour chaque point
        features = []
        for i in range(1, len(trajectory) - 1):
            prev = trajectory.positions[i-1]
            curr = trajectory.positions[i]
            next_pos = trajectory.positions[i+1]
            
            # Features: vitesse, accélération, variation altitude, courbure
            v1 = np.linalg.norm(curr.to_cartesian() - prev.to_cartesian()) / max(
                (curr.timestamp - prev.timestamp).total_seconds(), 0.1
            )
            v2 = np.linalg.norm(next_pos.to_cartesian() - curr.to_cartesian()) / max(
                (next_pos.timestamp - curr.timestamp).total_seconds(), 0.1
            )
            accel = abs(v2 - v1)
            alt_change = abs(curr.altitude - prev.altitude)
            
            features.append([v1, accel, alt_change, curr.altitude])
        
        features_array = np.array(features)
        
        # Normaliser
        mean = np.mean(features_array, axis=0)
        std = np.std(features_array, axis=0) + 1e-6
        normalized = (features_array - mean) / std
        
        # Détecter outliers (Mahalanobis distance simplifiée)
        distances = np.sqrt(np.sum(normalized ** 2, axis=1))
        threshold = np.mean(distances) + 3 * np.std(distances)
        
        outlier_indices = np.where(distances > threshold)[0]
        outlier_count = len(outlier_indices)
        
        for idx in outlier_indices:
            actual_idx = idx + 1  # Décalage car features commence à 1
            if actual_idx < len(trajectory):
                anomalies.append(AnomalyReport(
                    index=actual_idx,
                    timestamp=trajectory.positions[actual_idx].timestamp,
                    anomaly_type=AnomalyType.GEOGRAPHIC_ANOMALY,
                    severity='low',
                    confidence_score=0.7,
                    description=f"Outlier statistique multivarié (distance: {distances[idx]:.2f}, seuil: {threshold:.2f})",
                    measured_value=float(distances[idx]),
                    threshold_value=threshold
                ))
        
        return anomalies, outlier_count
    
    def _detect_known_patterns(
        self,
        trajectory: Trajectory
    ) -> Tuple[List[AnomalyReport], List[str]]:
        """Détecte les patterns de spoofing connus"""
        anomalies = []
        detected_patterns = []
        
        for pattern in self.known_patterns:
            try:
                is_detected, pattern_anomalies = pattern.detection_function(trajectory)
                if is_detected:
                    detected_patterns.append(pattern.name)
                    anomalies.extend(pattern_anomalies)
            except Exception as e:
                # Ignorer les erreurs de patterns individuels
                pass
        
        return anomalies, detected_patterns
    
    def _detect_constant_altitude_drift(
        self,
        trajectory: Trajectory
    ) -> Tuple[bool, List[AnomalyReport]]:
        """Détecte si position dérive mais altitude reste anormalement constante"""
        if len(trajectory) < 20:
            return False, []
        
        # Vérifier si altitude varie très peu
        altitudes = np.array([p.altitude for p in trajectory.positions])
        alt_std = np.std(altitudes)
        
        # Vérifier si position dérive significativement
        positions_cart = trajectory.get_cartesian_array()
        total_distance = np.sum(np.linalg.norm(np.diff(positions_cart[:, :2], axis=0), axis=1))
        
        # Pattern: beaucoup de mouvement horizontal, peu de variation altitude
        if total_distance > 10000 and alt_std < 50:  # 10km+, altitude varie <50m
            anomaly = AnomalyReport(
                index=len(trajectory) // 2,
                timestamp=trajectory.positions[len(trajectory) // 2].timestamp,
                anomaly_type=AnomalyType.GEOGRAPHIC_ANOMALY,
                severity='medium',
                confidence_score=0.4,
                description=f"Pattern suspect: altitude constante ({alt_std:.1f}m variation) sur {total_distance/1000:.1f}km",
                measured_value=float(alt_std),
                threshold_value=50.0
            )
            return True, [anomaly]
        
        return False, []
    
    def _detect_perfect_circle(
        self,
        trajectory: Trajectory
    ) -> Tuple[bool, List[AnomalyReport]]:
        """Détecte une trajectoire circulaire parfaite (GPS jammer)"""
        if len(trajectory) < 20:
            return False, []
        
        # Calculer le centroïde
        positions_cart = trajectory.get_cartesian_array()[:, :2]  # Seulement x, y
        centroid = np.mean(positions_cart, axis=0)
        
        # Distances au centroïde
        distances = np.linalg.norm(positions_cart - centroid, axis=1)
        
        # Vérifier si distances sont très uniformes (cercle parfait)
        dist_std = np.std(distances)
        dist_mean = np.mean(distances)
        
        if dist_mean > 100 and dist_std / dist_mean < 0.05:  # Coefficient de variation < 5%
            anomaly = AnomalyReport(
                index=len(trajectory) // 2,
                timestamp=trajectory.positions[len(trajectory) // 2].timestamp,
                anomaly_type=AnomalyType.GEOGRAPHIC_ANOMALY,
                severity='medium',
                confidence_score=0.3,
                description=f"Pattern circulaire suspect (CV: {dist_std/dist_mean*100:.1f}%, rayon: {dist_mean:.0f}m)",
                measured_value=float(dist_std / dist_mean),
                threshold_value=0.05
            )
            return True, [anomaly]
        
        return False, []
    
    def _detect_position_repetition(
        self,
        trajectory: Trajectory
    ) -> Tuple[bool, List[AnomalyReport]]:
        """Détecte des positions identiques répétées (replay attack)"""
        anomalies = []
        
        if len(trajectory) < 10:
            return False, []
        
        positions_cart = trajectory.get_cartesian_array()
        
        # Chercher des séquences répétées
        window_size = 5
        for i in range(len(positions_cart) - 2 * window_size):
            window1 = positions_cart[i:i+window_size]
            
            # Chercher si cette séquence se répète plus loin
            for j in range(i + window_size, len(positions_cart) - window_size):
                window2 = positions_cart[j:j+window_size]
                
                # Distance moyenne entre les deux fenêtres
                distance = np.mean(np.linalg.norm(window1 - window2, axis=1))
                
                if distance < 10:  # Positions presque identiques (<10m)
                    anomalies.append(AnomalyReport(
                        index=j,
                        timestamp=trajectory.positions[j].timestamp,
                        anomaly_type=AnomalyType.POSITION_JUMP,
                        severity='medium',
                        confidence_score=0.3,
                        description=f"Séquence de positions répétée (dist: {distance:.1f}m)",
                        measured_value=float(distance),
                        threshold_value=10.0
                    ))
                    return True, anomalies
        
        return False, []
    
    def _detect_sudden_offset(
        self,
        trajectory: Trajectory
    ) -> Tuple[bool, List[AnomalyReport]]:
        """Détecte un offset soudain appliqué à toute la trajectoire"""
        if len(trajectory) < 10:
            return False, []
        
        positions_cart = trajectory.get_cartesian_array()
        
        # Calculer les différences entre points consécutifs
        diffs = np.diff(positions_cart, axis=0)
        diff_norms = np.linalg.norm(diffs[:, :2], axis=1)  # Ignorer altitude
        
        # Chercher un saut soudain suivi de pattern normal
        for i in range(2, len(diff_norms) - 5):
            before_mean = np.mean(diff_norms[max(0, i-5):i])
            jump = diff_norms[i]
            after_mean = np.mean(diff_norms[i+1:i+6])
            
            # Pattern: saut important, puis retour à la normale
            if jump > before_mean * 10 and abs(before_mean - after_mean) < before_mean * 0.5:
                anomaly = AnomalyReport(
                    index=i,
                    timestamp=trajectory.positions[i].timestamp,
                    anomaly_type=AnomalyType.POSITION_JUMP,
                    severity='medium',
                    confidence_score=0.4,
                    description=f"Offset soudain détecté: saut de {jump:.0f}m (normal: {before_mean:.0f}m)",
                    measured_value=float(jump),
                    threshold_value=float(before_mean * 10)
                )
                return True, [anomaly]
        
        return False, []
    
    def _detect_quantization(
        self,
        trajectory: Trajectory
    ) -> Tuple[bool, List[AnomalyReport]]:
        """Détecte des valeurs trop régulières/quantifiées (spoofing algorithmique)"""
        if len(trajectory) < 20:
            return False, []
        
        # Vérifier si les coordonnées sont trop régulières
        lats = np.array([p.latitude for p in trajectory.positions])
        lons = np.array([p.longitude for p in trajectory.positions])
        alts = np.array([p.altitude for p in trajectory.positions])
        
        # Compter les décimales uniques pour latitude/longitude
        lat_decimals = [len(str(lat).split('.')[-1]) if '.' in str(lat) else 0 for lat in lats]
        lon_decimals = [len(str(lon).split('.')[-1]) if '.' in str(lon) else 0 for lon in lons]
        
        # Vérifier si altitudes se terminent toujours par 0 ou 5 (quantification)
        alt_last_digits = [int(abs(alt)) % 10 for alt in alts]
        zeros_and_fives = sum(1 for d in alt_last_digits if d == 0 or d == 5)
        
        if zeros_and_fives / len(alt_last_digits) > 0.9:  # Plus de 90% se terminent par 0 ou 5
            anomaly = AnomalyReport(
                index=len(trajectory) // 2,
                timestamp=trajectory.positions[len(trajectory) // 2].timestamp,
                anomaly_type=AnomalyType.GEOGRAPHIC_ANOMALY,
                severity='low',
                confidence_score=0.6,
                description=f"Quantification suspecte des altitudes ({zeros_and_fives/len(alt_last_digits)*100:.0f}% terminées par 0 ou 5)",
                measured_value=float(zeros_and_fives / len(alt_last_digits)),
                threshold_value=0.9
            )
            return True, [anomaly]
        
        return False, []
    
    def _detect_impossible_turn(
        self,
        trajectory: Trajectory
    ) -> Tuple[bool, List[AnomalyReport]]:
        """Détecte des virages instantanés physiquement impossibles"""
        anomalies = []
        
        if len(trajectory) < 3:
            return False, []
        
        for i in range(1, len(trajectory) - 1):
            prev = trajectory.positions[i-1].to_cartesian()[:2]
            curr = trajectory.positions[i].to_cartesian()[:2]
            next_pos = trajectory.positions[i+1].to_cartesian()[:2]
            
            # Vecteurs de mouvement
            v1 = curr - prev
            v2 = next_pos - curr
            
            v1_norm = np.linalg.norm(v1)
            v2_norm = np.linalg.norm(v2)
            
            if v1_norm > 10 and v2_norm > 10:  # Ignorer mouvements minimes
                # Angle entre les vecteurs
                cos_angle = np.dot(v1, v2) / (v1_norm * v2_norm)
                cos_angle = np.clip(cos_angle, -1, 1)
                angle_deg = np.degrees(np.arccos(cos_angle))
                
                dt = (trajectory.positions[i+1].timestamp - trajectory.positions[i-1].timestamp).total_seconds()
                
                # Virage > 90° en moins de 5 secondes = suspect
                if angle_deg > 90 and dt < 5:
                    anomalies.append(AnomalyReport(
                        index=i,
                        timestamp=trajectory.positions[i].timestamp,
                        anomaly_type=AnomalyType.ACCELERATION_EXCESSIVE,
                        severity='medium',
                        confidence_score=0.5,
                        description=f"Virage brutal: {angle_deg:.0f}° en {dt:.1f}s",
                        measured_value=float(angle_deg),
                        threshold_value=90.0
                    ))
        
        return len(anomalies) > 0, anomalies
    
    def _detect_velocity_discontinuity(
        self,
        trajectory: Trajectory
    ) -> Tuple[bool, List[AnomalyReport]]:
        """Détecte des discontinuités soudaines de vitesse"""
        anomalies = []
        
        if len(trajectory) < 5:
            return False, []
        
        velocities = []
        for i in range(len(trajectory) - 1):
            dist = np.linalg.norm(
                trajectory.positions[i+1].to_cartesian() - trajectory.positions[i].to_cartesian()
            )
            dt = (trajectory.positions[i+1].timestamp - trajectory.positions[i].timestamp).total_seconds()
            if dt > 0:
                velocities.append(dist / dt)
        
        velocities = np.array(velocities)
        
        # Détecter sauts soudains de vitesse
        velocity_changes = np.abs(np.diff(velocities))
        median_change = np.median(velocity_changes)
        
        for i, change in enumerate(velocity_changes):
            if change > median_change * 10 and change > 50:  # 10x la variation médiane ET >50 m/s
                anomalies.append(AnomalyReport(
                    index=i+1,
                    timestamp=trajectory.positions[i+1].timestamp,
                    anomaly_type=AnomalyType.ACCELERATION_EXCESSIVE,
                    severity='medium',
                    confidence_score=0.5,
                    description=f"Discontinuité de vitesse: Δv = {change:.1f} m/s (médiane: {median_change:.1f} m/s)",
                    measured_value=float(change),
                    threshold_value=float(median_change * 10)
                ))
        
        return len(anomalies) > 0, anomalies
    
    def _compute_trajectory_continuity(self, trajectory: Trajectory) -> float:
        """
        Calcule un score de continuité (smoothness) de la trajectoire
        1.0 = parfaitement continue, 0.0 = très discontinue
        """
        if len(trajectory) < 3:
            return 1.0
        
        positions_cart = trajectory.get_cartesian_array()
        
        # Calculer le jerk (dérivée 3ème)
        first_diff = np.diff(positions_cart, axis=0)
        second_diff = np.diff(first_diff, axis=0)
        third_diff = np.diff(second_diff, axis=0)
        
        # Norme moyenne du jerk (plus petit = plus lisse)
        jerk_norm = np.mean(np.linalg.norm(third_diff, axis=1))
        
        # Normaliser (empirique: jerk < 10 = bon, > 100 = mauvais)
        continuity_score = max(0.0, min(1.0, 1.0 - jerk_norm / 100.0))
        
        return float(continuity_score)
    
    def _compute_physical_plausibility(self, trajectory: Trajectory) -> float:
        """
        Calcule un score de plausibilité physique globale
        1.0 = parfaitement plausible, 0.0 = impossible
        """
        if len(trajectory) < 2:
            return 1.0
        
        scores = []
        
        # 1. Vitesses plausibles
        velocities = []
        for i in range(len(trajectory) - 1):
            dist = np.linalg.norm(
                trajectory.positions[i+1].to_cartesian() - trajectory.positions[i].to_cartesian()
            )
            dt = (trajectory.positions[i+1].timestamp - trajectory.positions[i].timestamp).total_seconds()
            if dt > 0:
                velocities.append(dist / dt)
        
        if velocities:
            avg_velocity = np.mean(velocities)
            velocity_score = max(0.0, min(1.0, 1.0 - (avg_velocity - self.max_speed) / self.max_speed))
            scores.append(velocity_score)
        
        # 2. Altitudes plausibles
        altitudes = [p.altitude for p in trajectory.positions]
        alt_in_range = sum(1 for alt in altitudes if self.MIN_ALTITUDE <= alt <= self.MAX_ALTITUDE)
        altitude_score = alt_in_range / len(altitudes)
        scores.append(altitude_score)
        
        # 3. Taux de montée plausibles
        climb_rates = []
        for i in range(len(trajectory) - 1):
            dalt = trajectory.positions[i+1].altitude - trajectory.positions[i].altitude
            dt = (trajectory.positions[i+1].timestamp - trajectory.positions[i].timestamp).total_seconds()
            if dt > 0:
                climb_rates.append(abs(dalt / dt))
        
        if climb_rates:
            max_climb = max(climb_rates)
            climb_score = max(0.0, min(1.0, 1.0 - (max_climb - self.MAX_CLIMB_RATE) / self.MAX_CLIMB_RATE))
            scores.append(climb_score)
        
        return float(np.mean(scores)) if scores else 1.0
    
    def _detect_replay_attack(
        self,
        trajectory: Trajectory
    ) -> Tuple[bool, List[AnomalyReport]]:
        """
        Détecte un replay attack (séquence GPS rejouée)
        Cherche des patterns répétitifs ou segments identiques
        """
        anomalies = []
        
        if len(trajectory) < 20:
            return False, []
        
        positions_cart = trajectory.get_cartesian_array()
        
        # Chercher des segments similaires (corrélation)
        segment_size = 10
        segments = []
        
        for i in range(0, len(positions_cart) - segment_size, 5):
            segment = positions_cart[i:i+segment_size]
            # Normaliser le segment (center sur premier point)
            segment_normalized = segment - segment[0]
            segments.append((i, segment_normalized))
        
        # Comparer tous les segments entre eux
        replay_detected = False
        for i, (idx1, seg1) in enumerate(segments):
            for idx2, seg2 in segments[i+2:]:  # Éviter comparaison avec voisins immédiats
                # Distance moyenne entre segments
                dist = np.mean(np.linalg.norm(seg1 - seg2, axis=1))
                
                if dist < 50:  # Segments très similaires (<50m de différence moyenne)
                    replay_detected = True
                    anomalies.append(AnomalyReport(
                        index=idx2,
                        timestamp=trajectory.positions[idx2].timestamp,
                        anomaly_type=AnomalyType.POSITION_JUMP,
                        severity='medium',
                        confidence_score=0.3,
                        description=f"Segment répété détecté (similarité: {dist:.1f}m avec index {idx1})",
                        measured_value=float(dist),
                        threshold_value=50.0
                    ))
                    break
            if replay_detected:
                break
        
        return replay_detected, anomalies
    
    def _compute_global_risk_score(
        self,
        trajectory: Trajectory,
        anomalies: List[AnomalyReport],
        confidence_scores: np.ndarray,
        continuity_score: float,
        physical_plausibility: float
    ) -> float:
        """
        Calcule un score de risque global combinant tous les facteurs
        0.0 = sûr, 1.0 = spoofing quasi-certain
        """
        # 1. Score basé sur les anomalies
        if len(anomalies) == 0:
            anomaly_score = 0.0
        else:
            severity_weights = {'critical': 1.0, 'high': 0.7, 'medium': 0.4, 'low': 0.1}
            total_weight = sum(severity_weights.get(a.severity, 0.1) for a in anomalies)
            anomaly_score = min(1.0, total_weight / len(trajectory) * 10)
        
        # 2. Score basé sur la confiance moyenne
        confidence_score = 1.0 - np.mean(confidence_scores)
        
        # 3. Score de discontinuité
        discontinuity_score = 1.0 - continuity_score
        
        # 4. Score d'implausibilité physique
        implausibility_score = 1.0 - physical_plausibility
        
        # Combinaison pondérée
        global_risk = (
            anomaly_score * 0.4 +
            confidence_score * 0.3 +
            discontinuity_score * 0.15 +
            implausibility_score * 0.15
        )
        
        return float(np.clip(global_risk, 0.0, 1.0))
    
    def _generate_recommendations(
        self,
        anomalies: List[AnomalyReport],
        global_risk_score: float,
        detected_patterns: List[str],
        replay_detected: bool
    ) -> List[str]:
        """Génère des recommandations basées sur l'analyse"""
        recommendations = []
        
        if global_risk_score < 0.2:
            recommendations.append("✅ Trajectoire semble authentique - Aucune action requise")
        elif global_risk_score < 0.5:
            recommendations.append("⚠️  Quelques anomalies détectées - Vérification manuelle recommandée")
            recommendations.append("   Examiner les points d'anomalies pour confirmer leur légitimité")
        else:
            recommendations.append("🚨 RISQUE ÉLEVÉ DE SPOOFING - Action immédiate requise")
            recommendations.append("   1. Croiser avec d'autres sources de données (radar, ATC)")
            recommendations.append("   2. Vérifier l'intégrité des signaux GPS/ADS-B")
            recommendations.append("   3. Considérer cette trajectoire comme potentiellement falsifiée")
        
        if replay_detected:
            recommendations.append("🔄 REPLAY ATTACK DÉTECTÉ - Segments de trajectoire répétés")
            recommendations.append("   Source GPS potentiellement compromise")
        
        if detected_patterns:
            recommendations.append(f"🎯 Patterns suspects détectés: {', '.join(detected_patterns)}")
            recommendations.append("   Ces patterns sont typiques de spoofing GPS/ADS-B")
        
        # Recommandations spécifiques par type d'anomalie
        anomaly_types = {a.anomaly_type for a in anomalies}
        if AnomalyType.SPEED_IMPOSSIBLE in anomaly_types:
            recommendations.append("⚡ Vitesses impossibles - Vérifier calibration des capteurs")
        if AnomalyType.POSITION_JUMP in anomaly_types:
            recommendations.append("📍 Sauts de position - Possible perte/reprise de signal GPS")
        
        return recommendations
    
    def _print_advanced_report(self, report: AdvancedSpoofingReport):
        """Affiche un rapport formaté avancé"""
        print("\n" + "="*80)
        print("📋 RAPPORT ANTI-SPOOFING AVANCÉ")
        print("="*80)
        
        print(f"\n🆔 Vol: {report.trajectory_id}")
        print(f"📊 Points analysés: {report.total_points}")
        print(f"🚨 Anomalies détectées: {len(report.anomalies)}")
        
        # Score de risque avec couleur
        risk_pct = report.global_risk_score * 100
        if report.global_risk_score < 0.2:
            risk_icon, risk_label = "🟢", "FAIBLE"
        elif report.global_risk_score < 0.5:
            risk_icon, risk_label = "🟡", "MOYEN"
        elif report.global_risk_score < 0.8:
            risk_icon, risk_label = "🟠", "ÉLEVÉ"
        else:
            risk_icon, risk_label = "🔴", "CRITIQUE"
        
        print(f"\n{risk_icon} SCORE DE RISQUE GLOBAL: {risk_pct:.1f}% ({risk_label})")
        
        # Métriques détaillées
        print(f"\n📈 Métriques de qualité:")
        print(f"   • Continuité trajectoire : {report.trajectory_continuity_score*100:.1f}%")
        print(f"   • Plausibilité physique  : {report.physical_plausibility*100:.1f}%")
        print(f"   • Confiance moyenne      : {np.mean(report.confidence_scores)*100:.1f}%")
        print(f"   • Outliers statistiques  : {report.statistical_outliers}")
        
        # Patterns détectés
        if report.detected_patterns:
            print(f"\n🎯 Patterns de spoofing détectés:")
            for pattern in report.detected_patterns:
                print(f"   • {pattern.replace('_', ' ').title()}")
        
        if report.replay_attack_detected:
            print(f"\n🔄 ⚠️  REPLAY ATTACK DÉTECTÉ")
        
        # Top anomalies
        if report.anomalies:
            print(f"\n🔍 Top 10 anomalies (par sévérité):")
            sorted_anomalies = sorted(report.anomalies, 
                                     key=lambda x: ({'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(x.severity, 0), -x.index),
                                     reverse=True)
            for i, a in enumerate(sorted_anomalies[:10], 1):
                severity_icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(a.severity, '⚪')
                print(f"   {i:2d}. {severity_icon} [{a.index:4d}] {a.description[:70]}")
        
        # Recommandations
        if report.recommendations:
            print(f"\n💡 Recommandations:")
            for rec in report.recommendations:
                print(f"   {rec}")
        
        print("\n" + "="*80)
