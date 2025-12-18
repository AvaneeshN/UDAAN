def compute_historical_disruption_score(
    past_delays,
    past_cancellations,
    technical_cancellations,
    recent_disruptions
):
    """
    Returns a normalized disruption score between 0 and 1.
    """

    delay_score = min(past_delays / 10, 1.0)
    cancellation_score = min(past_cancellations / 5, 1.0)
    technical_cancel_score = min(technical_cancellations / 3, 1.0)
    recent_score = min(recent_disruptions / 4, 1.0)

    disruption_score = (
        0.30 * delay_score +
        0.30 * cancellation_score +
        0.25 * technical_cancel_score +
        0.15 * recent_score
    )

    return round(disruption_score, 3)
