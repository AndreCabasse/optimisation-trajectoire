"""
Interpolation et optimisation par B-spline
"""
import numpy as np
from scipy import interpolate  # type: ignore
from typing import List, Tuple, Optional, Any
from datetime import datetime

from ..data.data_models import Position, Trajectory


class BSplineOptimizer:
    """
    Optimisation de trajectoires par B-splines
    """
    
    def __init__(
        self,
        degree: int = 3,
        smoothing_factor: Optional[float] = None,
        num_control_points: Optional[int] = None,
        preserve_endpoints: bool = True,
        auto_smooth: bool = True,
        preserve_distance: bool = True
    ):
        """
        Initialise l'optimiseur B-spline
        
        Args:
            degree: Degré de la B-spline (3 = cubique par défaut)
            smoothing_factor: Facteur de lissage (None = détection auto via validation croisée)
            num_control_points: Nombre de points de contrôle (None = auto)
            preserve_endpoints: Garantir le passage exact par les points de départ/arrivée
            auto_smooth: Déterminer automatiquement le meilleur smoothing par CV
            preserve_distance: Force l'interpolation exacte (smoothing=0) pour préserver la distance
                               Recommandé pour éviter que le lissage coupe artificiellement les virages
        """
        self.degree = degree
        self.preserve_distance = preserve_distance
        
        # Si preserve_distance activé, forcer smoothing à 0 pour interpolation exacte
        if self.preserve_distance:
            if smoothing_factor is not None and smoothing_factor > 0:
                print(f"⚠️  Warning: preserve_distance=True force smoothing_factor=0 (ignoré: {smoothing_factor})")
            self.smoothing_factor = 0.0
            self.auto_smooth = False  # Désactiver la détection auto
        else:
            self.smoothing_factor = smoothing_factor  # type: ignore
            self.auto_smooth = auto_smooth
        
        self.num_control_points = num_control_points
        self.preserve_endpoints = preserve_endpoints
        
        self.splines: Optional[List[Any]] = None  # Stocke les splines (x, y, z)
        self.t_min: Optional[float] = None  # Timestamp minimum utilisé pour fit
        self.t_max: Optional[float] = None  # Timestamp maximum utilisé pour fit
    
    def _estimate_optimal_smoothing(self, coords: np.ndarray, t_norm: np.ndarray) -> float:
        """
        Estime le facteur de lissage optimal par validation croisée
        Teste plusieurs valeurs et choisit celle qui minimise l'erreur de prédiction
        
        Args:
            coords: Coordonnées cartésiennes [N, 3]
            t_norm: Temps normalisés [N]
            
        Returns:
            Facteur de lissage optimal
        """
        # Valeurs candidates de smoothing à tester
        candidates = [0.0, 0.1, 0.3, 0.5, 1.0, 2.0, 5.0]
        
        # Utiliser 10% des points pour validation
        n_points = len(coords)
        n_val = max(5, n_points // 10)
        
        # Indices de validation (échantillonnage uniforme)
        val_indices = np.linspace(0, n_points - 1, n_val, dtype=int)
        train_mask = np.ones(n_points, dtype=bool)
        train_mask[val_indices] = False
        
        best_error = float('inf')
        best_smooth = 0.5  # Valeur par défaut
        
        for smooth_val in candidates:
            total_error = 0.0
            
            try:
                # Pour chaque dimension
                for dim in range(3):
                    # Ajuster sur les données d'entraînement
                    tck = interpolate.splrep(
                        t_norm[train_mask],
                        coords[train_mask, dim],
                        k=self.degree,
                        s=smooth_val if smooth_val > 0 else 0
                    )
                    
                    # Prédire sur les données de validation
                    predictions = interpolate.splev(t_norm[val_indices], tck)
                    actuals = coords[val_indices, dim]
                    
                    # Erreur quadratique moyenne
                    error = np.mean((predictions - actuals) ** 2)
                    total_error += error
                
                # Erreur moyenne sur les 3 dimensions
                avg_error = total_error / 3.0
                
                if avg_error < best_error:
                    best_error = avg_error
                    best_smooth = smooth_val
                    
            except Exception:
                # En cas d'échec (matrice singulière, etc.), passer
                continue
        
        print(f"  Smoothing optimal détecté: {best_smooth} (erreur CV: {best_error:.2f}m²)")
        return best_smooth
    
    def fit(self, trajectory: Trajectory) -> 'BSplineOptimizer':
        """
        Ajuste les B-splines à la trajectoire
        
        Args:
            trajectory: Trajectoire d'entrée
            
        Returns:
            Self pour chaînage
        """
        # Utiliser les coordonnées CARTÉSIENNES pour l'interpolation
        coords = trajectory.get_cartesian_array()  # x, y, z en mètres
        timestamps = trajectory.get_timestamps()
        
        # Éliminer les timestamps dupliqués en gardant le premier point
        unique_indices = [0]
        for i in range(1, len(timestamps)):
            if timestamps[i] != timestamps[i-1]:
                unique_indices.append(i)
        
        timestamps = timestamps[unique_indices]
        coords = coords[unique_indices]
        
        # Stocker les bornes temporelles pour evaluate()
        self.t_min = float(timestamps[0])
        self.t_max = float(timestamps[-1])
        
        # Normaliser le paramètre temporel entre 0 et 1
        t_norm = (timestamps - self.t_min) / (self.t_max - self.t_min)
        
        # Déterminer le nombre de points de contrôle (formule optimisée)
        if self.num_control_points is None:
            n = len(timestamps)
            # Formule basée sur la complexité de la trajectoire
            # Pour haute précision : garder plus de points
            if n < 30:
                self.num_control_points = max(int(n * 0.7), 8)
            elif n < 100:
                self.num_control_points = max(int(n * 0.6), 20)
            elif n < 500:
                self.num_control_points = max(int(n ** 0.65), 50)
            else:
                # Pour très longues trajectoires, limiter pour performance
                self.num_control_points = min(int(n ** 0.6), 200)
        
        # Détection automatique du smoothing optimal
        if self.auto_smooth and self.smoothing_factor is None:
            self.smoothing_factor = self._estimate_optimal_smoothing(coords, t_norm)
        
        # Créer les B-splines pour chaque dimension cartésienne (x, y, z)
        self.splines = []
        
        for dim in range(3):  # x, y, z
            # Utiliser splrep pour créer une spline
            if self.smoothing_factor is None:
                # Interpolation exacte
                tck = interpolate.splrep(
                    t_norm,
                    coords[:, dim],
                    k=self.degree,
                    s=0  # Pas de lissage
                )
            else:
                # Lissage
                tck = interpolate.splrep(
                    t_norm,
                    coords[:, dim],
                    k=self.degree,
                    s=self.smoothing_factor
                )
            
            self.splines.append(tck)
        
        return self
    
    def evaluate(
        self,
        trajectory: Trajectory,
        num_points: Optional[int] = None,
        timestamps: Optional[np.ndarray] = None
    ) -> Trajectory:
        """
        Évalue la B-spline pour générer une trajectoire lissée
        
        Args:
            trajectory: Trajectoire originale (pour référence)
            num_points: Nombre de points à générer (None = même que l'original)
            timestamps: Timestamps spécifiques (None = distribution uniforme)
            
        Returns:
            Trajectoire interpolée
        """
        if self.splines is None:
            raise RuntimeError("Les splines doivent être ajustées avant l'évaluation")
        
        # Utiliser les bornes temporelles de fit()
        assert self.t_min is not None and self.t_max is not None
        t_min, t_max = self.t_min, self.t_max
        
        if timestamps is not None:
            eval_timestamps = timestamps
        elif num_points is not None:
            eval_timestamps = np.linspace(t_min, t_max, num_points)
        else:
            # Utiliser les timestamps de la trajectoire d'entr\u00e9e
            eval_timestamps = trajectory.get_timestamps()
        
        # Normaliser entre 0 et 1
        t_norm = (eval_timestamps - t_min) / (t_max - t_min)
        
        # Évaluer chaque spline cartésienne (x, y, z)
        coords_interp = np.zeros((len(t_norm), 3))
        
        for dim in range(3):
            coords_interp[:, dim] = interpolate.splev(t_norm, self.splines[dim])
        
        # Convertir de coordonnées cartésiennes vers géographiques
        interpolated_positions = []
        
        # Timestamp de début
        t0_datetime = trajectory.positions[0].timestamp
        
        # Latitude de référence pour les conversions
        ref_lat = (trajectory.positions[0].latitude + trajectory.positions[-1].latitude) / 2
        
        for i, (t_rel, coords_cart) in enumerate(zip(eval_timestamps, coords_interp)):
            # Convertir cartésien (x, y, z) vers géographique (lat, lon, alt)
            x_cart, y_cart, z_cart = coords_cart
            lat, lon, alt = Position.from_cartesian(x_cart, y_cart, z_cart, reference_lat=ref_lat)
            
            # Timestamp absolu
            timestamp = datetime.fromtimestamp(t0_datetime.timestamp() + t_rel)
            
            # Calculer la vitesse si possible
            ground_speed = None
            vertical_rate = None
            
            if i > 0:
                dt = t_rel - eval_timestamps[i-1]
                if dt > 0:
                    # Calcul direct en cart\u00e9sien (plus pr\u00e9cis)
                    dx = coords_interp[i, 0] - coords_interp[i-1, 0]
                    dy = coords_interp[i, 1] - coords_interp[i-1, 1]
                    dz = coords_interp[i, 2] - coords_interp[i-1, 2]
                    
                    # Vitesse horizontale et verticale
                    ground_speed = np.sqrt(dx**2 + dy**2) / dt
                    vertical_rate = dz / dt
            
            pos = Position(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                timestamp=timestamp,
                ground_speed=ground_speed,
                vertical_rate=vertical_rate
            )
            interpolated_positions.append(pos)
        
        return Trajectory(
            positions=interpolated_positions,
            flight_id=f"{trajectory.flight_id}_bspline" if trajectory.flight_id else "bspline"
        )
    
    def _validate_distance_preservation(self, original: Trajectory, optimized: Trajectory) -> None:
        """
        Valide que la distance de la trajectoire est préservée (mode preserve_distance)
        
        Args:
            original: Trajectoire originale
            optimized: Trajectoire optimisée
        """
        dist_original = original.get_cumulative_distances()[-1] / 1000.0  # Convertir en km
        dist_optimized = optimized.get_cumulative_distances()[-1] / 1000.0  # Convertir en km
        
        # Calculer la variation
        if dist_original > 0:
            variation_pct = 100.0 * abs(dist_optimized - dist_original) / dist_original
            
            # Seuil d'alerte : ±1% pour preserve_distance=True
            if self.preserve_distance and variation_pct > 1.0:
                print(f"⚠️  ATTENTION: Distance non préservée!")
                print(f"   Original: {dist_original:.1f} km")
                print(f"   Optimisé: {dist_optimized:.1f} km")
                print(f"   Variation: {variation_pct:.2f}%")
                print(f"   → Le lissage a modifié la distance malgré preserve_distance=True")
            elif variation_pct > 0.1:  # Log si variation > 0.1%
                print(f"✓ Distance préservée: {dist_original:.1f} km → {dist_optimized:.1f} km ({variation_pct:.2f}%)")
    
    def optimize(self, trajectory: Trajectory, target_points: int = 100) -> Trajectory:
        """
        Optimise la trajectoire en réduisant le nombre de points tout en gardant la forme
        
        Args:
            trajectory: Trajectoire originale
            target_points: Nombre de points cible
            
        Returns:
            Trajectoire optimisée
        """
        # Ajuster les splines
        self.fit(trajectory)
        
        # Évaluer avec moins de points
        optimized = self.evaluate(trajectory, num_points=target_points)
        
        # Valider la préservation de distance si activée
        self._validate_distance_preservation(trajectory, optimized)
        
        return optimized
    
    def get_derivatives(
        self,
        trajectory: Trajectory,
        order: int = 1
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calcule les dérivées de la trajectoire (vitesse, accélération, etc.)
        
        Args:
            trajectory: Trajectoire de référence
            order: Ordre de la dérivée (1=vitesse, 2=accélération)
            
        Returns:
            (timestamps, derivatives) où derivatives est (N, 3)
        """
        if self.splines is None:
            raise RuntimeError("Les splines doivent être ajustées avant le calcul des dérivées")
        
        timestamps = trajectory.get_timestamps()
        t_min, t_max = timestamps[0], timestamps[-1]
        t_norm = (timestamps - t_min) / (t_max - t_min)
        
        derivatives = np.zeros((len(t_norm), 3))
        
        for dim in range(3):
            derivatives[:, dim] = interpolate.splev(
                t_norm,
                self.splines[dim],
                der=order
            )
        
        # Normaliser par rapport au temps réel
        time_scale = t_max - t_min
        derivatives /= time_scale**order
        
        return timestamps, derivatives
    
    def compute_curvature(self, trajectory: Trajectory) -> np.ndarray:
        """
        Calcule la courbure le long de la trajectoire
        
        Args:
            trajectory: Trajectoire de référence
            
        Returns:
            Array de courbures
        """
        # Obtenir vitesse et accélération
        _, velocity = self.get_derivatives(trajectory, order=1)
        _, acceleration = self.get_derivatives(trajectory, order=2)
        
        # Courbure = ||v × a|| / ||v||^3
        cross_product = np.cross(velocity, acceleration)
        curvature = np.linalg.norm(cross_product, axis=1) / (np.linalg.norm(velocity, axis=1)**3 + 1e-10)
        
        return curvature
    
    def resample_uniform(self, trajectory: Trajectory, spacing: float = 1000.0) -> Trajectory:
        """
        Rééchantillonne la trajectoire avec un espacement uniforme en distance
        
        Args:
            trajectory: Trajectoire originale
            spacing: Espacement en mètres
            
        Returns:
            Trajectoire rééchantillonnée
        """
        self.fit(trajectory)
        
        # Calculer la longueur totale de la trajectoire
        cartesian = trajectory.get_cartesian_array()
        distances = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(cartesian, axis=0), axis=1))])
        total_length = distances[-1]
        
        # Nombre de points
        num_points = int(total_length / spacing) + 1
        
        # Créer une interpolation distance -> temps
        timestamps = trajectory.get_timestamps()
        distance_to_time = interpolate.interp1d(distances, timestamps, kind='linear')
        
        # Nouvelles distances uniformes
        new_distances = np.linspace(0, total_length, num_points)
        new_timestamps = distance_to_time(new_distances)
        
        # Évaluer la spline aux nouveaux timestamps
        return self.evaluate(trajectory, timestamps=new_timestamps)
