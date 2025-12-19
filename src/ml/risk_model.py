import joblib
import numpy as np

class MLRiskPredictor:
    def __init__(self, model_path="src/ml/model.pkl"):
        self.model = joblib.load(model_path)

    def predict_risk(self, features: np.ndarray) -> float:
        prob = self.model.predict_proba(features.reshape(1, -1))[0][1]
        return round(float(prob), 3)

