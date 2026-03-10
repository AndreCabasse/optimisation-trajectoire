"""
Modèles de données pour les trajectoires aériennes
"""
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from datetime import datetime


@dataclass
class Position:
    """Représente une position 3D avec timestamp"""
    latitude: float  # degrés
    longitude: float  # degrés
    altitude: float  # mètres
    timestamp: datetime
    
    # Optionnel : données ADS-B supplémentaires
    ground_speed: Optional[float] = None  # m/s
    vertical_rate: Optional[float] = None  # m/s
    heading: Optional[float] = None  # degrés
    
    def to_cartesian(self, use_precise: bool = False, reference_point: Optional['Position'] = None) -> np.ndarray:
        """Convertit en coordonnées cartésiennes locales (x, y, z)
        
        IMPORTANT: Retourne des coordonnées LOCALES en mètres (offset depuis un point de référence),
        PAS des coordonnées ECEF absolues.
        
        Args:
            use_precise: Si True, utilise une projection locale plus précise (Mercator transverse).
                        Si False, utilise approximation sphérique simple (recommandé).
            reference_point: Point de référence (ignoré, gardé pour compatibilité).
        """
        # Pour éviter les bugs de conversion, on utilise TOUJOURS l'approximation locale
        # qui est cohérente avec le reste du code (offset en mètres, pas ECEF)
        
        # Approximation sphérique locale - précise à ~0.5% pour distances < 1000km
        # x = Est (mètres), y = Nord (mètres), z = altitude (mètres)
        
        # Latitude de référence pour la correction de longitude
        lat_rad = np.radians(self.latitude)
        
        # Conversion avec correction sphérique améliorée
        # Utilise le rayon de courbure de l'ellipsoïde WGS84
        a = 6378137.0  # Rayon équatorial WGS84 (mètres)
        e2 = 0.00669438  # Première excentricité au carré WGS84
        
        # Rayon de courbure dans le méridien
        N = a / np.sqrt(1 - e2 * np.sin(lat_rad)**2)
        
        # Conversion latitude → mètres Nord
        # 1 degré de latitude ≈ 111320m (varie légèrement)
        meters_per_deg_lat = 111132.92 - 559.82 * np.cos(2 * lat_rad) + 1.175 * np.cos(4 * lat_rad)
        y = self.latitude * meters_per_deg_lat
        
        # Conversion longitude → mètres Est (correction selon latitude)
        meters_per_deg_lon = (N + self.altitude) * np.cos(lat_rad) * np.pi / 180.0
        x = self.longitude * meters_per_deg_lon
        
        # Altitude inchangée
        z = self.altitude
        
        return np.array([x, y, z])
    
    @staticmethod
    def from_cartesian(x: float, y: float, z: float, reference_lat: float = 0.0) -> tuple[float, float, float]:
        """Convertit des coordonnées cartésiennes locales en coordonnées géographiques
        
        Args:
            x: Est (mètres)
            y: Nord (mètres)  
            z: Altitude (mètres)
            reference_lat: Latitude de référence pour la conversion (degrés)
            
        Returns:
            (latitude, longitude, altitude) en degrés et mètres
        """
        # Constantes WGS84
        a = 6378137.0  # Rayon équatorial
        e2 = 0.00669438  # Première excentricité au carré
        
        # Estimation itérative de la latitude (car meters_per_deg_lat dépend de lat)
        # Commencer avec une estimation
        lat_rad = np.radians(reference_lat) if reference_lat != 0 else y / 111320.0 / 180.0 * np.pi
        
        # Itération pour converger (2-3 itérations suffisent)
        for _ in range(3):
            meters_per_deg_lat = 111132.92 - 559.82 * np.cos(2 * lat_rad) + 1.175 * np.cos(4 * lat_rad)
            lat = y / meters_per_deg_lat
            lat_rad = np.radians(lat)
        
        # Longitude
        N = a / np.sqrt(1 - e2 * np.sin(lat_rad)**2)
        meters_per_deg_lon = (N + z) * np.cos(lat_rad) * np.pi / 180.0
        lon = x / meters_per_deg_lon if meters_per_deg_lon > 0 else 0.0
        
        return lat, lon, z


@dataclass
class WeatherConditions:
    """Conditions météorologiques à un point donné"""
    wind_speed: float  # m/s
    wind_direction: float  # degrés
    temperature: Optional[float] = None  # Celsius
    pressure: Optional[float] = None  # hPa
    
    def get_wind_vector(self) -> np.ndarray:
        """Retourne le vecteur vent (composantes Est, Nord)"""
        wind_rad = np.radians(self.wind_direction)
        # Convention météo : direction d'où vient le vent
        wind_east = -self.wind_speed * np.sin(wind_rad)
        wind_north = -self.wind_speed * np.cos(wind_rad)
        return np.array([wind_east, wind_north])


