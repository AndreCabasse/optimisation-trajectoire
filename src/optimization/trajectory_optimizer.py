"""
Optimiseur principal de trajectoires
Combine Kalman, B-spline et données météo
"""
from __future__ import annotations
import numpy as np
from typing import Optional, Dict, List
from enum import Enum

from ..data.data_models import Trajectory, OptimizedTrajectory, Position, WeatherConditions
from ..filters.kalman_filter import KalmanFilter
from ..optimization.bspline import BSplineOptimizer
from ..weather.weather_api import WeatherAPI, WindFieldInterpolator


class OptimizationMethod(Enum):
    """Méthodes d'optimisation disponibles"""
    KALMAN = "kalman"
    BSPLINE = "bspline"
    HYBRID = "hybrid"  # Kalman + B-spline
    WEATHER = "weather"  # Optimisation avec météo
    DIRECT_COLLOCATION = "direct_collocation"  # Optimisation directe par NLP


class OptimizationProfile(Enum):
    """
    Profils d'optimisation pour Direct Collocation
    Définit les priorités et pondérations dans la fonction objectif
    """
    FUEL_SAVER = "fuel_saver"      # Priorité: économie de carburant (distance minimale)
    COMFORT = "comfort"            # Priorité: confort passagers (smoothness maximale)
    BALANCED = "balanced"          # Priorité: équilibre réalisme/efficacité (défaut)


