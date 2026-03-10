"""
Interface pour récupérer les données météorologiques
"""
import numpy as np
from typing import Optional, Dict, List
from datetime import datetime
import requests  # type: ignore
from dataclasses import dataclass

from ..data.data_models import WeatherConditions


@dataclass
class WeatherPoint:
    """Point météo avec position et conditions"""
    latitude: float
    longitude: float
    altitude: float
    timestamp: datetime
    conditions: WeatherConditions


class WeatherAPI:
    """
    Interface générique pour les API météo
    Supporte plusieurs sources de données
    """
    
    def __init__(self, api_key: Optional[str] = None, source: str = 'openweather'):
        """
        Initialise l'API météo
        
        Args:
            api_key: Clé API (si nécessaire)
            source: Source des données ('openweather', 'noaa', 'mock')
        """
        self.api_key = api_key
        self.source = source
        self._cache: Dict[tuple, WeatherConditions] = {}
    
    def get_weather(
        self,
        latitude: float,
        longitude: float,
        altitude: float = 0,
        timestamp: Optional[datetime] = None
    ) -> WeatherConditions:
        """
        Récupère les conditions météo pour un point donné
        
        Args:
            latitude: Latitude en degrés
            longitude: Longitude en degrés
            altitude: Altitude en mètres
            timestamp: Timestamp (None = maintenant)
            
        Returns:
            Conditions météorologiques
        """
        # Vérifier le cache
        cache_key = (round(latitude, 2), round(longitude, 2), round(altitude, -2))
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Récupérer les données selon la source
        if self.source == 'openweather':
            conditions = self._get_openweather(latitude, longitude, altitude)
        elif self.source == 'noaa':
            conditions = self._get_noaa(latitude, longitude, altitude)
        else:
            # Mode mock pour le développement
            conditions = self._get_mock_weather(latitude, longitude, altitude)
        
        # Mise en cache
        self._cache[cache_key] = conditions
        
        return conditions
    
    def _get_openweather(
        self,
        latitude: float,
        longitude: float,
        altitude: float
    ) -> WeatherConditions:
        """Récupère les données depuis OpenWeatherMap API"""
        if not self.api_key:
            raise ValueError("Clé API OpenWeatherMap requise")
        
        try:
            # API Current Weather
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extraire les données de vent
            wind_speed = data.get('wind', {}).get('speed', 0)  # m/s
            wind_direction = data.get('wind', {}).get('deg', 0)  # degrés
            temperature = data.get('main', {}).get('temp', 15)  # Celsius
            pressure = data.get('main', {}).get('pressure', 1013)  # hPa
            
            return WeatherConditions(
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                temperature=temperature,
                pressure=pressure
            )
        
        except requests.RequestException as e:
            print(f"Erreur API OpenWeatherMap : {e}")
            # Retourner des valeurs par défaut
            return self._get_mock_weather(latitude, longitude, altitude)
    
    def _get_noaa(
        self,
        latitude: float,
        longitude: float,
        altitude: float
    ) -> WeatherConditions:
        """Récupère les données depuis NOAA (à implémenter)"""
        # TODO: Implémenter l'API NOAA
        print("API NOAA non encore implémentée, utilisation de données mock")
        return self._get_mock_weather(latitude, longitude, altitude)
    
    def _get_mock_weather(
        self,
        latitude: float,
        longitude: float,
        altitude: float
    ) -> WeatherConditions:
        """
        Génère des données météo simulées pour les tests
        Utilise un modèle simple basé sur la position
        """
        # Modèle de vent simplifié : jet stream autour de 10km d'altitude
        base_wind_speed = 5.0  # m/s au sol
        
        # Le vent augmente avec l'altitude
        altitude_factor = min(altitude / 10000, 1.0)  # Max à 10km
        wind_speed = base_wind_speed + altitude_factor * 45.0  # Jusqu'à 50 m/s
        
        # Direction dominante Ouest (270°) avec variation
        wind_direction = 270 + 30 * np.sin(np.radians(latitude * 2))
        
        # Température décroît avec l'altitude (environ -6.5°C / 1000m)
        temperature = 15 - (altitude / 1000) * 6.5
        
        # Pression atmosphérique (formule barométrique simplifiée)
        pressure = 1013.25 * np.exp(-altitude / 8500)
        
        return WeatherConditions(
            wind_speed=float(wind_speed),
            wind_direction=float(wind_direction % 360),
            temperature=float(temperature),
            pressure=float(pressure)
        )
    
    def get_weather_along_trajectory(
        self,
        positions: List[tuple],  # [(lat, lon, alt), ...]
        timestamps: Optional[List[datetime]] = None
    ) -> List[WeatherConditions]:
        """
        Récupère les conditions météo pour plusieurs points
        
        Args:
            positions: Liste de tuples (latitude, longitude, altitude)
            timestamps: Timestamps optionnels
            
        Returns:
            Liste de conditions météorologiques
        """
        weather_data = []
        
        for i, (lat, lon, alt) in enumerate(positions):
            timestamp = timestamps[i] if timestamps else None
            conditions = self.get_weather(lat, lon, alt, timestamp)
            weather_data.append(conditions)
        
        return weather_data
    
    def clear_cache(self):
        """Vide le cache météo"""
        self._cache.clear()


class WindFieldInterpolator:
    """
    Interpolateur de champ de vent pour trajectoires
    """
    
    def __init__(self, weather_api: WeatherAPI):
        """
        Initialise l'interpolateur
        
        Args:
            weather_api: Instance de WeatherAPI
        """
        self.weather_api = weather_api
    
    def get_wind_at_position(
        self,
        latitude: float,
        longitude: float,
        altitude: float
    ) -> np.ndarray:
        """
        Récupère le vecteur vent à une position donnée
        
        Args:
            latitude: Latitude en degrés
            longitude: Longitude en degrés
            altitude: Altitude en mètres
            
        Returns:
            Vecteur vent [Est, Nord] en m/s
        """
        conditions = self.weather_api.get_weather(latitude, longitude, altitude)
        return conditions.get_wind_vector()
    
    def compute_wind_effect(
        self,
        velocity: np.ndarray,
        wind: np.ndarray,
        dt: float
    ) -> np.ndarray:
        """
        Calcule l'effet du vent sur la trajectoire
        
        Args:
            velocity: Vitesse sol [vx, vy] en m/s
            wind: Vecteur vent [wx, wy] en m/s
            dt: Intervalle de temps en secondes
            
        Returns:
            Déplacement dû au vent [dx, dy] en mètres
        """
        # Le vent affecte directement la position
        displacement = wind * dt
        return displacement
    
    def estimate_fuel_consumption(
        self,
        ground_speed: float,
        wind_speed: float,
        wind_direction: float,
        heading: float
    ) -> float:
        """
        Estime l'impact du vent sur la consommation de carburant
        
        Args:
            ground_speed: Vitesse sol en m/s
            wind_speed: Vitesse du vent en m/s
            wind_direction: Direction du vent en degrés
            heading: Cap de l'avion en degrés
            
        Returns:
            Facteur de consommation (1.0 = normal, >1 = plus, <1 = moins)
        """
        # Composante du vent dans la direction de vol
        relative_angle = np.radians(heading - wind_direction)
        headwind_component = wind_speed * np.cos(relative_angle)
        
        # Vent de face augmente la consommation, vent arrière la diminue
        # Modèle simplifié : +/- 2% par 10 m/s de vent
        fuel_factor = 1.0 + (headwind_component / 10.0) * 0.02
        
        return max(0.8, min(1.2, fuel_factor))
