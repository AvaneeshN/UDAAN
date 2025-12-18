def compute_technical_risk(
    aircraft_age_years,
    recent_technical_issues,
    maintenance_delay_count,
    past_flight_disruptions
):
    age_risk = min(aircraft_age_years / 30, 1.0)
    issue_risk = min(recent_technical_issues / 5, 1.0)
    maintenance_risk = min(maintenance_delay_count / 4, 1.0)
    disruption_risk = min(past_flight_disruptions / 6, 1.0)

    technical_risk_score = (
        0.35 * issue_risk +
        0.25 * maintenance_risk +
        0.20 * age_risk +
        0.20 * disruption_risk
    )

    return round(technical_risk_score, 3)
