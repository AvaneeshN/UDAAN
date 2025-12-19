from models.aircraft import Aircraft

def compute_technical_risk(
    aircraft: Aircraft,
    technical_cancellations: int
) -> float:
    """
    Computes technical risk using unified Aircraft model
    """

    age_risk = min(aircraft.age_years / 30, 1.0)
    failure_risk = min(aircraft.technical_failure_rate, 1.0)
    delay_risk = min(aircraft.avg_tech_delay_min / 60, 1.0)
    disruption_risk = min(technical_cancellations / 5, 1.0)

    technical_risk_score = (
        0.30 * failure_risk +
        0.25 * delay_risk +
        0.25 * age_risk +
        0.20 * disruption_risk
    )

    return round(technical_risk_score, 3)

