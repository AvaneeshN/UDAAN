CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    raw_scores TEXT NOT NULL,
    normalized_scores TEXT NOT NULL,
    explanation TEXT NOT NULL,
    technical_risk REAL,
    historical_disruption REAL,
    overall_risk REAL,
    decision_time TEXT NOT NULL
);
