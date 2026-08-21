from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression

from ml.features import FEATURE_NAMES
from ml.model_contract import MODEL_SCHEMA_VERSION, TRAINING_DATA_SOURCE


DEFAULT_MODEL_PATH = Path(__file__).with_name("model.pkl")

DEMO_FEATURES = np.array([
    [18, 0.3, 25, 7.5, 6, 2, 1, 2],
    [5, 0.1, 5, 4.0, 1, 0, 0, 0],
    [22, 0.5, 40, 9.0, 8, 3, 2, 4],
], dtype=float)
DEMO_LABELS = np.array([1, 0, 1], dtype=int)


def train_demo_model(
    output_path: str | Path = DEFAULT_MODEL_PATH,
) -> Path:
    """Build the deterministic demo artifact used for integration tests."""
    if DEMO_FEATURES.shape[1] != len(FEATURE_NAMES):
        raise ValueError(
            "Training features do not match the ML feature contract"
        )

    model = LogisticRegression(
        solver="liblinear",
        random_state=42,
        max_iter=1000,
    )
    model.fit(DEMO_FEATURES, DEMO_LABELS)

    artifact = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "feature_names": FEATURE_NAMES,
        "sklearn_version": sklearn.__version__,
        "training_data_source": TRAINING_DATA_SOURCE,
        "model": model,
    }

    resolved_path = Path(output_path)
    joblib.dump(artifact, resolved_path)
    return resolved_path


if __name__ == "__main__":
    model_path = train_demo_model()
    print(f"Demo ML model written to {model_path}")
