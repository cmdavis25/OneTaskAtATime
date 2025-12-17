"""
Unit tests for Elo-based priority system.

Tests the elo_to_effective_priority conversion and band constraints.
"""

import pytest
from src.algorithms.priority import elo_to_effective_priority


class TestEloToEffectivePriority:
    """Test Elo rating conversion to effective priority."""

    def test_high_priority_band_minimum(self):
        """High tasks (base=3) with min Elo (1000) map to 2.0."""
        result = elo_to_effective_priority(3, 1000.0)
        assert result == 2.0

    def test_high_priority_band_maximum(self):
        """High tasks (base=3) with max Elo (2000) map to 3.0."""
        result = elo_to_effective_priority(3, 2000.0)
        assert result == 3.0

    def test_high_priority_band_middle(self):
        """High tasks (base=3) with middle Elo (1500) map to 2.5."""
        result = elo_to_effective_priority(3, 1500.0)
        assert result == 2.5

    def test_medium_priority_band_minimum(self):
        """Medium tasks (base=2) with min Elo (1000) map to 1.0."""
        result = elo_to_effective_priority(2, 1000.0)
        assert result == 1.0

    def test_medium_priority_band_maximum(self):
        """Medium tasks (base=2) with max Elo (2000) map to 2.0."""
        result = elo_to_effective_priority(2, 2000.0)
        assert result == 2.0

    def test_medium_priority_band_middle(self):
        """Medium tasks (base=2) with middle Elo (1500) map to 1.5."""
        result = elo_to_effective_priority(2, 1500.0)
        assert result == 1.5

    def test_low_priority_band_minimum(self):
        """Low tasks (base=1) with min Elo (1000) map to 0.0."""
        result = elo_to_effective_priority(1, 1000.0)
        assert result == 0.0

    def test_low_priority_band_maximum(self):
        """Low tasks (base=1) with max Elo (2000) map to 1.0."""
        result = elo_to_effective_priority(1, 2000.0)
        assert result == 1.0

    def test_low_priority_band_middle(self):
        """Low tasks (base=1) with middle Elo (1500) map to 0.5."""
        result = elo_to_effective_priority(1, 1500.0)
        assert result == 0.5

    def test_elo_clamping_above_maximum(self):
        """Elo values above 2000 are clamped to 2000."""
        result_high = elo_to_effective_priority(3, 2500.0)
        result_normal = elo_to_effective_priority(3, 2000.0)
        assert result_high == result_normal == 3.0

    def test_elo_clamping_below_minimum(self):
        """Elo values below 1000 are clamped to 1000."""
        result_low = elo_to_effective_priority(3, 500.0)
        result_normal = elo_to_effective_priority(3, 1000.0)
        assert result_low == result_normal == 2.0

    def test_band_separation_high_vs_medium(self):
        """Worst High task (Elo=1000) equals best Medium task (Elo=2000) at boundary."""
        worst_high = elo_to_effective_priority(3, 1000.0)
        best_medium = elo_to_effective_priority(2, 2000.0)
        assert worst_high == best_medium == 2.0

    def test_band_separation_medium_vs_low(self):
        """Worst Medium task (Elo=1000) equals best Low task (Elo=2000) at boundary."""
        worst_medium = elo_to_effective_priority(2, 1000.0)
        best_low = elo_to_effective_priority(1, 2000.0)
        assert worst_medium == best_low == 1.0

    def test_invalid_base_priority_zero(self):
        """Invalid base_priority (0) raises ValueError."""
        with pytest.raises(ValueError, match="Invalid base_priority"):
            elo_to_effective_priority(0, 1500.0)

    def test_invalid_base_priority_four(self):
        """Invalid base_priority (4) raises ValueError."""
        with pytest.raises(ValueError, match="Invalid base_priority"):
            elo_to_effective_priority(4, 1500.0)

    def test_invalid_base_priority_negative(self):
        """Invalid base_priority (-1) raises ValueError."""
        with pytest.raises(ValueError, match="Invalid base_priority"):
            elo_to_effective_priority(-1, 1500.0)

    def test_elo_granularity_high_band(self):
        """Verify fine-grained Elo differences map to distinct effective priorities."""
        # Two tasks 10 Elo apart should have different effective priorities
        elo1 = 1500.0
        elo2 = 1510.0
        result1 = elo_to_effective_priority(3, elo1)
        result2 = elo_to_effective_priority(3, elo2)
        assert result2 > result1
        assert abs(result2 - result1) == pytest.approx(0.01, rel=1e-2)


class TestEloSystemProperties:
    """Test mathematical properties of the Elo system."""

    def test_monotonic_increase_within_band(self):
        """Effective priority increases monotonically with Elo within each band."""
        for base_priority in [1, 2, 3]:
            prev_effective = elo_to_effective_priority(base_priority, 1000.0)
            for elo in range(1100, 2001, 100):
                current_effective = elo_to_effective_priority(base_priority, float(elo))
                assert current_effective > prev_effective
                prev_effective = current_effective

    def test_band_isolation(self):
        """All High tasks rank above all Medium tasks, all Medium above all Low."""
        # Lowest High (Elo 1000) >= Highest Medium (Elo 2000)
        assert elo_to_effective_priority(3, 1000.0) >= elo_to_effective_priority(2, 2000.0)

        # Lowest Medium (Elo 1000) >= Highest Low (Elo 2000)
        assert elo_to_effective_priority(2, 1000.0) >= elo_to_effective_priority(1, 2000.0)

        # Any High > Any Medium (except boundary)
        assert elo_to_effective_priority(3, 1001.0) > elo_to_effective_priority(2, 1999.0)

    def test_default_starting_rating(self):
        """Default Elo (1500) places tasks at midpoint of their band."""
        assert elo_to_effective_priority(3, 1500.0) == 2.5  # Middle of [2.0, 3.0]
        assert elo_to_effective_priority(2, 1500.0) == 1.5  # Middle of [1.0, 2.0]
        assert elo_to_effective_priority(1, 1500.0) == 0.5  # Middle of [0.0, 1.0]
