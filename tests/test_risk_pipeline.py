import pytest

from models.aircraft import Aircraft
from risk_prediction.historical_disruption import (
    compute_historical_disruption_score,
)
from technical_risk.technical_risk import compute_technical_risk


@pytest.fixture
def sample_aircraft():
    return Aircraft(
        aircraft_id="VT-ABC",
        aircraft_type="A320",
        age_years=18,
        emission_factor=0.1,
        technical_failure_rate=0.3,
        avg_tech_delay_min=25,
    )


def test_rule_based_risk_components_match_known_values(sample_aircraft):
    technical_risk = compute_technical_risk(
        sample_aircraft,
        technical_cancellations=1,
    )
    historical_risk = compute_historical_disruption_score(
        past_delays=6,
        past_cancellations=2,
        technical_cancellations=1,
        recent_disruptions=2,
    )

    assert technical_risk == 0.384
    assert historical_risk == 0.458
    assert round(0.6 * technical_risk + 0.4 * historical_risk, 3) == 0.414


def test_rule_based_risks_are_capped_at_one():
    high_risk_aircraft = Aircraft(
        aircraft_id="VT-HIGH",
        aircraft_type="A320",
        age_years=60,
        emission_factor=0.1,
        technical_failure_rate=1,
        avg_tech_delay_min=180,
    )

    technical_risk = compute_technical_risk(
        high_risk_aircraft,
        technical_cancellations=20,
    )
    historical_risk = compute_historical_disruption_score(
        past_delays=100,
        past_cancellations=100,
        technical_cancellations=100,
        recent_disruptions=100,
    )

    assert technical_risk == 1
    assert historical_risk == 1
