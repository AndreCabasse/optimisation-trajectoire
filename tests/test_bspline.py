"""
Tests unitaires pour l'optimiseur B-spline
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimization.bspline import BSplineOptimizer
from src.data.data_models import Position, Trajectory


class TestBSplineOptimizer:
    """Tests pour BSplineOptimizer"""
    
    @pytest.fixture
    def simple_trajectory(self):
        """Crée une trajectoire simple"""
        positions = []
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        for i in range(100):
            pos = Position(
                latitude=48.0 + i * 0.01,
                longitude=2.0 + i * 0.01,
                altitude=10000.0,
                timestamp=base_time + timedelta(seconds=i*10)
            )
            positions.append(pos)
        
        return Trajectory(positions=positions, flight_id="TEST001")
    
    def test_bspline_initialization(self):
        """Test de l'initialisation"""
        bs = BSplineOptimizer(degree=3, smoothing_factor=0.5)
        
        assert bs.degree == 3
        assert bs.smoothing_factor == 0.5
        assert bs.splines is None  # Pas encore fitted
    
    def test_bspline_fit(self, simple_trajectory):
        """Test du fit"""
        bs = BSplineOptimizer()
        bs.fit(simple_trajectory)
        
        assert bs.splines is not None
        assert len(bs.splines) == 3  # x, y, z
        assert bs.t_min is not None
        assert bs.t_max is not None
    
    def test_bspline_evaluate_same_length(self, simple_trajectory):
        """Évaluation avec même nombre de points"""
        bs = BSplineOptimizer()
        bs.fit(simple_trajectory)
        
        evaluated = bs.evaluate(simple_trajectory, num_points=len(simple_trajectory))
        
        assert len(evaluated) == len(simple_trajectory)
    
    def test_bspline_optimize_reduces_points(self, simple_trajectory):
        """Test de réduction de points"""
        bs = BSplineOptimizer()
        optimized = bs.optimize(simple_trajectory, target_points=50)
        
        assert len(optimized) == 50
        assert len(optimized) < len(simple_trajectory)
    
    def test_bspline_preserves_endpoints(self, simple_trajectory):
        """Vérifie la préservation des extrémités"""
        bs = BSplineOptimizer()
        optimized = bs.optimize(simple_trajectory, target_points=50)
        
        # Premier point
        orig_start = simple_trajectory.positions[0]
        opt_start = optimized.positions[0]
        
        # Tolérance plus large car interpolation
        assert abs(orig_start.latitude - opt_start.latitude) < 0.01
        assert abs(orig_start.longitude - opt_start.longitude) < 0.01
        
        # Dernier point
        orig_end = simple_trajectory.positions[-1]
        opt_end = optimized.positions[-1]
        
        assert abs(orig_end.latitude - opt_end.latitude) < 0.01
        assert abs(orig_end.longitude - opt_end.longitude) < 0.01
    
    def test_bspline_smooth_trajectory(self, simple_trajectory):
        """Vérifie que la trajectoire est lisse"""
        bs = BSplineOptimizer(smoothing_factor=0.5)
        optimized = bs.optimize(simple_trajectory, target_points=50)
        
        # Calculer les variations d'accélération
        coords = optimized.get_cartesian_array()
        first_diff = np.diff(coords, axis=0)
        second_diff = np.diff(first_diff, axis=0)
        
        # Les différences secondes doivent être petites (trajectoire lisse)
        max_accel = np.max(np.linalg.norm(second_diff, axis=1))
        assert max_accel < 1000  # Valeur arbitraire raisonnable
    
    def test_bspline_with_different_degrees(self, simple_trajectory):
        """Test avec différents degrés"""
        for degree in [1, 2, 3, 5]:
            bs = BSplineOptimizer(degree=degree)
            optimized = bs.optimize(simple_trajectory, target_points=50)
            
            assert len(optimized) == 50
    
    def test_bspline_minimum_points(self):
        """Test avec nombre minimal de points"""
        positions = [
            Position(48.0, 2.0, 10000, datetime(2024, 1, 1, 12, 0, 0)),
            Position(48.1, 2.1, 10000, datetime(2024, 1, 1, 12, 1, 0)),
            Position(48.2, 2.2, 10000, datetime(2024, 1, 1, 12, 2, 0)),
            Position(48.3, 2.3, 10000, datetime(2024, 1, 1, 12, 3, 0)),
        ]
        
        traj = Trajectory(positions=positions, flight_id="TEST_MIN")
        bs = BSplineOptimizer(degree=3)
        
        # Devrait fonctionner même avec peu de points
        optimized = bs.optimize(traj, target_points=10)
        assert len(optimized) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
