"""
Tests unitaires pour le TrajectoryOptimizer
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod
from src.data.data_models import Position, Trajectory


class TestTrajectoryOptimizer:
    """Tests pour TrajectoryOptimizer"""
    
    @pytest.fixture
    def sample_trajectory(self):
        """Crée une trajectoire test"""
        positions = []
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        for i in range(100):
            pos = Position(
                latitude=48.0 + i * 0.01,
                longitude=2.0 + i * 0.01,
                altitude=10000 + i * 10,
                timestamp=base_time + timedelta(seconds=i*10)
            )
            positions.append(pos)
        
        return Trajectory(positions=positions, flight_id="TEST001")
    
    def test_optimizer_kalman(self, sample_trajectory):
        """Test méthode Kalman"""
        opt = TrajectoryOptimizer(method=OptimizationMethod.KALMAN)
        result = opt.optimize(sample_trajectory)
        
        assert result is not None
        assert result.method == "kalman"
        assert len(result.optimized_positions) == len(sample_trajectory)
        assert 'compression_ratio' in result.metrics
        assert 'smoothness' in result.metrics
    
    def test_optimizer_bspline(self, sample_trajectory):
        """Test méthode B-spline"""
        opt = TrajectoryOptimizer(method=OptimizationMethod.BSPLINE)
        result = opt.optimize(sample_trajectory, target_points=50)
        
        assert result is not None
        assert result.method == "bspline"
        assert len(result.optimized_positions) == 50
    
    def test_optimizer_hybrid(self, sample_trajectory):
        """Test méthode Hybride"""
        opt = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
        result = opt.optimize(sample_trajectory, target_points=50)
        
        assert result is not None
        assert result.method == "hybrid"
        assert len(result.optimized_positions) == 50
    
    def test_optimizer_metrics_present(self, sample_trajectory):
        """Vérifie que toutes les métriques sont présentes"""
        opt = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
        result = opt.optimize(sample_trajectory, target_points=50)
        
        required_metrics = [
            'compression_ratio',
            'smoothness',
            'original_smoothness',
            'distance_original',
            'distance_optimized',
            'distance_change_percent'
        ]
        
        for metric in required_metrics:
            assert metric in result.metrics, f"Missing metric: {metric}"
    
    def test_optimizer_compression_ratio(self, sample_trajectory):
        """Vérifie le calcul du taux de compression"""
        opt = TrajectoryOptimizer(method=OptimizationMethod.BSPLINE)
        result = opt.optimize(sample_trajectory, target_points=50)
        
        expected_ratio = 50 / len(sample_trajectory)
        assert abs(result.metrics['compression_ratio'] - expected_ratio) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
