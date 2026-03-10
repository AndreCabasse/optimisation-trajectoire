"""
Tests pour les modèles de données
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.data_models import Position, Trajectory


class TestPosition:
    """Tests pour Position"""
    
    def test_position_creation(self):
        """Test création d'une position"""
        pos = Position(
            latitude=48.8566,
            longitude=2.3522,
            altitude=10000,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert pos.latitude == 48.8566
        assert pos.longitude == 2.3522
        assert pos.altitude == 10000
    
    def test_position_to_cartesian(self):
        """Test conversion en coordonnées cartésiennes"""
        pos = Position(
            latitude=48.0,
            longitude=2.0,
            altitude=10000,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        cart = pos.to_cartesian()
        
        assert cart.shape == (3,)
        assert cart[2] == 10000  # Altitude directe


class TestTrajectory:
    """Tests pour Trajectory"""
    
    @pytest.fixture
    def simple_trajectory(self):
        """Crée une trajectoire simple"""
        positions = []
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        for i in range(10):
            pos = Position(
                latitude=48.0 + i * 0.01,
                longitude=2.0 + i * 0.01,
                altitude=10000 + i * 100,
                timestamp=base_time + timedelta(seconds=i*60)
            )
            positions.append(pos)
        
        return Trajectory(positions=positions, flight_id="TEST001")
    
    def test_trajectory_creation(self, simple_trajectory):
        """Test création trajectoire"""
        assert len(simple_trajectory) == 10
        assert simple_trajectory.flight_id == "TEST001"
    
    def test_trajectory_duration(self, simple_trajectory):
        """Test calcul durée"""
        duration = simple_trajectory.duration
        assert duration == 9 * 60  # 9 intervalles de 60s
    
    def test_trajectory_get_coordinates_array(self, simple_trajectory):
        """Test extraction coordonnées"""
        coords = simple_trajectory.get_coordinates_array()
        
        assert coords.shape == (10, 3)
        assert coords[0, 0] == 48.0  # Première latitude
    
    def test_trajectory_get_cartesian_array(self, simple_trajectory):
        """Test extraction cartésienne"""
        cart = simple_trajectory.get_cartesian_array()
        
        assert cart.shape == (10, 3)
    
    def test_trajectory_validation_minimum_points(self):
        """Test validation minimum de points"""
        with pytest.raises(ValueError):
            Trajectory(positions=[
                Position(48.0, 2.0, 10000, datetime.now())
            ])  # Seulement 1 point
    
    def test_trajectory_subset(self, simple_trajectory):
        """Test extraction sous-ensemble"""
        subset = simple_trajectory.subset(2, 5)
        
        assert len(subset) == 3  # Indices 2, 3, 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