class Trajectory:
    """Classe représentant une trajectoire complète"""
    
    def __init__(self, positions: List[Position], flight_id: Optional[str] = None):
        self.positions = positions
        self.flight_id = flight_id
        self._validate()
    
    def _validate(self):
        """Valide la trajectoire"""
        if len(self.positions) < 2:
            raise ValueError("Une trajectoire doit contenir au moins 2 points")
        
        # Vérifier que les timestamps sont ordonnés
        for i in range(1, len(self.positions)):
            if self.positions[i].timestamp < self.positions[i-1].timestamp:
                raise ValueError("Les timestamps doivent être en ordre croissant")
    
    @property
    def duration(self) -> float:
        """Durée totale en secondes"""
        return (self.positions[-1].timestamp - self.positions[0].timestamp).total_seconds()
    
    @property
    def length(self) -> int:
        """Nombre de points dans la trajectoire"""
        return len(self.positions)
    
    def get_coordinates_array(self) -> np.ndarray:
        """Retourne un array numpy (N, 3) avec lat, lon, alt"""
        return np.array([
            [p.latitude, p.longitude, p.altitude]
            for p in self.positions
        ])
    
    def get_cartesian_array(self) -> np.ndarray:
        """Retourne un array numpy (N, 3) en coordonnées cartésiennes"""
        return np.array([p.to_cartesian() for p in self.positions])
    
    def get_timestamps(self) -> np.ndarray:
        """Retourne les timestamps en secondes depuis le début"""
        t0 = self.positions[0].timestamp
        return np.array([
            (p.timestamp - t0).total_seconds()
            for p in self.positions
        ])
    
    def get_cumulative_distances(self) -> np.ndarray:
        """Calcule les distances cumulatives le long de la trajectoire (en mètres)"""
        coords = self.get_cartesian_array()
        distances = np.zeros(len(coords))
        
        for i in range(1, len(coords)):
            segment_distance = np.linalg.norm(coords[i] - coords[i-1])
            distances[i] = distances[i-1] + segment_distance
        
        return distances
    
    def find_index_by_time(self, elapsed_seconds: float) -> int:
        """
        Trouve l'index du point le plus proche d'un temps écoulé donné
        
        Args:
            elapsed_seconds: Temps en secondes depuis le début de la trajectoire
            
        Returns:
            Index du point le plus proche
        """
        timestamps = self.get_timestamps()
        idx = np.argmin(np.abs(timestamps - elapsed_seconds))
        return int(idx)
    
    def find_index_by_distance(self, distance_meters: float) -> int:
        """
        Trouve l'index du point le plus proche d'une distance parcourue donnée
        
        Args:
            distance_meters: Distance en mètres depuis le début de la trajectoire
            
        Returns:
            Index du point le plus proche
        """
        distances = self.get_cumulative_distances()
        idx = np.argmin(np.abs(distances - distance_meters))
        return int(idx)
    
    def subset(self, start_idx: int, end_idx: int) -> 'Trajectory':
        """Retourne une sous-trajectoire"""
        return Trajectory(
            positions=self.positions[start_idx:end_idx],
            flight_id=f"{self.flight_id}_subset" if self.flight_id else None
        )
    
    def __len__(self) -> int:
        return len(self.positions)
    
    def __repr__(self) -> str:
        return (f"Trajectory(flight_id={self.flight_id}, "
                f"points={len(self.positions)}, "
                f"duration={self.duration:.1f}s)")


@dataclass
class OptimizedTrajectory:
    """Résultat d'une optimisation de trajectoire"""
    original: Trajectory
    optimized_positions: List[Position]
    method: str  # 'kalman', 'bspline', 'hybrid'
    metrics: dict  # Métriques d'optimisation
    
    def get_optimized_trajectory(self) -> Trajectory:
        """Retourne la trajectoire optimisée en tant qu'objet Trajectory"""
        return Trajectory(
            positions=self.optimized_positions,
            flight_id=f"{self.original.flight_id}_optimized" if self.original.flight_id else "optimized"
        )
    
    def get_improvement(self, metric: str = 'smoothness') -> float:
        """Calcule l'amélioration par rapport à la trajectoire originale"""
        if metric in self.metrics:
            return self.metrics[metric]
        return 0.0
    
    def __repr__(self) -> str:
        return (f"OptimizedTrajectory(method={self.method}, "
                f"points={len(self.optimized_positions)})")
