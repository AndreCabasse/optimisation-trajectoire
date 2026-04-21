"""
Lightweight GPS/ADS-B spoofing injector for BiLSTM testing.
Injects spoofing patterns into a Trajectory from a given start index.
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum

from src.data.data_models import Trajectory, Position


class SpoofingType(Enum):
    POSITION_OFFSET = "position_offset"   # Décalage soudain lat/lon
    GRADUAL_DRIFT   = "gradual_drift"     # Dérive progressive croissante
    ALTITUDE_FREEZE = "altitude_freeze"   # Altitude figée, position dérive
    COMBINED        = "combined"          # Décalage + dérive + bruit


# Paramètres prédéfinis par intensité
_INTENSITY_PARAMS = {
    "Légère":  dict(lat=0.008, lon=0.008, alt=80.0,  drift=0.0001, noise=0.0003),
    "Moyenne": dict(lat=0.04,  lon=0.04,  alt=250.0, drift=0.0008, noise=0.0008),
    "Forte":   dict(lat=0.12,  lon=0.12,  alt=600.0, drift=0.003,  noise=0.002),
}


@dataclass
class SpoofingConfig:
    spoof_type:  SpoofingType = SpoofingType.POSITION_OFFSET
    start_index: int          = 0
    lat_offset:  float        = 0.04
    lon_offset:  float        = 0.04
    alt_offset:  float        = 0.0
    drift_rate:  float        = 0.0008
    noise_std:   float        = 0.0008


class SpoofingInjector:
    """Injecte du spoofing GPS/ADS-B dans une Trajectory à partir d'un index donné."""

    @staticmethod
    def from_intensity(
        spoof_type:  SpoofingType,
        start_index: int,
        intensity:   str = "Moyenne",
        seed:        int = 42,
    ) -> SpoofingConfig:
        """Construit une SpoofingConfig depuis un niveau d'intensité prédéfini."""
        p = _INTENSITY_PARAMS.get(intensity, _INTENSITY_PARAMS["Moyenne"])
        return SpoofingConfig(
            spoof_type=spoof_type,
            start_index=start_index,
            lat_offset=p["lat"],
            lon_offset=p["lon"],
            alt_offset=p["alt"],
            drift_rate=p["drift"],
            noise_std=p["noise"],
        )

    @staticmethod
    def inject(trajectory: Trajectory, config: SpoofingConfig) -> Trajectory:
        """
        Retourne une nouvelle Trajectory avec du spoofing injecté depuis
        `config.start_index`. La trajectoire originale n'est pas modifiée.
        """
        rng = np.random.default_rng(42)
        positions = trajectory.positions
        n = len(positions)
        start = max(0, min(config.start_index, n - 1))

        # Partie propre (avant l'injection)
        new_positions = list(positions[:start])

        for i in range(start, n):
            step = i - start
            p = positions[i]
            lat, lon, alt = p.latitude, p.longitude, p.altitude

            noise_lat = rng.normal(0, config.noise_std)
            noise_lon = rng.normal(0, config.noise_std)

            st = config.spoof_type

            if st == SpoofingType.POSITION_OFFSET:
                lat += config.lat_offset + noise_lat
                lon += config.lon_offset + noise_lon

            elif st == SpoofingType.GRADUAL_DRIFT:
                lat += config.drift_rate * step + noise_lat
                lon += config.drift_rate * step + noise_lon

            elif st == SpoofingType.ALTITUDE_FREEZE:
                # Altitude bloquée sur la valeur au point d'injection
                alt = positions[start].altitude
                n_remaining = max(n - start, 1)
                lat += config.lat_offset * step / n_remaining + noise_lat
                lon += config.lon_offset * step / n_remaining + noise_lon

            elif st == SpoofingType.COMBINED:
                lat += config.lat_offset + config.drift_rate * step + noise_lat
                lon += config.lon_offset + config.drift_rate * step + noise_lon
                alt += config.alt_offset

            new_positions.append(Position(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                timestamp=p.timestamp,
            ))

        flight_id = (trajectory.flight_id + "_spoofed") if trajectory.flight_id else "spoofed"
        return Trajectory(positions=new_positions, flight_id=flight_id)
