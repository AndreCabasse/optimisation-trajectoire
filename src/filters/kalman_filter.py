"""
Implémentation du filtre de Kalman pour le lissage et la prédiction de trajectoires
"""
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

from ..data.data_models import Position, Trajectory


@dataclass
class KalmanState:
    """État du filtre de Kalman"""
    x: np.ndarray  # Vecteur d'état [pos_x, pos_y, pos_z, vel_x, vel_y, vel_z]
    P: np.ndarray  # Matrice de covariance
    timestamp: float


class KalmanFilter:
    """
    Filtre de Kalman pour le lissage de trajectoires 3D
    
    Modèle d'état : vitesse constante (peut être étendu)
    État : [x, y, z, vx, vy, vz]
    """
    
    def __init__(
        self,
        process_noise: float = 0.5,
        measurement_noise: float = 5.0,
        initial_velocity_uncertainty: float = 10.0,
        adaptive: bool = True,
        altitude_dependent_noise: bool = True
    ):
        """
        Initialise le filtre de Kalman
        
        Args:
            process_noise: Bruit du processus (incertitude du modèle) - réduit pour meilleure précision
            measurement_noise: Bruit de mesure (incertitude des données ADS-B) - 5m typique pour ADS-B
            initial_velocity_uncertainty: Incertitude initiale sur la vitesse
            adaptive: Activer l'adaptation dynamique du bruit
            altitude_dependent_noise: Ajuster le bruit selon l'altitude (plus précis en haute altitude)
        """
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.initial_velocity_uncertainty = initial_velocity_uncertainty
        self.adaptive = adaptive
        self.altitude_dependent_noise = altitude_dependent_noise
        self.innovation_history: List[float] = []  # Pour adaptation
        
        # Dimension de l'état : 6 (position + vitesse en 3D)
        self.state_dim = 6
        # Dimension de la mesure : 3 (seulement la position)
        self.measurement_dim = 3
        
        # Matrices du système
        self.F = None  # Matrice de transition (sera mise à jour avec dt)
        self.H = np.array([  # Matrice d'observation
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ])
        self.Q = None  # Covariance du bruit de processus (sera mise à jour avec dt)
        self.R = np.eye(self.measurement_dim) * measurement_noise**2  # Covariance du bruit de mesure
        self.R_base = self.R.copy()  # Sauvegarder la valeur de base
        
        # État actuel
        self.state: Optional[KalmanState] = None
        self.current_altitude = 0.0  # Pour ajustement du bruit
    
    def _build_transition_matrix(self, dt: float) -> np.ndarray:
        """
        Construit la matrice de transition F pour un intervalle de temps dt
        Modèle : position constante + vitesse
        """
        F = np.eye(self.state_dim)
        F[0, 3] = dt  # x = x + vx * dt
        F[1, 4] = dt  # y = y + vy * dt
        F[2, 5] = dt  # z = z + vz * dt
        return F
    
    def _build_process_covariance(self, dt: float) -> np.ndarray:
        """
        Construit la matrice de covariance du bruit de processus Q
        """
        # Modèle de bruit d'accélération continue
        q = self.process_noise**2
        
        Q = np.zeros((self.state_dim, self.state_dim))
        
        # Bloc position-position
        Q[0:3, 0:3] = np.eye(3) * (q * dt**4 / 4)
        
        # Bloc position-vitesse
        Q[0:3, 3:6] = np.eye(3) * (q * dt**3 / 2)
        Q[3:6, 0:3] = np.eye(3) * (q * dt**3 / 2)
        
        # Bloc vitesse-vitesse
        Q[3:6, 3:6] = np.eye(3) * (q * dt**2)
        
        return Q
    
    def initialize(self, position: np.ndarray, timestamp: float):
        """
        Initialise le filtre avec la première position
        
        Args:
            position: Position initiale [x, y, z]
            timestamp: Timestamp initial
        """
        # État initial : position connue, vitesse nulle
        x = np.zeros(self.state_dim)
        x[0:3] = position
        x[3:6] = 0  # Vitesse initiale inconnue
        
        # Covariance initiale
        P = np.eye(self.state_dim)
        P[0:3, 0:3] *= self.measurement_noise**2  # Incertitude sur la position
        P[3:6, 3:6] *= self.initial_velocity_uncertainty**2  # Incertitude sur la vitesse
        
        self.state = KalmanState(x=x, P=P, timestamp=timestamp)
    
    def predict(self, dt: float) -> KalmanState:
        """
        Étape de prédiction du filtre de Kalman
        
        Args:
            dt: Intervalle de temps depuis la dernière mesure
            
        Returns:
            État prédit
        """
        if self.state is None:
            raise RuntimeError("Le filtre doit être initialisé avant la prédiction")
        
        # Mettre à jour les matrices avec dt
        F = self._build_transition_matrix(dt)
        Q = self._build_process_covariance(dt)
        
        # Prédiction
        x_pred = F @ self.state.x
        P_pred = F @ self.state.P @ F.T + Q
        
        return KalmanState(
            x=x_pred,
            P=P_pred,
            timestamp=self.state.timestamp + dt
        )
    
    def update(self, measurement: np.ndarray, timestamp: float) -> KalmanState:
        """
        Étape de mise à jour du filtre de Kalman
        
        Args:
            measurement: Mesure de position [x, y, z]
            timestamp: Timestamp de la mesure
            
        Returns:
            État mis à jour
        """
        if self.state is None:
            # Première mesure : initialiser
            self.initialize(measurement, timestamp)
            assert self.state is not None
            return self.state
        
        # Calculer dt
        dt = timestamp - self.state.timestamp
        
        # Prédiction
        predicted = self.predict(dt)
        
        # Ajuster le bruit de mesure selon l'altitude si activé
        if self.altitude_dependent_noise:
            alt = measurement[2]  # altitude
            # ADS-B est plus précis en altitude (facteur ~0.5 à 10km vs sol)
            # Formule : précision améliore avec altitude jusqu'à ~10km
            altitude_factor = max(0.5, 1.0 - (alt / 20000.0))  # Meilleur à haute altitude
            self.R = self.R_base * altitude_factor
            self.current_altitude = alt
        
        # Innovation
        y = measurement - self.H @ predicted.x
        
        # Adaptation dynamique si activée
        if self.adaptive:
            innovation_norm = float(np.linalg.norm(y))
            self.innovation_history.append(innovation_norm)
            # Garder seulement les 50 dernières innovations
            if len(self.innovation_history) > 50:
                self.innovation_history.pop(0)
            
            # Si innovations anormalement grandes → augmenter bruit de mesure
            if len(self.innovation_history) >= 10:
                mean_innov = np.mean(self.innovation_history[-10:])
                if mean_innov > 3 * self.measurement_noise:
                    # Outlier détecté - augmenter temporairement R
                    self.R = self.R * 2.0
        
        # Covariance de l'innovation
        S = self.H @ predicted.P @ self.H.T + self.R
        
        # Gain de Kalman
        K = predicted.P @ self.H.T @ np.linalg.inv(S)
        
        # Mise à jour
        x_updated = predicted.x + K @ y
        P_updated = (np.eye(self.state_dim) - K @ self.H) @ predicted.P
        
        self.state = KalmanState(
            x=x_updated,
            P=P_updated,
            timestamp=timestamp
        )
        
        return self.state
    
    def filter_trajectory(self, trajectory: Trajectory) -> Trajectory:
        """
        Applique le filtre de Kalman à une trajectoire complète
        
        Args:
            trajectory: Trajectoire brute
            
        Returns:
            Trajectoire filtrée
        """
        filtered_positions: List[Position] = []
        
        # Convertir en coordonnées cartésiennes pour le filtrage
        cart_coords = trajectory.get_cartesian_array()  # x, y, z en mètres
        timestamps = trajectory.get_timestamps()
        
        # Latitude de référence pour les conversions
        ref_lat = (trajectory.positions[0].latitude + trajectory.positions[-1].latitude) / 2
        
        # Réinitialiser l'état
        self.state = None
        
        for i, (cart_coords_point, t) in enumerate(zip(cart_coords, timestamps)):
            # Mise à jour avec la mesure cartésienne (x, y, z)
            state = self.update(cart_coords_point, t)
            
            # Extraire les coordonnées cartésiennes filtrées
            x_filt, y_filt, z_filt = state.x[0:3]
            
            # Convertir de cartésien vers géographique
            lat_filt, lon_filt, alt_filt = Position.from_cartesian(
                x_filt, y_filt, z_filt, reference_lat=ref_lat
            )
            
            # Calculer la vitesse sol (m/s) directement depuis les vitesses estimées
            ground_speed = None
            if i > 0:
                vx, vy = state.x[3], state.x[4]
                ground_speed = np.sqrt(vx**2 + vy**2)
            
            # Créer la position filtrée
            filtered_pos = Position(
                latitude=lat_filt,
                longitude=lon_filt,
                altitude=alt_filt,
                timestamp=trajectory.positions[i].timestamp,
                ground_speed=ground_speed,
                vertical_rate=state.x[5] if i > 0 else None
            )
            
            filtered_positions.append(filtered_pos)
        
        return Trajectory(
            positions=filtered_positions,
            flight_id=f"{trajectory.flight_id}_kalman" if trajectory.flight_id else "filtered"
        )
    
    def smooth_trajectory(self, trajectory: Trajectory) -> Trajectory:
        """
        Applique un lissage RTS (Rauch-Tung-Striebel) pour un résultat optimal
        
        Args:
            trajectory: Trajectoire brute
            
        Returns:
            Trajectoire lissée
        """
        # Phase forward : filtrage normal
        cart_coords = trajectory.get_cartesian_array()  # x, y, z en mètres
        timestamps = trajectory.get_timestamps()
        
        # États filtrés (forward)
        filtered_states: List[KalmanState] = []
        self.state = None
        
        for cart_point, t in zip(cart_coords, timestamps):
            state = self.update(cart_point, t)
            filtered_states.append(KalmanState(
                x=state.x.copy(),
                P=state.P.copy(),
                timestamp=t
            ))
        
        # Phase backward : lissage RTS
        smoothed_states = [filtered_states[-1]]
        
        for i in range(len(filtered_states) - 2, -1, -1):
            dt = filtered_states[i+1].timestamp - filtered_states[i].timestamp
            F = self._build_transition_matrix(dt)
            Q = self._build_process_covariance(dt)
            
            # Prédiction du prochain état
            x_pred = F @ filtered_states[i].x
            P_pred = F @ filtered_states[i].P @ F.T + Q
            
            # Gain de lissage
            C = filtered_states[i].P @ F.T @ np.linalg.inv(P_pred)
            
            # État lissé
            x_smooth = filtered_states[i].x + C @ (smoothed_states[0].x - x_pred)
            P_smooth = filtered_states[i].P + C @ (smoothed_states[0].P - P_pred) @ C.T
            
            smoothed_states.insert(0, KalmanState(
                x=x_smooth,
                P=P_smooth,
                timestamp=filtered_states[i].timestamp
            ))
        
        # Convertir en Trajectory
        smoothed_positions = []
        
        # Latitude de référence pour les conversions
        ref_lat = (trajectory.positions[0].latitude + trajectory.positions[-1].latitude) / 2
        
        for i, state in enumerate(smoothed_states):
            # Coordonnées cartésiennes lissées
            x_smooth, y_smooth, z_smooth = state.x[0:3]
            
            # Convertir en coordonnées géographiques
            lat_smooth, lon_smooth, alt_smooth = Position.from_cartesian(
                x_smooth, y_smooth, z_smooth, reference_lat=ref_lat
            )
            
            # Calculer la vitesse sol depuis les vitesses estimées
            vx, vy = state.x[3], state.x[4]
            ground_speed = np.sqrt(vx**2 + vy**2)
            
            smoothed_pos = Position(
                latitude=lat_smooth,
                longitude=lon_smooth,
                altitude=alt_smooth,
                timestamp=trajectory.positions[i].timestamp,
                ground_speed=ground_speed,
                vertical_rate=state.x[5]
            )
            smoothed_positions.append(smoothed_pos)
        
        return Trajectory(
            positions=smoothed_positions,
            flight_id=f"{trajectory.flight_id}_smoothed" if trajectory.flight_id else "smoothed"
        )
