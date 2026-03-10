"""
Tests unitaires pour le filtre de Kalman
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.filters.kalman_filter import KalmanFilter
from src.data.data_models import Position, Trajectory


class TestKalmanFilter:
    """Tests pour KalmanFilter"""
    
    @pytest.fixture
    def simple_trajectory(self):
        """Crée une trajectoire simple pour les tests"""
        positions = []
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        for i in range(100):
            pos = Position(
                latitude=48.0 + i * 0.01,
                longitude=2.0 + i * 0.01,
                altitude=10000 + i * 10,
                timestamp=base_time + timedelta(seconds=i*10),
                ground_speed=250.0
            )
            positions.append(pos)
        
        return Trajectory(positions=positions, flight_id="TEST001")
    
    @pytest.fixture
    def noisy_trajectory(self, simple_trajectory):
        """Ajoute du bruit gaussien à une trajectoire"""
        noisy_positions = []
        
        for pos in simple_trajectory.positions:
            # Ajouter bruit gaussien (±10m)
            noise_lat = np.random.normal(0, 0.0001)  # ~10m
            noise_lon = np.random.normal(0, 0.0001)
            noise_alt = np.random.normal(0, 10)
            
            noisy_pos = Position(
                latitude=pos.latitude + noise_lat,
                longitude=pos.longitude + noise_lon,
                altitude=pos.altitude + noise_alt,
                timestamp=pos.timestamp,
                ground_speed=pos.ground_speed
            )
            noisy_positions.append(noisy_pos)
        
        return Trajectory(positions=noisy_positions, flight_id="TEST001_NOISY")
    
    def test_kalman_initialization(self):
        """Test de l'initialisation du filtre"""
        kf = KalmanFilter(
            process_noise=0.5,
            measurement_noise=5.0
        )
        
        assert kf.process_noise == 0.5
        assert kf.measurement_noise == 5.0
        assert kf.state is None  # Pas encore initialisé
    
    def test_kalman_reduces_noise(self, noisy_trajectory):
        """Vérifie que Kalman réduit le bruit"""
        kf = KalmanFilter(process_noise=0.5, measurement_noise=5.0)
        smoothed = kf.smooth_trajectory(noisy_trajectory)
        
        # Calculer la variance des altitudes
        noisy_alts = np.array([p.altitude for p in noisy_trajectory.positions])
        smooth_alts = np.array([p.altitude for p in smoothed.positions])
        
        # La variance doit être réduite
        assert np.var(smooth_alts) < np.var(noisy_alts)
    
    def test_kalman_preserves_length(self, simple_trajectory):
        """Vérifie que Kalman conserve le nombre de points"""
        kf = KalmanFilter()
        smoothed = kf.smooth_trajectory(simple_trajectory)
        
        assert len(smoothed) == len(simple_trajectory)
    
    def test_kalman_preserves_endpoints(self, simple_trajectory):
        """Vérifie que les extrémités sont approximativement préservées"""
        kf = KalmanFilter()
        smoothed = kf.smooth_trajectory(simple_trajectory)
        
        # Tolérance de 100m pour les endpoints
        orig_start = simple_trajectory.positions[0]
        smooth_start = smoothed.positions[0]
        
        assert abs(orig_start.latitude - smooth_start.latitude) < 0.001  # ~100m
        assert abs(orig_start.longitude - smooth_start.longitude) < 0.001
        
        orig_end = simple_trajectory.positions[-1]
        smooth_end = smoothed.positions[-1]
        
        assert abs(orig_end.latitude - smooth_end.latitude) < 0.001
        assert abs(orig_end.longitude - smooth_end.longitude) < 0.001
    
    def test_kalman_timestamps_preserved(self, simple_trajectory):
        """Vérifie que les timestamps sont préservés"""
        kf = KalmanFilter()
        smoothed = kf.smooth_trajectory(simple_trajectory)
        
        for i, (orig, smooth) in enumerate(zip(simple_trajectory.positions, smoothed.positions)):
            assert orig.timestamp == smooth.timestamp, f"Timestamp mismatch at index {i}"
    
    def test_kalman_improves_smoothness(self, noisy_trajectory):
        """Vérifie que le lissage améliore la régularité"""
        kf = KalmanFilter()
        smoothed = kf.smooth_trajectory(noisy_trajectory)
        
        # Calculer les différences secondes (approximation accélération)
        def compute_second_diff(traj):
            coords = traj.get_cartesian_array()
            first_diff = np.diff(coords, axis=0)
            second_diff = np.diff(first_diff, axis=0)
            return np.mean(np.linalg.norm(second_diff, axis=1))
        
        noisy_jerk = compute_second_diff(noisy_trajectory)
        smooth_jerk = compute_second_diff(smoothed)
        
        # Le jerk doit être réduit (trajectoire plus lisse)
        assert smooth_jerk < noisy_jerk
    
    def test_kalman_with_zero_noise(self, simple_trajectory):
        """Test avec bruit nul (ne devrait presque pas changer)"""
        kf = KalmanFilter(process_noise=0.001, measurement_noise=0.001)
        smoothed = kf.smooth_trajectory(simple_trajectory)
        
        # Les positions doivent être très proches
        for orig, smooth in zip(simple_trajectory.positions, smoothed.positions):
            assert abs(orig.latitude - smooth.latitude) < 0.0001
            assert abs(orig.longitude - smooth.longitude) < 0.0001
            assert abs(orig.altitude - smooth.altitude) < 1.0  # 1m de tolérance
    
    def test_kalman_velocity_estimation(self, simple_trajectory):
        """Vérifie que Kalman estime correctement les vitesses"""
        kf = KalmanFilter()
        smoothed = kf.smooth_trajectory(simple_trajectory)
        
        # Vérifier que les vitesses sont estimées (non None)
        ground_speeds = [p.ground_speed for p in smoothed.positions if p.ground_speed is not None]
        
        assert len(ground_speeds) > 0
        
        # Les vitesses doivent être réalistes (entre 50 et 300 m/s pour un avion)
        for speed in ground_speeds:
            assert 50 < speed < 300, f"Unrealistic speed: {speed} m/s"