class TrajectoryOptimizer:
    """
    Optimiseur principal qui combine toutes les techniques
    """
    
    def __init__(
        self,
        method: OptimizationMethod = OptimizationMethod.HYBRID,
        weather_api_key: Optional[str] = None,
        kalman_config: Optional[Dict] = None,
        bspline_config: Optional[Dict] = None,
        optimization_profile: OptimizationProfile = OptimizationProfile.BALANCED
    ):
        """
        Initialise l'optimiseur
        
        Args:
            method: Méthode d'optimisation à utiliser
            weather_api_key: Clé API pour les données météo
            kalman_config: Configuration du filtre de Kalman
            bspline_config: Configuration B-spline
            optimization_profile: Profil d'optimisation pour Direct Collocation
                                  (FUEL_SAVER, COMFORT, ou BALANCED)
        """
        self.method = method
        self.optimization_profile = optimization_profile
        
        # Initialiser les composants
        kalman_config = kalman_config or {}
        self.kalman = KalmanFilter(**kalman_config)
        
        bspline_config = bspline_config or {}
        self.bspline = BSplineOptimizer(**bspline_config)
        
        # API météo (mode mock par défaut si pas de clé)
        weather_source = 'mock' if not weather_api_key else 'openweather'
        self.weather_api = WeatherAPI(api_key=weather_api_key, source=weather_source)
        self.wind_interpolator = WindFieldInterpolator(self.weather_api)
    
    def optimize(
        self,
        trajectory: Trajectory,
        use_weather: bool = False,
        target_points: Optional[int] = None,
        start_time: Optional[float] = None,
        start_distance: Optional[float] = None
    ) -> OptimizedTrajectory:
        """
        Optimise une trajectoire selon la méthode configurée
        
        Args:
            trajectory: Trajectoire brute à optimiser
            use_weather: Utiliser les données météo pour l'optimisation
            target_points: Nombre de points cible (pour réduire la résolution)
            start_time: Temps en secondes depuis le départ où commencer l'optimisation (optionnel)
            start_distance: Distance en mètres depuis le départ où commencer l'optimisation (optionnel)
            
        Returns:
            Trajectoire optimisée avec métriques
            
        Note:
            Si start_time ou start_distance est spécifié, seule la partie après ce point sera optimisée.
            La partie avant restera inchangée.
        """
        print(f"Optimisation de la trajectoire avec méthode : {self.method.value}")
        print(f"Points originaux : {len(trajectory)}")
        
        # Déterminer le point de départ de l'optimisation
        start_idx = 0
        if start_time is not None:
            start_idx = trajectory.find_index_by_time(start_time)
            print(f"Optimisation à partir de t={start_time}s (index {start_idx})")
        elif start_distance is not None:
            start_idx = trajectory.find_index_by_distance(start_distance)
            print(f"Optimisation à partir de {start_distance}m (index {start_idx})")
        
        # Si un point de départ est spécifié, diviser la trajectoire
        if start_idx > 0:
            prefix_positions = trajectory.positions[:start_idx]
            trajectory_to_optimize = Trajectory(
                positions=trajectory.positions[start_idx:],
                flight_id=trajectory.flight_id
            )
            print(f"Conservation de {start_idx} points initiaux")
            print(f"Optimisation de {len(trajectory_to_optimize)} points")
        else:
            prefix_positions = []
            trajectory_to_optimize = trajectory
        
        if self.method == OptimizationMethod.KALMAN:
            optimized = self._optimize_kalman(trajectory_to_optimize)
            method_name = "kalman"
        
        elif self.method == OptimizationMethod.BSPLINE:
            optimized = self._optimize_bspline(trajectory_to_optimize, target_points)
            method_name = "bspline"
        
        elif self.method == OptimizationMethod.HYBRID:
            optimized = self._optimize_hybrid(trajectory_to_optimize, target_points)
            method_name = "hybrid"
        
        elif self.method == OptimizationMethod.WEATHER:
            if not use_weather:
                use_weather = True
            optimized = self._optimize_with_weather(trajectory_to_optimize, target_points)
            method_name = "weather"
        
        elif self.method == OptimizationMethod.DIRECT_COLLOCATION:
            optimized = self._optimize_direct_collocation(trajectory_to_optimize, target_points, use_weather)
            method_name = "direct_collocation"
        
        else:
            raise ValueError(f"Méthode inconnue : {self.method}")
        
        # Combiner la partie préservée avec la partie optimisée
        if prefix_positions:
            final_positions = prefix_positions + optimized.positions
            final_trajectory = Trajectory(
                positions=final_positions,
                flight_id=trajectory.flight_id
            )
        else:
            final_trajectory = optimized
        
        # Calculer les métriques
        metrics = self._compute_metrics(trajectory, final_trajectory, use_weather)
        
        # Valider le résultat de l'optimisation
        self._validate_optimization_result(trajectory, final_trajectory, self.method)
        
        print(f"Optimisation terminée. Points finaux : {len(final_trajectory)}")
        if prefix_positions:
            print(f"  - Points préservés : {len(prefix_positions)}")
            print(f"  - Points optimisés : {len(optimized)}")
        
        return OptimizedTrajectory(
            original=trajectory,
            optimized_positions=final_trajectory.positions,
            method=method_name,
            metrics=metrics
        )
    
    def _optimize_kalman(self, trajectory: Trajectory) -> Trajectory:
        """Optimisation par filtre de Kalman uniquement"""
        return self.kalman.smooth_trajectory(trajectory)
    
    def _optimize_bspline(
        self,
        trajectory: Trajectory,
        target_points: Optional[int]
    ) -> Trajectory:
        """
        Optimisation par B-spline uniquement avec préservation de distance
        
        Note: preserve_distance=True par défaut garantit une interpolation exacte
              qui préserve la distance originale (±0.1%)
        """
        if target_points:
            return self.bspline.optimize(trajectory, target_points)
        else:
            self.bspline.fit(trajectory)
            return self.bspline.evaluate(trajectory)
    
    def _optimize_hybrid(
        self,
        trajectory: Trajectory,
        target_points: Optional[int]
    ) -> Trajectory:
        """
        Optimisation hybride : Kalman d'abord, puis B-spline
        
        Approche en 2 étapes :
        1. Kalman filtre le bruit (préserve distance naturellement)
        2. B-spline compresse les points (preserve_distance=True → interpolation exacte)
        
        Cette méthode combine robustesse (Kalman) et compression efficace (B-spline)
        tout en garantissant la préservation de la distance originale (±0.5%)
        """
        # Étape 1 : Lissage Kalman pour éliminer le bruit
        print("  Étape 1/2 : Lissage Kalman...")
        smoothed = self.kalman.smooth_trajectory(trajectory)
        
        # Étape 2 : B-spline pour interpolation et réduction de points
        print("  Étape 2/2 : Interpolation B-spline...")
        if target_points:
            optimized = self.bspline.optimize(smoothed, target_points)
        else:
            self.bspline.fit(smoothed)
            optimized = self.bspline.evaluate(smoothed)
        
        return optimized
    
    def _optimize_with_weather(
        self,
        trajectory: Trajectory,
        target_points: Optional[int]
    ) -> Trajectory:
        """
        Optimisation avec prise en compte de la météo
        Calcule une NOUVELLE trajectoire optimisée en fonction des vents
        pour minimiser le temps de vol ou la consommation
        """
        # D'abord, appliquer le lissage pour avoir une trajectoire propre
        smoothed = self.kalman.smooth_trajectory(trajectory)
        
        # Garder les premiers 10% de la trajectoire intacts (phase de décollage/montée)
        takeoff_phase_length = max(5, len(smoothed) // 10)
        takeoff_positions = smoothed.positions[:takeoff_phase_length]
        
        # Créer une trajectoire à partir du point de fin de décollage
        cruise_trajectory = Trajectory(
            positions=smoothed.positions[takeoff_phase_length:],
            flight_id=smoothed.flight_id
        )
        
        # Obtenir les waypoints pour la phase de croisière
        n_waypoints = min(10, len(cruise_trajectory) // 50) if target_points else 5
        waypoint_indices = np.linspace(0, len(cruise_trajectory)-1, n_waypoints, dtype=int)
        waypoints = [cruise_trajectory.positions[i] for i in waypoint_indices]
        
        print(f"  Phase décollage: {takeoff_phase_length} points conservés")
        print(f"  Optimisation croisière: {n_waypoints} waypoints avec prise en compte du vent...")
        
        # Commencer avec les positions de décollage
        optimized_positions = list(takeoff_positions)
        
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            
            # Calculer le nombre de points pour ce segment
            if target_points:
                remaining_points = target_points - len(optimized_positions)
                remaining_segments = len(waypoints) - 1 - i
                segment_points = max(5, remaining_points // remaining_segments)
            else:
                segment_points = 20
            
            # Obtenir les conditions météo moyennes pour ce segment
            mid_lat = (start.latitude + end.latitude) / 2
            mid_lon = (start.longitude + end.longitude) / 2
            mid_alt = (start.altitude + end.altitude) / 2
            weather = self.weather_api.get_weather(mid_lat, mid_lon, mid_alt)
            
            # Calculer la trajectoire optimale pour ce segment en tenant compte du vent
            segment = self._optimize_segment_with_wind(
                start, end, weather, segment_points
            )
            
            # Ajouter les points (sauf le dernier pour éviter les doublons)
            if i < len(waypoints) - 2:
                optimized_positions.extend(segment[:-1])
            else:
                optimized_positions.extend(segment)
        
        return Trajectory(
            positions=optimized_positions,
            flight_id=f"{trajectory.flight_id}_weather_optimized"
        )
    
    def _optimize_segment_with_wind(
        self,
        start: Position,
        end: Position,
        weather: WeatherConditions,
        num_points: int
    ) -> List[Position]:
        """
        Optimise un segment de trajectoire en tenant compte du vent
        Utilise une trajectoire légèrement courbée pour profiter du vent favorable
        """
        from datetime import timedelta
        
        # Calculer le vecteur vent
        wind_vector = weather.get_wind_vector()  # [Est, Nord] en m/s
        
        # Convertir positions en cartésien
        start_cart = start.to_cartesian()
        end_cart = end.to_cartesian()
        
        # Vecteur direct
        direct_vector = end_cart - start_cart
        distance = np.linalg.norm(direct_vector[:2])  # Distance horizontale
        
        # Créer une trajectoire légèrement courbée pour profiter du vent
        # On ajoute une déviation perpendiculaire proportionnelle au vent latéral
        perpendicular = np.array([-direct_vector[1], direct_vector[0], 0])
        if np.linalg.norm(perpendicular[:2]) > 0:
            perpendicular = perpendicular / np.linalg.norm(perpendicular[:2])
        
        # Calculer la composante du vent perpendiculaire à la route
        direct_unit = direct_vector / (np.linalg.norm(direct_vector) + 1e-10)
        wind_3d = np.array([wind_vector[0], wind_vector[1], 0])
        
        # Produit scalaire pour composante parallèle
        wind_parallel = np.dot(wind_3d[:2], direct_unit[:2])
        
        # Déviation optimale pour profiter du vent (plus conservatrice)
        # Maximum 3% de déviation latérale (plus réaliste pour aviation commerciale)
        max_deviation = distance * 0.03
        wind_strength = np.linalg.norm(wind_vector)
        
        # Si vent favorable, dévier légèrement pour l'optimiser
        # Si vent défavorable, dévier légèrement pour le minimiser
        deviation_factor = np.clip(wind_parallel / 50.0, -max_deviation, max_deviation)
        perpendicular_norm = np.linalg.norm(perpendicular[:2])
        if perpendicular_norm > 1e-10:
            perpendicular = perpendicular / perpendicular_norm
        
        # Composante du vent perpendiculaire à la trajectoire
        wind_3d = np.array([wind_vector[0], wind_vector[1], 0])
        lateral_wind = np.dot(wind_3d[:2], perpendicular[:2])
        
        # Déviation maximale : 5% de la distance si vent latéral > 10 m/s
        max_deviation = 0.05 * distance * min(abs(lateral_wind) / 10.0, 1.0)
        deviation_sign = 1 if lateral_wind > 0 else -1
        
        positions: list[Position] = []
        dt_total = (end.timestamp - start.timestamp).total_seconds()
        
        for i in range(num_points):
            t = i / (num_points - 1)
            
            # Interpolation linéaire de base
            cart_pos = start_cart + t * direct_vector
            
            # Ajouter une courbure sinusoïdale pour optimiser selon le vent
            deviation = max_deviation * np.sin(np.pi * t) * deviation_sign
            cart_pos += perpendicular * deviation
            
            # Convertir en géographique avec la méthode précise
            ref_lat = (start.latitude + end.latitude) / 2
            lat, lon, alt = Position.from_cartesian(
                cart_pos[0], cart_pos[1], cart_pos[2], 
                reference_lat=ref_lat
            )
            
            # Calculer le timestamp
            timestamp = start.timestamp + timedelta(seconds=dt_total * t)
            
            # Calculer la vitesse sol en tenant compte du vent
            if i > 0:
                prev_cart = positions[-1].to_cartesian()
                dx = cart_pos[0] - prev_cart[0]
                dy = cart_pos[1] - prev_cart[1]
                dt_seg = dt_total / (num_points - 1)
                
                # Vitesse vraie
                true_speed = np.sqrt(dx**2 + dy**2) / dt_seg
                
                # Ajouter composante du vent dans direction du mouvement
                movement_dir = np.array([dx, dy]) / (np.sqrt(dx**2 + dy**2) + 1e-10)
                wind_contribution = np.dot(wind_vector, movement_dir)
                ground_speed = true_speed + wind_contribution
            else:
                ground_speed = start.ground_speed
            
            positions.append(Position(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                timestamp=timestamp,
                ground_speed=ground_speed,
                vertical_rate=(end.altitude - start.altitude) / dt_total if dt_total > 0 else 0
            ))
        
        return positions
    
    def _get_optimization_weights(self, profile: OptimizationProfile) -> Dict[str, float]:
        """
        Retourne les pondérations de la fonction objectif selon le profil choisi
        
        Args:
            profile: Profil d'optimisation
            
        Returns:
            Dictionnaire des pondérations {distance, smoothness, altitude, climb, wind}
        """
        if profile == OptimizationProfile.FUEL_SAVER:
            # Priorité: minimiser la distance (carburant)
            return {
                'distance': 0.50,      # Distance MAXIMALE (économie carburant)
                'smoothness': 0.10,    # Confort secondaire
                'altitude': 0.30,      # Réalisme modéré
                'climb': 0.50,         # Maintenir limites physiques
                'wind': 0.20           # Utiliser les vents favorables
            }
        
        elif profile == OptimizationProfile.COMFORT:
            # Priorité: confort passagers (smoothness)
            return {
                'distance': 0.01,      # Distance peu importante
                'smoothness': 0.40,    # Smoothness MAXIMALE (confort)
                'altitude': 0.50,      # Réalisme important
                'climb': 0.80,         # Taux de montée doux
                'wind': 0.01           # Vents peu importants
            }
        
        else:  # OptimizationProfile.BALANCED (défaut)
            # Équilibre entre tous les critères (config actuelle)
            return {
                'distance': 0.01,      # Distance faible
                'smoothness': 0.30,    # Confort moyen
                'altitude': 0.50,      # Réalisme important
                'climb': 0.80,         # Limites physiques critiques
                'wind': 0.05           # Bonus vents
            }
    
    def _optimize_direct_collocation(
        self,
        trajectory: Trajectory,
        target_points: Optional[int],
        use_weather: bool = False
    ) -> Trajectory:
        """
        Optimisation directe par collocation (NLP)
        Résout un problème d'optimisation non-linéaire pour minimiser:
        - Le temps de vol
        - La consommation de carburant (approximée par la distance)
        - Les écarts de vitesse/accélération
        
        Contraintes:
        - Position de départ et d'arrivée fixées
        - Limites d'altitude (min/max)
        - Limites d'accélération
        - Continuité de la trajectoire
        """
        from scipy.optimize import minimize, Bounds  # type: ignore
        from datetime import timedelta
        
        print("  Optimisation directe par collocation (NLP)...")
        
        # Nombre de points de collocation
        n_points = target_points if target_points else 50
        n_points = max(10, min(n_points, 100))  # Entre 10 et 100
        
        # Lisser d'abord la trajectoire avec Kalman pour avoir une estimation initiale
        smoothed = self.kalman.smooth_trajectory(trajectory)
        
        # Garder les premiers 10% de la trajectoire intacts (phase de décollage/montée)
        takeoff_phase_length = max(5, len(smoothed) // 10)
        takeoff_positions = smoothed.positions[:takeoff_phase_length]
        
        # Créer une trajectoire à partir du point de fin de décollage
        cruise_trajectory = Trajectory(
            positions=smoothed.positions[takeoff_phase_length:],
            flight_id=smoothed.flight_id
        )
        
        # Points de départ et d'arrivée pour la phase de croisière
        start_pos = cruise_trajectory.positions[0]
        end_pos = cruise_trajectory.positions[-1]
        
        print(f"  Phase décollage: {takeoff_phase_length} points conservés")
        
        # Durée totale de la phase de croisière
        total_time = (end_pos.timestamp - start_pos.timestamp).total_seconds()
        
        # Convertir en cartésien pour l'optimisation
        start_cart = start_pos.to_cartesian()
        end_cart = end_pos.to_cartesian()
        
        # Ajuster le nombre de points pour la phase de croisière
        # AMÉLIORATION: Plus de points pour meilleure précision
        n_cruise = max(50, min(n_points - takeoff_phase_length, 200))  # Entre 50 et 200 points
        
        # Utiliser la trajectoire lissée comme estimation initiale (bien meilleure qu'interpolation linéaire)
        # Créer des indices pour échantillonner la trajectoire de croisière
        cruise_indices = np.linspace(0, len(cruise_trajectory) - 1, n_cruise, dtype=int)
        cruise_points = [cruise_trajectory.positions[i].to_cartesian() for i in cruise_indices]
        cruise_points_array = np.array(cruise_points)
        
        # Variables d'optimisation: points intermédiaires (exclure début et fin)
        n_vars = (n_cruise - 2) * 3
        
        # Estimation initiale depuis la trajectoire lissée
        x0 = cruise_points_array[1:-1].flatten()  # Exclure premier et dernier point
        
        # Stocker les points de référence pour les contraintes
        ref_points = cruise_points_array
        
        # Obtenir les pondérations selon le profil d'optimisation choisi
        weights = self._get_optimization_weights(self.optimization_profile)
        print(f"  Profil d'optimisation: {self.optimization_profile.value}")
        print(f"  Pondérations: distance={weights['distance']:.2f}, smoothness={weights['smoothness']:.2f}, "
              f"altitude={weights['altitude']:.2f}, climb={weights['climb']:.2f}, wind={weights['wind']:.2f}")
        
        # Fonction objectif
        def objective(x):
            """
            Minimiser: 
            1. Distance totale (économie de carburant)
            2. Variations d'accélération (confort et usure)
            3. Vent contraire (temps de vol)
            4. Écart par rapport au profil d'altitude de référence
            """
            # Reconstruire tous les points (départ + intermédiaires + arrivée)
            all_points = np.zeros((n_cruise, 3))
            all_points[0] = start_cart
            all_points[-1] = end_cart
            
            for i in range(n_cruise - 2):
                all_points[i + 1] = x[i*3:(i+1)*3]
            
            # 1. Distance totale
            distances = np.sqrt(np.sum(np.diff(all_points, axis=0)**2, axis=1))
            total_distance = np.sum(distances)
            
            # 2. Pénalité pour variations d'accélération (smoothness)
            acceleration_penalty = 0
            if n_cruise >= 3:
                # Différences secondes (approximation de l'accélération)
                second_diff = np.diff(all_points, n=2, axis=0)
                acceleration_penalty = np.sum(second_diff**2) * 50
            
            # 3. Pénalité pour profil d'altitude non réaliste
            # Calculer l'écart par rapport au profil de référence (trajectoire lissée)
            altitude_penalty = 0
            for i in range(n_cruise):
                # Écart vertical par rapport à la trajectoire de référence
                alt_diff = all_points[i, 2] - ref_points[i, 2]
                # Pénaliser les écarts d'altitude importants
                altitude_penalty += alt_diff**2 * 0.5
            
            # 4. Pénalité pour taux de montée/descente excessif
            climb_penalty = 0
            max_climb_rate = 15.0  # m/s maximum (≈3000 ft/min)
            for i in range(len(distances)):
                if distances[i] > 0:
                    # Calculer le temps de segment (approximation)
                    avg_speed = 250.0  # m/s (≈900 km/h vitesse de croisière typique)
                    dt = distances[i] / avg_speed
                    
                    # Taux de montée/descente
                    dz = all_points[i + 1, 2] - all_points[i, 2]
                    climb_rate = abs(dz / dt) if dt > 0 else 0
                    
                    # Pénaliser si dépasse le taux max
                    if climb_rate > max_climb_rate:
                        climb_penalty += (climb_rate - max_climb_rate)**2 * 2000
            
            # 5. Pénalité pour vent contraire (si météo activée)
            wind_penalty = 0
            if use_weather:
                # Latitude de référence pour les conversions
                ref_lat = (start_pos.latitude + end_pos.latitude) / 2
                
                for i in range(len(all_points) - 1):
                    # Position cartésienne → géographique
                    lat1, lon1, alt1 = Position.from_cartesian(
                        all_points[i, 0], all_points[i, 1], all_points[i, 2],
                        reference_lat=ref_lat
                    )
                    
                    # Obtenir le vent
                    weather = self.weather_api.get_weather(lat1, lon1, alt1)
                    wind_vector = weather.get_wind_vector()
                    
                    # Direction du mouvement
                    movement = all_points[i + 1] - all_points[i]
                    movement_2d = movement[:2]
                    
                    if np.linalg.norm(movement_2d) > 0:
                        movement_2d_norm = movement_2d / np.linalg.norm(movement_2d)
                        # Composante du vent dans la direction du mouvement
                        wind_effect = -np.dot(wind_vector, movement_2d_norm)
                        # Pénaliser le vent contraire
                        if wind_effect > 0:
                            wind_penalty += wind_effect * distances[i] * 0.05
            
            # Fonction objectif pondérée selon le profil d'optimisation
            # Les pondérations proviennent du profil choisi (FUEL_SAVER, COMFORT, BALANCED)
            total_cost = (
                total_distance * weights['distance'] +       # Distance (varie selon profil)
                acceleration_penalty * weights['smoothness'] +  # Smoothness (confort)
                altitude_penalty * weights['altitude'] +     # Altitude (réalisme)
                climb_penalty * weights['climb'] +           # Climb rate (limites physiques)
                wind_penalty * weights['wind']               # Vent (efficacité)
            )
            
            return total_cost
        
        # Contraintes sur les limites d'altitude et positions
        # Altitude: utiliser les altitudes de la trajectoire de référence avec une marge
        alt_margin = 1500  # ±1500m de marge autour de la trajectoire de référence
        
        # Créer les bornes pour chaque variable
        bounds_list = []
        for i in range(n_cruise - 2):
            idx = i + 1  # Index dans ref_points
            
            # Bornes pour x (±100km autour de la position de référence)
            x_ref = ref_points[idx, 0]
            bounds_list.append((x_ref - 100000, x_ref + 100000))
            
            # Bornes pour y (±100km autour de la position de référence)
            y_ref = ref_points[idx, 1]
            bounds_list.append((y_ref - 100000, y_ref + 100000))
            
            # Bornes pour z (altitude): ±1500m autour de la référence
            z_ref = ref_points[idx, 2]
            bounds_list.append((max(0, z_ref - alt_margin), z_ref + alt_margin))
        
        # Créer les bornes inférieures et supérieures
        lb = np.array([b[0] for b in bounds_list])
        ub = np.array([b[1] for b in bounds_list])
        bounds = Bounds(lb, ub)  # type: ignore
        
        # Options d'optimisation (AMÉLIORÉ pour meilleure précision)
        options = {
            'maxiter': 500,  # Plus d'itérations pour convergence complète
            'disp': False,
            'ftol': 1e-9,  # Tolérance très stricte pour précision maximale
            'eps': 1e-8  # Pas plus petit pour gradients numériques plus précis
        }
        
        print(f"  Résolution du problème NLP avec {n_cruise} points de collocation...")
        print(f"  Contraintes: altitude ±{alt_margin}m, position ±100km")
        
        # Résoudre le problème d'optimisation
        result = minimize(
            objective,
            x0,
            method='SLSQP',  # Sequential Least Squares Programming
            bounds=bounds,
            options=options
        )
        
        if not result.success:
            print(f"  Avertissement: convergence partielle ({result.message})")
        else:
            print(f"  ✓ Convergence réussie")
        
        # Reconstruire la trajectoire optimisée
        # Commencer avec les positions de décollage
        optimized_positions = list(takeoff_positions)
        
        # Latitude de référence pour la conversion
        ref_lat = (start_pos.latitude + end_pos.latitude) / 2
        ref_lat_rad = ref_lat * np.pi / 180
        
        # Convertir les variables optimisées en positions (phase de croisière)
        for i in range(n_cruise - 2):
            x_cart = result.x[i*3:(i+1)*3]
            
            # Convertir cartésien → géographique avec la méthode précise
            lat, lon, alt = Position.from_cartesian(
                x_cart[0], x_cart[1], x_cart[2],
                reference_lat=ref_lat
            )
            
            # Interpoler le timestamp
            alpha = (i + 1) / (n_cruise - 1)
            timestamp = start_pos.timestamp + timedelta(seconds=total_time * alpha)
            
            optimized_positions.append(Position(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                timestamp=timestamp
            ))
        
        optimized_positions.append(end_pos)
        
        print(f"  Réduction objectif: {objective(x0):.1f} → {result.fun:.1f}")
        
        return Trajectory(
            positions=optimized_positions,
            flight_id=f"{trajectory.flight_id}_nlp_optimized"
        )
    
    def _validate_optimization_result(
        self,
        original: Trajectory,
        optimized: Trajectory,
        method: OptimizationMethod
    ) -> None:
        """
        Valide le résultat de l'optimisation avec des seuils spécifiques par méthode
        
        Args:
            original: Trajectoire originale
            optimized: Trajectoire optimisée
            method: Méthode d'optimisation utilisée
        """
        warnings = []
        
        # 1. Validation de la distance (seuils par méthode)
        dist_original = original.get_cumulative_distances()[-1] / 1000.0  # Convertir en km
        dist_optimized = optimized.get_cumulative_distances()[-1] / 1000.0  # Convertir en km
        
        if dist_original > 0:
            dist_variation_pct = 100.0 * abs(dist_optimized - dist_original) / dist_original
            
            # Seuils spécifiques par méthode
            distance_thresholds = {
                OptimizationMethod.KALMAN: 0.5,      # ±0.5% attendu
                OptimizationMethod.BSPLINE: 1.0,     # ±1.0% avec preserve_distance=True
                OptimizationMethod.HYBRID: 0.5,      # ±0.5% (Kalman + B-spline strict)
                OptimizationMethod.WEATHER: 5.0,     # ±5.0% (peut modifier trajectoire)
                OptimizationMethod.DIRECT_COLLOCATION: 3.0  # ±3.0% (optimisation NLP)
            }
            
            threshold = distance_thresholds.get(method, 2.0)
            
            if dist_variation_pct > threshold:
                warnings.append(
                    f"Distance: {dist_variation_pct:.2f}% de variation "
                    f"(seuil {method.value}: {threshold}%) - "
                    f"{dist_original:.1f} km → {dist_optimized:.1f} km"
                )
        
        # 2. Validation des altitudes (0-15000m pour aviation commerciale)
        altitudes = np.array([pos.altitude for pos in optimized.positions])
        
        if np.any(altitudes < 0):
            min_alt = np.min(altitudes)
            warnings.append(f"Altitude négative détectée: {min_alt:.1f}m")
        
        if np.any(altitudes > 15000):
            max_alt = np.max(altitudes)
            warnings.append(f"Altitude excessive détectée: {max_alt:.1f}m (limite: 15000m)")
        
        # 3. Validation du taux de montée (<15 m/s pour A320neo)
        timestamps = optimized.get_timestamps()
        if len(timestamps) > 1:
            dt = np.diff(timestamps)
            dh = np.diff(altitudes)
            climb_rates = np.abs(dh / (dt + 1e-6))
            max_climb_rate = np.max(climb_rates)
            
            if max_climb_rate > 15.0:
                warnings.append(
                    f"Taux de montée excessif: {max_climb_rate:.1f} m/s "
                    f"(limite A320neo: 15 m/s)"
                )
        
        # 4. Validation des forces G (calcul approximatif)
        # G-force latérale basée sur la courbure et la vitesse
        coords = optimized.get_cartesian_array()
        if len(coords) > 2:
            velocities = []
            for i in range(1, len(coords)):
                dt = timestamps[i] - timestamps[i-1]
                if dt > 0:
                    dx = coords[i] - coords[i-1]
                    v = np.linalg.norm(dx) / dt
                    velocities.append(v)
            
            if velocities:
                avg_velocity = np.mean(velocities)
                
                # Calculer la courbure approximative
                for i in range(1, len(coords) - 1):
                    # Vecteurs entre points successifs
                    v1 = coords[i] - coords[i-1]
                    v2 = coords[i+1] - coords[i]
                    
                    # Angle de virage
                    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10)
                    cos_angle = np.clip(cos_angle, -1.0, 1.0)
                    angle = np.arccos(cos_angle)
                    
                    # Rayon de courbure approximatif
                    segment_length = (np.linalg.norm(v1) + np.linalg.norm(v2)) / 2
                    if angle > 0.01:  # Éviter division par zéro
                        radius = segment_length / angle
                        
                        # Force centrifuge: a = v²/r, g = a/9.81
                        if radius > 10:  # Éviter rayons trop petits
                            lateral_g = (avg_velocity ** 2) / (radius * 9.81)
                            
                            if lateral_g > 1.5:
                                warnings.append(
                                    f"Force G excessive détectée: {lateral_g:.2f}g "
                                    f"(limite confort: 1.5g)"
                                )
                                break  # Un avertissement suffit
        
        # Afficher les avertissements
        if warnings:
            print("\n⚠️  AVERTISSEMENTS DE VALIDATION:")
            for warning in warnings:
                print(f"   • {warning}")
            print()
        else:
            print("✓ Validation réussie: résultat conforme aux contraintes physiques")
    
    def _compute_metrics(
        self,
        original: Trajectory,
        optimized: Trajectory,
        use_weather: bool
    ) -> Dict:
        """
        Calcule les métriques d'optimisation (version améliorée avec métriques avancées)
        
        Args:
            original: Trajectoire originale
            optimized: Trajectoire optimisée
            use_weather: Si les données météo ont été utilisées
            
        Returns:
            Dictionnaire de métriques
        """
        metrics = {}
        
        # Réduction du nombre de points
        metrics['compression_ratio'] = len(optimized) / len(original)
        
        # Calcul de la smoothness (lissage)
        metrics['smoothness'] = self._compute_smoothness(optimized)
        metrics['original_smoothness'] = self._compute_smoothness(original)
        
        # Distance totale
        orig_dist = self._compute_total_distance(original)
        opt_dist = self._compute_total_distance(optimized)
        metrics['distance_original'] = orig_dist
        metrics['distance_optimized'] = opt_dist
        metrics['distance_change_percent'] = ((opt_dist - orig_dist) / orig_dist) * 100
        
        # ========== NOUVELLES MÉTRIQUES AVANCÉES ==========
        
        # Consommation de carburant estimée
        metrics['fuel_consumption_kg'] = self._estimate_fuel_consumption(optimized)
        metrics['fuel_consumption_original_kg'] = self._estimate_fuel_consumption(original)
        fuel_saving = metrics['fuel_consumption_original_kg'] - metrics['fuel_consumption_kg']
        metrics['fuel_saving_kg'] = fuel_saving
        metrics['fuel_saving_percent'] = (fuel_saving / metrics['fuel_consumption_original_kg']) * 100
        
        # Facteur de charge (G-force) maximal
        metrics['max_g_force'] = self._compute_max_g_force(optimized)
        metrics['avg_g_force'] = self._compute_avg_g_force(optimized)
        
        # Temps de vol réel (avec vent si météo activée)
        if use_weather:
            metrics['flight_time_seconds'] = self._compute_flight_time_with_wind(optimized)
            metrics['flight_time_original_seconds'] = self._compute_flight_time_with_wind(original)
            time_saving = metrics['flight_time_original_seconds'] - metrics['flight_time_seconds']
            metrics['time_saving_seconds'] = time_saving
            metrics['time_saving_percent'] = (time_saving / metrics['flight_time_original_seconds']) * 100
        else:
            metrics['flight_time_seconds'] = optimized.duration
            metrics['flight_time_original_seconds'] = original.duration
        
        # Taux de montée/descente
        climb_rates = self._compute_climb_rates(optimized)
        metrics['max_climb_rate_ms'] = float(np.max(np.abs(climb_rates)))
        metrics['avg_climb_rate_ms'] = float(np.mean(np.abs(climb_rates)))
        
        # Qualité de la trajectoire
        metrics['curvature_max'] = self._compute_max_curvature(optimized)
        metrics['curvature_avg'] = self._compute_avg_curvature(optimized)
        
        return metrics
    
    def _compute_smoothness(self, trajectory: Trajectory) -> float:
        """
        Calcule un indice de lissage (plus bas = plus lisse)
        Basé sur la variation d'accélération
        """
        cartesian = trajectory.get_cartesian_array()
        
        # Calculer les accélérations
        velocity = np.diff(cartesian, axis=0)
        acceleration = np.diff(velocity, axis=0)
        
        # Jerk (dérivée de l'accélération)
        jerk = np.diff(acceleration, axis=0)
        
        # Métrique : norme moyenne du jerk (plus bas = plus lisse)
        smoothness = np.mean(np.linalg.norm(jerk, axis=1))
        
        return float(smoothness)
    
    def _compute_total_distance(self, trajectory: Trajectory) -> float:
        """Calcule la distance totale parcourue en mètres"""
        cartesian = trajectory.get_cartesian_array()
        distances = np.linalg.norm(np.diff(cartesian, axis=0), axis=1)
        return float(np.sum(distances))
    
    def _estimate_fuel_savings(self, trajectory: Trajectory, metrics: Optional[Dict] = None) -> float:
        """
        Estime les économies de carburant en %
        (Modèle très simplifié)
        """
        # Cette estimation serait beaucoup plus complexe dans un cas réel
        # Elle nécessiterait un modèle de performance de l'avion
        
        # Pour l'instant, on suppose que toute réduction de distance
        # se traduit par des économies proportionnelles
        if metrics is None:
            metrics = {}
        smoothness_factor = min(100, metrics.get('smoothness', 100))
        
        # Moins de manœuvres brusques = économies
        savings = max(0, (100 - smoothness_factor) * 0.1)
        
        return float(savings)
    
    def _estimate_fuel_consumption(self, trajectory: Trajectory, aircraft_type: str = "A320") -> float:
        """
        Estime la consommation de carburant réaliste en kg
        Modèle corrigé - indépendant du nombre de points
        
        Prend en compte:
        - Distance totale parcourue
        - Temps de vol par phase (montée/croisière/descente)
        - Altitude moyenne de croisière
        - Caractéristiques de la trajectoire (virages, smoothness)
        """
        # Paramètres réalistes A320neo
        aircraft_params = {
            "A320": {
                # Consommation spécifique (kg/h) par phase
                "fuel_flow_cruise": 2400,  # kg/h en croisière
                "fuel_flow_climb": 3200,   # kg/h en montée
                "fuel_flow_descent": 800,  # kg/h en descente (ralenti)
                
                # Consommation de base par distance (kg/km)
                "base_sfc": 3.5,  # Consommation spécifique de croisière
                
                # Facteurs correctifs
                "altitude_efficiency": {
                    "low": 1.10,      # < 6000m : +10% consommation
                    "medium": 1.0,    # 6000-12000m : optimal
                    "high": 1.03      # > 12000m : +3% consommation
                },
                "smoothness_factor": 0.05,  # Impact du lissage sur la consommation
                "curvature_penalty": 100.0,  # Pénalité par unité de courbure moyenne
            }
        }
        
        params = aircraft_params[aircraft_type]
        
        # ============ MÉTHODE CORRIGÉE : BASÉE SUR TEMPS ET DISTANCE TOTALE ============
        
        # 1. CALCULER LA DISTANCE TOTALE EN 3D
        total_distance_km = self._compute_total_distance(trajectory) / 1000  # en km
        
        # 2. CALCULER LE TEMPS PAR PHASE DE VOL
        time_climb = 0.0
        time_cruise = 0.0
        time_descent = 0.0
        
        altitudes = []
        
        for i in range(len(trajectory) - 1):
            pos1 = trajectory.positions[i]
            pos2 = trajectory.positions[i+1]
            
            alt_diff = pos2.altitude - pos1.altitude
            dt = (pos2.timestamp - pos1.timestamp).total_seconds() / 3600  # en heures
            
            avg_altitude = (pos1.altitude + pos2.altitude) / 2
            altitudes.append(avg_altitude)
            
            if alt_diff > 50:  # Montée
                time_climb += dt
            elif alt_diff < -50:  # Descente
                time_descent += dt
            else:  # Croisière
                time_cruise += dt
        
        # 3. CONSOMMATION DE BASE PAR PHASE (basée sur le temps)
        fuel_by_phase = (
            time_climb * float(params["fuel_flow_climb"]) +  # type: ignore
            time_cruise * float(params["fuel_flow_cruise"]) +  # type: ignore
            time_descent * float(params["fuel_flow_descent"])  # type: ignore
        )
        
        # 4. FACTEUR D'ALTITUDE MOYEN
        avg_altitude = float(np.mean(altitudes)) if altitudes else 8000.0
        altitude_efficiency = params["altitude_efficiency"]
        
        if avg_altitude < 6000:
            alt_factor = float(altitude_efficiency["low"])  # type: ignore
        elif avg_altitude < 12000:
            alt_factor = float(altitude_efficiency["medium"])  # type: ignore
        else:
            alt_factor = float(altitude_efficiency["high"])  # type: ignore
        
        # Appliquer le facteur d'altitude
        fuel_with_altitude = fuel_by_phase * alt_factor
        
        # 5. PÉNALITÉ POUR COURBURE EXCESSIVE (virages)
        # Plus la trajectoire est courbée, plus elle consomme (traînée induite)
        avg_curvature = self._compute_avg_curvature(trajectory)
        curvature_penalty = avg_curvature * float(params["curvature_penalty"]) * total_distance_km  # type: ignore
        
        # 6. PÉNALITÉ POUR MANQUE DE SMOOTHNESS
        # Une trajectoire avec beaucoup de variations consomme plus
        smoothness = self._compute_smoothness(trajectory)
        # Smoothness élevé = mauvais → pénalité
        smoothness_penalty = (smoothness / 100.0) * float(params["smoothness_factor"]) * fuel_by_phase  # type: ignore
        
        # 7. FACTEUR DE CHARGE (G-forces)
        # Des G-forces élevées = plus de traînée induite
        avg_g = self._compute_avg_g_force(trajectory)
        g_penalty = max(0, (avg_g - 1.0)) * 0.10 * fuel_by_phase  # 10% par G supplémentaire
        
        # TOTAL = base + pénalités
        total_fuel = fuel_with_altitude + curvature_penalty + smoothness_penalty + g_penalty
        
        # Limite de sécurité : jamais moins de 2 kg/km, jamais plus de 6 kg/km
        min_fuel = total_distance_km * 2.0
        max_fuel = total_distance_km * 6.0
        total_fuel = np.clip(total_fuel, min_fuel, max_fuel)
        
        return float(total_fuel)
    
    def _compute_max_g_force(self, trajectory: Trajectory) -> float:
        """
        Calcule le facteur de charge maximal (G-force) de manière réaliste
        
        Prend en compte :
        - Accélération centripète dans les virages
        - Accélération tangentielle
        - Composante gravitationnelle
        """
        cartesian = trajectory.get_cartesian_array()
        timestamps = trajectory.get_timestamps()
        
        max_g = 1.0  # Au minimum 1G (gravité au sol)
        
        for i in range(1, len(cartesian) - 1):
            dt1 = timestamps[i] - timestamps[i-1]
            dt2 = timestamps[i+1] - timestamps[i]
            
            if dt1 <= 0 or dt2 <= 0:
                continue
            
            # Vecteurs vitesse
            v1 = (cartesian[i] - cartesian[i-1]) / dt1
            v2 = (cartesian[i+1] - cartesian[i]) / dt2
            
            # Vitesse moyenne au point i
            v_avg = (v1 + v2) / 2
            v_speed = np.linalg.norm(v_avg)
            
            if v_speed < 10:  # Ignorer les vitesses très faibles
                continue
            
            # Accélération totale (changement de vitesse)
            dt_avg = (dt1 + dt2) / 2
            accel = (v2 - v1) / dt_avg
            
            # Composantes de l'accélération
            # 1. Accélération tangentielle (dans la direction du mouvement)
            v_unit = v_avg / v_speed
            accel_tangential = np.dot(accel, v_unit)
            
            # 2. Accélération normale (perpendiculaire, dans les virages)
            accel_normal_vec = accel - accel_tangential * v_unit
            accel_normal = np.linalg.norm(accel_normal_vec)
            
            # 3. Facteur de charge dans le plan horizontal (virages)
            # n = sqrt(1 + (a_n / g)²) pour virages coordonnés
            # Simplifié : n ≈ 1 + a_n / g pour petits angles
            g_lateral = accel_normal / 9.81
            
            # 4. Facteur de charge vertical (montée/descente)
            # Composante verticale de l'accélération
            accel_vertical = abs(accel[2]) / 9.81
            
            # 5. Facteur de charge total (combinaison vectorielle)
            # En vol, le facteur de charge ressenti combine :
            # - La gravité (1G vers le bas)
            # - L'accélération centripète (virages)
            # - L'accélération tangentielle (accélérations)
            
            # Approximation : g_total = sqrt(1² + g_lateral² + g_vertical²)
            g_force = np.sqrt(1.0 + g_lateral**2 + accel_vertical**2)
            
            max_g = max(max_g, g_force)
        
        return float(max_g)
    
    def _compute_avg_g_force(self, trajectory: Trajectory) -> float:
        """
        Calcule le facteur de charge moyen de manière réaliste
        """
        cartesian = trajectory.get_cartesian_array()
        timestamps = trajectory.get_timestamps()
        
        g_forces = []
        
        for i in range(1, len(cartesian) - 1):
            dt1 = timestamps[i] - timestamps[i-1]
            dt2 = timestamps[i+1] - timestamps[i]
            
            if dt1 <= 0 or dt2 <= 0:
                continue
            
            # Vecteurs vitesse
            v1 = (cartesian[i] - cartesian[i-1]) / dt1
            v2 = (cartesian[i+1] - cartesian[i]) / dt2
            
            v_avg = (v1 + v2) / 2
            v_speed = np.linalg.norm(v_avg)
            
            if v_speed < 10:
                continue
            
            # Accélération
            dt_avg = (dt1 + dt2) / 2
            accel = (v2 - v1) / dt_avg
            
            # Composantes
            v_unit = v_avg / v_speed
            accel_tangential = np.dot(accel, v_unit)
            accel_normal_vec = accel - accel_tangential * v_unit
            accel_normal = np.linalg.norm(accel_normal_vec)
            
            g_lateral = accel_normal / 9.81
            accel_vertical = abs(accel[2]) / 9.81
            
            g_force = np.sqrt(1.0 + g_lateral**2 + accel_vertical**2)
            g_forces.append(g_force)
        
        return float(np.mean(g_forces)) if g_forces else 1.0
    
    def _compute_flight_time_with_wind(self, trajectory: Trajectory) -> float:
        """
        Calcule le temps de vol réel en tenant compte du vent
        """
        total_time = 0.0
        avg_speed = 240.0  # m/s (vitesse air typique)
        
        for i in range(len(trajectory) - 1):
            pos1 = trajectory.positions[i]
            pos2 = trajectory.positions[i+1]
            
            # Distance 3D
            cart1 = pos1.to_cartesian()
            cart2 = pos2.to_cartesian()
            distance = np.linalg.norm(cart2 - cart1)
            
            # Obtenir vent au point milieu
            mid_lat = (pos1.latitude + pos2.latitude) / 2
            mid_lon = (pos1.longitude + pos2.longitude) / 2
            mid_alt = (pos1.altitude + pos2.altitude) / 2
            
            weather = self.weather_api.get_weather(mid_lat, mid_lon, mid_alt)
            wind_vector = weather.get_wind_vector()
            
            # Direction du mouvement
            movement = (cart2 - cart1)[:2]
            if np.linalg.norm(movement) > 0:
                movement_norm = movement / np.linalg.norm(movement)
                # Composante du vent dans la direction du mouvement
                wind_component = np.dot(wind_vector, movement_norm)
            else:
                wind_component = 0
            
            # Vitesse sol = vitesse air + vent
            ground_speed = avg_speed + wind_component
            ground_speed = max(50, ground_speed)  # Vitesse minimale
            
            # Temps du segment
            segment_time = distance / ground_speed
            total_time += segment_time
        
        return float(total_time)
    
    def _compute_climb_rates(self, trajectory: Trajectory) -> np.ndarray:
        """
        Calcule les taux de montée/descente (m/s)
        """
        climb_rates = []
        
        for i in range(len(trajectory) - 1):
            alt_diff = trajectory.positions[i+1].altitude - trajectory.positions[i].altitude
            time_diff = (trajectory.positions[i+1].timestamp - trajectory.positions[i].timestamp).total_seconds()
            
            if time_diff > 0:
                climb_rate = alt_diff / time_diff
                climb_rates.append(climb_rate)
        
        return np.array(climb_rates)
    
    def _compute_max_curvature(self, trajectory: Trajectory) -> float:
        """
        Calcule la courbure maximale de la trajectoire
        """
        cartesian = trajectory.get_cartesian_array()
        
        if len(cartesian) < 3:
            return 0.0
        
        # Première et seconde dérivées
        first_deriv = np.diff(cartesian, axis=0)
        second_deriv = np.diff(first_deriv, axis=0)
        
        curvatures = []
        for i in range(len(second_deriv)):
            # Curvature = ||r' x r''|| / ||r'||^3
            v = first_deriv[i]
            a = second_deriv[i]
            
            v_norm = np.linalg.norm(v)
            if v_norm > 0:
                cross = np.cross(v, a)
                curvature = np.linalg.norm(cross) / (v_norm ** 3)
                curvatures.append(curvature)
        
        return float(np.max(curvatures)) if curvatures else 0.0
    
    def _compute_avg_curvature(self, trajectory: Trajectory) -> float:
        """
        Calcule la courbure moyenne de la trajectoire
        """
        cartesian = trajectory.get_cartesian_array()
        
        if len(cartesian) < 3:
            return 0.0
        
        # Première et seconde dérivées
        first_deriv = np.diff(cartesian, axis=0)
        second_deriv = np.diff(first_deriv, axis=0)
        
        curvatures = []
        for i in range(len(second_deriv)):
            v = first_deriv[i]
            a = second_deriv[i]
            
            v_norm = np.linalg.norm(v)
            if v_norm > 0:
                cross = np.cross(v, a)
                curvature = np.linalg.norm(cross) / (v_norm ** 3)
                curvatures.append(curvature)
        
        return float(np.mean(curvatures)) if curvatures else 0.0
    
    def visualize_optimization(
        self,
        optimized_traj: OptimizedTrajectory,
        output_file: Optional[str] = None
    ):
        """
        Visualise la comparaison original vs optimisé
        
        Args:
            optimized_traj: Trajectoire optimisée
            output_file: Fichier de sortie (None = affichage)
        """
        try:
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D  # type: ignore
            
            fig = plt.figure(figsize=(15, 5))
            
            # Trajectoires 3D
            ax1 = fig.add_subplot(131, projection='3d')
            
            orig_cart = optimized_traj.original.get_cartesian_array()
            opt_cart = np.array([
                pos.to_cartesian() for pos in optimized_traj.optimized_positions
            ])
            
            ax1.plot(orig_cart[:, 0], orig_cart[:, 1], orig_cart[:, 2],
                    'b.-', label='Original', alpha=0.6)
            ax1.plot(opt_cart[:, 0], opt_cart[:, 1], opt_cart[:, 2],
                    'r-', label='Optimisé', linewidth=2)
            ax1.set_xlabel('X (m)')
            ax1.set_ylabel('Y (m)')
            ax1.set_zlabel('Altitude (m)')
            ax1.legend()
            ax1.set_title('Trajectoires 3D')
            
            # Profil d'altitude
            ax2 = fig.add_subplot(132)
            orig_ts = optimized_traj.original.get_timestamps()
            opt_ts = np.array([
                (pos.timestamp - optimized_traj.optimized_positions[0].timestamp).total_seconds()
                for pos in optimized_traj.optimized_positions
            ])
            
            ax2.plot(orig_ts, orig_cart[:, 2], 'b.-', label='Original', alpha=0.6)
            ax2.plot(opt_ts, opt_cart[:, 2], 'r-', label='Optimisé', linewidth=2)
            ax2.set_xlabel('Temps (s)')
            ax2.set_ylabel('Altitude (m)')
            ax2.legend()
            ax2.set_title('Profil d\'altitude')
            ax2.grid(True)
            
            # Métriques
            ax3 = fig.add_subplot(133)
            ax3.axis('off')
            
            metrics_text = f"Méthode: {optimized_traj.method}\n\n"
            metrics_text += "Métriques:\n"
            for key, value in optimized_traj.metrics.items():
                if isinstance(value, float):
                    metrics_text += f"  {key}: {value:.2f}\n"
                else:
                    metrics_text += f"  {key}: {value}\n"
            
            ax3.text(0.1, 0.5, metrics_text, fontfamily='monospace',
                    fontsize=10, verticalalignment='center')
            ax3.set_title('Métriques d\'optimisation')
            
            plt.tight_layout()
            
            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                print(f"Visualisation sauvegardée : {output_file}")
            else:
                plt.show()
            
        except ImportError:
            print("Matplotlib non disponible pour la visualisation")
