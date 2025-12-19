# src/ml/train_model.py
import numpy as np
from sklearn.linear_model import LogisticRegression
import joblib

# Dummy historical data (later replaced with real data)
X = np.array([
    [18, 0.3, 25, 7.5, 6, 2, 1, 2],
    [5, 0.1, 5, 4.0, 1, 0, 0, 0],
    [22, 0.5, 40, 9.0, 8, 3, 2, 4]
])

y = [1, 0, 1]  # 1 = disrupted, 0 = normal

model = LogisticRegression()
model.fit(X, y)

joblib.dump(model, "src/ml/model.pkl")