class TestKalmanEdgeCases:
    """Tests des cas limites"""
    
    def test_kalman_with_duplicate_timestamps(self):
        """Test avec timestamps dupliqués"""
        positions = [
            Position(48.0, 2.0, 10000, datetime(2024, 1, 1, 12, 0, 0)),
            Position(48.01, 2.01, 10010, datetime(2024, 1, 1, 12, 0, 0)),  # Même timestamp
            Position(48.02, 2.02, 10020, datetime(2024, 1, 1, 12, 0, 10))
        ]
        
        traj = Trajectory(positions=positions, flight_id="TEST_DUP")
        kf = KalmanFilter()
        
        # Ne devrait pas crasher
        smoothed = kf.smooth_trajectory(traj)
        assert len(smoothed) == len(traj)
    
    def test_kalman_with_minimum_points(self):
        """Test avec le minimum de points (2)"""
        positions = [
            Position(48.0, 2.0, 10000, datetime(2024, 1, 1, 12, 0, 0)),
            Position(48.1, 2.1, 11000, datetime(2024, 1, 1, 12, 10, 0))
        ]
        
        traj = Trajectory(positions=positions, flight_id="TEST_MIN")
        kf = KalmanFilter()
        smoothed = kf.smooth_trajectory(traj)
        
        assert len(smoothed) == 2
    
    def test_kalman_with_high_altitude_variation(self):
        """Test avec variations d'altitude importantes"""
        positions = []
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # Simul montée rapide puis descente
        for i in range(50):
            alt = 1000 + i * 200  # Montée
            positions.append(Position(48.0 + i*0.01, 2.0, alt, base_time + timedelta(seconds=i*10)))
        
        for i in range(50):
            alt = 11000 - i * 200  # Descente
            positions.append(Position(48.5 + i*0.01, 2.0, alt, base_time + timedelta(seconds=(50+i)*10)))
        
        traj = Trajectory(positions=positions, flight_id="TEST_CLIMB")
        kf = KalmanFilter()
        smoothed = kf.smooth_trajectory(traj)
        
        # Devrait gérer sans problème
        assert len(smoothed) == len(traj)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
