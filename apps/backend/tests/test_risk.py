"""Risk engine unit tests."""
import pytest
from services.risk_service import calculate_lot_size, apply_dynamic_scaling


def test_lot_size_calculation():
    # $10,000 account, 2% risk, 10 pip SL, EURUSD
    lot = calculate_lot_size(10_000, 10, "EURUSD", 0.02)
    # Expected: 10000 * 0.02 / (10 * 10) = 2.0
    assert lot == 2.0


def test_lot_size_minimum():
    # Small account should produce minimum 0.01 lot
    lot = calculate_lot_size(100, 50, "EURUSD", 0.01)
    assert lot >= 0.01


def test_dynamic_scaling_wins():
    # After 3 consecutive wins, risk should increase
    risk = apply_dynamic_scaling(0.02, consecutive_wins=3, consecutive_losses=0)
    assert risk > 0.02


def test_dynamic_scaling_losses():
    # After 3 consecutive losses, risk should decrease
    risk = apply_dynamic_scaling(0.02, consecutive_wins=0, consecutive_losses=3)
    assert risk < 0.02


def test_dynamic_scaling_cap():
    # Risk never exceeds 3% regardless of wins
    risk = apply_dynamic_scaling(0.02, consecutive_wins=100, consecutive_losses=0)
    assert risk <= 0.03


def test_dynamic_scaling_floor():
    # Risk never falls below 0.5% regardless of losses
    risk = apply_dynamic_scaling(0.02, consecutive_wins=0, consecutive_losses=100)
    assert risk >= 0.005
