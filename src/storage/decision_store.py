import sqlite3
import json

class DecisionStore:
    def __init__(self, db_path="decision_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_id TEXT,
            recommended_action TEXT,
            raw_scores TEXT,
            normalized_scores TEXT,
            explanation TEXT,
            technical_risk REAL,
            historical_disruption REAL,
            overall_risk REAL,
            decision_time TEXT
        )
        """)

        conn.commit()
        conn.close()

    def save(self, result):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO decisions (
            flight_id,
            recommended_action,
            raw_scores,
            normalized_scores,
            explanation,
            technical_risk,
            historical_disruption,
            overall_risk,
            decision_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.flight_id,
            result.recommended_action,
            json.dumps(result.raw_scores),
            json.dumps(result.normalized_scores),
            json.dumps(result.explanation),
            result.explanation["technical_risk"],
            result.explanation["historical_disruption"],
            result.explanation["overall_operational_risk"],
            result.decision_time.isoformat()
        ))

        conn.commit()
        conn.close()
