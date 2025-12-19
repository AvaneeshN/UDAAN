def compute_technical_risk(
    aircraft_age_years: int,
    technical_failure_rate: float,
    avg_tech_delay_min: int
) -> float:
    age_risk = min(aircraft_age_years / 30, 1.0)
    failure_risk = min(technical_failure_rate, 1.0)
    delay_risk = min(avg_tech_delay_min / 60, 1.0)

    technical_risk_score = (
        0.4 * failure_risk +
        0.35 * age_risk +
        0.25 * delay_risk
    )

    return round(technical_risk_score, 3)

